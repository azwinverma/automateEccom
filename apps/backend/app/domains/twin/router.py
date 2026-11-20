from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.errors import NotFound, ValidationFailed
from app.domains.billing.service import entitlements
from app.domains.twin import service as twin
from app.domains.twin import simulation
from app.domains.twin.models import SimulationRun

router = APIRouter(tags=["twin"])


def _currency(db: Session, merchant_id: uuid.UUID) -> str:
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, merchant_id)
    return m.currency if m else "NPR"


# ----------------------------------------------------------------------------- Twin (TWIN-005/006)
@router.get("/twin/summary")
def twin_summary(
    sections: str | None = Query(default=None, description="Comma-separated section names; default all"),
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    names = [s.strip() for s in sections.split(",") if s.strip()] if sections else None
    if names and any(n not in twin.SECTIONS for n in names):
        raise ValidationFailed(
            "Unknown section", code="twin_section_unknown", details={"allowed": list(twin.SECTIONS)}
        )
    return {
        "sections": twin.read(db, ctx.merchant_id, names),
        "registry": list(twin.SECTIONS),
        "currency": _currency(db, ctx.merchant_id),
    }


@router.get("/twin/sections/{name}")
def twin_section(
    name: str,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    if name not in twin.SECTIONS:
        raise NotFound(code="twin_section_unknown")
    return twin.read(db, ctx.merchant_id, [name])[name]


@router.post("/twin/reconcile")
def twin_reconcile(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return {"sections": twin.reconcile(db, ctx.merchant_id)}


@router.get("/twin/freshness")
def twin_freshness(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return twin.freshness(db, ctx.merchant_id)


# ----------------------------------------------------------------------------- Simulation (SIM-001…006)
def _on(db: Session, ctx: TenantContext) -> None:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.simulation")


class DiscountIn(BaseModel):
    product_id: uuid.UUID
    discount_pct: float = Field(ge=1, le=70)
    days: int = Field(default=14, ge=3, le=60)


class PurchaseIn(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(ge=1, le=1_000_000)
    supplier_id: uuid.UUID | None = None


class SimulationIn(BaseModel):
    kind: Literal["discount", "purchase_quantity", "ad_budget"]
    discount: DiscountIn | None = None
    purchase: PurchaseIn | None = None


@router.post("/simulations", status_code=202)
def create_simulation(
    body: SimulationIn,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    if body.kind == "discount":
        if body.discount is None:
            raise ValidationFailed("Discount inputs are required", code="simulation_inputs_required")
        inputs = body.discount.model_dump(mode="json")
    elif body.kind == "purchase_quantity":
        if body.purchase is None:
            raise ValidationFailed("Purchase inputs are required", code="simulation_inputs_required")
        inputs = body.purchase.model_dump(mode="json")
    else:
        inputs = {}
    return simulation.view(simulation.create(db, ctx, body.kind, inputs))


@router.get("/simulations")
def list_simulations(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    _on(db, ctx)
    rows = db.scalars(select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(50))
    return {"items": [simulation.view(r) for r in rows], "currency": _currency(db, ctx.merchant_id)}


@router.get("/simulations/calibration")
def simulation_calibration(
    ctx: TenantContext = Depends(require("analytics.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    _on(db, ctx)
    return simulation.calibration(db, ctx.merchant_id)


@router.get("/simulations/{run_id}")
def get_simulation(
    run_id: uuid.UUID,
    ctx: TenantContext = Depends(require("analytics.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return {**simulation.view(simulation.get(db, ctx, run_id)), "currency": _currency(db, ctx.merchant_id)}
