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
from app.domains.intelligence import (
    aps,
    cod_risk,
    courier_brain,
    creative,
    memory,
    product_brain,
    profit,
    recommendations,
    return_intel,
)
from app.domains.intelligence.models import (
    CommerceMemoryFact,
    CommerceMemoryMetric,
    ProductIntelligenceProfile,
    Recommendation,
    ReturnInsight,
)

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
    return {
        "items": [recommendations.view(r) for r in db.scalars(stmt)],
        "currency": _currency(db, ctx.merchant_id),
    }


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


# ============================================================================= Phase 6 part B
def _currency(db: Session, merchant_id: uuid.UUID) -> str:
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, merchant_id)
    return m.currency if m else "NPR"


# ----------------------------------------------------------------------------- Profit (ANA-007/008)
@router.get("/profit")
def profit_summary(
    days: int = Query(default=30, ge=7, le=365),
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "analytics.profit")
    out = profit.compute(db, ctx.merchant_id, days)
    out["currency"] = _currency(db, ctx.merchant_id)
    out["settings"] = profit.settings_view(profit.settings_row(db, ctx.merchant_id))
    return out


@router.get("/profit/settings")
def get_profit_settings(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return profit.settings_view(profit.settings_row(db, ctx.merchant_id))


class ProfitSettingsIn(BaseModel):
    packaging_cost_minor: int | None = Field(default=None, ge=0, le=10_000_000)
    clear_packaging: bool = False
    min_margin_pct: float | None = Field(default=None, ge=0, le=100)
    min_contribution_minor: int | None = Field(default=None, ge=-10_000_000, le=10_000_000)
    max_return_rate_pct: float | None = Field(default=None, ge=0, le=100)


@router.put("/profit/settings")
def put_profit_settings(
    body: ProfitSettingsIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    changes = body.model_dump(exclude_none=True, exclude={"clear_packaging"})
    if body.clear_packaging:
        changes["packaging_cost_minor"] = None
    return profit.settings_view(profit.update_settings(db, ctx, changes))


# ----------------------------------------------------------------------------- Product Brain (PBR-009)
@router.get("/products/{product_id}/brain")
def product_brain_profile(
    product_id: uuid.UUID,
    refresh: bool = False,
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.core.errors import NotFound
    from app.domains.catalog.models import Product

    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    p = db.get(Product, product_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound(code="product_not_found")
    prof = (
        product_brain.recompute(db, ctx.merchant_id, product_id)
        if refresh
        else product_brain.get_or_compute(db, ctx.merchant_id, product_id)
    )
    out = product_brain.view(prof, fit=memory.confirmed_fit(db, ctx.merchant_id, product_id))
    out["currency"] = _currency(db, ctx.merchant_id)
    ent = entitlements.resolve(db, ctx.merchant_id)
    out["return_insights"] = (
        [
            return_intel.view(i)
            for i in db.scalars(
                select(ReturnInsight)
                .where(ReturnInsight.product_id == product_id, ReturnInsight.status.in_(("open", "acted")))
                .order_by(ReturnInsight.created_at.desc())
            )
        ]
        if ent.has("intelligence.returns")
        else None
    )
    out["facts"] = [
        memory.view(f)
        for f in db.scalars(
            select(CommerceMemoryFact).where(
                CommerceMemoryFact.subject_type == "product",
                CommerceMemoryFact.subject_id == str(product_id),
                CommerceMemoryFact.status == "active",
            )
        )
    ]
    return out


@router.get("/stock-risk")
def stock_risk(
    ctx: TenantContext = Depends(require("catalog.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    """UX-012: products that will run out soonest at their current demand."""
    from app.domains.catalog.models import Product

    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    rows = db.execute(
        select(ProductIntelligenceProfile, Product.title)
        .join(Product, Product.id == ProductIntelligenceProfile.product_id)
        .where(
            ProductIntelligenceProfile.cover_days.is_not(None) | (ProductIntelligenceProfile.available == 0)
        )
        .order_by(ProductIntelligenceProfile.cover_days.asc().nulls_first())
        .limit(20)
    ).all()
    items = []
    for prof, title in rows:
        risk = product_brain.stock_risk(prof)
        if risk in ("out", "high", "medium") and (prof.demand_per_day or 0) > 0:
            items.append({**product_brain.view(prof), "title": title})
    return {"items": items}


# ----------------------------------------------------------------------------- Return Intelligence
@router.get("/return-insights")
def list_return_insights(
    status: Literal["open", "acted", "dismissed", "resolved"] | None = None,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.domains.catalog.models import Product, Variant

    entitlements.require_feature(db, ctx.merchant_id, "intelligence.returns")
    stmt = select(ReturnInsight).order_by(ReturnInsight.created_at.desc()).limit(100)
    stmt = (
        stmt.where(ReturnInsight.status == status)
        if status
        else stmt.where(ReturnInsight.status.in_(("open", "acted")))
    )
    items = []
    for i in db.scalars(stmt):
        p = db.get(Product, i.product_id)
        v = db.get(Variant, i.variant_id) if i.variant_id else None
        items.append(return_intel.view(i, p.title if p else None, v.title if v else None))
    return {"items": items}


@router.post("/return-insights/refresh")
def refresh_return_insights(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.returns")
    return return_intel.detect(db, ctx.merchant_id)


class DismissIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/return-insights/{insight_id}/dismiss")
def dismiss_return_insight(
    insight_id: uuid.UUID,
    body: DismissIn,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.returns")
    return return_intel.view(return_intel.dismiss(db, ctx, insight_id, body.reason))


# ----------------------------------------------------------------------------- Commerce Memory (MEM-007)
def _labels(db: Session, facts: list[CommerceMemoryFact]) -> dict[str, str]:
    from app.domains.catalog.models import Product

    pids = [uuid.UUID(f.subject_id) for f in facts if f.subject_type == "product"]
    return (
        {
            str(k): v
            for k, v in db.execute(select(Product.id, Product.title).where(Product.id.in_(pids))).all()
        }
        if pids
        else {}
    )


@router.get("/memory/facts")
def list_memory_facts(
    include_history: bool = False,
    subject_type: str | None = None,
    subject_id: str | None = None,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    stmt = select(CommerceMemoryFact).order_by(CommerceMemoryFact.valid_from.desc()).limit(200)
    if not include_history:
        stmt = stmt.where(CommerceMemoryFact.status == "active")
    if subject_type:
        stmt = stmt.where(CommerceMemoryFact.subject_type == subject_type)
    if subject_id:
        stmt = stmt.where(CommerceMemoryFact.subject_id == subject_id)
    facts = list(db.scalars(stmt))
    labels = _labels(db, facts)
    return {
        "items": [memory.view(f, labels.get(f.subject_id)) for f in facts],
        "fact_types": sorted(memory.FACT_TYPES),
    }


@router.get("/memory/metrics")
def list_memory_metrics(
    metric: str,
    subject_type: str,
    subject_id: str,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.core.errors import ValidationFailed

    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    if metric not in memory.METRICS:
        raise ValidationFailed("Unknown metric", code="memory_metric_unknown")
    rows = db.scalars(
        select(CommerceMemoryMetric)
        .where(
            CommerceMemoryMetric.metric == metric,
            CommerceMemoryMetric.subject_type == subject_type,
            CommerceMemoryMetric.subject_id == subject_id,
        )
        .order_by(CommerceMemoryMetric.period_start)
    )
    return {
        "metric": metric,
        **memory.METRICS[metric],
        "points": [{"period_start": r.period_start.isoformat(), "value": r.value, "n": r.n} for r in rows],
    }


@router.post("/memory/refresh")
def refresh_memory(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    return memory.compute(db, ctx.merchant_id)


@router.post("/memory/facts/{fact_id}/confirm")
def confirm_memory_fact(
    fact_id: uuid.UUID,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    return memory.view(memory.confirm(db, ctx, fact_id))


class FactRejectIn(BaseModel):
    note: str = Field(min_length=3, max_length=300)


@router.post("/memory/facts/{fact_id}/reject")
def reject_memory_fact(
    fact_id: uuid.UUID,
    body: FactRejectIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    return memory.view(memory.reject(db, ctx, fact_id, body.note))


class FactCorrectIn(BaseModel):
    value: dict[str, Any]
    note: str = Field(min_length=3, max_length=300)


@router.post("/memory/facts/{fact_id}/correct")
def correct_memory_fact(
    fact_id: uuid.UUID,
    body: FactCorrectIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.product_brain")
    return memory.view(memory.correct(db, ctx, fact_id, body.value, body.note))


# ============================================================================= Phase 7: Creative Intelligence
def _creative_on(db: Session, ctx: TenantContext) -> None:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.creative_genome")


@router.get("/creative/genome")
def creative_genome(
    ctx: TenantContext = Depends(require("content.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    from sqlalchemy import func

    from app.domains.content.models import ContentPost
    from app.domains.intelligence.models import CreativePerformanceMetric

    _creative_on(db, ctx)
    measured = (
        db.scalar(
            select(func.count())
            .select_from(CreativePerformanceMetric)
            .join(ContentPost, ContentPost.id == CreativePerformanceMetric.post_id)
            .where(CreativePerformanceMetric.window_complete.is_(True))
        )
        or 0
    )
    return {
        **creative.genome_view(creative.latest(db, ctx.merchant_id), measured),
        "impact": creative.impact(db, ctx.merchant_id),
    }


@router.post("/creative/refresh")
def creative_refresh(
    ctx: TenantContext = Depends(require("content.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    _creative_on(db, ctx)
    return creative.run(db, ctx.merchant_id)


@router.get("/creative/posts")
def creative_posts(
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require("content.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Post results with how orders/chats were attributed (needs no plan: the seller's own numbers)."""
    from app.domains.content.models import ContentPost
    from app.domains.intelligence.models import CreativePerformanceMetric

    rows = db.execute(
        select(ContentPost, CreativePerformanceMetric)
        .outerjoin(CreativePerformanceMetric, CreativePerformanceMetric.post_id == ContentPost.id)
        .where(ContentPost.status == "published")
        .order_by(ContentPost.published_at.desc())
        .limit(limit)
    ).all()
    return {
        "items": [creative.performance_view(p, m) for p, m in rows],
        "window_days": creative.WINDOW_DAYS,
        "currency": _currency(db, ctx.merchant_id),
    }


@router.get("/creative/posts/{post_id}")
def creative_post(
    post_id: uuid.UUID,
    ctx: TenantContext = Depends(require("content.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.core.errors import NotFound
    from app.domains.content.models import ContentPost
    from app.domains.intelligence.models import CreativePerformanceMetric

    p = db.get(ContentPost, post_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound(code="post_not_found")
    m = db.scalar(select(CreativePerformanceMetric).where(CreativePerformanceMetric.post_id == post_id))
    return {**creative.performance_view(p, m), "currency": _currency(db, ctx.merchant_id)}


class PostMetricsIn(BaseModel):
    views: int | None = Field(default=None, ge=0, le=1_000_000_000)
    likes: int | None = Field(default=None, ge=0, le=1_000_000_000)
    comments: int | None = Field(default=None, ge=0, le=1_000_000_000)
    shares: int | None = Field(default=None, ge=0, le=1_000_000_000)
    saves: int | None = Field(default=None, ge=0, le=1_000_000_000)
    clicks: int | None = Field(default=None, ge=0, le=1_000_000_000)


@router.post("/creative/posts/{post_id}/metrics", status_code=201)
def creative_post_metrics(
    post_id: uuid.UUID,
    body: PostMetricsIn,
    ctx: TenantContext = Depends(require("content.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.domains.content.models import ContentPost
    from app.domains.intelligence.models import CreativePerformanceMetric

    creative.record_manual(db, ctx, post_id, body.model_dump())
    p = db.get(ContentPost, post_id)
    m = db.scalar(select(CreativePerformanceMetric).where(CreativePerformanceMetric.post_id == post_id))
    return creative.performance_view(p, m)


@router.get("/creative/suggestions")
def creative_suggestions(
    ctx: TenantContext = Depends(require("content.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    _creative_on(db, ctx)
    return creative.suggestions(db, ctx.merchant_id)


@router.get("/creative/experiments")
def list_experiments(
    ctx: TenantContext = Depends(require("content.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    from app.domains.intelligence.models import CreativeExperiment

    _creative_on(db, ctx)
    rows = db.scalars(select(CreativeExperiment).order_by(CreativeExperiment.created_at.desc()).limit(50))
    return {"items": [creative.experiment_view(e) for e in rows], "attributes": list(creative.ATTRIBUTES)}


class ExperimentIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    hypothesis: str = Field(min_length=3, max_length=300)
    attribute: str = Field(max_length=30)
    variant_a: str = Field(min_length=1, max_length=30)
    variant_b: str = Field(min_length=1, max_length=30)
    metric: Literal["orders", "inquiries"] = "orders"
    min_posts: int = Field(default=5, ge=3, le=50)
    max_days: int = Field(default=30, ge=7, le=90)


@router.post("/creative/experiments", status_code=201)
def create_experiment(
    body: ExperimentIn,
    ctx: TenantContext = Depends(require("content.publish")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _creative_on(db, ctx)
    return creative.experiment_view(creative.create_experiment(db, ctx, body.model_dump()))


@router.post("/creative/experiments/{exp_id}/stop")
def stop_experiment(
    exp_id: uuid.UUID,
    ctx: TenantContext = Depends(require("content.publish")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _creative_on(db, ctx)
    return creative.experiment_view(creative.stop_experiment(db, ctx, exp_id))
