"""Video jobs: Auto Reels (MED-008) and the shared video lifecycle (MED-009).

create (HTTP): feature + photo checks, usage reserved → outbox ``video.job_queued`` → Celery ``media`` queue
run (worker): generating → post_processing (store MP4 + poster as a media asset) → ready, usage finalized
failure: failed + usage released (merchant is not charged); cancel while queued releases usage too.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import session_scope, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements
from app.domains.catalog.models import Product, Variant
from app.domains.integrations.storage import get_storage, tenant_key
from app.domains.media import reels
from app.domains.media.models import MediaAsset, MediaDerivative, VideoJob
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)
MAX_PHOTOS = 10


def _get(db: Session, ctx: TenantContext, job_id: uuid.UUID) -> VideoJob:
    j = db.get(VideoJob, job_id)
    if j is None or j.merchant_id != ctx.merchant_id:
        raise NotFound()
    return j


def _genome_version(db: Session, ctx: TenantContext, version: int | None) -> int | None:
    """CGN-004: the seller applied the genome's suggested settings (validated, recorded on the job)."""
    from app.domains.intelligence.creative import valid_version

    return valid_version(db, ctx.merchant_id, version)


def create_auto_reel(
    db: Session,
    ctx: TenantContext,
    *,
    asset_ids: list[uuid.UUID],
    aspect: str,
    locale: str,
    headline: str | None,
    cta: str | None,
    product_id: uuid.UUID | None,
    show_price: bool,
    seconds_per_slide: float,
    idempotency_key: str,
    genome_version: int | None = None,
) -> VideoJob:
    entitlements.require_feature(db, ctx.merchant_id, "video.auto_reels")
    if aspect not in reels.ASPECTS:
        raise ValidationFailed(
            "Unsupported format", code="invalid_aspect", details={"allowed": list(reels.ASPECTS)}
        )
    if not 1 <= len(asset_ids) <= MAX_PHOTOS:
        raise ValidationFailed(f"Choose 1 to {MAX_PHOTOS} photos", code="invalid_photo_count")
    ready = set(
        db.scalars(
            select(MediaAsset.id).where(
                MediaAsset.merchant_id == ctx.merchant_id,
                MediaAsset.id.in_(asset_ids),
                MediaAsset.kind == "image",
                MediaAsset.status == "ready",
            )
        )
    )
    bad = [str(a) for a in asset_ids if a not in ready]
    if bad:
        raise Conflict(
            "Some photos are missing or still processing", code="media_not_ready", details={"asset_ids": bad}
        )
    if show_price and product_id is None:
        raise ValidationFailed("Pick the product whose price to show", code="product_required_for_price")
    if product_id is not None:
        # Any referenced product must be this merchant's, with or without a price overlay (QA-012).
        p = db.get(Product, product_id)
        if p is None or p.merchant_id != ctx.merchant_id:
            raise NotFound("Product not found", code="product_not_found")
    for text in (headline, cta):
        if text and reels.has_devanagari(text) and not reels.shaping_available():
            # Fail now (before charging) rather than in the worker.
            raise Conflict(
                "Nepali text rendering isn't available on this server yet", code="text_shaping_unavailable"
            )
    job = VideoJob(
        merchant_id=ctx.merchant_id,
        kind="auto_reel",
        aspect=aspect,
        asset_ids=list(dict.fromkeys(asset_ids)),
        locale=locale,
        headline=(headline or "").strip()[:80] or None,
        cta=(cta or "").strip()[:60] or None,
        product_id=product_id,
        show_price=show_price,
        seconds_per_slide=seconds_per_slide,
        genome_version=_genome_version(db, ctx, genome_version),
        created_by_user_id=ctx.actor.id,
    )
    db.add(job)
    db.flush()
    res = entitlements.reserve(
        db,
        ctx.merchant_id,
        "auto_reels",
        1,
        f"reel:{idempotency_key}",
        reference_type="video_job",
        reference_id=str(job.id),
    )
    job.usage_reservation_id = res.id
    audit.record(
        db,
        action="video.auto_reel_requested",
        resource_type="video_job",
        resource_id=job.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"aspect": aspect, "photos": len(job.asset_ids), "funding": res.funding},
    )
    outbox.publish(
        db,
        event_type="video.job_queued",
        aggregate_type="video_job",
        aggregate_id=job.id,
        merchant_id=ctx.merchant_id,
        payload={"job_id": str(job.id)},
    )
    return job


@handler("video.job_queued")
def _enqueue(db: Session, ev: OutboxEvent) -> None:
    from app.worker.tasks import run_video_job

    run_video_job.delay(ev.payload["job_id"])


def _price_text(db: Session, product_id: uuid.UUID, locale: str) -> str | None:
    """Price comes from the catalog (internal fact), never from AI."""
    lo, hi = db.execute(
        select(func.min(Variant.price_minor), func.max(Variant.price_minor)).where(
            Variant.product_id == product_id, Variant.status == "active"
        )
    ).one()
    if lo is None:
        return None
    return reels.format_npr(int(lo), locale, from_prefix=hi != lo)


