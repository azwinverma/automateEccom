"""Phase 6 intelligence, part A: Autopilot Score, recommendations, Courier Brain, COD Intelligence.

Every derived number carries its method version, sample size and window so the seller (and an
auditor) can see how much data it rests on. Thin data is reported as thin, never as 0% or 100%.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow


class AutopilotScoreSnapshot(IdMixin, TenantScoped, Base):
    """APS-003: one score per merchant per day and window."""

    __tablename__ = "autopilot_score_snapshots"
    __table_args__ = (UniqueConstraint("merchant_id", "computed_on", "window_days"),)

    computed_on: Mapped[date] = mapped_column(Date, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    overall: Mapped[float | None] = mapped_column(Float)  # None = not enough activity
    eligible: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    anomaly: Mapped[str | None] = mapped_column(String(60))  # APS-007: e.g. jump_+25pts
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CourierPerformanceMetric(IdMixin, TenantScoped, Base):
    """CRI-001: how a courier did on a route (origin → destination district), weight band and COD flag."""

    __tablename__ = "courier_performance_metrics"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "courier_account_id", "origin", "destination", "weight_band", "cod", "period_days"
        ),
        Index("ix_cpm_route", "merchant_id", "destination", "cod"),
    )

    courier_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courier_accounts.id", ondelete="CASCADE")
    )
    origin: Mapped[str] = mapped_column(String(30), nullable=False)
    destination: Mapped[str] = mapped_column(String(30), nullable=False)
    weight_band: Mapped[str] = mapped_column(String(10), nullable=False)  # le1kg | 1to3kg | gt3kg
    cod: Mapped[bool] = mapped_column(Boolean, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)  # finished parcels (delivered/returned/lost)
    delivered: Mapped[int] = mapped_column(Integer, nullable=False)
    first_attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_any: Mapped[int] = mapped_column(Integer, nullable=False)  # had at least one failed attempt
    returned: Mapped[int] = mapped_column(Integer, nullable=False)
    lost: Mapped[int] = mapped_column(Integer, nullable=False)
    eta_p50_days: Mapped[float | None] = mapped_column(Float)
    eta_p90_days: Mapped[float | None] = mapped_column(Float)
    avg_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    cod_settlement_days: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CODRiskAssessment(IdMixin, TimestampMixin, TenantScoped, Base):
    """CODI-002: explainable delivery-risk assessment for a COD order. Never a silent rejection."""

    __tablename__ = "cod_risk_assessments"
    __table_args__ = (
        UniqueConstraint("order_id"),
        CheckConstraint("level in ('LOW','MEDIUM','HIGHER')", name="level"),
        CheckConstraint(
            "recommended_action in ('cod_ok','verify_phone','request_partial_advance','manual_review')",
            name="action",
        ),
        CheckConstraint(
            "outcome is null or outcome in ('delivered','failed','returned','cancelled')", name="outcome"
        ),
        Index("ix_cod_risk_level", "merchant_id", "level", "created_at"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(8), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1, higher = riskier
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(30), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    data_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    override_level: Mapped[str | None] = mapped_column(String(8))
    override_reason: Mapped[str | None] = mapped_column(String(300))
    overridden_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispute_note: Mapped[str | None] = mapped_column(String(500))
    outcome: Mapped[str | None] = mapped_column(String(10))
    outcome_at: Mapped[datetime | None]


class Recommendation(IdMixin, TimestampMixin, TenantScoped, Base):
    """REC-001: evidence-backed suggestion with a typed action, routed through the Decision Policy."""

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "status in ('open','accepted','rejected','expired','executed','failed')", name="status"
        ),
        # REC-008: one open recommendation per subject + type.
        Index(
            "uq_recommendation_open",
            "merchant_id",
            "dedupe_key",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("ix_recommendations_status", "merchant_id", "status", "created_at"),
    )

    type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="open", nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(30))
    subject_id: Mapped[str | None] = mapped_column(String(64))
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # what/why keys + vars
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_impact: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    action: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # {type, params}
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("decision_records.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None]
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]
    reason: Mapped[str | None] = mapped_column(String(300))
    baseline: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    outcome_measured_at: Mapped[datetime | None]
