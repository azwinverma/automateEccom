"""Operational state for monitoring (spec 16 dashboards & alerts; DoD "Operations").

`collect()` refreshes platform-wide gauges from the database and Redis. It runs when the API's /metrics
endpoint is scraped, at most once every CACHE_S seconds, so a scrape every 15 s costs a handful of
aggregate queries. Each gauge is computed independently: one failing query is counted in
ops_collect_errors_total and never breaks the scrape.

`job()` wraps scheduled jobs: duration + outcome counters in the worker, and a last-success heartbeat in
Redis that the API exposes as job_last_success_timestamp_seconds (so "job hasn't run" can alert).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import metrics as M  # noqa: N812  (short alias keeps the gauge table readable)
from app.core.db import utcnow

log = structlog.get_logger(__name__)

CACHE_S = 15.0
QUEUES = ("default", "outbox", "ai", "media")
JOBS = (
    "nightly_intelligence",
    "reconcile_twin",
    "reconcile_channels",
    "sync_cod_settlements",
    "dispatch_outbox",
)
_lock = threading.Lock()
_last = 0.0


def _age(oldest: Any) -> float:
    return max(0.0, (utcnow() - oldest).total_seconds()) if oldest else 0.0


def _gauges() -> list[tuple[str, Callable[[Session], None]]]:
    from app.domains.catalog.models import Product, Variant
    from app.domains.channels.models import ChannelConnection, ChannelListing, WebhookEvent
    from app.domains.content.models import ContentPost
    from app.domains.fulfillment.models import LIVE_STATUSES, Shipment
    from app.domains.intelligence.models import ProductIntelligenceProfile, Recommendation
    from app.domains.payments.models import CODRecord
    from app.domains.platform.models import OutboxEvent
    from app.domains.returns.models import Refund
    from app.domains.twin.models import StoreTwinSection

    def q(db: Session, stmt: Any) -> Any:
        return db.execute(stmt.execution_options(skip_tenant_filter=True)).one()

    def outbox(db: Session) -> None:
        n, oldest = q(
            db, select(func.count(), func.min(OutboxEvent.created_at)).where(OutboxEvent.status == "pending")
        )
        M.OUTBOX_PENDING.set(n or 0)
        M.OUTBOX_OLDEST_PENDING.set(_age(oldest))
        M.OUTBOX_DEAD.set(
            q(db, select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "dead"))[0] or 0
        )

    def webhooks(db: Session) -> None:
        n, oldest = q(
            db,
            select(func.count(), func.min(WebhookEvent.received_at)).where(
                WebhookEvent.status.in_(("received", "failed"))
            ),
        )
        M.WEBHOOK_UNPROCESSED.set(n or 0)
        M.WEBHOOK_OLDEST_UNPROCESSED.set(_age(oldest))
        M.WEBHOOK_DEAD.set(
            q(db, select(func.count()).select_from(WebhookEvent).where(WebhookEvent.status == "dead"))[0] or 0
        )

    def publishing(db: Session) -> None:
        M.CONNECTIONS_NEED_ATTENTION.set(
            q(
                db,
                select(func.count())
                .select_from(ChannelConnection)
                .where(ChannelConnection.status.in_(("expired", "revoked", "error"))),
            )[0]
            or 0
        )
        M.LISTINGS_FAILED.set(
            q(
                db,
                select(func.count())
                .select_from(ChannelListing)
                .where(ChannelListing.status.in_(("failed", "out_of_sync"))),
            )[0]
            or 0
        )
        M.POSTS_FAILED.set(
            q(db, select(func.count()).select_from(ContentPost).where(ContentPost.status == "failed"))[0] or 0
        )

    def money(db: Session) -> None:
        M.REFUNDS_FAILED.set(
            q(db, select(func.count()).select_from(Refund).where(Refund.status == "failed"))[0] or 0
        )
        M.COD_SETTLEMENT_OVERDUE.set(
            q(
                db,
                select(func.count())
                .select_from(CODRecord)
                .where(
                    CODRecord.status.in_(("delivered", "cash_collected", "settlement_pending")),
                    CODRecord.updated_at < utcnow() - timedelta(days=7),
                ),
            )[0]
            or 0
        )

    def shipments(db: Session) -> None:
        M.SHIPMENTS_STUCK.set(
            q(
                db,
                select(func.count())
                .select_from(Shipment)
                .where(
                    Shipment.status.in_(LIVE_STATUSES), Shipment.updated_at < utcnow() - timedelta(days=3)
                ),
            )[0]
            or 0
        )

    def intelligence(db: Session) -> None:
        for name, oldest in db.execute(
            select(StoreTwinSection.section, func.min(StoreTwinSection.as_of))
            .group_by(StoreTwinSection.section)
            .execution_options(skip_tenant_filter=True)
        ).all():
            M.TWIN_SECTION_MAX_AGE.labels(name).set(_age(oldest))
        M.PRODUCT_BRAIN_MAX_AGE.set(_age(q(db, select(func.min(ProductIntelligenceProfile.as_of)))[0]))
        total, missing = q(
            db,
            select(func.count(), func.count().filter(Variant.cost_minor.is_(None)))
            .select_from(Variant)
            .join(Product, Product.id == Variant.product_id)
            .where(Variant.status == "active", Product.status == "active"),
        )
        M.VARIANTS_WITHOUT_COST_RATIO.set((missing or 0) / total if total else 0)
        M.RECOMMENDATIONS_OPEN.set(
            q(db, select(func.count()).select_from(Recommendation).where(Recommendation.status == "open"))[0]
            or 0
        )
        M.RECOMMENDATIONS_EXPIRED_7D.set(
            q(
                db,
                select(func.count())
                .select_from(Recommendation)
                .where(
                    Recommendation.status == "expired",
                    Recommendation.updated_at >= utcnow() - timedelta(days=7),
                ),
            )[0]
            or 0
        )

    return [
        ("outbox", outbox),
        ("webhooks", webhooks),
        ("publishing", publishing),
        ("money", money),
        ("shipments", shipments),
        ("intelligence", intelligence),
    ]


def _redis_gauges() -> None:
    from app.core.redis import get_redis

    r = get_redis()
    for name in QUEUES:
        try:
            M.QUEUE_BACKLOG.labels(name).set(r.llen(name))
        except Exception:
            M.OPS_COLLECT_ERRORS.labels(f"queue:{name}").inc()
    for job_name in JOBS:
        try:
            v = r.get(f"ops:job:{job_name}:last_success")
            if v is not None:
                M.JOB_LAST_SUCCESS.labels(job_name).set(float(v))
        except Exception:
            M.OPS_COLLECT_ERRORS.labels(f"job:{job_name}").inc()


def collect(force: bool = False) -> None:
    """Refresh the operational gauges (cached; safe to call on every scrape)."""
    from app.core.db import session_factory

    global _last
    with _lock:
        if not force and time.monotonic() - _last < CACHE_S:
            return
        _last = time.monotonic()
    with session_factory()() as db:
        for name, fn in _gauges():
            try:
                fn(db)
            except Exception:
                db.rollback()
                M.OPS_COLLECT_ERRORS.labels(name).inc()
                log.warning("ops_gauge_failed", gauge=name)
    try:
        _redis_gauges()
    except Exception:
        M.OPS_COLLECT_ERRORS.labels("redis").inc()


@contextmanager
def job(name: str) -> Iterator[None]:
    """Job health: duration, outcome, and a last-success heartbeat the API can alert on."""
    from app.core.redis import get_redis

    start = time.monotonic()
    try:
        yield
    except Exception:
        M.JOB_RUNS.labels(name, "failure").inc()
        raise
    finally:
        M.JOB_DURATION.labels(name).observe(time.monotonic() - start)
    M.JOB_RUNS.labels(name, "success").inc()
    try:
        get_redis().set(f"ops:job:{name}:last_success", str(time.time()))
    except Exception:
        log.warning("job_heartbeat_failed", job=name)


def tracked(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator form of job() for Celery tasks (place it under @celery.task)."""
    import functools

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*a: Any, **kw: Any) -> Any:
            with job(name):
                return fn(*a, **kw)

        return wrapper

    return deco
