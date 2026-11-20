from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.errors import NotFound
from app.domains.automation import control, engine, policy
from app.domains.automation.actions import ACTIONS
from app.domains.automation.facts import FIELDS, OPS, TRIGGERS
from app.domains.automation.models import DecisionRecord, Workflow, WorkflowRun
from app.domains.automation.templates import BY_CODE, TEMPLATES

router = APIRouter(tags=["automation"])


@router.get("/automation/catalog")
def catalog(ctx: TenantContext = Depends(require("automation.read"))) -> dict[str, Any]:
    """What the builder can offer: triggers (+ filter values), condition fields per subject, actions."""
    return {
        "triggers": [
            {
                "code": t.code,
                "subject": t.subject,
                "filter_values": list(t.filter_values),
                "fields": FIELDS.get(t.subject, {}),
            }
            for t in TRIGGERS.values()
        ],
        "ops": list(OPS),
        "actions": [
            {
                "code": a.code,
                "risk_class": a.risk,
                "subjects": list(a.subjects),
                "params": list(a.params),
                "required_params": list(a.required_params),
            }
            for a in ACTIONS.values()
        ],
        "templates": TEMPLATES,
    }


class WorkflowIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    definition: dict[str, Any] | None = None
    template_code: str | None = Field(default=None, max_length=60)


@router.get("/automation/workflows")
def list_workflows(
    ctx: TenantContext = Depends(require("automation.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    rows = db.scalars(select(Workflow).order_by(Workflow.created_at))
    return {"items": [engine.workflow_view(db, w) for w in rows]}


@router.post("/automation/workflows", status_code=201)
def create_workflow(
    body: WorkflowIn,
    ctx: TenantContext = Depends(require("automation.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    definition = body.definition
    if definition is None:
        tpl = BY_CODE.get(body.template_code or "")
        if tpl is None:
            raise NotFound(code="template_not_found")
        definition = tpl["definition"]
    w = engine.create(
        db, ctx, body.name, definition, description=body.description, template_code=body.template_code
    )
    return engine.workflow_view(db, w, detail=True)


@router.get("/automation/workflows/{workflow_id}")
def get_workflow(
    workflow_id: uuid.UUID,
    ctx: TenantContext = Depends(require("automation.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return engine.workflow_view(db, engine.get_workflow(db, ctx, workflow_id), detail=True)


class WorkflowPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    definition: dict[str, Any] | None = None


@router.patch("/automation/workflows/{workflow_id}")
def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowPatch,
    ctx: TenantContext = Depends(require("automation.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    w = engine.update(
        db, ctx, workflow_id, name=body.name, description=body.description, definition=body.definition
    )
    return engine.workflow_view(db, w, detail=True)


class StatusIn(BaseModel):
    status: Literal["active", "paused"]


@router.post("/automation/workflows/{workflow_id}/status")
def set_status(
    workflow_id: uuid.UUID,
    body: StatusIn,
    ctx: TenantContext = Depends(require("automation.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Turning a workflow on lets it act for the shop, so it needs automation.approve."""
    return engine.workflow_view(db, engine.set_status(db, ctx, workflow_id, body.status), detail=True)


class DryRunIn(BaseModel):
    definition: dict[str, Any]
    subject_id: uuid.UUID | None = None


@router.post("/automation/dry-run")
def dry_run(
    body: DryRunIn,
    ctx: TenantContext = Depends(require("automation.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return engine.dry_run(db, ctx, body.definition, str(body.subject_id) if body.subject_id else None)


@router.get("/automation/workflows/{workflow_id}/runs")
def workflow_runs(
    workflow_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require("automation.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    w = engine.get_workflow(db, ctx, workflow_id)
    rows = db.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == w.id)
        .order_by(WorkflowRun.id.desc())
        .limit(limit)
    )
    return {"items": [engine.run_view(db, r, detail=True) for r in rows]}


# ----------------------------------------------------------------------------- approvals
@router.get("/automation/approvals")
def approvals(
    ctx: TenantContext = Depends(require("automation.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return {"items": [engine.approval_view(db, sr) for sr in engine.pending_approvals(db)]}


class ResolveIn(BaseModel):
    note: str | None = Field(default=None, max_length=300)


@router.post("/automation/approvals/{step_run_id}/approve")
def approve(
    step_run_id: uuid.UUID,
    body: ResolveIn,
    ctx: TenantContext = Depends(require("automation.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return engine.run_view(db, engine.resolve_approval(db, ctx, step_run_id, True, body.note), detail=True)


@router.post("/automation/approvals/{step_run_id}/reject")
def reject(
    step_run_id: uuid.UUID,
    body: ResolveIn,
    ctx: TenantContext = Depends(require("automation.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return engine.run_view(db, engine.resolve_approval(db, ctx, step_run_id, False, body.note), detail=True)


# ----------------------------------------------------------------------------- policy + decisions
@router.get("/automation/policy")
def get_policy(
    ctx: TenantContext = Depends(require("automation.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return policy.settings_view(policy.settings(db, ctx.merchant_id))


class PolicyIn(BaseModel):
    confidence_threshold: float | None = Field(default=None, ge=0.5, le=1.0)
    thresholds: dict[str, int] | None = None
    enabled_r2: list[str] | None = Field(default=None, max_length=10)


@router.patch("/automation/policy")
def update_policy(
    body: PolicyIn,
    ctx: TenantContext = Depends(require("automation.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    s = policy.update_settings(
        db,
        ctx,
        thresholds=body.thresholds,
        enabled_r2=body.enabled_r2,
        confidence_threshold=body.confidence_threshold,
    )
    return policy.settings_view(s)


@router.get("/automation/decisions")
def decisions(
    decision: Literal["AUTO_EXECUTE", "REQUIRE_APPROVAL", "BLOCK"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require("automation.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(DecisionRecord).order_by(DecisionRecord.created_at.desc()).limit(limit)
    if decision:
        stmt = stmt.where(DecisionRecord.decision == decision)
    return {"items": [policy.decision_view(d) for d in db.scalars(stmt)]}


@router.get("/control-center")
def control_center(
    days: int = Query(default=7, ge=1, le=90),
    ctx: TenantContext = Depends(require("merchant.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return control.overview(
        db,
        ctx.merchant_id,
        days,
        include_revenue=ctx.has("orders.read"),
        include_usage=ctx.has("billing.read"),
    )


# ----------------------------------------------------------------------------- autopilot setup
class SetupApplyIn(BaseModel):
    mode: str = Field(default="smart", pattern="^(assisted|smart|autopilot)$")
    posting: bool = True
    campaigns: bool = True


@router.get("/automation/setup")
def setup_readiness(
    ctx: TenantContext = Depends(require("automation.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    """The end-to-end selling checklist: what's connected, what runs by itself, what to do next."""
    from app.domains.automation import setup

    return setup.readiness(db, ctx.merchant_id)


@router.post("/automation/setup/apply")
def setup_apply(
    body: SetupApplyIn,
    ctx: TenantContext = Depends(require("automation.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Turn the recommended automations on in one go (each change audited; plan limits apply)."""
    from app.domains.automation import setup

    return setup.apply(db, ctx, mode=body.mode, posting=body.posting, campaigns=body.campaigns)
