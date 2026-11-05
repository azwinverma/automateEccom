"""Commerce Autopilot Score (APS-001…005/007, spec 14).

Per capability c over a window: A = automated end-to-end with no human and a good outcome,
F = automated but failed/reverted, M = done by a person (including AI suggestions a person approved),
X = excluded with a reason (not in the plan, not possible on the channel, policy requires approval).
score_c = A / (A + F + M). Overall is volume-weighted over capabilities with at least 10 eligible
operations; below that a capability reads "not enough activity" rather than 0% or 100%.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import bind_tenant, utcnow
from app.core.ids import uuid7
from app.domains.automation.models import AutomationActionLog
from app.domains.intelligence.models import AutopilotScoreSnapshot

METHOD_VERSION = "aps-1.0"
MIN_ELIGIBLE = 10
# APS-001 registry: action-log capability (or "workflow:<action>") → APS capability.
CAPABILITY_OF: dict[str, str] = {
    "customer_messaging": "customer_replies",
    "order_capture": "order_capture",
    "customer_notifications": "delivery_notifications",
    "delivery_recovery": "delivery_recovery",
    "returns": "returns",
    "refunds": "refunds",
    "workflow:send_customer_message": "delivery_notifications",
    "workflow:send_review_request": "marketing",
    "workflow:request_reattempt": "delivery_recovery",
    "workflow:approve_return": "returns",
}
ACTION_CAPABILITY: dict[tuple[str, str], str] = {
    ("fulfillment", "book_courier"): "shipment_creation",
    ("fulfillment", "request_pickup"): "pickup_requests",
    ("workflow:book_courier", "book_courier"): "shipment_creation",
    ("workflow:request_pickup", "request_pickup"): "pickup_requests",
}
# Steps a person would do per operation, and minutes per step (documented estimates, spec 14).
STEPS = {
    "customer_replies": (2, 1.5),
    "order_capture": (6, 1.0),
    "shipment_creation": (4, 1.0),
    "pickup_requests": (2, 1.0),
    "delivery_notifications": (2, 1.0),
    "delivery_recovery": (4, 2.0),
    "returns": (3, 2.0),
    "refunds": (3, 2.0),
    "marketing": (2, 1.0),
}
AUTOMATED = ("automation", "ai")


def _capability(cap: str, action: str) -> str | None:
    return ACTION_CAPABILITY.get((cap, action)) or CAPABILITY_OF.get(cap)


def compute(db: Session, merchant_id: uuid.UUID, window_days: int = 30) -> dict[str, Any]:
    since = utcnow() - timedelta(days=window_days)
    rows = db.execute(
        select(
            AutomationActionLog.capability,
            AutomationActionLog.action,
            AutomationActionLog.performed_by,
            AutomationActionLog.outcome,
            AutomationActionLog.eligible,
            AutomationActionLog.human_intervened,
            AutomationActionLog.exclusion_reason,
            func.count(),
        )
        .where(AutomationActionLog.merchant_id == merchant_id, AutomationActionLog.occurred_at >= since)
        .group_by(
            AutomationActionLog.capability,
            AutomationActionLog.action,
            AutomationActionLog.performed_by,
            AutomationActionLog.outcome,
            AutomationActionLog.eligible,
            AutomationActionLog.human_intervened,
            AutomationActionLog.exclusion_reason,
        )
    ).all()
    caps: dict[str, dict[str, Any]] = {}
    for cap, action, by, outcome, eligible, human, exclusion, n in rows:
        c = _capability(cap, action)
        if c is None:
            continue
        b = caps.setdefault(c, {"A": 0, "F": 0, "M": 0, "X": 0, "excluded": {}})
        if not eligible:
            b["X"] += n
            b["excluded"][exclusion or "other"] = b["excluded"].get(exclusion or "other", 0) + n
        elif outcome in ("failed", "reverted") and by in AUTOMATED:
            b["F"] += n
        elif by in AUTOMATED and not human and outcome == "success":
            b["A"] += n
        else:
            b["M"] += n
    total_e = 0
    weighted = 0.0
    hours_saved = 0.0
    for c, b in caps.items():
        e = b["A"] + b["F"] + b["M"]
        b["eligible"] = e
        b["score"] = round(b["A"] / e, 3) if e >= MIN_ELIGIBLE else None
        b["status"] = "ok" if e >= MIN_ELIGIBLE else "not_enough_activity"
        steps, minutes = STEPS.get(c, (1, 1.0))
        b["steps_saved"] = b["A"] * steps
        hours_saved += b["A"] * steps * minutes / 60
        if b["score"] is not None:
            total_e += e
            weighted += e * b["score"]
    overall = round(weighted / total_e, 3) if total_e else None
    return {
        "window_days": window_days,
        "overall": overall,
        "eligible": total_e,
        "capabilities": caps,
        "hours_saved_estimate": round(hours_saved, 1),
        "method_version": METHOD_VERSION,
        "min_eligible": MIN_ELIGIBLE,
    }


# ----------------------------------------------------------------------------- improvement levers (APS-004)
def levers(db: Session, merchant_id: uuid.UUID, score: dict[str, Any]) -> list[dict[str, Any]]:
    """The biggest gaps E * (1 - score) that a configuration change could close, largest first."""
    from app.domains.automation.models import Workflow, WorkflowVersion
    from app.domains.automation.policy import settings as automation_settings
    from app.domains.billing.service import entitlements
    from app.domains.fulfillment.couriers import get_settings_row
    from app.domains.merchants.models import Merchant
    from app.domains.returns.service import get_policy

    m = db.get(Merchant, merchant_id)
    if m is None:
        return []
    ent = entitlements.resolve(db, merchant_id)
    s = automation_settings(db, merchant_id)
    active_actions = set()
    for w in db.scalars(
        select(Workflow).where(Workflow.merchant_id == merchant_id, Workflow.status == "active")
    ):
        v = db.get(WorkflowVersion, w.current_version_id)
        active_actions |= {st.get("action") for st in (v.definition["steps"] if v else [])}
    out = []
    for cap, b in score["capabilities"].items():
        manual = b["M"] + b["F"]
        if manual == 0:
            continue
        lever: dict[str, Any] | None = None
        if cap == "customer_replies":
            if not ent.has("inbox.ai_replies"):
                lever = {"type": "plan_upgrade", "params": {"feature": "inbox.ai_replies"}}
            elif m.automation_mode == "assisted":
                lever = {"type": "set_mode", "params": {"mode": "smart"}}
        elif cap in ("shipment_creation", "pickup_requests") and "book_courier" not in active_actions:
            lever = (
                {"type": "activate_template", "params": {"template": "book_courier_when_packed"}}
                if ent.has("automation.workflows")
                else {"type": "plan_upgrade", "params": {"feature": "automation.workflows"}}
            )
        elif cap == "delivery_recovery":
            if "request_reattempt" not in (s.enabled_r2 or []):
                lever = {"type": "enable_r2", "params": {"action": "request_reattempt"}}
            elif m.automation_mode == "assisted":
                lever = {"type": "set_mode", "params": {"mode": "smart"}}
        elif cap == "returns" and not get_policy(db, merchant_id).auto_approve:
            lever = {"type": "enable_return_auto_approve", "params": {}}
        elif cap == "delivery_notifications" and not get_settings_row(db, merchant_id).notify_customers:
            lever = {"type": "enable_customer_notifications", "params": {}}
        if lever is None:
            continue
        e = b["eligible"]
        out.append(
            {
                "capability": cap,
                "gap": manual,  # operations a person did that this lever could hand to automation
                "current_score": b["score"],
                "potential_score": round((b["A"] + manual) / e, 3) if e else None,
                "eligible": e,
                "lever": lever,
            }
        )
    return sorted(out, key=lambda x: -x["gap"])


# ----------------------------------------------------------------------------- daily snapshots (APS-003/007)
def snapshot(db: Session, merchant_id: uuid.UUID, window_days: int = 30) -> AutopilotScoreSnapshot:
    today = utcnow().date()
    sc = compute(db, merchant_id, window_days)
    prev = db.scalar(
        select(AutopilotScoreSnapshot)
        .where(
            AutopilotScoreSnapshot.merchant_id == merchant_id,
            AutopilotScoreSnapshot.window_days == window_days,
            AutopilotScoreSnapshot.computed_on < today,
        )
        .order_by(AutopilotScoreSnapshot.computed_on.desc())
        .limit(1)
    )
    anomaly = None
    if (
        prev
        and prev.overall is not None
        and sc["overall"] is not None
        and abs(sc["overall"] - prev.overall) >= 0.25
    ):
        anomaly = f"jump_{round((sc['overall'] - prev.overall) * 100):+d}pts"
    db.execute(
        pg_insert(AutopilotScoreSnapshot)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            computed_on=today,
            window_days=window_days,
            overall=sc["overall"],
            eligible=sc["eligible"],
            capabilities=sc["capabilities"],
            method_version=METHOD_VERSION,
            anomaly=anomaly,
            created_at=utcnow(),
        )
        .on_conflict_do_update(
            index_elements=["merchant_id", "computed_on", "window_days"],
            set_={
                "overall": sc["overall"],
                "eligible": sc["eligible"],
                "capabilities": sc["capabilities"],
                "anomaly": anomaly,
            },
        )
    )
    row = db.scalar(
        select(AutopilotScoreSnapshot).where(
            AutopilotScoreSnapshot.merchant_id == merchant_id,
            AutopilotScoreSnapshot.computed_on == today,
            AutopilotScoreSnapshot.window_days == window_days,
        )
    )
    assert row is not None
    return row


def snapshot_all(db: Session) -> int:
    since = utcnow() - timedelta(days=30)
    mids = db.scalars(
        select(AutomationActionLog.merchant_id)
        .where(AutomationActionLog.occurred_at >= since)
        .distinct()
        .execution_options(skip_tenant_filter=True)
    ).all()
    for mid in mids:
        bind_tenant(db, mid)
        snapshot(db, mid)
    return len(mids)


def history(db: Session, merchant_id: uuid.UUID, days: int = 30) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(AutopilotScoreSnapshot)
        .where(
            AutopilotScoreSnapshot.merchant_id == merchant_id,
            AutopilotScoreSnapshot.window_days == 30,
            AutopilotScoreSnapshot.computed_on >= utcnow().date() - timedelta(days=days),
        )
        .order_by(AutopilotScoreSnapshot.computed_on)
    )
    return [{"date": r.computed_on.isoformat(), "overall": r.overall, "anomaly": r.anomaly} for r in rows]
