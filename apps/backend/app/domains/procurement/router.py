from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.api.idempotent import run_idempotent
from app.core.context import TenantContext
from app.core.errors import ValidationFailed
from app.domains.billing.service import entitlements
from app.domains.catalog.models import Supplier
from app.domains.procurement import service, supplier_intel
from app.domains.procurement.models import PO_STATUSES, PurchaseOrder

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _on(db: Session, ctx: TenantContext) -> None:
    entitlements.require_feature(db, ctx.merchant_id, "procurement")


def _currency(db: Session, merchant_id: uuid.UUID) -> str:
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, merchant_id)
    return m.currency if m else "NPR"


def _key(idem: str | None, what: str) -> str:
    if not idem or not 8 <= len(idem) <= 128:
        raise ValidationFailed(
            f"An Idempotency-Key (8-128 characters) is required for {what}", code="idempotency_key_required"
        )
    return idem


# ----------------------------------------------------------------------------- suppliers
class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    contact_name: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    default_lead_time_days: int | None = Field(default=None, ge=0, le=365)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class SupplierPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    contact_name: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    default_lead_time_days: int | None = Field(default=None, ge=0, le=365)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "archived"] | None = None


@router.get("/suppliers")
def list_suppliers(
    include_archived: bool = False,
    ctx: TenantContext = Depends(require("procurement.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    stmt = select(Supplier).order_by(Supplier.name)
    if not include_archived:
        stmt = stmt.where(Supplier.status == "active")
    ms = (
        supplier_intel.metrics(db, ctx.merchant_id)
        if entitlements.resolve(db, ctx.merchant_id).has("intelligence.supplier")
        else {}
    )
    return {
        "items": [
            {**service.supplier_view(s), "performance": supplier_intel.view(ms[s.id]) if s.id in ms else None}
            for s in db.scalars(stmt)
        ],
        "performance_available": bool(entitlements.resolve(db, ctx.merchant_id).has("intelligence.supplier")),
        "currency": _currency(db, ctx.merchant_id),
    }


@router.post("/suppliers", status_code=201)
def create_supplier(
    body: SupplierIn,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.supplier_view(service.create_supplier(db, ctx, body.model_dump()))


@router.get("/suppliers/{supplier_id}")
def get_supplier(
    supplier_id: uuid.UUID,
    ctx: TenantContext = Depends(require("procurement.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    s = service.get_supplier(db, ctx, supplier_id)
    m = (
        supplier_intel.metrics(db, ctx.merchant_id).get(s.id)
        if entitlements.resolve(db, ctx.merchant_id).has("intelligence.supplier")
        else None
    )
    return {
        **service.supplier_view(s),
        "products": service.supplier_products(db, ctx.merchant_id, s.id),
        "performance": supplier_intel.view(m) if m else None,
        "currency": _currency(db, ctx.merchant_id),
    }


@router.patch("/suppliers/{supplier_id}")
def update_supplier(
    supplier_id: uuid.UUID,
    body: SupplierPatch,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.supplier_view(
        service.update_supplier(db, ctx, supplier_id, body.model_dump(exclude_unset=True))
    )


class SupplierProductIn(BaseModel):
    supplier_sku: str | None = Field(default=None, max_length=80)
    cost_minor: int | None = Field(default=None, ge=0, le=10_000_000_000)
    moq: int | None = Field(default=None, ge=1, le=1_000_000)
    lead_time_days: int | None = Field(default=None, ge=0, le=365)
    is_preferred: bool = False


@router.put("/suppliers/{supplier_id}/products/{variant_id}")
def set_supplier_product(
    supplier_id: uuid.UUID,
    variant_id: uuid.UUID,
    body: SupplierProductIn,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    service.set_supplier_product(db, ctx, supplier_id, variant_id, body.model_dump(exclude_unset=True))
    return {"items": service.supplier_products(db, ctx.merchant_id, supplier_id)}


@router.delete("/suppliers/{supplier_id}/products/{variant_id}")
def remove_supplier_product(
    supplier_id: uuid.UUID,
    variant_id: uuid.UUID,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    service.remove_supplier_product(db, ctx, supplier_id, variant_id)
    return {"items": service.supplier_products(db, ctx.merchant_id, supplier_id)}


@router.post("/suppliers/performance/refresh")
def refresh_performance(
    ctx: TenantContext = Depends(require("procurement.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    entitlements.require_feature(db, ctx.merchant_id, "intelligence.supplier")
    return {"suppliers": supplier_intel.compute(db, ctx.merchant_id)}


# ----------------------------------------------------------------------------- purchase orders
class POLineIn(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(ge=1, le=1_000_000)
    unit_cost_minor: int | None = Field(default=None, ge=0, le=10_000_000_000)


class POIn(BaseModel):
    supplier_id: uuid.UUID
    lines: list[POLineIn] = Field(min_length=1, max_length=200)
    freight_minor: int = Field(default=0, ge=0, le=10_000_000_000)
    duty_minor: int = Field(default=0, ge=0, le=10_000_000_000)
    other_minor: int = Field(default=0, ge=0, le=10_000_000_000)
    expected_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)
    location_id: uuid.UUID | None = None


class POPatch(BaseModel):
    version: int | None = None
    lines: list[POLineIn] | None = Field(default=None, min_length=1, max_length=200)
    freight_minor: int | None = Field(default=None, ge=0, le=10_000_000_000)
    duty_minor: int | None = Field(default=None, ge=0, le=10_000_000_000)
    other_minor: int | None = Field(default=None, ge=0, le=10_000_000_000)
    expected_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


@router.get("/purchase-orders")
def list_pos(
    status: str | None = Query(default=None, pattern="^(" + "|".join(PO_STATUSES) + ")$"),
    supplier_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require("procurement.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    if supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    return {"items": [service.po_view(db, po) for po in db.scalars(stmt)]}


@router.post("/purchase-orders", status_code=201)
def create_po(
    body: POIn,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key", max_length=160),
) -> Any:
    _on(db, ctx)
    key = _key(idem, "creating a purchase order")

    def _run() -> dict[str, Any]:
        data = body.model_dump()
        return service.po_view(db, service.create_po(db, ctx, data, idempotency_key=key))

    return run_idempotent(
        db,
        key=key,
        owner=f"merchant:{ctx.merchant_id}",
        scope="POST /procurement/purchase-orders",
        body=body,
        status_code=201,
        fn=_run,
    )


@router.get("/purchase-orders/{po_id}")
def get_po(
    po_id: uuid.UUID,
    ctx: TenantContext = Depends(require("procurement.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.po_view(db, service.get_po(db, ctx, po_id))


@router.patch("/purchase-orders/{po_id}")
def update_po(
    po_id: uuid.UUID,
    body: POPatch,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    data = body.model_dump(exclude_unset=True)
    version = data.pop("version", None)
    if data.get("lines") is not None:
        data["lines"] = [ln.model_dump() for ln in body.lines or []]
    return service.po_view(db, service.update_po(db, ctx, po_id, version, data))


@router.post("/purchase-orders/{po_id}/submit")
def submit_po(
    po_id: uuid.UUID,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.po_view(db, service.submit(db, ctx, po_id))


@router.post("/purchase-orders/{po_id}/approve")
def approve_po(
    po_id: uuid.UUID,
    ctx: TenantContext = Depends(require("procurement.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.po_view(db, service.approve(db, ctx, po_id))


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/purchase-orders/{po_id}/reject")
def reject_po(
    po_id: uuid.UUID,
    body: ReasonIn,
    ctx: TenantContext = Depends(require("procurement.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.po_view(db, service.reject(db, ctx, po_id, body.reason))


@router.post("/purchase-orders/{po_id}/send")
def send_po(
    po_id: uuid.UUID,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.po_view(db, service.mark_sent(db, ctx, po_id))


@router.post("/purchase-orders/{po_id}/cancel")
def cancel_po(
    po_id: uuid.UUID,
    body: ReasonIn,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    _on(db, ctx)
    return service.po_view(db, service.cancel(db, ctx, po_id, body.reason))


class ReceiveLineIn(BaseModel):
    po_line_id: uuid.UUID
    quantity: int = Field(default=0, ge=0, le=1_000_000)
    defective_quantity: int = Field(default=0, ge=0, le=1_000_000)


class ReceiveIn(BaseModel):
    lines: list[ReceiveLineIn] = Field(min_length=1, max_length=200)
    lot_code: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=500)


@router.post("/purchase-orders/{po_id}/receipts", status_code=201)
def receive_po(
    po_id: uuid.UUID,
    body: ReceiveIn,
    ctx: TenantContext = Depends(require("procurement.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key", max_length=160),
) -> Any:
    _on(db, ctx)
    key = _key(idem, "receiving stock")

    def _run() -> dict[str, Any]:
        service.receive(
            db,
            ctx,
            po_id,
            [ln.model_dump() for ln in body.lines],
            idempotency_key=key,
            lot_code=body.lot_code,
            note=body.note,
        )
        return service.po_view(db, service.get_po(db, ctx, po_id))

    return run_idempotent(
        db,
        key=key,
        owner=f"merchant:{ctx.merchant_id}",
        scope=f"POST /procurement/purchase-orders/{po_id}/receipts",
        body=body,
        status_code=201,
        fn=_run,
    )


@router.get("/incoming")
def incoming_stock(
    ctx: TenantContext = Depends(require("procurement.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    """Units on approved/sent orders that haven't arrived, per variant."""
    from app.domains.procurement.models import PurchaseOrderLine

    _on(db, ctx)
    vids = list(db.scalars(select(PurchaseOrderLine.variant_id).distinct()))
    return {
        "items": [
            {"variant_id": str(k), "quantity": v}
            for k, v in service.incoming(db, ctx.merchant_id, vids).items()
            if v > 0
        ]
    }
