"""Recommendations (REC-001…003/005…008, AUT-021).

Generators read this merchant's own data and create a Recommendation with an explanation object
(what / why / evidence / confidence / estimated impact / action). They are deterministic: no AI wording
and no numbers that aren't in the evidence. One open recommendation per subject and type (REC-008).

Every recommended action changes how the shop runs (settings, automation), so the Decision Policy
classifies it R3: it always waits for a person in Needs Your Attention. Accepting is that approval and
runs the action through the same services the seller would use. Rejecting records the reason.
After the evaluation window the outcome is measured against the baseline (pre/post, equal windows).
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, NotFound
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.automation import policy
from app.domains.billing.service import entitlements
from app.domains.intelligence import aps, courier_brain
from app.domains.intelligence.models import Recommendation

log = structlog.get_logger(__name__)

METHOD_VERSION = "rec-1.0"
EXPIRES = timedelta(days=30)
EVALUATION = timedelta(days=14)
MAX_OPEN = 10  # never flood the seller


# ----------------------------------------------------------------------------- generators
def _autopilot(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    if not entitlements.resolve(db, merchant_id).has("autopilot.improvements"):
        return []
    score = aps.compute(db, merchant_id, 30)
    out = []
    for lv in aps.levers(db, merchant_id, score):
        if lv["eligible"] < aps.MIN_ELIGIBLE:
            continue
        out.append(
            {
                "type": "autopilot_improvement",
                "dedupe_key": f"aps:{lv['capability']}:{lv['lever']['type']}",
                "subject_type": "capability",
                "subject_id": lv["capability"],
                "explanation": {
                    "what": f"lever.{lv['lever']['type']}",
                    "why": "manual_gap",
                    "vars": {
                        "capability": lv["capability"],
                        "manual": lv["gap"],
                        "eligible": lv["eligible"],
                        **lv["lever"]["params"],
                    },
                },
                "evidence": [
                    {
                        "metric": "aps",
                        "capability": lv["capability"],
                        "window_days": 30,
                        "eligible": lv["eligible"],
                        "manual_or_failed": lv["gap"],
                        "score": lv["current_score"],
                    }
                ],
                "confidence": 0.9,
                "estimated_impact": {
                    "capability": lv["capability"],
                    "score_from": lv["current_score"],
                    "score_to": lv["potential_score"],
                },
                "action": lv["lever"],
                "baseline": {"capability": lv["capability"], "score": lv["current_score"]},
            }
        )
    return out


def _courier(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Routes where another courier clearly delivers better (≥10 points, enough parcels on both)."""
    from app.domains.fulfillment.couriers import get_settings_row
    from app.domains.fulfillment.models import CourierAccount
    from app.domains.intelligence.models import CourierPerformanceMetric

    if not entitlements.resolve(db, merchant_id).has("intelligence.courier"):
        return []
    s = get_settings_row(db, merchant_id)
    if s.courier_selection == "smart":
        return []
    default = db.scalar(
        select(CourierAccount).where(
            CourierAccount.is_default.is_(True), CourierAccount.status != "disconnected"
        )
    )
    if default is None:
        return []
    rows = db.execute(
        select(
            CourierPerformanceMetric.destination,
            CourierPerformanceMetric.courier_account_id,
            func.sum(CourierPerformanceMetric.n),
            func.sum(CourierPerformanceMetric.delivered),
        ).group_by(CourierPerformanceMetric.destination, CourierPerformanceMetric.courier_account_id)
    ).all()
    by_dest: dict[str, dict[uuid.UUID, tuple[int, int]]] = {}
    for dest, acct, n, d in rows:
        by_dest.setdefault(dest, {})[acct] = (int(n), int(d))
    better: list[dict[str, Any]] = []
    for dest, accts in by_dest.items():
        mine = accts.get(default.id)
        if not mine or mine[0] < courier_brain.MIN_SAMPLE:
            continue
        for acct, (n, d) in accts.items():
            if acct == default.id or n < courier_brain.MIN_SAMPLE:
                continue
            gap = d / n - mine[1] / mine[0]
            if gap >= 0.10:
                better.append(
                    {
                        "destination": dest,
                        "courier_account_id": str(acct),
                        "their_success": round(d / n, 3),
                        "their_n": n,
                        "default_success": round(mine[1] / mine[0], 3),
                        "default_n": mine[0],
                    }
                )
    if not better:
        return []
    top = max(better, key=lambda b: b["their_success"] - b["default_success"])
    return [
        {
            "type": "courier_selection",
            "dedupe_key": "courier:smart_selection",
            "subject_type": "merchant",
            "subject_id": str(merchant_id),
            "explanation": {
                "what": "lever.set_courier_selection",
                "why": "better_route_courier",
                "vars": {**top, "routes": len(better)},
            },
            "evidence": better[:10],
            "confidence": 0.8,
            "estimated_impact": {
                "routes": len(better),
                "success_gain_points": round(100 * (top["their_success"] - top["default_success"])),
            },
            "action": {"type": "set_courier_selection", "params": {"mode": "smart"}},
            "baseline": {"default_success": top["default_success"], "destination": top["destination"]},
        }
    ]


