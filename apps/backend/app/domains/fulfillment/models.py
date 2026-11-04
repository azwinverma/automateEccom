"""Couriers, shipments, tracking, delivery attempts and COD settlements (FUL-001…010, PAY-002/010).

Route keys (origin/destination district) and failure reasons are stored from day one: Courier Brain
and COD Intelligence (Phase 6) learn from them (pull-forward rule, spec 22).
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
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow
from app.domains.integrations.base import FAILURE_REASONS, SHIPMENT_STATUSES

LIVE_STATUSES = (
    "booked",
    "pickup_requested",
    "picked_up",
    "in_transit",
    "out_for_delivery",
    "delivery_failed",
    "reattempt_requested",
    "returning",
)
TERMINAL_STATUSES = ("delivered", "returned_to_origin", "cancelled", "lost")
RECOVERY_STATUSES = (
    "open",
    "awaiting_customer",
    "customer_replied",
    "reattempt_requested",
    "returning",
    "resolved",
    "escalated",
)
SETTLEMENT_STATUSES = ("needs_review", "reconciled", "confirmed")
LINE_MATCH = (
    "matched",
    "amount_mismatch",
    "unknown_shipment",
    "not_delivered",
    "already_settled",
    "duplicate_in_report",
    "not_cod",
)


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} in ({','.join(repr(v) for v in values)})"


class CourierAccount(IdMixin, TimestampMixin, TenantScoped, Base):
    """A merchant's courier: an API courier (credentials sealed) or 'manual' (own rider / no API)."""

    __tablename__ = "courier_accounts"
    __table_args__ = (
        CheckConstraint("status in ('connected','error','disconnected')", name="status"),
        Index(
            "uq_courier_default",
            "merchant_id",
            unique=True,
            postgresql_where=text("is_default and status <> 'disconnected'"),
        ),
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="connected", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list, nullable=False)
    credentials_sealed: Mapped[str | None] = mapped_column(String(4096))
    webhook_secret_sealed: Mapped[str | None] = mapped_column(String(1024))
    # Pickup (origin) address: where the courier collects parcels. Route key = pickup_district.
    pickup_name: Mapped[str | None] = mapped_column(String(160))
    pickup_phone: Mapped[str | None] = mapped_column(String(20))
    pickup_district: Mapped[str | None] = mapped_column(String(30))
    pickup_municipality: Mapped[str | None] = mapped_column(String(120))
    pickup_area: Mapped[str | None] = mapped_column(String(160))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_settlement_sync_at: Mapped[datetime | None]
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    disconnected_at: Mapped[datetime | None]


class FulfillmentSettings(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "fulfillment_settings"
    __table_args__ = (
        UniqueConstraint("merchant_id"),
        CheckConstraint("default_weight_grams between 1 and 100000", name="weight"),
        CheckConstraint("recovery_wait_hours between 1 and 168", name="recovery_wait"),
    )

    # FUL-007: message customers about shipping where we're permitted (a conversation they started).
    notify_customers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_weight_grams: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    # FUL-008: how long to wait for the customer after a failed delivery before escalating.
    recovery_wait_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)


class DeliveryFeeRule(IdMixin, TimestampMixin, TenantScoped, Base):
    """What the merchant charges the customer for delivery: a district rule beats inside-valley,
    which beats the default. Optional free delivery over an order subtotal."""

    __tablename__ = "delivery_fee_rules"
    __table_args__ = (
        CheckConstraint("scope in ('default','inside_valley','district')", name="scope"),
        CheckConstraint("(scope = 'district') = (district is not null)", name="district"),
        CheckConstraint("fee_minor >= 0", name="fee"),
        CheckConstraint("free_over_minor is null or free_over_minor > 0", name="free_over"),
        # One rule per area (Postgres < 15 has no NULLS NOT DISTINCT, hence two partial indexes).
        Index(
            "uq_delivery_fee_scope",
            "merchant_id",
            "scope",
            unique=True,
            postgresql_where=text("district is null"),
        ),
        Index(
            "uq_delivery_fee_district",
            "merchant_id",
            "district",
            unique=True,
            postgresql_where=text("district is not null"),
        ),
    )

    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    district: Mapped[str | None] = mapped_column(String(30))
    fee_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    free_over_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


