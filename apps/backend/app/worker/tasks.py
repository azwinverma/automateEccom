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


@celery.task(name="app.worker.tasks.run_studio_job", ignore_result=True, acks_late=True)
def run_studio_job(job_id: str) -> None:
    import uuid

    from app.domains.studio.service import run_job

    run_job(uuid.UUID(job_id))


@celery.task(name="app.worker.tasks.requeue_stale_studio_jobs", ignore_result=True)
def requeue_stale_studio_jobs() -> int:
    from app.domains.studio.service import requeue_stale

    with session_scope() as db:
        return requeue_stale(db)


@celery.task(name="app.worker.tasks.refresh_channel_tokens", ignore_result=True)
def refresh_channel_tokens() -> dict[str, int]:
    from app.domains.channels.service import refresh_due_tokens

    with session_scope() as db:
        stats = refresh_due_tokens(db)
    if any(stats.values()):
        log.info("channel_tokens_refreshed", **stats)
    return stats


@celery.task(name="app.worker.tasks.reconcile_channels", ignore_result=True)
def reconcile_channels() -> dict[str, int]:
    from app.domains.channels.service import reconcile_all

    with session_scope() as db:
        stats = reconcile_all(db)
    log.info("channels_reconciled", **stats)
    return stats


@celery.task(name="app.worker.tasks.publish_due_content", ignore_result=True)
def publish_due_content() -> dict[str, int]:
    from app.domains.content.service import publish_due

    with session_scope() as db:
        stats = publish_due(db)
    if any(stats.values()):
        log.info("content_published", **stats)
    return stats


@celery.task(name="app.worker.tasks.run_video_job", ignore_result=True, acks_late=True)
def run_video_job(job_id: str) -> None:
    import uuid

    from app.domains.media.video import run_job

    run_job(uuid.UUID(job_id))


@celery.task(name="app.worker.tasks.purge_idempotency", ignore_result=True)
def purge_idempotency() -> int:
    with session_scope() as db:
        return idempotency.purge_expired(db)