def _restock(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Low-stock items that are actually selling (units in the last 30 days), with days of cover."""
    from app.domains.inventory.service import low_stock
    from app.domains.orders.models import Order, OrderLine

    out = []
    since = utcnow() - timedelta(days=30)
    for lvl, v, p in low_stock(db, merchant_id, limit=20):
        avail = lvl.on_hand - lvl.reserved
        sold = (
            db.scalar(
                select(func.coalesce(func.sum(OrderLine.quantity - OrderLine.cancelled_quantity), 0))
                .join(Order, Order.id == OrderLine.order_id)
                .where(
                    OrderLine.variant_id == v.id,
                    Order.placed_at >= since,
                    Order.status.not_in(("cancelled", "draft")),
                )
            )
            or 0
        )
        if sold <= 0:
            continue
        per_day = sold / 30
        cover = round(avail / per_day, 1) if per_day else None
        out.append(
            {
                "type": "restock",
                "dedupe_key": f"restock:{v.id}",
                "subject_type": "variant",
                "subject_id": str(v.id),
                "explanation": {
                    "what": "restock",
                    "why": "selling_low_stock",
                    "vars": {
                        "title": p.title,
                        "variant": v.title,
                        "available": avail,
                        "sold_30d": int(sold),
                        "cover_days": cover,
                    },
                },
                "evidence": [
                    {"metric": "units_sold", "window_days": 30, "value": int(sold)},
                    {"metric": "available", "value": avail},
                ],
                "confidence": 0.7 if sold >= 5 else 0.5,
                "estimated_impact": {"cover_days": cover},
                "action": {"type": "none", "params": {"product_id": str(p.id)}},
                "baseline": {"available": avail, "sold_30d": int(sold)},
            }
        )
    return out


GENERATORS = (_autopilot, _courier, _restock)


def generate(db: Session, merchant_id: uuid.UUID) -> int:
    open_n = (
        db.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.status == "open"))
        or 0
    )
    created = 0
    for gen in GENERATORS:
        try:
            with db.begin_nested():
                proposals = gen(db, merchant_id)
        except Exception:
            log.exception("recommendation_generator_failed", generator=gen.__name__)
            continue
        for p in proposals:
            if open_n + created >= MAX_OPEN:
                return created
            rejected_recently = db.scalar(
                select(Recommendation.id).where(
                    Recommendation.dedupe_key == p["dedupe_key"],
                    Recommendation.status == "rejected",
                    Recommendation.resolved_at >= utcnow() - EXPIRES,
                )
            )
            if rejected_recently:
                continue  # the seller said no recently: don't nag
            rid = db.execute(
                pg_insert(Recommendation)
                .values(
                    id=uuid7(),
                    merchant_id=merchant_id,
                    status="open",
                    method_version=METHOD_VERSION,
                    expires_at=utcnow() + EXPIRES,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                    **p,
                )
                .on_conflict_do_nothing(
                    index_elements=["merchant_id", "dedupe_key"], index_where=Recommendation.status == "open"
                )
                .returning(Recommendation.id)
            ).scalar_one_or_none()
            created += int(rid is not None)
    return created


def generate_all(db: Session) -> int:
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        n += generate(db, mid)
    return n


# ----------------------------------------------------------------------------- accept / reject (REC-005/006)
def get(db: Session, ctx: TenantContext, rec_id: uuid.UUID, *, lock: bool = False) -> Recommendation:
    stmt = select(Recommendation).where(Recommendation.id == rec_id)
    if lock:
        stmt = stmt.with_for_update()
    r = db.scalar(stmt)
    if r is None or r.merchant_id != ctx.merchant_id:
        raise NotFound(code="recommendation_not_found")
    return r


def accept(db: Session, ctx: TenantContext, rec_id: uuid.UUID) -> Recommendation:
    r = get(db, ctx, rec_id, lock=True)
    if r.status in ("accepted", "executed"):
        return r  # idempotent
    if r.status != "open":
        raise Conflict("This recommendation is no longer open", code="recommendation_closed")
    rec = policy.decide(
        db,
        ctx.merchant_id,
        policy.Proposal(
            action=f"recommendation:{r.action.get('type')}",
            risk_class="R3",
            source="recommendation",
            confidence=r.confidence,
            inputs={"recommendation_id": str(r.id)},
        ),
    )
    r.decision_id = rec.id
    r.resolved_by_user_id, r.resolved_at = ctx.actor.id, utcnow()
    try:
        with db.begin_nested():
            done = _execute(db, ctx, r)
    except AppError as e:
        r.status, r.reason = "failed", e.code
        policy.resolve(db, rec, "failed", ctx.actor.id)
        return r
    r.status = "executed" if done else "accepted"
    policy.resolve(db, rec, "approved", ctx.actor.id)
    policy.log_action(
        db,
        ctx.merchant_id,
        "recommendations",
        r.type,
        ctx.actor,
        key=f"rec:{r.id}",
        resource_type="recommendation",
        resource_id=r.id,
        human_intervened=True,
        decision_id=rec.id,
    )
    audit.record(
        db,
        action="intelligence.recommendation_accepted",
        resource_type="recommendation",
        resource_id=r.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"type": r.type, "action": r.action},
    )
    return r


def reject(db: Session, ctx: TenantContext, rec_id: uuid.UUID, reason: str) -> Recommendation:
    r = get(db, ctx, rec_id, lock=True)
    if r.status != "open":
        raise Conflict("This recommendation is no longer open", code="recommendation_closed")
    r.status, r.reason, r.resolved_by_user_id, r.resolved_at = (
        "rejected",
        reason[:300],
        ctx.actor.id,
        utcnow(),
    )
    audit.record(
        db,
        action="intelligence.recommendation_rejected",
        resource_type="recommendation",
        resource_id=r.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"type": r.type, "reason": reason[:300]},
    )
    return r


def _execute(db: Session, ctx: TenantContext, r: Recommendation) -> bool:
    """Runs the typed action through the normal services. Returns False for informational ones."""
    t, params = r.action.get("type"), r.action.get("params") or {}
    if t in ("none", "plan_upgrade"):
        return False
    if t == "set_mode":
        from app.domains.merchants.models import Merchant

        if params.get("mode") == "autopilot":
            entitlements.require_feature(db, ctx.merchant_id, "automation.autopilot")
        m = db.get(Merchant, ctx.merchant_id)
        assert m is not None
        m.automation_mode = params["mode"]
    elif t == "activate_template":
        from app.domains.automation import engine
        from app.domains.automation.templates import BY_CODE

        tpl = BY_CODE[params["template"]]
        w = engine.create(
            db,
            ctx,
            params["template"].replace("_", " ").capitalize(),
            tpl["definition"],
            description=None,
            template_code=params["template"],
        )
        engine.set_status(db, ctx, w.id, "active")
    elif t == "enable_r2":
        s = policy.settings(db, ctx.merchant_id)
        policy.update_settings(
            db,
            ctx,
            thresholds=None,
            enabled_r2=sorted({*(s.enabled_r2 or []), params["action"]}),
            confidence_threshold=None,
        )
    elif t == "enable_return_auto_approve":
        from app.domains.returns.service import update_policy

        update_policy(db, ctx, {"auto_approve": True})
    elif t == "enable_customer_notifications":
        from app.domains.fulfillment.couriers import get_settings_row

        get_settings_row(db, ctx.merchant_id).notify_customers = True
    elif t == "set_courier_selection":
        from app.domains.fulfillment.couriers import get_settings_row

        get_settings_row(db, ctx.merchant_id).courier_selection = params["mode"]
    else:
        raise AppError("Unknown action", code="recommendation_action_unknown")
    return True


# ----------------------------------------------------------------------------- outcomes (REC-007) + expiry
def measure(db: Session) -> dict[str, int]:
    now = utcnow()
    expired = 0
    for r in db.scalars(
        select(Recommendation)
        .where(Recommendation.status == "open", Recommendation.expires_at < now)
        .execution_options(skip_tenant_filter=True)
    ):
        r.status = "expired"
        expired += 1
    measured = 0
    for r in db.scalars(
        select(Recommendation)
        .where(
            Recommendation.status.in_(("executed", "accepted")),
            Recommendation.outcome_measured_at.is_(None),
            Recommendation.resolved_at < now - EVALUATION,
        )
        .execution_options(skip_tenant_filter=True)
    ):
        bind_tenant(db, r.merchant_id)
        r.outcome = _outcome(db, r)
        r.outcome_measured_at = now
        measured += 1
    return {"expired": expired, "measured": measured}


def _outcome(db: Session, r: Recommendation) -> dict[str, Any]:
    if r.type == "autopilot_improvement":
        cap = r.baseline.get("capability")
        after = aps.compute(db, r.merchant_id, int(EVALUATION.days))["capabilities"].get(cap, {})
        return {
            "method": "pre_post",
            "window_days": EVALUATION.days,
            "before": r.baseline.get("score"),
            "after": after.get("score"),
            "eligible_after": after.get("eligible", 0),
            "note": "Before/after comparison; other changes in the same period can contribute.",
        }
    return {
        "method": "pre_post",
        "window_days": EVALUATION.days,
        "before": r.baseline,
        "after": None,
        "note": "Not measurable automatically yet.",
    }


def view(r: Recommendation) -> dict[str, Any]:
    return {
        "id": r.id,
        "type": r.type,
        "status": r.status,
        "subject_type": r.subject_type,
        "subject_id": r.subject_id,
        "explanation": r.explanation,
        "evidence": r.evidence,
        "confidence": r.confidence,
        "estimated_impact": r.estimated_impact,
        "action": r.action,
        "method_version": r.method_version,
        "created_at": r.created_at,
        "expires_at": r.expires_at,
        "resolved_at": r.resolved_at,
        "reason": r.reason,
        "outcome": r.outcome,
        "outcome_measured_at": r.outcome_measured_at,
    }
