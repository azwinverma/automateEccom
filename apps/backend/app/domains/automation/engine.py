"""Workflow engine (AUT-001/005…015).

Definition (stored in an immutable WorkflowVersion):

    {"trigger": {"event": "order.status_changed", "filter": ["delivered"]},
     "steps": [
        {"id": "s1", "type": "condition", "when": {...}, "else": "stop"},
        {"id": "s2", "type": "wait", "hours": 72},
        {"id": "s3", "type": "branch", "when": {...}, "then": "s4", "else": "s5"},
        {"id": "s4", "type": "action", "action": "send_review_request", "params": {...}},
        {"id": "s5", "type": "approval", "note": "…"}]}

Steps run in order unless a condition/branch jumps. Every action goes through the Decision Policy
(``policy.decide``): AUTO_EXECUTE runs it now; REQUIRE_APPROVAL parks the run in Needs Your Attention;
BLOCK stops the run with the rule recorded. Facts are re-read for every step and again at approval.
A failing action is retried (3 attempts, backoff) and repeated failures of one action type pause the
merchant's workflows that use it (circuit breaker) and raise an exception.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.automation import facts as F
from app.domains.automation import policy
from app.domains.automation.actions import ACTIONS, RETRYABLE_CODES, validate_params
from app.domains.automation.models import (
    DecisionRecord,
    Workflow,
    WorkflowRun,
    WorkflowStepRun,
    WorkflowVersion,
)
from app.domains.billing.service import entitlements
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)

MAX_STEPS = 20
MAX_ATTEMPTS = 3
BREAKER_FAILURES = 3
BREAKER_WINDOW = timedelta(hours=1)
STEP_TYPES = ("condition", "branch", "wait", "action", "approval")
AUTOMATION = Actor(type="automation", display="Workflow")


# ----------------------------------------------------------------------------- definitions
def validate(definition: dict[str, Any]) -> dict[str, Any]:
    trig = definition.get("trigger") or {}
    t = F.TRIGGERS.get(trig.get("event", ""))
    if t is None:
        raise ValidationFailed(
            code="workflow_invalid", details={"path": "trigger.event", "reason": "unknown_trigger"}
        )
    flt = trig.get("filter") or []
    if flt and (not t.filter_values or any(v not in t.filter_values for v in flt)):
        raise ValidationFailed(
            code="workflow_invalid", details={"path": "trigger.filter", "reason": "unknown_value"}
        )
    steps = definition.get("steps") or []
    if not isinstance(steps, list) or not steps or len(steps) > MAX_STEPS:
        raise ValidationFailed(code="workflow_invalid", details={"path": "steps", "reason": "count"})
    ids = [s.get("id") for s in steps]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and 1 <= len(i) <= 40 for i in ids):
        raise ValidationFailed(code="workflow_invalid", details={"path": "steps", "reason": "ids"})
    targets = set(ids) | {"stop"}
    for i, s in enumerate(steps):
        path = f"steps.{i}"
        kind = s.get("type")
        if kind not in STEP_TYPES:
            raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "type"})
        if "next" in s and (s["next"] not in targets or (s["next"] != "stop" and ids.index(s["next"]) <= i)):
            raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "next"})
        if kind in ("condition", "branch"):
            if not isinstance(s.get("when"), dict):
                raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "when"})
            F.validate_condition(s["when"], t.subject, f"{path}.when")
            jumps = [s.get("else", "stop")] + ([s.get("then")] if kind == "branch" else [])
            if any(j not in targets for j in jumps):
                raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "target"})
            for j in jumps:  # jumps go forward only: no loops
                if j != "stop" and ids.index(j) <= i:
                    raise ValidationFailed(
                        code="workflow_invalid", details={"path": path, "reason": "backward_jump"}
                    )
        elif kind == "wait":
            h = s.get("hours")
            if not isinstance(h, int) or isinstance(h, bool) or not 1 <= h <= 720:
                raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "hours"})
        elif kind == "action":
            a = ACTIONS.get(s.get("action", ""))
            if a is None:
                raise ValidationFailed(
                    code="workflow_invalid", details={"path": path, "reason": "unknown_action"}
                )
            if t.subject not in a.subjects:
                raise ValidationFailed(
                    code="workflow_invalid", details={"path": path, "reason": "action_subject"}
                )
            validate_params(a.code, s.get("params") or {}, path)
    return {"trigger": {"event": t.code, "filter": list(flt)}, "steps": steps}


def _require_feature(db: Session, merchant_id: uuid.UUID) -> None:
    entitlements.require_feature(db, merchant_id, "automation.workflows")


def create(
    db: Session,
    ctx: TenantContext,
    name: str,
    definition: dict[str, Any],
    *,
    description: str | None,
    template_code: str | None,
) -> Workflow:
    _require_feature(db, ctx.merchant_id)
    d = validate(definition)
    w = Workflow(
        id=uuid7(),
        merchant_id=ctx.merchant_id,
        name=name.strip()[:120],
        description=(description or "")[:500] or None,
        status="draft",
        template_code=template_code,
        trigger_event=d["trigger"]["event"],
        created_by_user_id=ctx.actor.id,
    )
    db.add(w)
    db.flush()
    _new_version(db, ctx, w, d)
    audit.record(
        db,
        action="automation.workflow_created",
        resource_type="workflow",
        resource_id=w.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"template": template_code, "trigger": w.trigger_event},
    )
    return w


def _new_version(db: Session, ctx: TenantContext, w: Workflow, d: dict[str, Any]) -> WorkflowVersion:
    n = (
        db.scalar(
            select(func.coalesce(func.max(WorkflowVersion.version), 0)).where(
                WorkflowVersion.workflow_id == w.id
            )
        )
        or 0
    )
    v = WorkflowVersion(
        id=uuid7(),
        merchant_id=w.merchant_id,
        workflow_id=w.id,
        version=n + 1,
        definition=d,
        created_by_user_id=ctx.actor.id,
    )
    db.add(v)
    db.flush()
    w.current_version_id, w.trigger_event = v.id, d["trigger"]["event"]
    return v


def get_workflow(db: Session, ctx: TenantContext, workflow_id: uuid.UUID, *, lock: bool = False) -> Workflow:
    stmt = select(Workflow).where(Workflow.id == workflow_id)
    if lock:
        stmt = stmt.with_for_update()
    w = db.scalar(stmt)
    if w is None or w.merchant_id != ctx.merchant_id:
        raise NotFound(code="workflow_not_found")
    return w


def update(
    db: Session,
    ctx: TenantContext,
    workflow_id: uuid.UUID,
    *,
    name: str | None,
    description: str | None,
    definition: dict[str, Any] | None,
) -> Workflow:
    w = get_workflow(db, ctx, workflow_id, lock=True)
    if name:
        w.name = name.strip()[:120]
    if description is not None:
        w.description = description[:500] or None
    if definition is not None:
        v = _new_version(db, ctx, w, validate(definition))  # running runs keep their pinned version
        audit.record(
            db,
            action="automation.workflow_versioned",
            resource_type="workflow",
            resource_id=w.id,
            actor=ctx.actor,
            merchant_id=ctx.merchant_id,
            meta=ctx.meta,
            metadata={"version": v.version},
        )
    return w


def set_status(db: Session, ctx: TenantContext, workflow_id: uuid.UUID, status: str) -> Workflow:
    w = get_workflow(db, ctx, workflow_id, lock=True)
    if status == "active":
        _require_feature(db, ctx.merchant_id)
        w.paused_reason = None
    elif status == "paused":
        w.paused_reason = "paused_by_seller"
    w.status = status
    audit.record(
        db,
        action=f"automation.workflow_{status}",
        resource_type="workflow",
        resource_id=w.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )
    return w


# ----------------------------------------------------------------------------- triggers
def _matches(t: F.Trigger, flt: list[str], payload: dict[str, Any], facts: dict[str, Any]) -> bool:
    if t.code == "inventory.low_stock" and not payload.get("low_stock"):
        return False
    if t.code == "shipment.status_changed" and facts.get("shipment.direction") == "return":
        return False  # return pickups drive returns, not delivery workflows
    if flt and t.filter_field:
        # The status the event announced (not the current one: later events may already be queued).
        return payload.get("status") in flt
    return True


def start_runs(db: Session, ev: OutboxEvent) -> None:
    _start_runs(db, ev)


def _start_runs(db: Session, ev: OutboxEvent) -> int:
    if ev.merchant_id is None:
        return 0
    triggers = [t for t in F.TRIGGERS.values() if t.source_event == ev.event_type]
    if not triggers:
        return 0
    bind_tenant(db, ev.merchant_id)
    started = 0
    for t in triggers:
        workflows = list(
            db.scalars(select(Workflow).where(Workflow.trigger_event == t.code, Workflow.status == "active"))
        )
        if not workflows:
            continue
        stype, sid = F.subject_of(t, ev.payload)
        facts = F.facts_for(db, stype, sid)
        for w in workflows:
            v = db.get(WorkflowVersion, w.current_version_id)
            if v is None or not _matches(t, v.definition["trigger"].get("filter") or [], ev.payload, facts):
                continue
            run_id = db.execute(
                pg_insert(WorkflowRun)
                .values(
                    id=uuid7(),
                    merchant_id=w.merchant_id,
                    workflow_id=w.id,
                    version_id=v.id,
                    trigger_event=t.code,
                    trigger_key=f"evt:{ev.id}",
                    subject_type=stype,
                    subject_id=sid,
                    payload=dict(ev.payload),
                    status="running",
                    current_step=v.definition["steps"][0]["id"],
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                .on_conflict_do_nothing(index_elements=["workflow_id", "trigger_key"])
                .returning(WorkflowRun.id)
            ).scalar_one_or_none()
            if run_id is None:
                continue  # this event already started a run of this workflow
            started += 1
            run = db.get(WorkflowRun, run_id)
            assert run is not None
            try:
                with db.begin_nested():
                    advance(db, run)
            except Exception as e:  # one broken run never blocks the event for other workflows
                log.exception("workflow_run_crashed", run_id=str(run_id))
                run.status, run.error, run.finished_at = "failed", f"{type(e).__name__}"[:500], utcnow()
    return started


for _t in {t.source_event for t in F.TRIGGERS.values()}:
    handler(_t, name=f"automation.trigger.{_t}")(start_runs)


# ----------------------------------------------------------------------------- execution
def _steps(db: Session, run: WorkflowRun) -> list[dict[str, Any]]:
    v = db.get(WorkflowVersion, run.version_id)
    assert v is not None
    return list(v.definition["steps"])


def _next_id(steps: list[dict[str, Any]], current: str) -> str | None:
    """The step after ``current``: its explicit ``next`` (a forward jump or "stop"), else the following one."""
    idx = [s["id"] for s in steps].index(current)
    if steps[idx].get("next"):
        return str(steps[idx]["next"])
    return steps[idx + 1]["id"] if idx + 1 < len(steps) else None


def _finish(run: WorkflowRun, status: str = "completed", error: str | None = None) -> None:
    run.status, run.finished_at, run.next_run_at, run.error = status, utcnow(), None, error
    run.current_step = None


def _step_run(db: Session, run: WorkflowRun, step: dict[str, Any]) -> WorkflowStepRun:
    sr = db.scalar(
        select(WorkflowStepRun)
        .where(WorkflowStepRun.run_id == run.id, WorkflowStepRun.step_id == step["id"])
        .with_for_update()
    )
    if sr is None:
        sr = WorkflowStepRun(
            id=uuid7(),
            merchant_id=run.merchant_id,
            run_id=run.id,
            step_id=step["id"],
            kind=step["type"],
            action=step.get("action"),
            status="pending",
        )
        db.add(sr)
        db.flush()
    return sr


def advance(db: Session, run: WorkflowRun) -> WorkflowRun:
    """Run steps until the workflow finishes, waits, or needs a person."""
    steps = _steps(db, run)
    by_id = {s["id"]: s for s in steps}
    w = db.get(Workflow, run.workflow_id)
    for _ in range(MAX_STEPS + 1):
        if run.status not in ("running", "waiting") or run.current_step is None:
            return run
        if w is None or w.status != "active":
            _finish(run, "cancelled", "workflow_paused")
            return run
        step = by_id[run.current_step]
        sr = _step_run(db, run, step)
        facts = F.facts_for(db, run.subject_type, run.subject_id)  # re-read every step (safety rule)
        if run.subject_type and not facts:
            sr.status, sr.finished_at = "skipped", utcnow()
            _finish(run, "skipped", "subject_missing")
            return run
        kind = step["type"]
        nxt: str | None
        if kind in ("condition", "branch"):
            ok = F.evaluate(step["when"], facts)
            sr.status, sr.output, sr.finished_at = "done", {"result": ok}, utcnow()
            nxt = (step.get("then") or _next_id(steps, step["id"])) if ok else step.get("else", "stop")
            if kind == "condition" and ok:
                nxt = _next_id(steps, step["id"])
        elif kind == "wait":
            if sr.status == "pending":
                sr.status = "running"
                run.status, run.next_run_at = "waiting", utcnow() + timedelta(hours=int(step["hours"]))
                return run
            sr.status, sr.finished_at = "done", utcnow()
            run.status, run.next_run_at = "running", None
            nxt = _next_id(steps, step["id"])
        elif kind == "approval":
            if sr.status == "approved":
                nxt = _next_id(steps, step["id"])
            elif sr.status == "rejected":
                _finish(run, "completed", "rejected")
                return run
            else:
                sr.status = "awaiting_approval"
                sr.output = {"note": step.get("note")}
                run.status = "awaiting_approval"
                return run
        else:
            res = _run_action(db, run, w, step, sr, facts)
            if res != "continue":
                return run
            nxt = _next_id(steps, step["id"])
        if nxt in (None, "stop"):
            _finish(run, "completed")
            return run
        run.current_step = nxt
    _finish(run, "failed", "too_many_steps")
    return run


def _proposal(db: Session, run: WorkflowRun, step: dict[str, Any], facts: dict[str, Any]) -> policy.Proposal:
    a = ACTIONS[step["action"]]
    ent = entitlements.resolve(db, run.merchant_id)
    return policy.Proposal(
        action=a.code,
        risk_class=a.risk,
        source="workflow",
        confidence=a.confidence(facts),
        impact_minor=a.impact(db, facts),
        currency=facts.get("order.currency"),
        threshold_key=a.threshold_key,
        entitled=ent.has("automation.workflows"),
        capable=a.capable(db, facts),
        inputs={
            "workflow_id": str(run.workflow_id),
            "run_id": str(run.id),
            "step": step["id"],
            "subject": f"{run.subject_type}:{run.subject_id}",
        },
    )


def _run_action(
    db: Session,
    run: WorkflowRun,
    w: Workflow | None,
    step: dict[str, Any],
    sr: WorkflowStepRun,
    facts: dict[str, Any],
) -> str:
    if sr.status == "awaiting_approval":
        run.status = "awaiting_approval"
        return "stop"
    if sr.status == "rejected":
        _finish(run, "completed", "rejected")
        return "stop"
    if sr.status not in ("approved", "pending"):
        return "continue" if sr.status == "done" else "stop"
    if sr.status == "pending" and sr.decision_id is None:
        rec = policy.decide(db, run.merchant_id, _proposal(db, run, step, facts))
        sr.decision_id = rec.id
        if rec.decision == "BLOCK":
            sr.status, sr.finished_at, sr.error = "blocked", utcnow(), rec.rule
            policy.resolve(db, rec, "blocked")
            _log(db, run, step, "failed", rec, exclusion=rec.rule)
            _finish(run, "completed", f"blocked:{rec.rule}")
            return "stop"
        if rec.decision == "REQUIRE_APPROVAL":
            sr.status = "awaiting_approval"
            run.status = "awaiting_approval"
            return "stop"
    return _execute(db, run, step, sr, facts)


def _execute(
    db: Session, run: WorkflowRun, step: dict[str, Any], sr: WorkflowStepRun, facts: dict[str, Any]
) -> str:
    a = ACTIONS[step["action"]]
    approved = sr.status == "approved"
    rec = db.get(DecisionRecord, sr.decision_id) if sr.decision_id else None
    sr.attempts += 1
    ctx = TenantContext(merchant_id=run.merchant_id, actor=AUTOMATION)
    key = f"{run.id}:{step['id']}"
    try:
        with db.begin_nested():
            if approved and not a.capable(db, facts):
                raise AppError(
                    "The situation changed since this was proposed", code="automation_no_longer_applicable"
                )
            out = a.run(db, ctx, facts, step.get("params") or {}, key)
    except AppError as e:
        sr.error = e.code
        if e.code in RETRYABLE_CODES and sr.attempts < MAX_ATTEMPTS:
            run.status, run.next_run_at = "waiting", utcnow() + timedelta(minutes=2**sr.attempts * 5)
            return "stop"
        sr.status, sr.finished_at = "failed", utcnow()
        if rec:
            policy.resolve(db, rec, "failed")
        _log(db, run, step, "failed", rec, human=approved)
        _finish(run, "failed", e.code)
        _maybe_trip_breaker(db, run.merchant_id, a.code)
        return "stop"
    sr.status, sr.output, sr.finished_at, sr.error = "done", out, utcnow(), None
    if rec and rec.outcome is None:
        policy.resolve(db, rec, "approved" if approved else "executed", sr.resolved_by_user_id)
    _log(db, run, step, "success", rec, human=approved)
    run.status = "running"
    return "continue"


def _log(
    db: Session,
    run: WorkflowRun,
    step: dict[str, Any],
    outcome: str,
    rec: DecisionRecord | None,
    *,
    human: bool = False,
    exclusion: str | None = None,
) -> None:
    policy.log_action(
        db,
        run.merchant_id,
        "workflow:" + step["action"],
        step["action"],
        "automation",
        key=f"wf:{run.id}:{step['id']}:{outcome}",
        resource_type=run.subject_type,
        resource_id=run.subject_id,
        outcome=outcome,
        eligible=exclusion is None,
        human_intervened=human,
        exclusion_reason=exclusion,
        decision_id=rec.id if rec else None,
    )


def _maybe_trip_breaker(db: Session, merchant_id: uuid.UUID, action: str) -> None:
    db.flush()  # count the failure that just happened
    failures = (
        db.scalar(
            select(func.count())
            .select_from(WorkflowStepRun)
            .where(
                WorkflowStepRun.merchant_id == merchant_id,
                WorkflowStepRun.action == action,
                WorkflowStepRun.status == "failed",
                WorkflowStepRun.finished_at >= utcnow() - BREAKER_WINDOW,
            )
        )
        or 0
    )
    if failures < BREAKER_FAILURES:
        return
    for w in db.scalars(
        select(Workflow).where(Workflow.merchant_id == merchant_id, Workflow.status == "active")
    ):
        v = db.get(WorkflowVersion, w.current_version_id)
        if v and any(s.get("action") == action for s in v.definition["steps"]):
            w.status, w.paused_reason = "paused", f"circuit_breaker:{action}"
            log.warning("workflow_circuit_breaker", workflow_id=str(w.id), action=action)


# ----------------------------------------------------------------------------- approvals (AUT-009)
def pending_approvals(db: Session) -> list[WorkflowStepRun]:
    return list(
        db.scalars(
            select(WorkflowStepRun)
            .where(WorkflowStepRun.status == "awaiting_approval")
            .order_by(WorkflowStepRun.started_at)
        )
    )


def resolve_approval(
    db: Session, ctx: TenantContext, step_run_id: uuid.UUID, approve: bool, note: str | None
) -> WorkflowRun:
    sr = db.scalar(select(WorkflowStepRun).where(WorkflowStepRun.id == step_run_id).with_for_update())
    if sr is None or sr.merchant_id != ctx.merchant_id:
        raise NotFound(code="approval_not_found")
    run = db.scalar(select(WorkflowRun).where(WorkflowRun.id == sr.run_id).with_for_update())
    assert run is not None
    if sr.status != "awaiting_approval":
        raise Conflict("This was already decided", code="approval_already_resolved")
    sr.resolved_by_user_id = ctx.actor.id
    rec = db.get(DecisionRecord, sr.decision_id) if sr.decision_id else None
    audit.record(
        db,
        action="automation.step_approved" if approve else "automation.step_rejected",
        resource_type="workflow_run",
        resource_id=run.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"step": sr.step_id, "action": sr.action, "note": (note or "")[:300] or None},
    )
    if not approve:
        sr.status, sr.finished_at = "rejected", utcnow()
        sr.output = {**sr.output, "note": (note or "")[:300] or None}
        if rec:
            policy.resolve(db, rec, "rejected", ctx.actor.id)
        if sr.action:
            policy.log_action(
                db,
                run.merchant_id,
                "workflow:" + sr.action,
                sr.action,
                ctx.actor,
                key=f"wf:{run.id}:{sr.step_id}:rejected",
                resource_type=run.subject_type,
                resource_id=run.subject_id,
                outcome="reverted",
                human_intervened=True,
                decision_id=rec.id if rec else None,
            )
        _finish(run, "completed", "rejected")
        return run
    sr.status = "approved"
    run.status = "running"
    w = db.get(Workflow, run.workflow_id)
    if w is not None and w.status != "active":
        raise Conflict("This workflow is paused. Turn it on to continue.", code="workflow_paused")
    advance(db, run)
    return run


# ----------------------------------------------------------------------------- waits and retries
def resume_due(db: Session, limit: int = 200) -> int:
    rows = db.execute(
        select(WorkflowRun.id, WorkflowRun.merchant_id)
        .where(WorkflowRun.status == "waiting", WorkflowRun.next_run_at <= utcnow())
        .order_by(WorkflowRun.next_run_at)
        .limit(limit)
        .execution_options(skip_tenant_filter=True)
    ).all()
    n = 0
    for rid, mid in rows:
        bind_tenant(db, mid)
        run = db.scalar(select(WorkflowRun).where(WorkflowRun.id == rid).with_for_update(skip_locked=True))
        if run is None or run.status != "waiting":
            continue
        try:
            with db.begin_nested():
                advance(db, run)
            n += 1
        except Exception as e:
            log.exception("workflow_resume_crashed", run_id=str(rid))
            run.status, run.error, run.finished_at = "failed", type(e).__name__, utcnow()
    return n


# ----------------------------------------------------------------------------- dry run (AUT-015)
def dry_run(
    db: Session, ctx: TenantContext, definition: dict[str, Any], subject_id: str | None
) -> dict[str, Any]:
    """What would happen for this subject right now, without doing anything or recording decisions."""
    d = validate(definition)
    t = F.TRIGGERS[d["trigger"]["event"]]
    facts = F.facts_for(db, t.subject, subject_id) if subject_id else {}
    if subject_id and not facts:
        raise NotFound(code="dry_run_subject_not_found")
    trace: list[dict[str, Any]] = []
    flt = d["trigger"]["filter"]
    if flt and t.filter_field and facts.get(t.filter_field) not in flt:
        trace.append({"step": "trigger", "result": False, "note": "trigger_filter_not_met"})
    steps = d["steps"]
    current: str | None = steps[0]["id"]
    by_id = {s["id"]: s for s in steps}
    ent = entitlements.resolve(db, ctx.merchant_id)
    fake = WorkflowRun(
        merchant_id=ctx.merchant_id,
        workflow_id=uuid.UUID(int=0),
        subject_type=t.subject,
        subject_id=subject_id,
    )
    while current and current != "stop":
        s = by_id[current]
        entry: dict[str, Any] = {"step": s["id"], "type": s["type"]}
        if s["type"] in ("condition", "branch"):
            ok = F.evaluate(s["when"], facts)
            entry["result"] = ok
            current = (s.get("then") or _next_id(steps, s["id"])) if ok else s.get("else", "stop")
            if s["type"] == "condition" and ok:
                current = _next_id(steps, s["id"])
        elif s["type"] == "wait":
            entry["note"] = f"waits {s['hours']} h (skipped in a dry run)"
            current = _next_id(steps, s["id"])
        elif s["type"] == "approval":
            entry["decision"] = "REQUIRE_APPROVAL"
            current = _next_id(steps, s["id"])
        else:
            p = _proposal(db, fake, s, facts)
            p.entitled = ent.has("automation.workflows")
            decision, rule, risk = _preview(db, ctx.merchant_id, p)
            entry.update(
                {
                    "action": s["action"],
                    "decision": decision,
                    "rule": rule,
                    "risk_class": risk,
                    "impact_minor": p.impact_minor,
                }
            )
            current = None if decision == "BLOCK" else _next_id(steps, s["id"])
        trace.append(entry)
    visible = {k: v for k, v in facts.items() if not k.startswith("_")}
    return {"facts": visible, "trace": trace}


def _preview(db: Session, merchant_id: uuid.UUID, p: policy.Proposal) -> tuple[str, str, str]:
    with db.begin_nested() as sp:
        rec = policy.decide(db, merchant_id, p)
        out = (rec.decision, rec.rule, rec.risk_class)
        sp.rollback()  # a dry run records nothing
    return out


# ----------------------------------------------------------------------------- views
def workflow_view(db: Session, w: Workflow, *, detail: bool = False) -> dict[str, Any]:
    v = db.get(WorkflowVersion, w.current_version_id) if w.current_version_id else None
    stats = dict(
        db.execute(
            select(WorkflowRun.status, func.count())
            .where(WorkflowRun.workflow_id == w.id)
            .group_by(WorkflowRun.status)
        ).all()
    )
    out: dict[str, Any] = {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "status": w.status,
        "paused_reason": w.paused_reason,
        "template_code": w.template_code,
        "trigger_event": w.trigger_event,
        "version": v.version if v else None,
        "runs": {k: int(n) for k, n in stats.items()},
        "created_at": w.created_at,
        "updated_at": w.updated_at,
    }
    if detail and v is not None:
        out["definition"] = v.definition
    return out


def run_view(db: Session, run: WorkflowRun, *, detail: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "trigger_event": run.trigger_event,
        "subject_type": run.subject_type,
        "subject_id": run.subject_id,
        "status": run.status,
        "current_step": run.current_step,
        "next_run_at": run.next_run_at,
        "error": run.error,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }
    if detail:
        steps = db.scalars(
            select(WorkflowStepRun)
            .where(WorkflowStepRun.run_id == run.id)
            .order_by(WorkflowStepRun.started_at, WorkflowStepRun.id)
        )
        out["steps"] = []
        for s in steps:
            rec = db.get(DecisionRecord, s.decision_id) if s.decision_id else None
            out["steps"].append(
                {
                    "id": s.id,
                    "step_id": s.step_id,
                    "kind": s.kind,
                    "action": s.action,
                    "status": s.status,
                    "attempts": s.attempts,
                    "output": s.output,
                    "error": s.error,
                    "decision": policy.decision_view(rec) if rec else None,
                    "started_at": s.started_at,
                    "finished_at": s.finished_at,
                }
            )
    return out


def approval_view(db: Session, sr: WorkflowStepRun) -> dict[str, Any]:
    run = db.get(WorkflowRun, sr.run_id)
    w = db.get(Workflow, run.workflow_id) if run else None
    rec = db.get(DecisionRecord, sr.decision_id) if sr.decision_id else None
    f = F.facts_for(db, run.subject_type, run.subject_id) if run else {}
    return {
        "id": sr.id,
        "run_id": sr.run_id,
        "workflow_id": w.id if w else None,
        "workflow_name": w.name if w else None,
        "step_id": sr.step_id,
        "kind": sr.kind,
        "action": sr.action,
        "note": (sr.output or {}).get("note"),
        "subject_type": run.subject_type if run else None,
        "subject_id": run.subject_id if run else None,
        "order_id": f.get("order.id"),
        "order_number": f.get("order.number"),
        "decision": policy.decision_view(rec) if rec else None,
        "requested_at": sr.started_at,
    }
