from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, utcnow


class AuditLog(IdMixin, Base):
    """Append-only audit trail. UPDATE/DELETE are blocked by a database trigger (see migration).

    ``merchant_id`` is nullable: platform-level events (user login, staff actions) have no tenant.
    Not TenantScoped on purpose — reads always filter by merchant explicitly in the audit service.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_merchant_id_id", "merchant_id", "id"),
        Index("ix_audit_logs_resource", "merchant_id", "resource_type", "resource_id"),
        CheckConstraint("actor_type in ('user','system','automation','ai','staff','webhook')", name="actor"),
    )

    merchant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"))
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID | None]
    actor_display: Mapped[str | None] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), default="api", nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    trace_id: Mapped[str | None] = mapped_column(String(32))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
