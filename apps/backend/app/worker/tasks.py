from __future__ import annotations

import structlog

import app.domains.handlers  # noqa: F401  (registers outbox handlers)
from app.core.db import session_scope
from app.domains.billing.service import entitlements
from app.domains.platform import idempotency, outbox
from app.models import import_all
from app.worker.celery_app import celery

import_all()
log = structlog.get_logger(__name__)


@celery.task(name="app.worker.tasks.dispatch_outbox", ignore_result=True)
def dispatch_outbox() -> dict[str, int]:
    stats = outbox.dispatch_batch()
    if any(stats.values()):
        log.info("outbox_dispatched", **stats)
    return stats


@celery.task(name="app.worker.tasks.release_expired_usage", ignore_result=True)
def release_expired_usage() -> int:
    with session_scope() as db:
        n = entitlements.release_expired(db)
    if n:
        log.info("usage_reservations_expired", count=n)
    return n


@celery.task(name="app.worker.tasks.cleanup_media_uploads", ignore_result=True)
def cleanup_media_uploads() -> int:
    from app.domains.media.service import cleanup_expired_uploads

    with session_scope() as db:
        return cleanup_expired_uploads(db)


@celery.task(name="app.worker.tasks.purge_idempotency", ignore_result=True)
def purge_idempotency() -> int:
    with session_scope() as db:
        return idempotency.purge_expired(db)
