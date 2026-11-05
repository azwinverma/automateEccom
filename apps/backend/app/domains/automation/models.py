"""Automation engine and Autonomous Decision Policy (AUT-001…019, spec 06).

Workflow (+ immutable WorkflowVersion) → WorkflowRun (pins a version) → WorkflowStepRun.
Every automated decision writes a DecisionRecord; every operational action (automated or not)
writes an AutomationActionLog row, which is the Autopilot Score source (spec 14).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
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

RISK_CLASSES = ("R0", "R1", "R2", "R3", "R4")
DECISIONS = ("AUTO_EXECUTE", "REQUIRE_APPROVAL", "BLOCK")
RUN_STATUSES = ("running", "waiting", "awaiting_approval", "completed", "failed", "cancelled", "skipped")
STEP_STATUSES = (
    "pending",
    "running",
    "done",
    "skipped",
    "awaiting_approval",
    "approved",
    "rejected",
    "blocked",
    "failed",
)
PERFORMED_BY = ("automation", "ai", "user", "system")
OUTCOMES = ("success", "failed", "reverted", "pending")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} in ({','.join(repr(v) for v in values)})"


class AutomationSettings(IdMixin, TimestampMixin, TenantScoped, Base):
    """Merchant thresholds and R2 opt-ins for the Decision Policy (AUT-016/017)."""

    __tablename__ = "automation_settings"
    __table_args__ = (
        UniqueConstraint("merchant_id"),
        CheckConstraint("confidence_threshold between 0.5 and 1", name="confidence"),
    )

    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    # Money thresholds in minor units; percentages as whole numbers. Above → approval (R3).
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # R2 actions the merchant allowed to run automatically (still subject to mode + confidence).
    enabled_r2: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)


class Workflow(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint("status in ('draft','active','paused')", name="status"),
        Index("ix_workflows_trigger", "merchant_id", "trigger_event", "status"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default="draft", nullable=False)
    template_code: Mapped[str | None] = mapped_column(String(60))
    trigger_event: Mapped[str] = mapped_column(String(60), nullable=False)  # denormalised for lookup
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="SET NULL", use_alter=True)
    )
    paused_reason: Mapped[str | None] = mapped_column(String(120))  # e.g. circuit_breaker:book_courier
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class WorkflowVersion(IdMixin, TenantScoped, Base):
    """Immutable: an edit creates a new version; runs pin the version they started with."""

    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version"),)

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class WorkflowRun(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        CheckConstraint(_in("status", RUN_STATUSES), name="status"),
        # One run per workflow per triggering event (outbox redelivery can't double-run).
        UniqueConstraint("workflow_id", "trigger_key"),
        Index("ix_workflow_runs_due", "next_run_at", postgresql_where=text("status = 'waiting'")),
        Index("ix_workflow_runs_workflow", "workflow_id", "id"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_versions.id", ondelete="RESTRICT"))
    trigger_event: Mapped[str] = mapped_column(String(60), nullable=False)
    trigger_key: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(30))  # order | shipment | return | variant | …
    subject_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # refs, not copies
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(40))
    next_run_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(String(500))
    finished_at: Mapped[datetime | None]


class WorkflowStepRun(IdMixin, TenantScoped, Base):
    __tablename__ = "workflow_step_runs"
    __table_args__ = (
        CheckConstraint(_in("status", STEP_STATUSES), name="status"),
        UniqueConstraint("run_id", "step_id", "iteration"),
        Index("ix_step_runs_approval", "merchant_id", postgresql_where=text("status = 'awaiting_approval'")),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    step_id: Mapped[str] = mapped_column(String(40), nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(String(500))
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("decision_records.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None]
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class DecisionRecord(IdMixin, TenantScoped, Base):
    """AUT-019: why an automated action ran, waited for approval or was blocked."""

    __tablename__ = "decision_records"
    __table_args__ = (
        CheckConstraint(_in("risk_class", RISK_CLASSES), name="risk"),
        CheckConstraint(_in("decision", DECISIONS), name="decision"),
        Index("ix_decisions_merchant", "merchant_id", "created_at"),
    )

    source: Mapped[str] = mapped_column(String(20), nullable=False)  # workflow | inbox | recovery | returns
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    risk_class: Mapped[str] = mapped_column(String(2), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    rule: Mapped[str] = mapped_column(String(60), nullable=False)  # which policy rule decided
    mode: Mapped[str] = mapped_column(String(12), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    financial_impact_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(3))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # references
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # key + vars
    outcome: Mapped[str | None] = mapped_column(String(20))  # executed | approved | rejected | failed
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class AutomationActionLog(IdMixin, TenantScoped, Base):
    """AUT-018: every operational action with who did it and how it went (APS source)."""

    __tablename__ = "automation_action_logs"
    __table_args__ = (
        CheckConstraint(_in("performed_by", PERFORMED_BY), name="performed_by"),
        CheckConstraint(_in("outcome", OUTCOMES), name="outcome"),
        UniqueConstraint("merchant_id", "dedupe_key"),
        Index("ix_action_logs_merchant", "merchant_id", "occurred_at"),
        Index("ix_action_logs_capability", "merchant_id", "capability", "occurred_at"),
    )

    capability: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(30))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    performed_by: Mapped[str] = mapped_column(String(12), nullable=False)
    outcome: Mapped[str] = mapped_column(String(10), default="success", nullable=False)
    human_intervened: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(String(60))
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("decision_records.id", ondelete="SET NULL")
    )
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
