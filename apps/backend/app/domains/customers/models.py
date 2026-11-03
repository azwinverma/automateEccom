"""Customers, channel identities and structured Nepal addresses (CRM-001/002/003, ORD-012)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin


class Customer(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("status in ('active','merged')", name="status"),
        # One live customer per phone number per merchant: chats and orders with the same number join up.
        Index(
            "uq_customers_phone",
            "merchant_id",
            "phone",
            unique=True,
            postgresql_where=text("phone is not null and status = 'active'"),
        ),
    )

    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))  # +977XXXXXXXXXX
    email: Mapped[str | None] = mapped_column(String(254))
    locale: Mapped[str | None] = mapped_column(String(5))
    notes: Mapped[str | None] = mapped_column(String(2000))
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), default=list, server_default="{}", nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    last_seen_at: Mapped[datetime | None]


class CustomerIdentity(IdMixin, TimestampMixin, TenantScoped, Base):
    """How a customer appears on one channel (Messenger PSID, Instagram id, WooCommerce customer…)."""

    __tablename__ = "customer_identities"
    __table_args__ = (UniqueConstraint("merchant_id", "provider", "external_id"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160))


class CustomerAddress(IdMixin, TimestampMixin, TenantScoped, Base):
    """Structured Nepal address. ``completeness`` (0-1) is stored for COD/courier intelligence."""

    __tablename__ = "customer_addresses"
    __table_args__ = (
        CheckConstraint("ward is null or ward between 1 and 35", name="ward"),
        CheckConstraint("status in ('active','archived')", name="status"),
        CheckConstraint("completeness between 0 and 1", name="completeness"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    label: Mapped[str | None] = mapped_column(String(40))
    recipient_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    province: Mapped[str] = mapped_column(String(20), nullable=False)
    district: Mapped[str] = mapped_column(String(30), nullable=False)
    municipality: Mapped[str] = mapped_column(String(120), nullable=False)
    ward: Mapped[int] = mapped_column(Integer, nullable=False)
    area: Mapped[str | None] = mapped_column(String(160))
    landmark: Mapped[str | None] = mapped_column(String(200))
    completeness: Mapped[float] = mapped_column(default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
