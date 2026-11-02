"""Content posts (CNT-008..011): per-channel drafts → approval → schedule → publish (with retry)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin

POST_STATUSES = (
    "draft",
    "pending_approval",
    "approved",
    "scheduled",
    "publishing",
    "published",
    "failed",
    "cancelled",
)


class ContentPost(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "content_posts"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft','pending_approval','approved','scheduled','publishing','published','failed',"
            "'cancelled')",
            name="status",
        ),
        CheckConstraint("kind in ('post','story','reel')", name="kind"),
        CheckConstraint("source in ('seller','ai_studio','ai_schedule')", name="source"),
        Index("ix_content_due", "next_attempt_at", postgresql_where=text("status = 'scheduled'")),
        Index("ix_content_calendar", "merchant_id", "scheduled_at"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channel_connections.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="SET NULL")
    )
    studio_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("studio_jobs.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(8), default="post", nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list, nullable=False)
    asset_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=False
    )
    campaign: Mapped[str | None] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(16), default="seller", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    scheduled_at: Mapped[datetime | None]
    next_attempt_at: Mapped[datetime | None]
    published_at: Mapped[datetime | None]
    external_id: Mapped[str | None] = mapped_column(String(160))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    rejection_note: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}
