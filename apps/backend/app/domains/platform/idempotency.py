"""Idempotency service (FND-013).

Two entry points:
* ``begin``/``complete``/``abandon`` — HTTP handlers with an ``Idempotency-Key`` header.
  ``begin`` inserts an ``in_progress`` record in its *own* committed transaction so a concurrent
  duplicate sees it immediately (409). ``complete`` stores the response in the business transaction,
  so the stored response exists iff the business change committed. ``abandon`` deletes the marker
  after a failure so the client may retry.
* ``run_once`` — workers/webhooks: executes a callable at most once per (owner, scope, key), inside
  the caller's transaction (the marker and the side effects commit or roll back together).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import session_factory, utcnow
from app.core.errors import AppError, Conflict, ValidationFailed
from app.core.metrics import IDEMPOTENCY_REPLAYS
from app.domains.platform.models import IdempotencyRecord

T = TypeVar("T")
DEFAULT_TTL = timedelta(hours=24)
IN_PROGRESS_STALE_AFTER = timedelta(minutes=5)


class IdempotencyKeyReused(AppError):
    status_code = 422
    code = "idempotency_key_reused"
    message = "This Idempotency-Key was already used with a different request"


def request_fingerprint(body: Any) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def validate_key(key: str) -> str:
    if not (8 <= len(key) <= 128) or not key.isprintable() or " " in key:
        raise ValidationFailed(
            "Idempotency-Key must be 8-128 printable characters without spaces",
            details={"fields": [{"loc": ["header", "Idempotency-Key"]}]},
        )
    return key


@dataclass
class Replay:
    status: int
    body: Any


@dataclass
class Claim:
    record_id: uuid.UUID
    owner: str
    scope: str
    key: str


def begin(owner: str, scope: str, key: str, fingerprint: str) -> Claim | Replay:
    validate_key(key)
    with session_factory()() as db:
        now = utcnow()
        inserted = db.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=uuid.uuid4(),
                owner=owner,
                scope=scope,
                key=key,
                request_hash=fingerprint,
                status="in_progress",
                expires_at=now + DEFAULT_TTL,
                created_at=now,
            )
            .on_conflict_do_nothing(index_elements=["owner", "scope", "key"])
            .returning(IdempotencyRecord.id)
        ).scalar_one_or_none()
        if inserted is not None:
            db.commit()
            return Claim(inserted, owner, scope, key)
        rec = db.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.owner == owner,
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key == key,
            )
            .with_for_update()
        )
        if rec is None:  # deleted between insert attempt and select (abandoned) — let client retry
            raise Conflict("Please retry the request", code="idempotency_in_progress")
        if rec.request_hash != fingerprint:
            raise IdempotencyKeyReused()
        if rec.status == "completed":
            IDEMPOTENCY_REPLAYS.labels(scope).inc()
            return Replay(rec.response_status or 200, rec.response_body)
        if now - rec.created_at > IN_PROGRESS_STALE_AFTER:
            rec.created_at = now  # previous attempt crashed without abandoning; take over
            db.commit()
            return Claim(rec.id, owner, scope, key)
        raise Conflict(
            "A request with this Idempotency-Key is still in progress", code="idempotency_in_progress"
        )


def complete(db: Session, claim: Claim, status: int, body: Any) -> None:
    rec = db.get(IdempotencyRecord, claim.record_id)
    if rec is None:  # pragma: no cover - abandoned concurrently
        return
    rec.status = "completed"
    rec.response_status = status
    rec.response_body = body
    rec.completed_at = utcnow()


def abandon(claim: Claim) -> None:
    with session_factory()() as db:
        db.execute(
            delete(IdempotencyRecord).where(
                IdempotencyRecord.id == claim.record_id, IdempotencyRecord.status == "in_progress"
            )
        )
        db.commit()


def run_once[T](db: Session, owner: str, scope: str, key: str, fn: Callable[[], T]) -> tuple[bool, T | None]:
    """Run ``fn`` in ``db``'s transaction at most once per key. Returns (executed, result)."""
    now = utcnow()
    inserted = db.execute(
        pg_insert(IdempotencyRecord)
        .values(
            id=uuid.uuid4(),
            owner=owner,
            scope=scope,
            key=key,
            request_hash="-",
            status="completed",
            created_at=now,
            completed_at=now,
            expires_at=now + timedelta(days=30),
        )
        .on_conflict_do_nothing(index_elements=["owner", "scope", "key"])
        .returning(IdempotencyRecord.id)
    ).scalar_one_or_none()
    if inserted is None:
        return False, None
    return True, fn()


def purge_expired(db: Session) -> int:
    res = db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.expires_at < utcnow()))
    return int(getattr(res, "rowcount", 0) or 0)
