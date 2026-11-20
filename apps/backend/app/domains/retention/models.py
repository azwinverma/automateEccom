"""Retention campaigns (Retain): win-back, repeat-purchase reminders and one-off broadcasts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin

CAMPAIGN_KINDS = ("win_back", "repeat_reminder", "broadcast")
CAMPAIGN_STATUSES = ("draft", "active", "paused", "completed")
MESSAGE_STATUSES = ("sent", "skipped", "failed")


class Campaign(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "retention_campaigns"
    __table_args__ = (
        CheckConstraint(f"kind in {CAMPAIGN_KINDS}", name="kind"),
        CheckConstraint(f"status in {CAMPAIGN_STATUSES}", name="status"),
        CheckConstraint("days is null or (days between 1 and 365)", name="days"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="draft", nullable=False)
    days: Mapped[int | None] = mapped_column(Integer)  # win-back: quiet for N days; reminder: N days after
    segment: Mapped[str | None] = mapped_column(String(12))  # broadcast: all | repeat | new | inactive
    message_en: Mapped[str] = mapped_column(String(1000), nullable=False)
    message_ne: Mapped[str | None] = mapped_column(String(1000))
    daily_limit: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    activated_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    last_run_at: Mapped[datetime | None]
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class CampaignMessage(IdMixin, TimestampMixin, TenantScoped, Base):
    """One customer's turn in a campaign. ``cycle_key`` makes it at most once per lapse/order."""

    __tablename__ = "retention_campaign_messages"
    __table_args__ = (
        UniqueConstraint("campaign_id", "customer_id", "cycle_key"),
        CheckConstraint(f"status in {MESSAGE_STATUSES}", name="status"),
        Index("ix_campaign_messages_customer_sent", "customer_id", "sent_at"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retention_campaigns.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    cycle_key: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String(40))
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    sent_at: Mapped[datetime | None]
    converted_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    converted_minor: Mapped[int | None] = mapped_column(BigInteger)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
