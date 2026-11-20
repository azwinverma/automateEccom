"""Procurement (PRO-001…007) and Supplier Intelligence (SPI-001…004), Phase 8 (spec 13).

Suppliers and their per-variant terms live in the catalog (catalog_suppliers, catalog_variant_suppliers).
Purchase orders move draft → pending_approval → approved → sent → partially_received → received
(or cancelled). Receiving is recorded per receipt (a lot) and only good units reach stock; landed cost
(purchase + freight + duty + other, allocated by line value) becomes the variant's moving-average cost.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow

PO_STATUSES = ("draft", "pending_approval", "approved", "sent", "partially_received", "received", "cancelled")
OPEN_PO_STATUSES = ("draft", "pending_approval", "approved", "sent", "partially_received")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} in ({','.join(repr(v) for v in values)})"


class PurchaseOrder(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("merchant_id", "number"),
        UniqueConstraint("merchant_id", "idempotency_key"),
        CheckConstraint(_in("status", PO_STATUSES), name="status"),
        CheckConstraint("source in ('seller','recommendation')", name="source"),
        CheckConstraint(
            "freight_minor >= 0 and duty_minor >= 0 and other_minor >= 0 and subtotal_minor >= 0",
            name="money",
        ),
        Index("ix_po_status", "merchant_id", "status", "created_at"),
    )

    number: Mapped[str] = mapped_column(String(24), nullable=False)  # PO-1001
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_suppliers.id", ondelete="RESTRICT"))
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_locations.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="seller", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    freight_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    duty_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    other_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expected_at: Mapped[datetime | None]
    notes: Mapped[str | None] = mapped_column(String(1000))
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recommendations.id", ondelete="SET NULL")
    )
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("decision_records.id", ondelete="SET NULL")
    )
    approval_reason: Mapped[str | None] = mapped_column(String(40))  # above_threshold | needs_approver
    submitted_at: Mapped[datetime | None]
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    sent_at: Mapped[datetime | None]
    received_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    cancel_reason: Mapped[str | None] = mapped_column(String(300))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}

    @property
    def total_minor(self) -> int:
        return self.subtotal_minor + self.freight_minor + self.duty_minor + self.other_minor


class PurchaseOrderLine(IdMixin, TenantScoped, Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("po_id", "variant_id"),
        CheckConstraint("quantity > 0 and received_quantity >= 0 and defective_quantity >= 0", name="qty"),
        CheckConstraint("unit_cost_minor >= 0", name="cost"),
        Index("ix_po_lines_variant", "variant_id"),
    )

    po_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_variants.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # good + defective
    defective_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PurchaseReceipt(IdMixin, TenantScoped, Base):
    """PRO-005 / SPI-002: one delivery from the supplier = one lot, with its landed cost per unit."""

    __tablename__ = "purchase_receipts"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key"),
        Index("ix_receipts_po", "po_id"),
    )

    po_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_orders.id", ondelete="RESTRICT"))
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_suppliers.id", ondelete="RESTRICT"))
    lot_code: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    received_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    received_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class PurchaseReceiptLine(IdMixin, TenantScoped, Base):
    __tablename__ = "purchase_receipt_lines"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0 and defective_quantity >= 0 and quantity + defective_quantity > 0", name="qty"
        ),
        Index("ix_receipt_lines_variant", "variant_id", "created_at"),
    )

    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_receipts.id", ondelete="CASCADE"))
    po_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"))
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_variants.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # good units put in stock
    defective_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    landed_unit_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class SupplierPerformanceMetric(IdMixin, TenantScoped, Base):
    """SPI-001: how a supplier did over the window, with true economics per unit."""

    __tablename__ = "supplier_performance_metrics"
    __table_args__ = (UniqueConstraint("merchant_id", "supplier_id", "window_days"),)

    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_suppliers.id", ondelete="CASCADE"))
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    received_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_unit_cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    avg_landed_cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    defect_rate: Mapped[float | None] = mapped_column(Float)
    sold_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    return_rate: Mapped[float | None] = mapped_column(Float)
    quality_return_rate: Mapped[float | None] = mapped_column(Float)  # quality/not-as-described/wrong item
    on_time_rate: Mapped[float | None] = mapped_column(Float)
    lead_time_days_avg: Mapped[float | None] = mapped_column(Float)
    lead_time_days_sd: Mapped[float | None] = mapped_column(Float)
    fill_rate: Mapped[float | None] = mapped_column(Float)
    contribution_per_unit_minor: Mapped[int | None] = mapped_column(BigInteger)
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # components + not_included
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
