"""Inventory: locations, immutable ledger, current levels, reservations (INV-001…008).

The ledger is the truth; ``inventory_levels`` is the running total per variant x location, updated in
the same transaction as each ledger entry and row-locked during changes so reservations can't oversell
(same approach as the billing counters, ADR-005). A variant is *tracked* once it has a level row.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow


class InventoryLocation(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "inventory_locations"
    __table_args__ = (
        UniqueConstraint("merchant_id", "code"),
        CheckConstraint("status in ('active','archived')", name="status"),
        Index(
            "uq_inventory_default_location",
            "merchant_id",
            unique=True,
            postgresql_where=text("is_default and status = 'active'"),
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    district: Mapped[str | None] = mapped_column(String(30))  # origin district for courier routes
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)


class InventoryLevel(IdMixin, TenantScoped, Base):
    __tablename__ = "inventory_levels"
    __table_args__ = (
        UniqueConstraint("variant_id", "location_id"),
        CheckConstraint("on_hand >= 0 and reserved >= 0 and damaged >= 0", name="nonneg"),
        CheckConstraint("reserved <= on_hand", name="reserved_le_on_hand"),
        CheckConstraint("low_stock_threshold is null or low_stock_threshold >= 0", name="threshold"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_locations.id", ondelete="RESTRICT"))
    on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damaged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


LEDGER_KINDS = (
    "receive",
    "adjust",
    "count",
    "damage",
    "reserve",
    "release",
    "commit",
    "return_to_stock",
    "transfer_out",
    "transfer_in",
)


class InventoryLedgerEntry(IdMixin, TenantScoped, Base):
    """Append-only (UPDATE/DELETE blocked by a trigger). Deltas apply to the level's counters."""

    __tablename__ = "inventory_ledger"
    __table_args__ = (
        CheckConstraint(f"kind in ({','.join(repr(k) for k in LEDGER_KINDS)})", name="kind"),
        Index("ix_inventory_ledger_variant", "merchant_id", "variant_id", "id"),
        Index(
            "uq_inventory_ledger_key",
            "merchant_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key is not null"),
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_variants.id", ondelete="RESTRICT"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_locations.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    on_hand_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damaged_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_hand_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300))
    reference_type: Mapped[str | None] = mapped_column(String(40))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID | None]
    idempotency_key: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class InventoryReservation(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="qty"),
        CheckConstraint("status in ('active','committed','released','expired')", name="status"),
        # One reservation per order line: retries re-use it instead of double-reserving.
        UniqueConstraint(
            "merchant_id", "reference_type", "reference_id", "variant_id", name="uq_inventory_reservation_ref"
        ),
        Index("ix_inventory_reservations_expiry", "expires_at", postgresql_where=text("status = 'active'")),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_variants.id", ondelete="CASCADE"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_locations.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    reference_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime | None]