def run_job(job_id: uuid.UUID) -> VideoJob | None:
    with session_scope() as db:
        job = db.scalar(
            select(VideoJob)
            .where(VideoJob.id == job_id)
            .with_for_update(skip_locked=True)
            .execution_options(skip_tenant_filter=True)
        )
        if job is None or job.status != "queued":
            return job
        job.status, job.attempts = "generating", job.attempts + 1
        storage = get_storage()
        photos = []
        for aid in job.asset_ids:
            d = db.scalar(
                select(MediaDerivative).where(
                    MediaDerivative.asset_id == aid, MediaDerivative.kind == "medium"
                )
            )
            photos.append(storage.get(d.key) if d else storage.get(db.get(MediaAsset, aid).original_key))  # type: ignore[union-attr]
        price = _price_text(db, job.product_id, job.locale) if job.show_price and job.product_id else None
        overlay = reels.Overlay(headline=job.headline, price=price, cta=job.cta)
        params = (job.aspect, job.seconds_per_slide, job.merchant_id)
    aspect, seconds, merchant_id = params
    try:
        result = reels.render(photos, aspect, seconds, overlay)
    except reels.ReelError as e:
        _fail(job_id, e.code)
        return None
    with session_scope() as db:
        job = db.get(VideoJob, job_id)
        assert job is not None
        if job.status == "cancelled":
            return job
        job.status = "post_processing"
        asset_id = uuid.uuid4()
        key = tenant_key(str(merchant_id), "media", str(asset_id), "original.mp4")
        poster_key = tenant_key(str(merchant_id), "media", str(asset_id), "poster.jpg")
        storage = get_storage()
        storage.put(key, result.video, "video/mp4")
        storage.put(poster_key, result.poster_jpeg, "image/jpeg")
        asset = MediaAsset(
            id=asset_id,
            merchant_id=merchant_id,
            kind="video",
            status="ready",
            purpose="content",
            file_name=f"auto-reel-{aspect.replace(':', 'x')}.mp4",
            declared_content_type="video/mp4",
            detected_format="MP4",
            size_bytes=len(result.video),
            derivative_bytes=len(result.poster_jpeg),
            original_key=key,
            width=result.width,
            height=result.height,
            scan_status="skipped",
            source="auto_reel",
            uploaded_by_user_id=job.created_by_user_id,
            processed_at=utcnow(),
        )
        db.add(asset)
        db.flush()
        db.add(
            MediaDerivative(
                merchant_id=merchant_id,
                asset_id=asset_id,
                kind="poster",
                key=poster_key,
                content_type="image/jpeg",
                width=result.width,
                height=result.height,
                size_bytes=len(result.poster_jpeg),
            )
        )
        db.add(
            MediaDerivative(
                merchant_id=merchant_id,
                asset_id=asset_id,
                kind="video",
                key=key,
                content_type="video/mp4",
                width=result.width,
                height=result.height,
                size_bytes=len(result.video),
            )
        )
        if job.usage_reservation_id:
            ev = entitlements.finalize(db, job.usage_reservation_id)
            job.credits_charged = int(ev.credits_charged) if ev else 0
        job.status, job.output_asset_id, job.duration_s, job.finished_at = (
            "ready",
            asset_id,
            result.duration_s,
            utcnow(),
        )
        job.provider, job.model, job.provider_cost_usd_micros = "internal", "ffmpeg-auto-reel-v1", 0
        audit.record(
            db,
            action="video.auto_reel_ready",
            resource_type="video_job",
            resource_id=job.id,
            actor=Actor.system("auto-reel"),
            merchant_id=merchant_id,
            metadata={"duration_s": result.duration_s, "bytes": len(result.video)},
        )
        return job


def _fail(job_id: uuid.UUID, code: str) -> None:
    with session_scope() as db:
        job = db.get(VideoJob, job_id)
        assert job is not None
        job.status, job.error_code, job.finished_at = "failed", code, utcnow()
        if job.usage_reservation_id:
            entitlements.release(db, job.usage_reservation_id)  # not charged for failures
        audit.record(
            db,
            action="video.failed",
            resource_type="video_job",
            resource_id=job.id,
            actor=Actor.system("auto-reel"),
            merchant_id=job.merchant_id,
            metadata={"error_code": code},
        )
    log.warning("video_job_failed", job_id=str(job_id), error_code=code)


def cancel(db: Session, ctx: TenantContext, job_id: uuid.UUID) -> VideoJob:
    job = _get(db, ctx, job_id)
    if job.status in ("ready", "failed", "cancelled"):
        raise Conflict(
            "This video is already finished", code="video_finished", details={"status": job.status}
        )
    job.status, job.finished_at = "cancelled", utcnow()
    if job.usage_reservation_id:
        entitlements.release(db, job.usage_reservation_id)
    audit.record(
        db,
        action="video.cancelled",
        resource_type="video_job",
        resource_id=job.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )
    return job


def job_view(db: Session, j: VideoJob) -> dict[str, Any]:
    from app.domains.media.service import asset_view

    out = None
    if j.output_asset_id:
        a = db.get(MediaAsset, j.output_asset_id)
        out = asset_view(db, a) if a else None
    return {
        "id": j.id,
        "kind": j.kind,
        "status": j.status,
        "aspect": j.aspect,
        "asset_ids": j.asset_ids,
        "headline": j.headline,
        "cta": j.cta,
        "show_price": j.show_price,
        "seconds_per_slide": j.seconds_per_slide,
        "genome_version": j.genome_version,
        "product_id": j.product_id,
        "duration_s": j.duration_s,
        "credits_charged": j.credits_charged,
        "error_code": j.error_code,
        "output": out,
        "created_at": j.created_at,
        "finished_at": j.finished_at,
    }
