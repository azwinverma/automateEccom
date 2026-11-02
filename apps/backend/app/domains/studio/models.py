"""AI Product Studio jobs. The AI result is a *draft document* (JSONB is appropriate here: it is model
output awaiting review, not relational commerce data). Applying a draft creates real catalog rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin


class StudioJob(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "studio_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued','running','ready','failed','applied','discarded')", name="status"
        ),
        Index("ix_studio_stale", "updated_at", postgresql_where=text("status in ('queued','running')")),
    )

    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    asset_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="ne", nullable=False)
    seller_notes: Mapped[str | None] = mapped_column(String(2000))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float | None]
    needs_review: Mapped[bool] = mapped_column(default=False, nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_request_group: Mapped[uuid.UUID | None]
    ai_provider: Mapped[str | None] = mapped_column(String(32))
    ai_model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[int | None] = mapped_column(Integer)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    finished_at: Mapped[datetime | None]
