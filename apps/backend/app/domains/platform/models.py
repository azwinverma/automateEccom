"""Cross-cutting platform primitives: transactional outbox, idempotency records, feature flags."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, utcnow


class OutboxEvent(IdMixin, Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("status in ('pending','dispatched','dead')", name="status"),
        Index("ix_outbox_pending", "available_at", postgresql_where=text("status = 'pending'")),
        Index("ix_outbox_merchant", "merchant_id", "id"),
    )

    merchant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    headers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    dispatched_at: Mapped[datetime | None]


class OutboxConsumption(Base):
    """Exactly-once-per-handler guard: a handler's side effects commit together with this row."""

    __tablename__ = "outbox_consumptions"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="CASCADE"), primary_key=True
    )
    handler: Mapped[str] = mapped_column(String(120), primary_key=True)
    consumed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class IdempotencyRecord(IdMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("owner", "scope", "key"),
        CheckConstraint("status in ('in_progress','completed')", name="status"),
        Index("ix_idempotency_expires", "expires_at"),
    )

    # owner = "user:<uuid>" | "merchant:<uuid>" | "provider:<code>"; scope = operation name
    owner: Mapped[str] = mapped_column(String(80), nullable=False)
    scope: Mapped[str] = mapped_column(String(120), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="in_progress", nullable=False)
    response_status: Mapped[int | None]
    response_body: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None]
    expires_at: Mapped[datetime] = mapped_column(nullable=False)


class FeatureFlag(TimestampMixin, Base):
    __tablename__ = "feature_flags"
    __table_args__ = (CheckConstraint("rollout_percentage between 0 and 100", name="rollout"),)

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    default_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kill_switch: Mapped[bool] = mapped_column(default=False, nullable=False)


class FeatureFlagOverride(IdMixin, TimestampMixin, Base):
    __tablename__ = "feature_flag_overrides"
    __table_args__ = (UniqueConstraint("flag_key", "merchant_id"),)

    flag_key: Mapped[str] = mapped_column(ForeignKey("feature_flags.key", ondelete="CASCADE"))
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"))
    enabled: Mapped[bool] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)
