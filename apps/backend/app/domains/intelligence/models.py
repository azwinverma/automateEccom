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


# ============================================================================= Phase 6 part B
class ProfitSettings(IdMixin, TimestampMixin, TenantScoped, Base):
    """Merchant inputs for true profit (ANA) and profit-aware suggestions (spec 14 thresholds)."""

    __tablename__ = "profit_settings"
    __table_args__ = (
        UniqueConstraint("merchant_id"),
        CheckConstraint("packaging_cost_minor is null or packaging_cost_minor >= 0", name="packaging"),
        CheckConstraint("min_margin_pct between 0 and 100", name="margin"),
        CheckConstraint("max_return_rate_pct between 0 and 100", name="return_rate"),
    )

    packaging_cost_minor: Mapped[int | None] = mapped_column(BigInteger)  # per order; None = not included
    min_margin_pct: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    min_contribution_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    max_return_rate_pct: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)


class ProductIntelligenceProfile(IdMixin, TenantScoped, Base):
    """PBR-001: one recomputable profile per product. Missing inputs are listed, never zero."""

    __tablename__ = "product_intelligence_profiles"
    __table_args__ = (UniqueConstraint("product_id"), Index("ix_pip_cover", "merchant_id", "cover_days"))

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"))
    units_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_90d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    in_stock_days_90d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    demand_per_day: Mapped[float | None] = mapped_column(Float)  # EWMA over in-stock days
    available: Mapped[int | None] = mapped_column(Integer)  # None = stock not tracked
    cover_days: Mapped[float | None] = mapped_column(Float)
    stockouts_90d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    margin_pct: Mapped[float | None] = mapped_column(Float)
    contribution_per_unit_minor: Mapped[int | None] = mapped_column(BigInteger)
    return_rate: Mapped[float | None] = mapped_column(Float)
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # details + not_included
    completeness: Mapped[float] = mapped_column(Float, nullable=False)
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class ReturnInsight(IdMixin, TimestampMixin, TenantScoped, Base):
    """RTI-002: a return pattern on a product (or one of its variants) with its evidence."""

    __tablename__ = "return_insights"
    __table_args__ = (
        CheckConstraint("status in ('open','acted','dismissed','resolved')", name="status"),
        Index(
            "uq_return_insight_open",
            "merchant_id",
            "product_id",
            "pattern",
            unique=True,
            postgresql_where=text("status in ('open','acted')"),
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="SET NULL")
    )
    pattern: Mapped[str] = mapped_column(String(40), nullable=False)  # high_return_rate | reason:size_small
    status: Mapped[str] = mapped_column(String(10), default="open", nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    sold: Mapped[int] = mapped_column(Integer, nullable=False)
    returned: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_rate: Mapped[float | None] = mapped_column(Float)
    p_value: Mapped[float | None] = mapped_column(Float)
    reasons: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    causes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    acted_at: Mapped[datetime | None]
    post_change_rate: Mapped[float | None] = mapped_column(Float)
    post_change_sold: Mapped[int | None] = mapped_column(Integer)
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)


class CommerceMemoryMetric(IdMixin, TenantScoped, Base):
    """MEM-001/002: named, registered metrics per subject and period. Recomputed idempotently."""

    __tablename__ = "commerce_memory_metrics"
    __table_args__ = (
        UniqueConstraint("merchant_id", "subject_type", "subject_id", "metric", "period", "period_start"),
        CheckConstraint("period in ('day','week','month')", name="period"),
    )

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    metric: Mapped[str] = mapped_column(String(40), nullable=False)
    period: Mapped[str] = mapped_column(String(5), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CommerceMemoryFact(IdMixin, TenantScoped, Base):
    """MEM-003: a versioned, evidence-backed fact. The seller can confirm, correct or reject it."""

    __tablename__ = "commerce_memory_facts"
    __table_args__ = (
        CheckConstraint("status in ('active','superseded','rejected_by_merchant')", name="status"),
        CheckConstraint("source in ('derived','merchant')", name="source"),
        Index(
            "uq_memory_fact_active",
            "merchant_id",
            "subject_type",
            "subject_id",
            "fact_type",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_memory_fact_subject", "merchant_id", "subject_type", "subject_id"),
    )

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    fact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    source: Mapped[str] = mapped_column(String(10), default="derived", nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # seller said it's right
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    valid_to: Mapped[datetime | None]
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(String(300))


# ============================================================================= Phase 7: Creative Intelligence
class ContentChannelMetric(IdMixin, TenantScoped, Base):
    """CNT-013: what the channel (or the seller, typing from the app's insights) reports for a post.

    Cumulative counts at `captured_at`. Source says where the numbers came from; Nivaro never invents them.
    """

    __tablename__ = "content_channel_metrics"
    __table_args__ = (
        CheckConstraint("source in ('channel','manual')", name="source"),
        CheckConstraint(
            "coalesce(views,0) >= 0 and coalesce(likes,0) >= 0 and coalesce(comments,0) >= 0 "
            "and coalesce(shares,0) >= 0 and coalesce(saves,0) >= 0 and coalesce(clicks,0) >= 0",
            name="counts",
        ),
        Index("ix_ccm_post", "post_id", "captured_at"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_posts.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(8), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(40))
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    saves: Mapped[int | None] = mapped_column(Integer)
    clicks: Mapped[int | None] = mapped_column(Integer)
    entered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    captured_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CreativePerformanceMetric(IdMixin, TenantScoped, Base):
    """CGN-001: a post's results over its attribution window (commerce outcomes first)."""

    __tablename__ = "creative_performance_metrics"
    __table_args__ = (UniqueConstraint("post_id", "window_days"),)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_posts.id", ondelete="CASCADE"))
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    window_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    views: Mapped[int | None] = mapped_column(Integer)
    engagements: Mapped[int | None] = mapped_column(Integer)  # likes + comments + shares + saves
    clicks: Mapped[int | None] = mapped_column(Integer)
    metrics_source: Mapped[str | None] = mapped_column(String(8))  # channel | manual | None (no data)
    inquiries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders: Mapped[float] = mapped_column(Float, default=0, nullable=False)  # weighted by attribution
    revenue_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    contribution_minor: Mapped[int | None] = mapped_column(BigInteger)  # None = product cost unknown
    attribution: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CreativeGenomeProfile(IdMixin, TenantScoped, Base):
    """CGN-002: learned content preferences, one immutable version per computation."""

    __tablename__ = "creative_genome_profiles"
    __table_args__ = (UniqueConstraint("merchant_id", "version"),)

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    posts: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preferences: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # learning | ready
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CreativeExperiment(IdMixin, TimestampMixin, TenantScoped, Base):
    """CGN-003: two values of one creative attribute compared with a stopping rule declared up front."""

    __tablename__ = "creative_experiments"
    __table_args__ = (
        CheckConstraint("status in ('running','concluded','stopped')", name="status"),
        CheckConstraint("metric in ('orders','inquiries')", name="metric"),
        CheckConstraint("min_posts between 3 and 50 and max_days between 7 and 90", name="rule"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    hypothesis: Mapped[str] = mapped_column(String(300), nullable=False)
    attribute: Mapped[str] = mapped_column(String(30), nullable=False)
    variant_a: Mapped[str] = mapped_column(String(30), nullable=False)
    variant_b: Mapped[str] = mapped_column(String(30), nullable=False)
    metric: Mapped[str] = mapped_column(String(10), default="orders", nullable=False)
    min_posts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None]
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
