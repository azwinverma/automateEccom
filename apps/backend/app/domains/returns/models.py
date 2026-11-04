"""Returns, exchanges and refunds (RET-001…011, PAY-007).

Flow (spec 12): requested → (eligibility) → approved | rejected → return shipment → received →
inspected → refunded | exchanged → closed. Reasons are a controlled vocabulary (+ free text) from day
one: Return Intelligence (Phase 6) learns from them.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin

RETURN_REASONS = (
    "size_small",
    "size_large",
    "colour_different",
    "quality_defect",
    "damaged_in_transit",
    "not_as_described",
    "changed_mind",
    "late_delivery",
    "wrong_item",
    "other",
)
# The shop's fault: the shop pays return shipping, and these need a photo as evidence by default.
SHOP_FAULT_REASONS = ("quality_defect", "damaged_in_transit", "not_as_described", "wrong_item")
RETURN_STATUSES = (
    "requested",
    "approved",
    "rejected",
    "in_transit",
    "received",
    "inspected",
    "refunded",
    "exchanged",
    "closed",
    "cancelled",
)
OPEN_RETURN_STATUSES = ("requested", "approved", "in_transit", "received", "inspected")
CONDITIONS = ("resellable", "damaged", "missing", "used")
REFUND_STATUSES = ("pending_approval", "processing", "succeeded", "failed", "rejected")
REFUND_METHODS = ("original_payment", "bank_transfer", "esewa", "khalti", "fonepay", "cash", "other")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} in ({','.join(repr(v) for v in values)})"


class ReturnPolicy(IdMixin, TimestampMixin, TenantScoped, Base):
    """One per merchant (RET-001). Defaults are conservative: nothing happens automatically."""

    __tablename__ = "return_policies"
    __table_args__ = (
        UniqueConstraint("merchant_id"),
        CheckConstraint("window_days between 0 and 90", name="window"),
        CheckConstraint("auto_refund_max_minor >= 0 and return_shipping_fee_minor >= 0", name="money"),
    )

    window_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    allow_refund: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_exchange: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String(24)), default=lambda: list(SHOP_FAULT_REASONS), nullable=False
    )
    # Charged (deducted from the refund) when the customer is at fault, e.g. changed mind / size.
    return_shipping_fee_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # RET-010: refunds up to this amount go through without a manager; 0 = every refund is approved.
    auto_refund_max_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000))  # shown to staff (and later customers)


class ReturnRequest(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "return_requests"
    __table_args__ = (
        UniqueConstraint("merchant_id", "number"),
        UniqueConstraint("merchant_id", "idempotency_key"),
        CheckConstraint(_in("status", RETURN_STATUSES), name="status"),
        CheckConstraint("resolution in ('refund','exchange')", name="resolution"),
        CheckConstraint("source in ('seller','chat','customer')", name="source"),
        Index("ix_returns_status", "merchant_id", "status", "id"),
    )

    number: Mapped[str] = mapped_column(String(24), nullable=False)  # R-1001-1
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="requested", nullable=False)
    resolution: Mapped[str] = mapped_column(String(10), default="refund", nullable=False)
    source: Mapped[str] = mapped_column(String(10), default="seller", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    # RET-002: the eligibility checks at request time (kept: the policy may change later).
    eligibility: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(300))  # approved despite failing checks
    # RET-011: abuse signals (merchant-scoped operational facts only), shown to the seller.
    signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    customer_pays_shipping: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    return_shipping_fee_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    refund_due_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000))
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_by: Mapped[str | None] = mapped_column(String(16))  # seller | automation
    decided_at: Mapped[datetime | None]
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    received_at: Mapped[datetime | None]
    inspected_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    exchange_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ReturnLine(IdMixin, TenantScoped, Base):
    __tablename__ = "return_lines"
    __table_args__ = (
        CheckConstraint(_in("reason", RETURN_REASONS), name="reason"),
        CheckConstraint("condition is null or " + _in("condition", CONDITIONS), name="condition"),
        CheckConstraint("quantity > 0", name="qty"),
        Index("ix_return_lines_return", "return_id"),
        Index("ix_return_lines_order_line", "order_line_id"),
    )

    return_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("return_requests.id", ondelete="CASCADE"))
    order_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_lines.id", ondelete="RESTRICT"))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="SET NULL")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_refund_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # paid per unit, net of discount
    reason: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_note: Mapped[str | None] = mapped_column(String(500))
    evidence_asset_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), default=list, nullable=False)
    exchange_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="SET NULL")
    )
    condition: Mapped[str | None] = mapped_column(String(12))  # set at inspection (RET-007)
    restocked_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inspection_note: Mapped[str | None] = mapped_column(String(500))


class Refund(IdMixin, TimestampMixin, TenantScoped, Base):
    """Idempotent, provider-tracked, threshold-controlled (PAY-007, RET-009/010)."""

    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key"),
        CheckConstraint(_in("status", REFUND_STATUSES), name="status"),
        CheckConstraint(_in("method", REFUND_METHODS), name="method"),
        CheckConstraint("amount_minor > 0", name="amount"),
        Index(
            "uq_refunds_provider",
            "provider",
            "provider_refund_id",
            unique=True,
            postgresql_where=text("provider_refund_id is not null"),
        ),
        Index("ix_refunds_order", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    return_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("return_requests.id", ondelete="SET NULL"))
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(40))
    provider_refund_id: Mapped[str | None] = mapped_column(String(120))
    reference: Mapped[str | None] = mapped_column(String(120))  # seller's transfer reference (manual)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300))
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
