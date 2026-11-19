"""COD Intelligence (CODI-001…005, spec 12).

Explainable delivery-risk for cash-on-delivery orders, from this merchant's own operational facts.

ALLOWED inputs only: the customer's delivery and return history with this merchant, new vs repeat,
address completeness, order value against this merchant's usual orders, and this merchant's
failed-delivery rate to the destination district. PROHIBITED: anything derived from names, gender,
religion, caste or ethnicity, inferred sensitive traits, and cross-merchant personal data. A static
test enforces the factor list and that this module never reads a person's name.

Decision Policy (CODI-003): LOW → accepted as usual; MEDIUM → "verify the phone" shown to the seller;
HIGHER → order held for review (needs_review="cod_risk"). Never an automatic rejection. The seller can
override with a reason (audited) and record a customer dispute.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.intelligence.models import CODRiskAssessment
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

MODEL_VERSION = "codi-1.0"
ALLOWED_FACTORS = frozenset(
    {
        "delivery_history",
        "new_customer",
        "return_history",
        "address_completeness",
        "order_value",
        "route_failures",
    }
)
BASE = 0.2
LEVELS = ((0.35, "LOW"), (0.6, "MEDIUM"), (1.01, "HIGHER"))
MIN_NORM_ORDERS = 10
MIN_ROUTE_SAMPLE = 10


def _level(score: float) -> str:
    return next(lvl for limit, lvl in LEVELS if score < limit)


def assess(db: Session, order_id: uuid.UUID) -> CODRiskAssessment | None:
    from app.domains.fulfillment.models import Shipment
    from app.domains.orders.models import Order
    from app.domains.returns.models import ReturnRequest

    o = db.get(Order, order_id)
    if o is None or o.payment_method != "cod":
        return None
    factors: list[dict[str, Any]] = []
    known = 0
    total = 4  # history, address, value, route

    def add(code: str, contribution: float, **evidence: Any) -> None:
        assert code in ALLOWED_FACTORS
        factors.append({"code": code, "contribution": round(contribution, 3), "evidence": evidence})

    # Customer's own history with this merchant.
    if o.customer_id:
        known += 1
        past = db.execute(
            select(Order.status, func.count())
            .where(Order.customer_id == o.customer_id, Order.id != o.id, Order.payment_method == "cod")
            .group_by(Order.status)
        ).all()
        by = dict(past)
        delivered = int(by.get("delivered", 0)) + int(by.get("completed", 0))
        failed = int(by.get("returned", 0)) + int(by.get("delivery_failed", 0))
        if delivered == 0 and failed == 0:
            add("new_customer", 0.1, previous_orders=0)
        elif failed:
            add(
                "delivery_history",
                min(0.45, 0.25 * failed / max(1, delivered + failed) + 0.1 * failed),
                delivered=delivered,
                failed=failed,
            )
        else:
            add("delivery_history", -min(0.2, 0.05 * delivered + 0.05), delivered=delivered, failed=0)
        returns = (
            db.scalar(
                select(func.count())
                .select_from(ReturnRequest)
                .where(
                    ReturnRequest.customer_id == o.customer_id,
                    ReturnRequest.status.not_in(("rejected", "cancelled")),
                )
            )
            or 0
        )
        if returns >= 2:
            add("return_history", 0.1, returns=int(returns))
    # Address completeness (structured address from Phase 2).
    known += 1
    essentials = all((o.ship_phone, o.ship_district, o.ship_municipality, o.ship_ward))
    if not essentials:
        add("address_completeness", 0.2, complete=False, completeness=o.address_completeness)
    elif o.address_completeness < 0.99:
        add("address_completeness", 0.03, complete=True, completeness=o.address_completeness)
    # Order value against this merchant's usual orders.
    totals = list(
        db.scalars(
            select(Order.total_minor)
            .where(
                Order.id != o.id,
                Order.status.not_in(("cancelled", "draft")),
                Order.placed_at >= utcnow() - timedelta(days=90),
            )
            .limit(500)
        )
    )
    if len(totals) >= MIN_NORM_ORDERS:
        known += 1
        median = statistics.median(totals)
        ratio = o.total_minor / median if median else 1
        if ratio >= 3:
            add("order_value", 0.25, ratio=round(ratio, 1), median_minor=int(median))
        elif ratio >= 2:
            add("order_value", 0.15, ratio=round(ratio, 1), median_minor=int(median))
    # This merchant's failed-delivery rate to the destination district.
    if o.ship_district:
        rows = db.execute(
            select(Shipment.attempt_count, Shipment.status).where(
                Shipment.destination_district == o.ship_district,
                Shipment.direction == "outbound",
                Shipment.status.in_(("delivered", "returned_to_origin", "lost")),
            )
        ).all()
        if len(rows) >= MIN_ROUTE_SAMPLE:
            known += 1
            failed = sum(1 for att, st in rows if att > 0 or st != "delivered")
            rate = failed / len(rows)
            if rate > 0.25:
                add("route_failures", 0.15, failed_rate=round(rate, 2), n=len(rows), district=o.ship_district)
    score = max(0.0, min(1.0, BASE + sum(f["contribution"] for f in factors)))
    level = _level(score)
    action = {"LOW": "cod_ok", "MEDIUM": "verify_phone"}.get(level) or (
        "request_partial_advance" if any(f["code"] == "order_value" for f in factors) else "manual_review"
    )
    db.execute(
        pg_insert(CODRiskAssessment)
        .values(
            id=uuid7(),
            merchant_id=o.merchant_id,
            order_id=o.id,
            level=level,
            score=round(score, 3),
            factors=factors,
            recommended_action=action,
            model_version=MODEL_VERSION,
            data_completeness=round(known / total, 2),
            disputed=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["order_id"])
    )
    a = db.scalar(select(CODRiskAssessment).where(CODRiskAssessment.order_id == o.id))
    if a is not None and a.level == "HIGHER" and a.override_level is None and o.needs_review is None:
        o.needs_review = "cod_risk"  # held for a person; never rejected automatically
    return a


@handler("orders.created", name="intelligence.cod_risk")
def _on_order(db: Session, ev: OutboxEvent) -> None:
    from app.domains.billing.service import entitlements
    from app.domains.orders.models import Order

    o = db.scalar(
        select(Order)
        .where(Order.id == uuid.UUID(ev.payload["order_id"]))
        .execution_options(skip_tenant_filter=True)
    )
    if o is None or o.payment_method != "cod":
        return
    bind_tenant(db, o.merchant_id)
    if entitlements.resolve(db, o.merchant_id).has("intelligence.cod"):
        assess(db, o.id)


@handler("orders.status_changed", name="intelligence.cod_outcome")
def _on_status(db: Session, ev: OutboxEvent) -> None:
    """CODI-005: outcomes for calibration. First failure counts as failed even if delivered later."""
    status = ev.payload.get("status")
    outcome = {
        "delivered": "delivered",
        "delivery_failed": "failed",
        "returned": "returned",
        "cancelled": "cancelled",
    }.get(status or "")
    if outcome is None:
        return
    a = db.scalar(
        select(CODRiskAssessment)
        .where(CODRiskAssessment.order_id == uuid.UUID(ev.payload["order_id"]))
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if a is None or (a.outcome in ("failed", "returned") and outcome == "delivered"):
        return
    a.outcome, a.outcome_at = outcome, utcnow()


def get(db: Session, ctx: TenantContext, order_id: uuid.UUID) -> CODRiskAssessment:
    a = db.scalar(select(CODRiskAssessment).where(CODRiskAssessment.order_id == order_id))
    if a is None or a.merchant_id != ctx.merchant_id:
        raise NotFound(code="cod_assessment_not_found")
    return a


def override(
    db: Session, ctx: TenantContext, order_id: uuid.UUID, level: str, reason: str
) -> CODRiskAssessment:
    from app.domains.orders.models import Order

    if level not in ("LOW", "MEDIUM", "HIGHER"):
        raise ValidationFailed(code="cod_level_invalid")
    a = get(db, ctx, order_id)
    before = a.override_level or a.level
    a.override_level, a.override_reason, a.overridden_by_user_id = level, reason[:300], ctx.actor.id
    o = db.get(Order, order_id)
    if o is not None:
        if level != "HIGHER" and o.needs_review == "cod_risk":
            o.needs_review = None
        elif level == "HIGHER" and o.needs_review is None:
            o.needs_review = "cod_risk"
    audit.record(
        db,
        action="intelligence.cod_override",
        resource_type="order",
        resource_id=order_id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"from": before, "to": level, "reason": reason[:300], "model_version": a.model_version},
    )
    return a


def dispute(db: Session, ctx: TenantContext, order_id: uuid.UUID, note: str) -> CODRiskAssessment:
    a = get(db, ctx, order_id)
    a.disputed, a.dispute_note = True, note[:500]
    audit.record(
        db,
        action="intelligence.cod_dispute",
        resource_type="order",
        resource_id=order_id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"note": note[:500]},
    )
    return a


def calibration(db: Session) -> dict[str, Any]:
    """CODI-005: outcome by level (is HIGHER really riskier?) and a regional disparity view."""
    from app.domains.orders.models import Order

    rows = db.execute(
        select(
            func.coalesce(CODRiskAssessment.override_level, CODRiskAssessment.level),
            CODRiskAssessment.outcome,
            func.count(),
        ).group_by(
            func.coalesce(CODRiskAssessment.override_level, CODRiskAssessment.level),
            CODRiskAssessment.outcome,
        )
    ).all()
    levels: dict[str, dict[str, int]] = {}
    for lvl, outcome, n in rows:
        levels.setdefault(lvl, {})[outcome or "open"] = int(n)
    by_level = {
        lvl: {
            **c,
            "failed_rate": round((c.get("failed", 0) + c.get("returned", 0)) / done, 3)
            if (done := c.get("delivered", 0) + c.get("failed", 0) + c.get("returned", 0))
            else None,
        }
        for lvl, c in levels.items()
    }
    region = db.execute(
        select(
            Order.ship_province,
            func.count(),
            func.sum(case((CODRiskAssessment.level == "HIGHER", 1), else_=0)),
        )
        .join(Order, Order.id == CODRiskAssessment.order_id)
        .group_by(Order.ship_province)
    ).all()
    overrides = (
        db.scalar(
            select(func.count())
            .select_from(CODRiskAssessment)
            .where(CODRiskAssessment.override_level.is_not(None))
        )
        or 0
    )
    total = db.scalar(select(func.count()).select_from(CODRiskAssessment)) or 0
    return {
        "model_version": MODEL_VERSION,
        "by_level": by_level,
        "by_province": [
            {"province": p, "assessed": int(n), "higher_share": round(int(h or 0) / int(n), 3) if n else None}
            for p, n, h in region
        ],
        "override_rate": round(overrides / total, 3) if total else None,
        "assessed": int(total),
    }


def view(a: CODRiskAssessment) -> dict[str, Any]:
    return {
        "order_id": a.order_id,
        "level": a.override_level or a.level,
        "model_level": a.level,
        "score": a.score,
        "factors": a.factors,
        # After a seller override the advice follows the level they set.
        "recommended_action": (
            {"LOW": "cod_ok", "MEDIUM": "verify_phone"}.get(a.override_level, a.recommended_action)
            if a.override_level
            else a.recommended_action
        ),
        "model_version": a.model_version,
        "data_completeness": a.data_completeness,
        "overridden": a.override_level is not None,
        "override_reason": a.override_reason,
        "disputed": a.disputed,
        "dispute_note": a.dispute_note,
        "outcome": a.outcome,
        "created_at": a.created_at,
    }
