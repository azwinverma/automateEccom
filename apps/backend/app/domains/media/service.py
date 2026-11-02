"""Media use cases: signed upload → complete → async processing → ready/rejected (MED-001..004, 010, 011)."""

from __future__ import annotations

import hashlib
import math
import uuid
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements, register_gauge
from app.domains.integrations.storage import get_storage, tenant_key
from app.domains.media import imaging
from app.domains.media.models import MediaAsset, MediaDerivative
from app.domains.media.scanner import get_scanner
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)

ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
SIGNED_URL_TTL = 300


@register_gauge("storage_mb")
def storage_mb(db: Session, merchant_id: uuid.UUID) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(MediaAsset.size_bytes + MediaAsset.derivative_bytes), 0)).where(
            MediaAsset.merchant_id == merchant_id, MediaAsset.status.not_in(("deleted", "rejected"))
        )
    )
    return math.ceil(int(total or 0) / (1024 * 1024))


def _get(db: Session, ctx: TenantContext, asset_id: uuid.UUID) -> MediaAsset:
    a = db.get(MediaAsset, asset_id)
    if a is None or a.merchant_id != ctx.merchant_id or a.status == "deleted":
        raise NotFound()
    return a


def _absolute(url: str) -> str:
    return url if url.startswith("http") else get_settings().public_api_base_url.rstrip("/") + url


# ----------------------------------------------------------------------------- upload
def create_upload(
    db: Session, ctx: TenantContext, file_name: str, content_type: str, size_bytes: int, purpose: str
) -> tuple[MediaAsset, dict[str, Any]]:
    s = get_settings()
    content_type = content_type.lower().strip()
    if content_type not in ALLOWED_UPLOAD_TYPES:
        raise ValidationFailed(
            "Upload a JPEG, PNG, WebP or HEIC photo",
            code="unsupported_media_type",
            details={"allowed": sorted(ALLOWED_UPLOAD_TYPES)},
        )
    if not 0 < size_bytes <= s.media_max_upload_bytes:
        raise ValidationFailed(
            f"Photos must be under {s.media_max_upload_bytes // (1024 * 1024)} MB",
            code="file_too_large",
            details={"max_bytes": s.media_max_upload_bytes},
        )
    entitlements.check_gauge(db, ctx.merchant_id, "storage_mb", adding=math.ceil(size_bytes / (1024 * 1024)))
    asset_id = uuid.uuid4()
    key = tenant_key(str(ctx.merchant_id), "media", str(asset_id), "original")
    a = MediaAsset(
        id=asset_id,
        merchant_id=ctx.merchant_id,
        file_name=file_name[:255],
        purpose=purpose,
        declared_content_type=content_type,
        size_bytes=size_bytes,
        original_key=key,
        uploaded_by_user_id=ctx.actor.id,
        upload_expires_at=utcnow() + timedelta(seconds=s.media_upload_ttl_seconds),
    )
    db.add(a)
    db.flush()
    url = get_storage().signed_put_url(key, content_type, ttl_s=s.media_upload_ttl_seconds)
    return a, {
        "method": "PUT",
        "url": _absolute(url),
        "headers": {"Content-Type": content_type},
        "expires_at": a.upload_expires_at,
    }


def complete_upload(db: Session, ctx: TenantContext, asset_id: uuid.UUID) -> MediaAsset:
    a = _get(db, ctx, asset_id)
    if a.status != "pending_upload":
        return a  # idempotent: completing twice is harmless
    if a.upload_expires_at and a.upload_expires_at < utcnow() - timedelta(minutes=5):
        raise Conflict("Upload window expired. Start the upload again.", code="upload_expired")
    try:
        data = get_storage().get(a.original_key)
    except (FileNotFoundError, OSError) as e:
        raise Conflict("We didn't receive the file yet. Retry the upload.", code="upload_missing") from e
    if len(data) > get_settings().media_max_upload_bytes:
        raise ValidationFailed("File is larger than allowed", code="file_too_large")
    a.size_bytes = len(data)  # trust the bytes we stored, not the declared size
    a.sha256 = hashlib.sha256(data).hexdigest()
    a.status = "uploaded"
    db.flush()
    audit.record(
        db,
        action="media.uploaded",
        resource_type="media",
        resource_id=a.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"file_name": a.file_name, "bytes": a.size_bytes},
    )
    outbox.publish(
        db,
        event_type="media.uploaded",
        aggregate_type="media",
        aggregate_id=a.id,
        merchant_id=ctx.merchant_id,
        payload={"asset_id": str(a.id)},
    )
    return a


