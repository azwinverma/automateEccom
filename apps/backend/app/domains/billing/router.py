from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.pagination import build_page, paginate_desc
from app.domains.billing.models import CreditTransaction, Plan, PlanVersion
from app.domains.billing.service import entitlements

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription")
def subscription(
    ctx: TenantContext = Depends(require("billing.read")), db: Session = Depends(get_db)
) -> dict:
    ent = entitlements.resolve(db, ctx.merchant_id)
    sub = ent.subscription
    if sub is None:
        return {"plan": None, "status": "none"}
    pv = db.get(PlanVersion, sub.plan_version_id)
    plan = db.get(Plan, pv.plan_id) if pv else None
    return {
        "plan": {"code": plan.code, "name": plan.name, "tagline_key": plan.tagline_key} if plan else None,
        "plan_version": pv.version if pv else None,
        "price": {
            "monthly_minor": pv.price_monthly_minor,
            "annual_minor": pv.price_annual_minor,
            "currency": pv.currency,
        }
        if pv
        else None,
        "status": sub.status,
        "trial_ends_at": sub.trial_ends_at,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
    }


@router.get("/entitlements")
def get_entitlements(
    ctx: TenantContext = Depends(require("billing.read")), db: Session = Depends(get_db)
) -> dict:
    ent = entitlements.resolve(db, ctx.merchant_id)
    return {
        "plan": ent.plan_code,
        "features": ent.features,
        "limits": entitlements.usage_summary(db, ctx.merchant_id),
    }


@router.get("/credits")
def credits(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("billing.read")),
    db: Session = Depends(get_db),
) -> dict:
    rows = list(db.scalars(paginate_desc(select(CreditTransaction), CreditTransaction.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {
        "balance": entitlements.balance(db, ctx.merchant_id),
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "kind": t.kind,
                "reference_type": t.reference_type,
                "created_at": t.created_at,
            }
            for t in items
        ],
        "next_cursor": nxt,
    }
