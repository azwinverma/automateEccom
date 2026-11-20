"""Celery worker + beat. Long-running AI/media/publish jobs run here, never in HTTP requests."""

from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.tracing import configure_tracing

settings = get_settings()
celery = Celery("commerce_os", broker=settings.broker_url, backend=None, include=["app.worker.tasks"])
celery.conf.update(
    task_acks_late=True,  # redeliver if a worker dies mid-task; tasks must be idempotent
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=900,
    task_soft_time_limit=840,
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
    task_routes={
        "app.worker.tasks.dispatch_outbox": {"queue": "outbox"},
        "app.worker.tasks.run_studio_job": {"queue": "ai"},
        "app.worker.tasks.run_video_job": {"queue": "media"},
    },
    beat_schedule={
        "dispatch-outbox": {"task": "app.worker.tasks.dispatch_outbox", "schedule": 2.0},
        "release-expired-usage": {"task": "app.worker.tasks.release_expired_usage", "schedule": 60.0},
        "cleanup-media-uploads": {"task": "app.worker.tasks.cleanup_media_uploads", "schedule": 3600.0},
        "requeue-stale-studio-jobs": {
            "task": "app.worker.tasks.requeue_stale_studio_jobs",
            "schedule": 300.0,
        },
        "refresh-channel-tokens": {"task": "app.worker.tasks.refresh_channel_tokens", "schedule": 300.0},
        # CHN-012: spec default is every 6h per merchant.
        "reconcile-channels": {"task": "app.worker.tasks.reconcile_channels", "schedule": 6 * 3600.0},
        "publish-due-content": {"task": "app.worker.tasks.publish_due_content", "schedule": 30.0},
        "release-expired-stock": {"task": "app.worker.tasks.release_expired_stock", "schedule": 120.0},
        "purge-idempotency": {"task": "app.worker.tasks.purge_idempotency", "schedule": 3600.0},
        # FUL-006: polling is per-shipment rate limited (30 min, 6 h for webhook couriers).
        # AUT-007/010: workflow waits and retries come due.
        "nightly-intelligence": {"task": "app.worker.tasks.nightly_intelligence", "schedule": 24 * 3600.0},
        "resume-workflows": {"task": "app.worker.tasks.resume_workflows", "schedule": 60.0},
        "poll-shipments": {"task": "app.worker.tasks.poll_shipments", "schedule": 300.0},
        "escalate-delivery-recoveries": {
            "task": "app.worker.tasks.escalate_delivery_recoveries",
            "schedule": 600.0,
        },
        "sync-cod-settlements": {"task": "app.worker.tasks.sync_cod_settlements", "schedule": 6 * 3600.0},
        # TWIN-003: periodic reconciliation (spec 03 default every 6 h).
        "reconcile-twin": {"task": "app.worker.tasks.reconcile_twin", "schedule": 6 * 3600.0},
    },
)


@worker_process_init.connect
def _init(**_: object) -> None:
    configure_logging(settings.log_level, settings.log_json)
    configure_tracing(settings)
