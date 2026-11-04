"""Payments and COD records (PAY-002…005, 008, 009)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin

PAYMENT_STATUSES = ("pending", "paid", "failed", "cancelled", "needs_review", "refunded")
COD_STATUSES = (
    "requested",
    "approved",
    "handed_to_courier",
    "delivered",
    "cash_collected",
    "settlement_pending",
    "settled",
    "failed_delivery",
    "returned_to_origin",
    "cancelled",
)


class Payment(IdMixin, TimestampMixin, TenantScoped, Base):
    """One payment attempt for an order: an online intent (verified server-side) or a seller-recorded one."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(f"status in ({','.join(repr(s) for s in PAYMENT_STATUSES)})", name="status"),
        CheckConstraint("amount_minor > 0", name="amount"),
        CheckConstraint("kind in ('online','manual')", name="kind"),
        UniqueConstraint("merchant_id", "idempotency_key"),
        Index(
            "uq_payments_provider_id",
            "provider",
            "provider_payment_id",
            unique=True,
            postgresql_where=text("provider_payment_id is not null"),
        ),
        Index("ix_payments_order", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)  # sandbox_wallet | manual | …
    method: Mapped[str | None] = mapped_column(
        String(30)
    )  # bank_transfer | esewa | khalti | fonepay | cash | other
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_minor: Mapped[int | None] = mapped_column(BigInteger)  # what the provider confirmed
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(120))
    redirect_url: Mapped[str | None] = mapped_column(String(1000))
    reference: Mapped[str | None] = mapped_column(String(120))  # seller's bank/wallet reference
    failure_code: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    verified_at: Mapped[datetime | None]
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class CODRecord(IdMixin, TimestampMixin, TenantScoped, Base):
    """Cash-on-delivery money trail per order: from request to settlement (settlement lands in Phase 3)."""

    __tablename__ = "cod_records"
    __table_args__ = (
        UniqueConstraint("order_id"),
        CheckConstraint(f"status in ({','.join(repr(s) for s in COD_STATUSES)})", name="status"),
        CheckConstraint("amount_minor >= 0 and collected_minor >= 0", name="amounts"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24), default="requested", nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    collected_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
