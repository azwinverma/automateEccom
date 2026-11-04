from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.api.idempotent import run_idempotent
from app.core.context import TenantContext
from app.core.errors import PermissionDenied
from app.core.pagination import build_page, paginate_desc
from app.domains.customers import service as customers
from app.domains.customers.router import AddressIn
from app.domains.orders import service
from app.domains.orders.models import ORDER_STATUSES, Order

router = APIRouter(tags=["orders"])
Minor = Field(default=0, ge=0, le=10_000_000_000, strict=True)


class LineIn(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0, le=10_000, strict=True)
    unit_price_minor: int | None = Field(default=None, ge=0, le=10_000_000_000, strict=True)
    line_discount_minor: int = Minor


class OrderIn(BaseModel):
    lines: list[LineIn] = Field(min_length=1, max_length=100)
    customer_id: uuid.UUID | None = None
    customer_name: str | None = Field(default=None, max_length=160)
    customer_phone: str | None = Field(default=None, max_length=24)
    address: AddressIn | None = None
    address_id: uuid.UUID | None = None
    save_address: bool = True
    payment_method: Literal["cod", "prepaid"] = "cod"
    delivery_fee_minor: int = Minor
    discount_minor: int = Minor
    tax_minor: int = Minor
    notes: str | None = Field(default=None, max_length=2000)
    confirm: bool = True


class TransitionIn(BaseModel):
    to: str = Field(pattern=f"^({'|'.join(ORDER_STATUSES)})$")
    reason: str | None = Field(default=None, max_length=300)
    expected_version: int | None = None


class CancelLine(BaseModel):
    line_id: uuid.UUID
    quantity: int = Field(gt=0, le=10_000, strict=True)


class CancelLinesIn(BaseModel):
    items: list[CancelLine] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=2, max_length=300)


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


@router.get("/orders")
def list_orders(
    status: str | None = Query(None, max_length=200),
    q: str | None = Query(None, max_length=100),
    customer_id: uuid.UUID | None = None,
    needs_review: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status.in_([s for s in status.split(",") if s in ORDER_STATUSES]))
    if customer_id:
        stmt = stmt.where(Order.customer_id == customers.get_customer(db, ctx, customer_id).id)
    if needs_review is not None:
        stmt = stmt.where(Order.needs_review.is_not(None) if needs_review else Order.needs_review.is_(None))
    if q:
        term = q.strip().lstrip("#")
        conds = [Order.ship_name.ilike(f"%{term}%"), Order.external_number == term]
        if term.isdigit():
            conds.append(Order.number == int(term))
            if len(term) >= 4:
                conds.append(Order.ship_phone.like(f"%{term[-10:]}%"))
        stmt = stmt.where(or_(*conds))
    rows = list(db.scalars(paginate_desc(stmt, Order.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {"items": [service.order_view(db, o) for o in items], "next_cursor": nxt}


@router.post("/orders", status_code=201)
def create_order(
    body: OrderIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """Seller-entered order (ORD-007). With ``confirm`` (default) stock is reserved straight away."""

    def _do() -> dict[str, Any]:
        o = service.create_order(
            db,
            ctx,
            service.OrderInput(
                lines=[service.LineInput(**ln.model_dump()) for ln in body.lines],
                customer_id=body.customer_id,
                customer_name=body.customer_name,
                customer_phone=body.customer_phone,
                address=customers.AddressInput(**body.address.model_dump()) if body.address else None,
                address_id=body.address_id,
                save_address=body.save_address,
                payment_method=body.payment_method,
                delivery_fee_minor=body.delivery_fee_minor,
                discount_minor=body.discount_minor,
                tax_minor=body.tax_minor,
                notes=body.notes,
                source="seller",
                confirm=body.confirm,
            ),
        )
        return service.order_view(db, o, detail=True)

    return run_idempotent(
        db,
        key=idem,
        owner=f"merchant:{ctx.merchant_id}",
        scope="orders.create",
        body=body.model_dump(mode="json"),
        status_code=201,
        fn=_do,
    )


@router.get("/orders/{order_id}")
def get_order(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.order_view(db, service.get_order(db, ctx, order_id), detail=True)


@router.post("/orders/{order_id}/transition")
def transition(
    order_id: uuid.UUID,
    body: TransitionIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    if body.to == "cancelled" and not ctx.has("orders.cancel"):
        raise PermissionDenied(details={"permission": "orders.cancel"})
    o = service.transition(
        db, ctx, order_id, body.to, reason=body.reason, expected_version=body.expected_version
    )
    return service.order_view(db, o, detail=True)


@router.post("/orders/{order_id}/cancel-lines")
def cancel_lines(
    order_id: uuid.UUID,
    body: CancelLinesIn,
    ctx: TenantContext = Depends(require("orders.cancel")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = service.cancel_lines(db, ctx, order_id, [(i.line_id, i.quantity) for i in body.items], body.reason)
    return service.order_view(db, o, detail=True)


@router.post("/orders/{order_id}/notes", status_code=201)
def add_note(
    order_id: uuid.UUID,
    body: NoteIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    ev = service.add_note(db, ctx, order_id, body.note)
    db.flush()
    return {"id": ev.id}


@router.get("/orders/{order_id}/timeline")
def timeline(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return {"items": service.timeline(db, ctx, order_id)}
