from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, utcnow


class AIExecution(IdMixin, Base):
    """Cost ledger (AIG-014): one row per provider attempt. ``request_group`` ties attempts of one
    gateway call together. Never stores prompts/outputs (PII) — only metadata."""

    __tablename__ = "ai_executions"
    __table_args__ = (
        CheckConstraint("status in ('succeeded','failed','skipped')", name="status"),
        Index("ix_ai_exec_merchant_created", "merchant_id", "created_at"),
        Index("ix_ai_exec_group", "request_group"),
    )

    merchant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"))
    request_group: Mapped[uuid.UUID] = mapped_column(nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    byok: Mapped[bool] = mapped_column(default=False, nullable=False)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    units: Mapped[float | None]
    cost_usd_micros: Mapped[int | None] = mapped_column(BigInteger)
    credits_charged: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[int | None] = mapped_column(Integer)
    plan_code: Mapped[str | None] = mapped_column(String(40))
    usage_reservation_id: Mapped[uuid.UUID | None]
    trace_id: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class ProviderCredential(IdMixin, TimestampMixin, Base):
    """BYOK credential (AIG-011). Key is envelope-encrypted with AAD bound to merchant+provider."""

    __tablename__ = "ai_provider_credentials"
    __table_args__ = (
        CheckConstraint("status in ('active','revoked')", name="status"),
        Index(
            "uq_ai_cred_active",
            "merchant_id",
            "provider",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    key_sealed: Mapped[str | None] = mapped_column(String(2048))
    key_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    fallback_to_platform: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    last_tested_at: Mapped[datetime | None]
    last_test_ok: Mapped[bool | None]
    rotated_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class PromptTemplate(IdMixin, TimestampMixin, Base):
    """Prompt registry (AIG-012)."""

    __tablename__ = "ai_prompt_templates"
    __table_args__ = (
        UniqueConstraint("name", "locale", "version"),
        CheckConstraint("rollout_state in ('draft','canary','active','retired')", name="rollout"),
        Index(
            "uq_prompt_active",
            "name",
            "locale",
            unique=True,
            postgresql_where=text("rollout_state = 'active'"),
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    system_template: Mapped[str] = mapped_column(String, nullable=False)
    user_template: Mapped[str] = mapped_column(String, nullable=False)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tools: Mapped[list[str] | None] = mapped_column(JSONB)
    eval_score: Mapped[float | None]
    rollout_state: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
