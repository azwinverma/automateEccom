"""Media assets (MED-001..004, MED-010/011). Originals are private; clients only ever get short-lived
signed URLs to derivatives. Provenance records whether an asset is a seller photo or AI output, so
generated imagery is never silently passed off as the real product."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin


class MediaAsset(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending_upload','uploaded','processing','ready','rejected','deleted')", name="status"
        ),
        CheckConstraint("kind in ('image','video')", name="kind"),
        CheckConstraint("scan_status in ('pending','clean','infected','skipped','error')", name="scan"),
        CheckConstraint(
            "source in ('seller_upload','ai_generated','ai_edited','channel_import','csv_import')",
            name="source",
        ),
        CheckConstraint("purpose in ('product','content','brand','other')", name="purpose"),
        CheckConstraint("size_bytes >= 0", name="size"),
        Index("ix_media_pending", "created_at", postgresql_where=text("status = 'pending_upload'")),
        Index("ix_media_merchant_status", "merchant_id", "status", "id"),
    )

    kind: Mapped[str] = mapped_column(String(8), default="image", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending_upload", nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), default="product", nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    declared_content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_format: Mapped[str | None] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    derivative_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    original_key: Mapped[str] = mapped_column(String(500), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    quality_score: Mapped[float | None] = mapped_column(Float)
    quality_flags: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list, nullable=False)
    had_location_metadata: Mapped[bool] = mapped_column(default=False, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(20), default="seller_upload", nullable=False)
    parent_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    ai_request_group: Mapped[uuid.UUID | None]
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    upload_expires_at: Mapped[datetime | None]
    processed_at: Mapped[datetime | None]


class MediaDerivative(IdMixin, TenantScoped, Base):
    __tablename__ = "media_derivatives"
    __table_args__ = (UniqueConstraint("asset_id", "kind"),)

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("media_assets.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)


class VideoJob(IdMixin, TimestampMixin, TenantScoped, Base):
    """Video generation job (MED-008 Auto Reels; premium AI video uses the same lifecycle).

    QUEUED → SUBMITTED (premium only, provider accepted) → GENERATING → POST_PROCESSING → READY
    any non-terminal → FAILED | CANCELLED
    """

    __tablename__ = "media_video_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued','submitted','generating','post_processing','ready','failed','cancelled')",
            name="status",
        ),
        CheckConstraint("kind in ('auto_reel','premium')", name="kind"),
        CheckConstraint("aspect in ('9:16','1:1','4:5','16:9')", name="aspect"),
        Index("ix_video_stale", "updated_at", postgresql_where=text("status in ('queued','generating')")),
    )

    kind: Mapped[str] = mapped_column(String(16), default="auto_reel", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    template: Mapped[str] = mapped_column(String(32), default="showcase", nullable=False)
    aspect: Mapped[str] = mapped_column(String(5), default="9:16", nullable=False)
    asset_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="SET NULL")
    )
    locale: Mapped[str] = mapped_column(String(5), default="ne", nullable=False)
    headline: Mapped[str | None] = mapped_column(String(80))
    cta: Mapped[str | None] = mapped_column(String(60))
    show_price: Mapped[bool] = mapped_column(default=False, nullable=False)
    seconds_per_slide: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    genome_version: Mapped[int | None] = mapped_column(Integer)  # CGN-004: settings suggested by the genome
    output_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    duration_s: Mapped[float | None] = mapped_column(Float)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(100))
    provider_cost_usd_micros: Mapped[int | None] = mapped_column(BigInteger)
    credits_charged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_reservation_id: Mapped[uuid.UUID | None]
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    finished_at: Mapped[datetime | None]
