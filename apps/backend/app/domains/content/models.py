"""Content posts (CNT-008..011): per-channel drafts → approval → schedule → publish (with retry)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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
        CheckConstraint("source in ('seller','ai_studio','ai_schedule','autopost')", name="source"),
        CheckConstraint(
            "hook_type in ('price_first','product_closeup','problem_solution','social_proof','offer',"
            "'unknown')",
            name="hook_type",
        ),
        CheckConstraint("language_mix in ('ne','en','ne_en_mixed','none')", name="language_mix"),
        CheckConstraint("cta_type in ('dm','comment','link','call','none')", name="cta_type"),
        CheckConstraint("caption_bucket in ('short','medium','long')", name="caption_bucket"),
        CheckConstraint(
            "background is null or background in ('white','lifestyle','blurred_photo','other')",
            name="background",
        ),
        CheckConstraint("posting_hour is null or posting_hour between 0 and 23", name="posting_hour"),
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
    # Creative attributes (CNT-012; specs/09): recorded now so the Creative Genome can learn later.
    video_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_video_jobs.id", ondelete="SET NULL")
    )
    duration_s: Mapped[float | None]
    hook_type: Mapped[str] = mapped_column(
        String(20), default="unknown", server_default="unknown", nullable=False
    )
    price_shown: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    price_timing_s: Mapped[float | None]
    language_mix: Mapped[str] = mapped_column(
        String(12), default="none", server_default="none", nullable=False
    )
    caption_bucket: Mapped[str] = mapped_column(
        String(8), default="short", server_default="short", nullable=False
    )
    cta_type: Mapped[str] = mapped_column(String(8), default="none", server_default="none", nullable=False)
    human_presence: Mapped[bool | None]
    background: Mapped[str | None] = mapped_column(String(16))
    template_id: Mapped[str | None] = mapped_column(String(60))
    posting_hour: Mapped[int | None] = mapped_column(Integer)
    creative_attrs_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # CGN-004: the Creative Genome version that informed this post (None = not genome-informed).
    genome_version: Mapped[int | None] = mapped_column(Integer)

    __mapper_args__ = {"version_id_col": version}


class AutopostSettings(IdMixin, TimestampMixin, TenantScoped, Base):
    """Post a product to the chosen accounts automatically when it goes live (one row per merchant)."""

    __tablename__ = "content_autopost_settings"
    __table_args__ = (
        CheckConstraint("kind in ('post','story')", name="kind"),
        UniqueConstraint("merchant_id"),
    )

    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    connection_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(8), default="post", nullable=False)
    require_approval: Mapped[bool] = mapped_column(default=True, nullable=False)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
