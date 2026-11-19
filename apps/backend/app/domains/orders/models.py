"""Orders, lines (snapshots) and the order timeline (ORD-001…012)."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow

ORDER_STATUSES = (
    "draft",
    "pending_confirmation",
    "confirmed",
    "payment_pending",
    "cod_pending",
    "ready_to_ship",
    "shipped",
    "delivered",
    "completed",
    "cancelled",
    "delivery_failed",
    "returned",
)
PAYMENT_STATUSES = ("unpaid", "pending", "paid", "failed", "refunded", "cod_pending", "cod_collected")
SOURCES = ("chat", "seller", "channel", "api")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} in ({','.join(repr(v) for v in values)})"


class Order(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("merchant_id", "number"),
        CheckConstraint(_in("status", ORDER_STATUSES), name="status"),
        CheckConstraint(_in("payment_status", PAYMENT_STATUSES), name="payment_status"),
        CheckConstraint(_in("source", SOURCES), name="source"),
        CheckConstraint("payment_method in ('cod','prepaid','none')", name="payment_method"),
        CheckConstraint(
            "subtotal_minor >= 0 and discount_minor >= 0 and delivery_fee_minor >= 0 and tax_minor >= 0"
            " and total_minor >= 0",
            name="money_nonneg",
        ),
        CheckConstraint("ship_ward is null or ship_ward between 1 and 35", name="ship_ward"),
        # External imports are idempotent on (connection, external order id); chat/API on source_key.
        Index(
            "uq_orders_external",
            "merchant_id",
            "connection_id",
            "external_order_id",
            unique=True,
            postgresql_where=text("external_order_id is not null"),
        ),
        Index(
            "uq_orders_source_key",
            "merchant_id",
            "source_key",
            unique=True,
            postgresql_where=text("source_key is not null"),
        ),
        Index("ix_orders_status", "merchant_id", "status", "id"),
        Index("ix_orders_customer", "customer_id"),
    )

    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_key: Mapped[str | None] = mapped_column(String(160))
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("channel_connections.id", ondelete="SET NULL")
    )
    external_order_id: Mapped[str | None] = mapped_column(String(120))
    external_number: Mapped[str | None] = mapped_column(String(60))
    conversation_id: Mapped[uuid.UUID | None]  # FK added with conversations
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    discount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    delivery_fee_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(10), default="cod", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(16), default="unpaid", nullable=False)
    # Shipping address snapshot (structured, ORD-012). Imported orders may be incomplete: see ship_text.
    ship_name: Mapped[str | None] = mapped_column(String(160))
    ship_phone: Mapped[str | None] = mapped_column(String(20))
    ship_province: Mapped[str | None] = mapped_column(String(20))
    ship_district: Mapped[str | None] = mapped_column(String(30))
    ship_municipality: Mapped[str | None] = mapped_column(String(120))
    ship_ward: Mapped[int | None] = mapped_column(Integer)
    ship_area: Mapped[str | None] = mapped_column(String(160))
    ship_landmark: Mapped[str | None] = mapped_column(String(200))
    ship_text: Mapped[str | None] = mapped_column(String(600))
    address_completeness: Mapped[float] = mapped_column(default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000))
    cancel_reason: Mapped[str | None] = mapped_column(String(300))
    needs_review: Mapped[str | None] = mapped_column(
        String(40)
    )  # unmatched_items | stock_short | address_incomplete
    confirmed_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    placed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}


class OrderLine(IdMixin, TenantScoped, Base):
    """Snapshot of what was sold: price, SKU and titles at order time never change afterwards."""

    __tablename__ = "order_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="qty"),
        CheckConstraint("cancelled_quantity >= 0 and cancelled_quantity <= quantity", name="cancelled_qty"),
        CheckConstraint("unit_price_minor >= 0 and line_discount_minor >= 0", name="money_nonneg"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="SET NULL")
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="SET NULL")
    )
    sku: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_title: Mapped[str | None] = mapped_column(String(255))
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cancelled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    line_discount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # Phase 6 (ANA): the variant's cost when the order was placed; None = cost not set then.
    unit_cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    matched: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # imported line found in catalog

    @property
    def active_quantity(self) -> int:
        return self.quantity - self.cancelled_quantity

    @property
    def total_minor(self) -> int:
        if not self.quantity:
            return 0
        discount = self.line_discount_minor * self.active_quantity // self.quantity
        return self.unit_price_minor * self.active_quantity - discount


class OrderEvent(IdMixin, TenantScoped, Base):
    """Order timeline: who/what did it, when, from where, automated or manual (ORD-011, APS source)."""

    __tablename__ = "order_events"
    __table_args__ = (Index("ix_order_events_order", "order_id", "id"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str | None] = mapped_column(String(24))
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID | None]
    actor_display: Mapped[str | None] = mapped_column(String(200))
    automated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="api", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(40))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