class Shipment(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint(_in("status", SHIPMENT_STATUSES), name="status"),
        CheckConstraint("weight_grams > 0", name="weight"),
        CheckConstraint(
            "cod_amount_minor >= 0 and (charge_minor is null or charge_minor >= 0)", name="money"
        ),
        UniqueConstraint("merchant_id", "idempotency_key"),
        CheckConstraint("direction in ('outbound','return')", name="direction"),
        CheckConstraint("(direction = 'return') = (return_id is not null)", name="return_link"),
        # One live outbound shipment per order, one live pickup per return; cancelled ones can be replaced.
        Index(
            "uq_shipment_live_order",
            "order_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled' and direction = 'outbound'"),
        ),
        Index(
            "uq_shipment_live_return",
            "return_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled' and direction = 'return'"),
        ),
        Index(
            "uq_shipment_tracking",
            "courier_account_id",
            "tracking_number",
            unique=True,
            postgresql_where=text("tracking_number is not null"),
        ),
        Index("ix_shipments_status", "merchant_id", "status", "id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True)
    # RET-006: a return pickup travels customer → shop and never moves the order or COD.
    direction: Mapped[str] = mapped_column(
        String(10), default="outbound", server_default="outbound", nullable=False
    )
    return_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("return_requests.id", ondelete="RESTRICT"))
    courier_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courier_accounts.id", ondelete="RESTRICT")
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    courier_name: Mapped[str | None] = mapped_column(String(80))  # manual: "Pathao", "own rider"…
    service_code: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="booked", nullable=False)
    provider_shipment_id: Mapped[str | None] = mapped_column(String(120))
    tracking_number: Mapped[str | None] = mapped_column(String(80))
    label_url: Mapped[str | None] = mapped_column(String(1000))
    weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    cod_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    charge_minor: Mapped[int | None] = mapped_column(BigInteger)  # what the courier quoted us
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    eta_days_min: Mapped[int | None] = mapped_column(Integer)
    eta_days_max: Mapped[int | None] = mapped_column(Integer)
    origin_district: Mapped[str | None] = mapped_column(String(30))
    destination_district: Mapped[str | None] = mapped_column(String(30))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    booked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    pickup_reference: Mapped[str | None] = mapped_column(String(80))
    pickup_requested_at: Mapped[datetime | None]
    picked_up_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]
    returned_at: Mapped[datetime | None]
    return_received_at: Mapped[datetime | None]  # goods back on the shelf (seller confirmed)
    cancelled_at: Mapped[datetime | None]
    last_event_at: Mapped[datetime | None]
    last_polled_at: Mapped[datetime | None]
    notes: Mapped[str | None] = mapped_column(String(500))
    # FUL-007: customer notifications already sent for this parcel (shipped, out_for_delivery, …).
    notified: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), default=list, server_default="{}", nullable=False
    )


class ShipmentEvent(IdMixin, TenantScoped, Base):
    __tablename__ = "shipment_events"
    __table_args__ = (
        UniqueConstraint("shipment_id", "event_key"),
        CheckConstraint(_in("status", SHIPMENT_STATUSES), name="status"),
        CheckConstraint("source in ('courier_webhook','courier_poll','seller','system')", name="source"),
        Index("ix_shipment_events_shipment", "shipment_id", "occurred_at"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    event_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    raw_status: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(160))
    failure_reason: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None]
    applied: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # False = out of order
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class DeliveryAttempt(IdMixin, TimestampMixin, TenantScoped, Base):
    """A failed delivery and its recovery (FUL-008): message → reply → reattempt → resolved/escalated."""

    __tablename__ = "delivery_attempts"
    __table_args__ = (
        UniqueConstraint("shipment_id", "attempt_no"),
        CheckConstraint(_in("failure_reason", FAILURE_REASONS), name="failure_reason"),
        CheckConstraint(_in("recovery_status", RECOVERY_STATUSES), name="recovery_status"),
        Index(
            "ix_delivery_attempts_open",
            "merchant_id",
            "recovery_status",
            postgresql_where=text("recovery_status not in ('resolved')"),
        ),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(40), nullable=False)
    failed_at: Mapped[datetime] = mapped_column(nullable=False)
    recovery_status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)
    customer_contacted_at: Mapped[datetime | None]
    customer_reply: Mapped[str | None] = mapped_column(String(1000))
    customer_replied_at: Mapped[datetime | None]
    reattempt_requested_at: Mapped[datetime | None]
    reattempt_note: Mapped[str | None] = mapped_column(String(500))
    reattempt_by: Mapped[str | None] = mapped_column(String(16))  # seller | automation
    escalated_at: Mapped[datetime | None]
    resolved_at: Mapped[datetime | None]
    resolution: Mapped[str | None] = mapped_column(
        String(16)
    )  # delivered | returned | failed_again | cancelled


class CODSettlement(IdMixin, TimestampMixin, TenantScoped, Base):
    """A courier's statement of COD cash collected and paid to the merchant (or a seller-recorded
    hand-over from their own rider). Reconciled line by line against our shipments."""

    __tablename__ = "cod_settlements"
    __table_args__ = (
        CheckConstraint(_in("status", SETTLEMENT_STATUSES), name="status"),
        CheckConstraint("source in ('courier_api','file_import','manual')", name="source"),
        UniqueConstraint("courier_account_id", "reference"),
    )

    courier_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courier_accounts.id", ondelete="RESTRICT")
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="needs_review", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    collected_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    fees_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    net_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expected_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    issue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    period_start: Mapped[datetime | None]
    period_end: Mapped[datetime | None]
    imported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None]
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    bank_reference: Mapped[str | None] = mapped_column(String(120))


class CODSettlementLine(IdMixin, TenantScoped, Base):
    __tablename__ = "cod_settlement_lines"
    __table_args__ = (
        CheckConstraint(_in("match_status", LINE_MATCH), name="match_status"),
        CheckConstraint("collected_minor >= 0 and fee_minor >= 0", name="money"),
        Index("ix_cod_lines_settlement", "settlement_id", "id"),
        Index("ix_cod_lines_shipment", "shipment_id"),
    )

    settlement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cod_settlements.id", ondelete="CASCADE"))
    tracking_number: Mapped[str] = mapped_column(String(80), nullable=False)
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shipments.id", ondelete="SET NULL"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    collected_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fee_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expected_minor: Mapped[int | None] = mapped_column(BigInteger)
    match_status: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    accepted_at: Mapped[datetime | None]  # seller accepted a non-matching line (audited, with reason)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    accept_reason: Mapped[str | None] = mapped_column(String(300))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
