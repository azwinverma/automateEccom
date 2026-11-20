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


@celery.task(name="app.worker.tasks.release_expired_stock", ignore_result=True)
def release_expired_stock() -> int:
    from app.domains.inventory.service import release_expired

    with session_scope() as db:
        return release_expired(db)


@celery.task(name="app.worker.tasks.poll_shipments", ignore_result=True)
def poll_shipments() -> dict[str, int]:
    from app.domains.fulfillment.service import poll_due

    with session_scope() as db:
        stats = poll_due(db)
    if any(stats.values()):
        log.info("shipments_polled", **stats)
    return stats


@celery.task(name="app.worker.tasks.escalate_delivery_recoveries", ignore_result=True)
def escalate_delivery_recoveries() -> int:
    from app.domains.fulfillment.service import escalate_stale

    with session_scope() as db:
        return escalate_stale(db)


@celery.task(name="app.worker.tasks.sync_cod_settlements", ignore_result=True)
def sync_cod_settlements() -> dict[str, int]:
    from app.domains.fulfillment.settlement import sync_all

    with session_scope() as db:
        stats = sync_all(db)
    if stats["imported"] or stats["failed"]:
        log.info("cod_settlements_synced", **stats)
    return stats


@celery.task(name="app.worker.tasks.resume_workflows", ignore_result=True)
def resume_workflows() -> int:
    from app.domains.automation.engine import resume_due

    with session_scope() as db:
        return resume_due(db)


@celery.task(name="app.worker.tasks.reconcile_twin", ignore_result=True)
def reconcile_twin() -> int:
    """TWIN-003: recompute every merchant's Twin sections to correct any drift."""
    from app.domains.twin import service as twin

    with session_scope() as db:
        return twin.reconcile_all(db)


@celery.task(name="app.worker.tasks.nightly_intelligence", ignore_result=True)
def nightly_intelligence() -> dict[str, int]:
    """Phase 6: Courier Brain, Return Intelligence, Product Brain, Commerce Memory, Autopilot Score,
    recommendations and their outcomes."""
    from app.domains.intelligence import (
        aps,
        courier_brain,
        memory,
        product_brain,
        recommendations,
        return_intel,
    )

    stats: dict[str, int] = {}
    with session_scope() as db:
        stats["courier_merchants"] = courier_brain.recompute_all(db)
    # Part B: returns first (fit facts), then profiles (use returns), then memory (uses courier metrics).
    with session_scope() as db:
        stats["return_merchants"] = return_intel.detect_all(db)
    with session_scope() as db:
        stats["product_profiles"] = product_brain.recompute_all(db)
    with session_scope() as db:
        stats["memory_merchants"] = memory.compute_all(db)
    # Phase 7: post results → attribution → Creative Genome → experiments.
    from app.domains.intelligence import creative

    with session_scope() as db:
        stats["creative_merchants"] = creative.run_all(db)
    # Phase 8: supplier performance (before suggestions, which use it).
    from app.domains.procurement import supplier_intel

    with session_scope() as db:
        stats["supplier_merchants"] = supplier_intel.compute_all(db)
    # Phase 9: daily Twin snapshot (trends, simulation baselines).
    from app.domains.twin import service as twin

    with session_scope() as db:
        stats["twin_snapshots"] = twin.snapshot_all(db)
    with session_scope() as db:
        stats["aps_snapshots"] = aps.snapshot_all(db)
    with session_scope() as db:
        stats["recommendations"] = recommendations.generate_all(db)
    with session_scope() as db:
        stats.update(recommendations.measure(db))
    log.info("nightly_intelligence", **stats)
    return stats
