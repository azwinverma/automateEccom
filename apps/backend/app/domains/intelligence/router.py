from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.domains.billing.service import entitlements
from app.domains.intelligence import aps, cod_risk, courier_brain, recommendations
from app.domains.intelligence.models import Recommendation

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ----------------------------------------------------------------------------- Autopilot Score
@router.get("/autopilot-score")
def autopilot_score(
    window_days: int = Query(default=30, ge=7, le=90),
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "autopilot.score")
    score = aps.compute(db, ctx.merchant_id, window_days)
    ent = entitlements.resolve(db, ctx.merchant_id)
    return {
        **score,
        "levers": aps.levers(db, ctx.merchant_id, score) if ent.has("autopilot.improvements") else [],
        "history": aps.history(db, ctx.merchant_id),
    }


# ----------------------------------------------------------------------------- Courier Brain
@router.get("/couriers/performance")
def courier_performance(
    refresh: bool = False,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.courier")
    if refresh:
        courier_brain.recompute(db, ctx.merchant_id)
    return {
        "items": courier_brain.performance(db, ctx.merchant_id),
        "min_sample": courier_brain.MIN_SAMPLE,
        "period_days": courier_brain.PERIOD_DAYS,
        "method_version": courier_brain.METHOD_VERSION,
    }


@router.get("/couriers/recommendation")
def courier_recommendation(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Ranked couriers for an order with the explanation (rules when Courier Brain isn't on the plan)."""
    from app.domains.fulfillment import couriers
    from app.domains.orders import service as orders

    o = orders.get_order(db, ctx, order_id)
    return couriers.courier_options(
        db, ctx, o, couriers.get_settings_row(db, ctx.merchant_id).default_weight_grams
    )


# ----------------------------------------------------------------------------- COD Intelligence
@router.get("/cod/assessments/{order_id}")
def cod_assessment(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.cod")
    return cod_risk.view(cod_risk.get(db, ctx, order_id))


@router.post("/cod/assessments/{order_id}/assess")
def cod_assess_now(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Assess an order that predates the feature (or was created before the plan included it)."""
    from app.domains.orders import service as orders

    entitlements.require_feature(db, ctx.merchant_id, "intelligence.cod")
    o = orders.get_order(db, ctx, order_id)
    a = cod_risk.assess(db, o.id)
    if a is None:
        from app.core.errors import ValidationFailed

        raise ValidationFailed("Only cash-on-delivery orders are assessed", code="cod_not_cod_order")
    return cod_risk.view(a)


class OverrideIn(BaseModel):
    level: Literal["LOW", "MEDIUM", "HIGHER"]
    reason: str = Field(min_length=3, max_length=300)


@router.post("/cod/assessments/{order_id}/override")
def cod_override(
    order_id: uuid.UUID,
    body: OverrideIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.cod")
    return cod_risk.view(cod_risk.override(db, ctx, order_id, body.level, body.reason))


class DisputeIn(BaseModel):
    note: str = Field(min_length=3, max_length=500)


@router.post("/cod/assessments/{order_id}/dispute")
def cod_dispute(
    order_id: uuid.UUID,
    body: DisputeIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.cod")
    return cod_risk.view(cod_risk.dispute(db, ctx, order_id, body.note))


@router.get("/cod/calibration")
def cod_calibration(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.cod")
    return cod_risk.calibration(db)


# ----------------------------------------------------------------------------- Recommendations
@router.get("/recommendations")
def list_recommendations(
    status: Literal["open", "accepted", "rejected", "expired", "executed", "failed"] | None = "open",
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(Recommendation).order_by(Recommendation.created_at.desc()).limit(100)
    if status:
        stmt = stmt.where(Recommendation.status == status)
    return {"items": [recommendations.view(r) for r in db.scalars(stmt)]}


@router.post("/recommendations/refresh")
def refresh_recommendations(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return {"created": recommendations.generate(db, ctx.merchant_id)}


@router.post("/recommendations/{rec_id}/accept")
def accept_recommendation(
    rec_id: uuid.UUID,
    ctx: TenantContext = Depends(require("automation.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Recommended actions change how the shop runs, so accepting needs automation.approve (R3)."""
    return recommendations.view(recommendations.accept(db, ctx, rec_id))


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/recommendations/{rec_id}/reject")
def reject_recommendation(
    rec_id: uuid.UUID,
    body: RejectIn,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return recommendations.view(recommendations.reject(db, ctx, rec_id, body.reason))
