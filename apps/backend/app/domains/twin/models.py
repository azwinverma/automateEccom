"""Digital Store Twin (TWIN-001…006) and simulations (SIM-001…006), Phase 9 (specs 03, 04, 14).

The Twin is a derived, read-only model of the live business. Sections are recomputed from Commerce Core
(never written by clients); every section carries `source_version` (monotonic), `as_of` and
`computed_at`. Readers that need exact values call Commerce Core.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
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


class StoreTwinSection(IdMixin, TenantScoped, Base):
    __tablename__ = "store_twin_sections"
    __table_args__ = (UniqueConstraint("merchant_id", "section"),)

    section: Mapped[str] = mapped_column(String(30), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_version: Mapped[int] = mapped_column(BigInteger, nullable=False)  # µs of the newest applied change
    as_of: Mapped[datetime] = mapped_column(nullable=False)  # when the source data was read
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    trigger: Mapped[str] = mapped_column(String(40), nullable=False)  # event type | reconcile | read
    lag_ms: Mapped[int | None] = mapped_column(Integer)  # event created → section updated


class StoreTwinSnapshot(IdMixin, TenantScoped, Base):
    __tablename__ = "store_twin_snapshots"
    __table_args__ = (UniqueConstraint("merchant_id", "snapshot_on"),)

    snapshot_on: Mapped[date] = mapped_column(Date, nullable=False)
    sections: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class SimulationRun(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        CheckConstraint("kind in ('discount','purchase_quantity','ad_budget')", name="kind"),
        CheckConstraint("status in ('queued','running','completed','failed')", name="status"),
        Index("ix_sim_runs", "merchant_id", "created_at"),
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="queued", nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    outputs: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    assumptions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[str | None] = mapped_column(String(8))  # low | medium | high
    method_version: Mapped[str] = mapped_column(String(20), nullable=False)
    baseline_as_of: Mapped[datetime | None]
    error_code: Mapped[str | None] = mapped_column(String(60))
    completed_at: Mapped[datetime | None]
    # SIM-006: what actually happened over the simulated window (when it can be measured).
    actual: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    abs_pct_error: Mapped[float | None] = mapped_column(Float)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
