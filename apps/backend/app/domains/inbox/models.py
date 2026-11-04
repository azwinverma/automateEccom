"""Unified inbox: conversations, messages, chat order drafts (CRM-005…012, ORD-006)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow

INTENTS = (
    "product_question",
    "stock",
    "size",
    "price",
    "delivery",
    "order",
    "payment",
    "order_status",
    "cancellation",
    "return",
    "exchange",
    "refund",
    "complaint",
    "greeting",
    "human",
    "other",
)


class Conversation(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("merchant_id", "connection_id", "external_thread_id"),
        CheckConstraint("status in ('open','snoozed','closed')", name="status"),
        Index("ix_conversations_inbox", "merchant_id", "status", "last_message_at"),
    )

    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("channel_connections.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_thread_id: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    labels: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), default=list, server_default="{}", nullable=False
    )
    last_intent: Mapped[str | None] = mapped_column(String(24))
    ai_summary: Mapped[str | None] = mapped_column(String(2000))
    ai_summary_at: Mapped[datetime | None]
    # The seller took over: the AI stops replying until it's handed back.
    human_handoff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    escalation_reason: Mapped[str | None] = mapped_column(String(40))
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="ne", nullable=False)
    last_message_at: Mapped[datetime | None]
    last_inbound_at: Mapped[datetime | None]
    first_response_due_at: Mapped[datetime | None]  # SLA: cleared by the first reply


class Message(IdMixin, TenantScoped, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("direction in ('in','out')", name="direction"),
        CheckConstraint("author_type in ('customer','seller','ai','system')", name="author"),
        CheckConstraint(
            "status in ('received','suggested','queued','sent','failed','discarded')", name="status"
        ),
        Index(
            "uq_messages_external",
            "merchant_id",
            "conversation_id",
            "external_message_id",
            unique=True,
            postgresql_where=text("external_message_id is not null"),
        ),
        Index("ix_messages_conversation", "conversation_id", "id"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    direction: Mapped[str] = mapped_column(String(3), nullable=False)
    author_type: Mapped[str] = mapped_column(String(10), nullable=False)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(160))
    intent: Mapped[str | None] = mapped_column(String(24))
    confidence: Mapped[float | None] = mapped_column(Float)
    # What the agent looked up to write this reply (tool name → facts), shown to the seller.
    grounding: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None]


class OrderDraft(IdMixin, TimestampMixin, TenantScoped, Base):
    """Chat-to-order slot filling. ``version`` bumps on every change; the order is created idempotently on
    (conversation, version) so a repeated "yes" never makes two orders."""

    __tablename__ = "order_drafts"
    __table_args__ = (
        CheckConstraint(
            "status in ('collecting','awaiting_confirmation','confirmed','abandoned')", name="status"
        ),
        Index(
            "uq_order_drafts_active",
            "conversation_id",
            unique=True,
            postgresql_where=text("status in ('collecting','awaiting_confirmation')"),
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24), default="collecting", nullable=False)
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    awaiting_field: Mapped[str | None] = mapped_column(String(24))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
