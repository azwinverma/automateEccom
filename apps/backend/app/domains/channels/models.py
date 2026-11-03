"""Channel connections, OAuth state, webhook inbox and channel listings (CHN-003/004/010/011/013, CAT-010)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin, utcnow


class ChannelConnection(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "channel_connections"
    __table_args__ = (
        CheckConstraint("status in ('connected','expired','revoked','error','disconnected')", name="status"),
        Index(
            "uq_channel_live_account",
            "merchant_id",
            "provider",
            "external_account_id",
            unique=True,
            postgresql_where=text("status <> 'disconnected'"),
        ),
        Index("ix_channel_token_expiry", "token_expires_at", postgresql_where=text("status = 'connected'")),
    )

    store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="connected", nullable=False)
    access_token_sealed: Mapped[str | None] = mapped_column(String(4096))
    refresh_token_sealed: Mapped[str | None] = mapped_column(String(4096))
    token_expires_at: Mapped[datetime | None]
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(80)), default=list, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list, nullable=False)
    last_health_check_at: Mapped[datetime | None]
    last_healthy_at: Mapped[datetime | None]
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    disconnected_at: Mapped[datetime | None]
    # Per-connection webhook signing secret (stores like WooCommerce sign each webhook with its own secret).
    webhook_secret_sealed: Mapped[str | None] = mapped_column(String(1024))
    webhook_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), default=list, server_default="{}", nullable=False
    )
    webhooks_registered_at: Mapped[datetime | None]


class OAuthState(IdMixin, TenantScoped, Base):
    """Single-use, short-lived OAuth state bound to merchant + user + provider (CSRF protection)."""

    __tablename__ = "channel_oauth_states"

    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"))
    reconnect_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("channel_connections.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None]


class WebhookEvent(IdMixin, Base):
    """Raw inbound webhook record (CHN-010/011). Unique (provider, external_event_id) is the dedupe key;
    duplicates from provider retries are acknowledged but never processed twice."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "external_event_id"),
        CheckConstraint("status in ('received','processed','ignored','failed','dead')", name="status"),
        Index("ix_webhook_status", "status", "received_at"),
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("merchants.id", ondelete="SET NULL"))
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("channel_connections.id", ondelete="SET NULL")
    )
    external_account_id: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="received", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    received_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    occurred_at: Mapped[datetime | None]
    processed_at: Mapped[datetime | None]


class ChannelListing(IdMixin, TimestampMixin, TenantScoped, Base):
    """A product's presence on one connected channel (CAT-010)."""

    __tablename__ = "channel_listings"
    __table_args__ = (
        UniqueConstraint("connection_id", "product_id"),
        CheckConstraint(
            "status in ('pending','publishing','published','failed','out_of_sync',"
            "'unpublishing','unpublished')",
            name="status",
        ),
        CheckConstraint("price_override_minor is null or price_override_minor >= 0", name="price"),
        Index("ix_listing_product", "product_id"),
        CheckConstraint(
            "drift_code is null or drift_code in "
            "('missing_on_channel','hidden_on_channel','price_changed','variants_changed')",
            name="drift_code",
        ),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channel_connections.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"))
    external_id: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    price_override_minor: Mapped[int | None] = mapped_column(BigInteger)
    title_override: Mapped[str | None] = mapped_column(String(255))
    desired_state: Mapped[str] = mapped_column(String(16), default="published", nullable=False)
    published_product_version: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_synced_at: Mapped[datetime | None]
    # CHN-012: what reconciliation last found on the channel. Drift is reported, never silently overwritten.
    drift_code: Mapped[str | None] = mapped_column(String(32))
    drift_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    drift_detected_at: Mapped[datetime | None]
    last_reconciled_at: Mapped[datetime | None]
