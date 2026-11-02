"""Subscription, entitlement, usage and credit models (specs/08_SUBSCRIPTIONS_BILLING_USAGE.md).

Plans, versions, features and limits are data. Business code asks the EntitlementService about a
feature code or a metered resource; it never inspects plan names.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow

PERIODS = ("month", "day", "lifetime")
OVERAGE_POLICIES = ("block", "credits", "overage")


class Feature(TimestampMixin, Base):
    __tablename__ = "billing_features"

    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class MeteredResource(TimestampMixin, Base):
    __tablename__ = "billing_resources"
    __table_args__ = (CheckConstraint("kind in ('consumable','gauge')", name="kind"),)

    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    # consumable: counted per period (AI generations). gauge: current count (products, members).
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Credits consumed per unit when the overage policy is 'credits'.
    credits_per_unit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Plan(TimestampMixin, IdMixin, Base):
    __tablename__ = "billing_plans"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    tagline_key: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_public: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_default_for_signup: Mapped[bool] = mapped_column(default=False, nullable=False)


class PlanVersion(TimestampMixin, IdMixin, Base):
    __tablename__ = "billing_plan_versions"
    __table_args__ = (
        UniqueConstraint("plan_id", "version"),
        CheckConstraint("status in ('draft','active','retired')", name="status"),
        Index(
            "uq_plan_versions_one_active", "plan_id", unique=True, postgresql_where=text("status = 'active'")
        ),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_plans.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NPR", nullable=False)
    # Null = price not configured (pricing comes from GTM; never invented in code).
    price_monthly_minor: Mapped[int | None] = mapped_column(BigInteger)
    price_annual_minor: Mapped[int | None] = mapped_column(BigInteger)
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PlanEntitlement(Base):
    __tablename__ = "billing_plan_entitlements"

    plan_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("billing_plan_versions.id", ondelete="CASCADE"), primary_key=True
    )
    feature_code: Mapped[str] = mapped_column(ForeignKey("billing_features.code"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(nullable=False)


class PlanLimit(Base):
    __tablename__ = "billing_plan_limits"
    __table_args__ = (
        CheckConstraint("period in ('month','day','lifetime')", name="period"),
        CheckConstraint("overage_policy in ('block','credits','overage')", name="overage"),
        CheckConstraint("limit_value is null or limit_value >= 0", name="limit_nonneg"),
    )

    plan_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("billing_plan_versions.id", ondelete="CASCADE"), primary_key=True
    )
    resource_code: Mapped[str] = mapped_column(ForeignKey("billing_resources.code"), primary_key=True)
    period: Mapped[str] = mapped_column(String(16), primary_key=True)
    limit_value: Mapped[int | None] = mapped_column(BigInteger)  # null = unlimited
    overage_policy: Mapped[str] = mapped_column(String(16), default="block", nullable=False)
    overage_unit_price_minor: Mapped[int | None] = mapped_column(BigInteger)


class AddOn(TimestampMixin, IdMixin, Base):
    __tablename__ = "billing_addons"

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_code: Mapped[str | None] = mapped_column(ForeignKey("billing_resources.code"))
    period: Mapped[str | None] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    feature_code: Mapped[str | None] = mapped_column(ForeignKey("billing_features.code"))
    price_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="NPR", nullable=False)


class Subscription(TimestampMixin, IdMixin, TenantScoped, Base):
    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        CheckConstraint("status in ('trialing','active','past_due','canceled','expired')", name="status"),
        CheckConstraint("billing_interval in ('month','year')", name="interval"),
        Index(
            "uq_subscriptions_one_live",
            "merchant_id",
            unique=True,
            postgresql_where=text("status in ('trialing','active','past_due')"),
        ),
    )

    plan_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_plan_versions.id"))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(8), default="month", nullable=False)
    trial_ends_at: Mapped[datetime | None]
    current_period_start: Mapped[datetime] = mapped_column(nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(nullable=False)
    cancel_at: Mapped[datetime | None]


class SubscriptionAddOn(TimestampMixin, IdMixin, TenantScoped, Base):
    __tablename__ = "billing_subscription_addons"

    subscription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_subscriptions.id"), index=True)
    addon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_addons.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class EntitlementOverride(TimestampMixin, IdMixin, TenantScoped, Base):
    """Admin/support override of a feature or limit for one merchant (audited, optionally expiring)."""

    __tablename__ = "billing_entitlement_overrides"
    __table_args__ = (
        CheckConstraint("(feature_code is not null) <> (resource_code is not null)", name="one_target"),
    )

    feature_code: Mapped[str | None] = mapped_column(ForeignKey("billing_features.code"))
    enabled: Mapped[bool | None]
    resource_code: Mapped[str | None] = mapped_column(ForeignKey("billing_resources.code"))
    period: Mapped[str | None] = mapped_column(String(16))
    limit_value: Mapped[int | None] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime | None]


class UsageCounter(TenantScoped, Base):
    """UsageAggregate: running total per merchant/resource/period window. Row-locked during reserve."""

    __tablename__ = "billing_usage_counters"
    __table_args__ = (
        CheckConstraint("used >= 0 and reserved >= 0", name="nonneg"),
        UniqueConstraint("merchant_id", "resource_code", "period", "period_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    resource_code: Mapped[str] = mapped_column(ForeignKey("billing_resources.code"))
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime | None]
    used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)


class UsageReservation(IdMixin, TenantScoped, Base):
    __tablename__ = "billing_usage_reservations"
    __table_args__ = (
        CheckConstraint("status in ('reserved','finalized','released','expired')", name="status"),
        CheckConstraint("funding in ('quota','credits','overage')", name="funding"),
        UniqueConstraint("merchant_id", "idempotency_key"),
        Index("ix_reservations_open", "expires_at", postgresql_where=text("status = 'reserved'")),
    )

    resource_code: Mapped[str] = mapped_column(ForeignKey("billing_resources.code"))
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    finalized_quantity: Mapped[int | None] = mapped_column(BigInteger)
    funding: Mapped[str] = mapped_column(String(16), default="quota", nullable=False)
    credits_held: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="reserved", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    # Counter windows touched (month/day...) so finalize/release adjust the same rows.
    counter_ids: Mapped[str] = mapped_column(String(400), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    settled_at: Mapped[datetime | None]


class UsageEvent(IdMixin, TenantScoped, Base):
    """Immutable record of consumed usage (billing evidence)."""

    __tablename__ = "billing_usage_events"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key"),
        Index("ix_usage_events_merchant_resource", "merchant_id", "resource_code", "occurred_at"),
    )

    resource_code: Mapped[str] = mapped_column(ForeignKey("billing_resources.code"))
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    funding: Mapped[str] = mapped_column(String(16), default="quota", nullable=False)
    credits_charged: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("billing_usage_reservations.id"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class UsageAlert(IdMixin, TenantScoped, Base):
    __tablename__ = "billing_usage_alerts"
    __table_args__ = (
        UniqueConstraint("merchant_id", "resource_code", "period", "period_start", "threshold"),
    )

    resource_code: Mapped[str] = mapped_column(ForeignKey("billing_resources.code"))
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)  # 70 / 85 / 100
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class CreditWallet(TimestampMixin, IdMixin, TenantScoped, Base):
    __tablename__ = "billing_credit_wallets"
    __table_args__ = (UniqueConstraint("merchant_id"), CheckConstraint("balance >= 0", name="nonneg"))

    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)


class CreditTransaction(IdMixin, TenantScoped, Base):
    __tablename__ = "billing_credit_transactions"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key"),
        CheckConstraint(
            "kind in ('grant','purchase','hold','release','consume','refund','expire','adjustment')",
            name="kind",
        ),
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_credit_wallets.id"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # signed
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
