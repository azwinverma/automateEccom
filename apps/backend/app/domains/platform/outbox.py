"""Transactional outbox (FND-012).

``publish`` writes the event row in the caller's transaction. The dispatcher (Celery beat, every few
seconds) claims due rows with ``FOR UPDATE SKIP LOCKED`` so multiple workers never double-claim, and
runs registered handlers. Each handler's side effects commit together with an OutboxConsumption row,
which makes handlers effectively exactly-once even when an event is retried after a partial failure.
Failed events back off exponentially; after ``outbox_max_attempts`` they move to ``dead`` (the DLQ),
visible and replayable from the admin console.
"""

from __future__ import annotations

import json
import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from typing import Any

import jsonschema
import structlog
from opentelemetry import propagate
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import CONTRACTS_DIR, get_settings
from app.core.db import session_factory, utcnow
from app.core.errors import NotFound
from app.core.ids import uuid7
from app.core.metrics import OUTBOX_DISPATCH, OUTBOX_PENDING
from app.domains.platform.models import OutboxConsumption, OutboxEvent

log = structlog.get_logger(__name__)

Handler = Callable[[Session, OutboxEvent], None]


@dataclass(frozen=True)
class _Registration:
    name: str
    fn: Handler


_HANDLERS: dict[str, list[_Registration]] = {}


def handler(event_type: str, name: str | None = None) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        reg = _Registration(name or f"{fn.__module__}.{fn.__name__}", fn)
        regs = _HANDLERS.setdefault(event_type, [])
        if all(r.name != reg.name for r in regs):
            regs.append(reg)
        return fn

    return deco


def registered_handlers(event_type: str) -> list[_Registration]:
    return list(_HANDLERS.get(event_type, []))


@lru_cache
def catalog() -> dict[str, Any]:
    path = CONTRACTS_DIR / "event-catalog.json"
    with path.open() as f:
        data: dict[str, Any] = json.load(f)
    return {e["type"]: e for e in data["events"]}


class UnknownEventType(ValueError):
    pass


def publish(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str | uuid.UUID,
    payload: dict[str, Any],
    merchant_id: uuid.UUID | None,
    delay_seconds: int = 0,
) -> OutboxEvent:
    spec = catalog().get(event_type)
    if spec is None:
        raise UnknownEventType(f"{event_type} is not declared in packages/contracts/event-catalog.json")
    jsonschema.validate(payload, spec["payload_schema"])
    headers: dict[str, str] = {}
    propagate.inject(headers)  # W3C trace context so the worker span links to the request span
    ev = OutboxEvent(
        id=uuid7(),
        merchant_id=merchant_id,
        event_type=event_type,
        event_version=spec.get("version", 1),
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=payload,
        headers=headers,
        available_at=utcnow() + timedelta(seconds=delay_seconds),
    )
    db.add(ev)
    return ev


def backoff_seconds(attempts: int) -> float:
    base: float = min(2**attempts, 3600)
    return base / 2 + random.uniform(0, base / 2)  # noqa: S311 - jitter, not crypto


def dispatch_batch(limit: int | None = None) -> dict[str, int]:
    """Claim and process due events. Safe to run concurrently on many workers."""
    s = get_settings()
    limit = limit or s.outbox_batch_size
    stats = {"dispatched": 0, "retried": 0, "dead": 0}
    session_cls = session_factory()

    with session_cls() as claim_db:
        ids = list(
            claim_db.scalars(
                select(OutboxEvent.id)
                .where(OutboxEvent.status == "pending", OutboxEvent.available_at <= utcnow())
                .order_by(OutboxEvent.available_at)
                .limit(limit)
            )
        )

    for event_id in ids:
        outcome = _process_one(event_id)
        if outcome:
            stats[outcome] += 1

    with session_cls() as db:
        OUTBOX_PENDING.set(
            db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "pending"))
            or 0
        )
    return stats


def _process_one(event_id: uuid.UUID) -> str | None:
    s = get_settings()
    with session_factory()() as db:
        ev = db.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.id == event_id,
                OutboxEvent.status == "pending",
                OutboxEvent.available_at <= utcnow(),
            )
            .with_for_update(skip_locked=True)
        )
        if ev is None:  # claimed by another worker or already done
            return None
        failures: list[str] = []
        for reg in registered_handlers(ev.event_type):
            if db.get(OutboxConsumption, (ev.id, reg.name)) is not None:
                continue
            sp = db.begin_nested()
            try:
                reg.fn(db, ev)
                db.execute(
                    pg_insert(OutboxConsumption)
                    .values(event_id=ev.id, handler=reg.name, consumed_at=utcnow())
                    .on_conflict_do_nothing()
                )
                sp.commit()
            except Exception as exc:
                sp.rollback()
                failures.append(f"{reg.name}: {type(exc).__name__}: {exc}"[:500])
                log.warning(
                    "outbox_handler_failed",
                    event_type=ev.event_type,
                    handler=reg.name,
                    event_id=str(ev.id),
                    error_type=type(exc).__name__,
                )
        if failures:
            ev.attempts += 1
            ev.last_error = "\n".join(failures)[:4000]
            if ev.attempts >= s.outbox_max_attempts:
                ev.status = "dead"
                outcome = "dead"
                log.error("outbox_event_dead", event_type=ev.event_type, event_id=str(ev.id))
            else:
                ev.available_at = utcnow() + timedelta(seconds=backoff_seconds(ev.attempts))
                outcome = "retried"
        else:
            ev.status = "dispatched"
            ev.dispatched_at = utcnow()
            outcome = "dispatched"
        event_type = ev.event_type
        db.commit()
        OUTBOX_DISPATCH.labels(event_type, outcome).inc()
        return outcome


def requeue(db: Session, event_id: uuid.UUID) -> OutboxEvent:
    """Replay a dead/failed event (admin action; caller audits)."""
    ev = db.get(OutboxEvent, event_id)
    if ev is None:
        raise NotFound()
    ev.status = "pending"
    ev.available_at = utcnow()
    ev.attempts = 0
    ev.last_error = None
    return ev
