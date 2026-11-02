from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin


class Merchant(IdMixin, TimestampMixin, Base):
    """The tenant. Owns stores, members, subscription and all commerce data."""

    __tablename__ = "merchants"
    __table_args__ = (
        CheckConstraint("status in ('active','suspended','closed')", name="status"),
        CheckConstraint("default_locale in ('en','ne')", name="default_locale"),
        CheckConstraint("char_length(currency) = 3", name="currency"),
        CheckConstraint("brand_tone in ('friendly','premium','playful','minimal')", name="brand_tone"),
        CheckConstraint("brand_emoji in ('none','light','lots')", name="brand_emoji"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="NP", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NPR", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kathmandu", nullable=False)
    default_locale: Mapped[str] = mapped_column(String(5), default="ne", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    automation_mode: Mapped[str] = mapped_column(String(16), default="assisted", nullable=False)
    # Brand voice (CNT-001): fed to copy-generation prompts.
    brand_tone: Mapped[str] = mapped_column(
        String(16), default="friendly", server_default="friendly", nullable=False
    )
    brand_emoji: Mapped[str] = mapped_column(
        String(8), default="light", server_default="light", nullable=False
    )
    brand_avoid_words: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), default=list, server_default="{}", nullable=False
    )
    brand_sample_caption: Mapped[str | None] = mapped_column(String(600))


class Store(IdMixin, TimestampMixin, TenantScoped, Base):
    """A brand / storefront under a merchant. Channels and catalogs attach to stores later."""

    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("merchant_id", "slug"),
        CheckConstraint("status in ('active','archived')", name="status"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="NPR", nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)


class Membership(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("merchant_id", "user_id"),
        CheckConstraint("role in ('owner','admin','manager','staff','viewer')", name="role"),
        CheckConstraint("status in ('active','removed')", name="status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Invitation(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint("status in ('pending','accepted','revoked','expired')", name="status"),
        CheckConstraint("role in ('owner','admin','manager','staff','viewer')", name="role"),
        # One live invitation per email per merchant.
        Index(
            "uq_invitations_pending_email",
            "merchant_id",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Envelope-encrypted invite token so the async mailer can build the link; purged on accept/revoke.
    token_sealed: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    accepted_at: Mapped[datetime | None]
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
