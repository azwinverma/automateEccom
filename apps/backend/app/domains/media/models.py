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
from sqlalchemy.dialects.postgresql import ARRAY
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