# ----------------------------------------------------------------------------- processing
def process_asset(db: Session, asset_id: uuid.UUID) -> MediaAsset | None:
    a = db.scalar(
        select(MediaAsset)
        .where(MediaAsset.id == asset_id)
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if a is None or a.status not in ("uploaded", "processing"):
        return a
    bind_tenant(db, a.merchant_id)
    a.status = "processing"
    storage = get_storage()
    data = storage.get(a.original_key)

    scan = get_scanner().scan(data)
    a.scan_status = scan.status
    if scan.status == "error":
        raise RuntimeError("malware scanner unavailable")  # transient → outbox retries with backoff
    if scan.status == "infected":
        storage.delete(a.original_key)  # quarantine: never keep infected bytes
        _reject(db, a, "malware_detected", {"signature": scan.signature})
        return a
    try:
        result = imaging.process(data)
    except imaging.ImageRejected as e:
        _reject(db, a, e.reason)
        return a

    total = 0
    for d in result.derivatives:
        key = tenant_key(
            str(a.merchant_id),
            "media",
            str(a.id),
            f"{d.kind}.{'webp' if 'webp' in d.content_type else 'jpg'}",
        )
        storage.put(key, d.data, d.content_type)
        existing = db.scalar(
            select(MediaDerivative).where(MediaDerivative.asset_id == a.id, MediaDerivative.kind == d.kind)
        )
        if existing is None:
            db.add(
                MediaDerivative(
                    merchant_id=a.merchant_id,
                    asset_id=a.id,
                    kind=d.kind,
                    key=key,
                    content_type=d.content_type,
                    width=d.width,
                    height=d.height,
                    size_bytes=len(d.data),
                )
            )
        total += len(d.data)
    a.detected_format = result.format
    a.width, a.height = result.width, result.height
    a.quality_score, a.quality_flags = result.quality_score, result.quality_flags
    a.had_location_metadata = result.had_location
    a.derivative_bytes = total
    a.status, a.processed_at = "ready", utcnow()
    db.flush()
    audit.record(
        db,
        action="media.processed",
        resource_type="media",
        resource_id=a.id,
        actor=Actor.system("media-pipeline"),
        merchant_id=a.merchant_id,
        metadata={
            "flags": result.quality_flags,
            "stripped_location": result.had_location,
            "scan": scan.status,
        },
    )
    outbox.publish(
        db,
        event_type="media.ready",
        aggregate_type="media",
        aggregate_id=a.id,
        merchant_id=a.merchant_id,
        payload={"asset_id": str(a.id), "quality_flags": result.quality_flags},
    )
    return a


def _reject(db: Session, a: MediaAsset, reason: str, metadata: dict[str, Any] | None = None) -> None:
    a.status, a.rejection_reason, a.processed_at = "rejected", reason, utcnow()
    db.flush()
    audit.record(
        db,
        action="media.rejected",
        resource_type="media",
        resource_id=a.id,
        actor=Actor.system("media-pipeline"),
        merchant_id=a.merchant_id,
        metadata={"reason": reason, **(metadata or {})},
    )
    log.info("media_rejected", asset_id=str(a.id), reason=reason)


@handler("media.uploaded")
def _on_uploaded(db: Session, ev: OutboxEvent) -> None:
    process_asset(db, uuid.UUID(ev.payload["asset_id"]))


# ----------------------------------------------------------------------------- reads / delete / cleanup
def asset_view(db: Session, a: MediaAsset, with_urls: bool = True) -> dict[str, Any]:
    derivatives = (
        db.scalars(select(MediaDerivative).where(MediaDerivative.asset_id == a.id)).all()
        if a.status == "ready"
        else []
    )
    storage = get_storage()
    return {
        "id": a.id,
        "status": a.status,
        "kind": a.kind,
        "purpose": a.purpose,
        "file_name": a.file_name,
        "width": a.width,
        "height": a.height,
        "size_bytes": a.size_bytes,
        "quality_score": a.quality_score,
        "quality_flags": a.quality_flags,
        "stripped_location_metadata": a.had_location_metadata,
        "scan_status": a.scan_status,
        "rejection_reason": a.rejection_reason,
        "source": a.source,
        "created_at": a.created_at,
        "derivatives": {
            d.kind: {
                "width": d.width,
                "height": d.height,
                "content_type": d.content_type,
                "url": _absolute(storage.signed_get_url(d.key, SIGNED_URL_TTL)) if with_urls else None,
            }
            for d in derivatives
        },
    }


def delete_asset(db: Session, ctx: TenantContext, asset_id: uuid.UUID) -> None:
    from app.domains.catalog.models import ProductMedia

    a = _get(db, ctx, asset_id)
    used = db.scalar(select(func.count()).select_from(ProductMedia).where(ProductMedia.asset_id == a.id))
    if used:
        raise Conflict(
            "This photo is used by a product. Remove it from the product first.", code="media_in_use"
        )
    _purge_objects(db, a)
    a.status = "deleted"
    audit.record(
        db,
        action="media.deleted",
        resource_type="media",
        resource_id=a.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )


def _purge_objects(db: Session, a: MediaAsset) -> None:
    storage = get_storage()
    for d in db.scalars(select(MediaDerivative).where(MediaDerivative.asset_id == a.id)):
        storage.delete(d.key)
        db.delete(d)
    storage.delete(a.original_key)
    a.derivative_bytes = 0


def cleanup_expired_uploads(db: Session, limit: int = 200) -> int:
    """MED-011: abandoned signed uploads (never completed) are deleted after a grace period."""
    cutoff = utcnow() - timedelta(hours=24)
    rows = db.scalars(
        select(MediaAsset)
        .where(MediaAsset.status == "pending_upload", MediaAsset.created_at < cutoff)
        .limit(limit)
        .execution_options(skip_tenant_filter=True)
    ).all()
    for a in rows:
        get_storage().delete(a.original_key)
        a.status = "deleted"
    return len(rows)
