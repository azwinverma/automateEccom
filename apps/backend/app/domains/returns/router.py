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
from app.core.errors import ValidationFailed
from app.core.pagination import decode_cursor, encode_cursor
from app.domains.catalog.models import Product, Variant
from app.domains.inventory import service as inventory
from app.domains.orders import service as orders
from app.domains.orders.models import Order, OrderLine
from app.domains.returns import service
from app.domains.returns.models import CONDITIONS, REFUND_METHODS, RETURN_REASONS, Refund, ReturnRequest

router = APIRouter(tags=["returns"])

BUCKETS: dict[str, tuple[str, ...]] = {
    "to_decide": ("requested",),
    "in_progress": ("approved", "in_transit", "received"),
    "to_refund": ("inspected",),
    "done": ("refunded", "exchanged", "closed", "rejected", "cancelled"),
}


def _need_key(idem: str | None, what: str) -> str:
    if not idem:
        raise ValidationFailed(
            f"Idempotency-Key header is required for {what}", code="idempotency_key_required"
        )
    return idem


# ----------------------------------------------------------------------------- policy
class PolicyIn(BaseModel):
    window_days: int | None = Field(default=None, ge=0, le=90)
    allow_refund: bool | None = None
    allow_exchange: bool | None = None
    evidence_reasons: list[str] | None = Field(default=None, max_length=len(RETURN_REASONS))
    return_shipping_fee_minor: int | None = Field(default=None, ge=0, le=10_000_000, strict=True)
    auto_approve: bool | None = None
    auto_refund_max_minor: int | None = Field(default=None, ge=0, le=10_000_000_000, strict=True)
    notes: str | None = Field(default=None, max_length=1000)


@router.get("/returns/policy")
def get_policy(
    ctx: TenantContext = Depends(require("returns.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return service.policy_view(service.get_policy(db, ctx.merchant_id))


@router.patch("/returns/policy")
def update_policy(
    body: PolicyIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.policy_view(service.update_policy(db, ctx, body.model_dump(exclude_unset=True)))


# ----------------------------------------------------------------------------- order → what can come back
@router.get("/orders/{order_id}/returnable")
def returnable(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("returns.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Lines with the quantity still returnable, the refund per unit and exchange options."""
    o = orders.get_order(db, ctx, order_id)
    policy = service.get_policy(db, ctx.merchant_id)
    left = service.returnable_quantities(db, o)
    at = service.delivered_at(db, o)
    lines = []
    for ln in db.scalars(select(OrderLine).where(OrderLine.order_id == o.id).order_by(OrderLine.position)):
        p = db.get(Product, ln.product_id) if ln.product_id else None
        options = []
        if p is not None:
            vs = list(
                db.scalars(
                    select(Variant).where(
                        Variant.product_id == p.id,
                        Variant.status == "active",
                        Variant.price_minor == ln.unit_price_minor,
                    )
                )
            )
            av = inventory.availability(db, ctx.merchant_id, [v.id for v in vs])
            options = [
                {
                    "variant_id": v.id,
                    "title": v.title,
                    "available": av[v.id].available if av[v.id].tracked else None,
                }
                for v in vs
                if v.id != ln.variant_id
            ]
        lines.append(
            {
                "order_line_id": ln.id,
                "title": ln.title,
                "variant_title": ln.variant_title,
                "sku": ln.sku,
                "returnable_quantity": max(0, left.get(ln.id, 0)),
                "unit_refund_minor": service._unit_refund(o, ln),
                "final_sale": bool(p and p.final_sale),
                "exchange_options": options,
            }
        )
    from datetime import timedelta

    return {
        "order_id": o.id,
        "order_status": o.status,
        "delivered_at": at,
        "deadline": at + timedelta(days=policy.window_days) if at else None,
        "currency": o.currency,
        "lines": lines,
        "policy": service.policy_view(policy),
        "refundable_minor": max(0, service.paid_minor(db, o) - service.refunded_minor(db, o.id)),
    }


class LineIn(BaseModel):
    order_line_id: uuid.UUID
    quantity: int = Field(ge=1, le=10_000)
    reason: str = Field(pattern=f"^({'|'.join(RETURN_REASONS)})$")
    reason_note: str | None = Field(default=None, max_length=500)
    evidence_asset_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    exchange_variant_id: uuid.UUID | None = None


class ReturnIn(BaseModel):
    resolution: Literal["refund", "exchange"] = "refund"
    lines: list[LineIn] = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=1000)


def _lines(body: ReturnIn) -> list[service.LineIn]:
    return [service.LineIn(**li.model_dump()) for li in body.lines]


@router.post("/orders/{order_id}/returns/check")
def check_eligibility(
    order_id: uuid.UUID,
    body: ReturnIn,
    ctx: TenantContext = Depends(require("returns.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = orders.get_order(db, ctx, order_id)
    eligible, hard_ok, checks = service.check_eligibility(
        db, o, _lines(body), body.resolution, service.get_policy(db, ctx.merchant_id)
    )
    return {"eligible": eligible, "can_request": hard_ok, "checks": checks}


@router.post("/orders/{order_id}/returns", status_code=201)
def create_return(
    order_id: uuid.UUID,
    body: ReturnIn,
    ctx: TenantContext = Depends(require("returns.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key", max_length=160),
) -> Any:
    key = _need_key(idem, "creating a return")

    def _run() -> dict[str, Any]:
        r = service.create(db, ctx, order_id, _lines(body), body.resolution, key, note=body.note)
        return service.return_view(db, r, detail=True)

    return run_idempotent(
        db,
        key=key,
        owner=f"merchant:{ctx.merchant_id}",
        scope=f"POST /orders/{order_id}/returns",
        body=body,
        status_code=201,
        fn=_run,
    )


@router.get("/orders/{order_id}/returns")
def order_returns(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("returns.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = orders.get_order(db, ctx, order_id)
    rows = db.scalars(
        select(ReturnRequest).where(ReturnRequest.order_id == o.id).order_by(ReturnRequest.id.desc())
    )
    return {"items": [service.return_view(db, r, detail=True) for r in rows]}


# ----------------------------------------------------------------------------- returns
@router.get("/returns")
def list_returns(
    bucket: str | None = Query(default=None, pattern="^(to_decide|in_progress|to_refund|done)$"),
    q: str | None = Query(default=None, max_length=80),
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require("returns.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from sqlalchemy import func

    stmt = select(ReturnRequest).join(Order, Order.id == ReturnRequest.order_id)
    if bucket:
        stmt = stmt.where(ReturnRequest.status.in_(BUCKETS[bucket]))
    if q:
        term = q.strip().lstrip("#")
        conds: list[Any] = [ReturnRequest.number.ilike(f"%{term}%"), Order.ship_name.ilike(f"%{term}%")]
        if term.isdigit():
            conds.append(Order.number == int(term))
        stmt = stmt.where(or_(*conds))
    if cursor:
        stmt = stmt.where(ReturnRequest.id < decode_cursor(cursor))
    rows = list(db.scalars(stmt.order_by(ReturnRequest.id.desc()).limit(limit + 1)))
    counts = dict(db.execute(select(ReturnRequest.status, func.count()).group_by(ReturnRequest.status)).all())
    return {
        "items": [service.return_view(db, r) for r in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1].id) if len(rows) > limit else None,
        "counts": {k: int(sum(counts.get(s, 0) for s in v)) for k, v in BUCKETS.items()},
    }


@router.get("/returns/{return_id}")
def get_return(
    return_id: uuid.UUID,
    ctx: TenantContext = Depends(require("returns.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.return_view(db, service.get_return(db, ctx, return_id), detail=True)


class ApproveIn(BaseModel):
    override_reason: str | None = Field(default=None, max_length=300)


@router.post("/returns/{return_id}/approve")
def approve(
    return_id: uuid.UUID,
    body: ApproveIn,
    ctx: TenantContext = Depends(require("returns.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    r = service.approve(db, ctx, return_id, override_reason=body.override_reason)
    return service.return_view(db, r, detail=True)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/returns/{return_id}/reject")
def reject(
    return_id: uuid.UUID,
    body: ReasonIn,
    ctx: TenantContext = Depends(require("returns.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.return_view(db, service.reject(db, ctx, return_id, body.reason), detail=True)


class OptionalReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


@router.post("/returns/{return_id}/cancel")
def cancel(
    return_id: uuid.UUID,
    body: OptionalReasonIn,
    ctx: TenantContext = Depends(require("returns.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.return_view(db, service.cancel(db, ctx, return_id, body.reason), detail=True)


class PickupIn(BaseModel):
    courier_account_id: uuid.UUID
    tracking_number: str | None = Field(default=None, max_length=80)
    courier_name: str | None = Field(default=None, max_length=80)


@router.post("/returns/{return_id}/pickup", status_code=201)
def book_pickup(
    return_id: uuid.UUID,
    body: PickupIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key", max_length=160),
) -> Any:
    key = _need_key(idem, "booking a return pickup")

    def _run() -> dict[str, Any]:
        service.book_pickup(
            db,
            ctx,
            return_id,
            body.courier_account_id,
            key,
            tracking_number=body.tracking_number,
            courier_name=body.courier_name,
        )
        return service.return_view(db, service.get_return(db, ctx, return_id), detail=True)

    return run_idempotent(
        db,
        key=key,
        owner=f"merchant:{ctx.merchant_id}",
        scope=f"POST /returns/{return_id}/pickup",
        body=body,
        status_code=201,
        fn=_run,
    )


@router.post("/returns/{return_id}/received")
def received(
    return_id: uuid.UUID,
    ctx: TenantContext = Depends(require("returns.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.return_view(db, service.mark_received(db, ctx, return_id), detail=True)


class InspectLineIn(BaseModel):
    line_id: uuid.UUID
    condition: str = Field(pattern=f"^({'|'.join(CONDITIONS)})$")
    restock: int = Field(default=0, ge=0, le=10_000)
    note: str | None = Field(default=None, max_length=500)


class InspectIn(BaseModel):
    items: list[InspectLineIn] = Field(min_length=1, max_length=100)


@router.post("/returns/{return_id}/inspect")
def inspect(
    return_id: uuid.UUID,
    body: InspectIn,
    ctx: TenantContext = Depends(require("returns.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    r = service.inspect(db, ctx, return_id, [service.InspectIn(**i.model_dump()) for i in body.items])
    return service.return_view(db, r, detail=True)


# ----------------------------------------------------------------------------- refunds
class RefundIn(BaseModel):
    amount_minor: int = Field(gt=0, le=10_000_000_000, strict=True)
    method: str = Field(pattern=f"^({'|'.join(REFUND_METHODS)})$")
    return_id: uuid.UUID | None = None
    reference: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=300)


@router.post("/orders/{order_id}/refunds", status_code=201)
def create_refund(
    order_id: uuid.UUID,
    body: RefundIn,
    ctx: TenantContext = Depends(require("refunds.create")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key", max_length=160),
) -> Any:
    key = _need_key(idem, "refunds")

    def _run() -> dict[str, Any]:
        ref = service.request_refund(
            db,
            ctx,
            order_id,
            body.amount_minor,
            body.method,
            key,
            return_id=body.return_id,
            reference=body.reference,
            reason=body.reason,
        )
        return service.refund_view(ref)

    return run_idempotent(
        db,
        key=key,
        owner=f"merchant:{ctx.merchant_id}",
        scope=f"POST /orders/{order_id}/refunds",
        body=body,
        status_code=201,
        fn=_run,
    )


@router.get("/orders/{order_id}/refunds")
def order_refunds(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("refunds.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = orders.get_order(db, ctx, order_id)
    rows = db.scalars(select(Refund).where(Refund.order_id == o.id).order_by(Refund.id))
    return {"items": [service.refund_view(x) for x in rows]}


@router.get("/refunds")
def list_refunds(
    status: str | None = Query(
        default=None, pattern="^(pending_approval|processing|succeeded|failed|rejected)$"
    ),
    ctx: TenantContext = Depends(require("refunds.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(Refund).order_by(Refund.id.desc()).limit(200)
    if status:
        stmt = stmt.where(Refund.status == status)
    out = []
    for x in db.scalars(stmt):
        v = service.refund_view(x)
        o = db.get(Order, x.order_id)
        v["order_number"] = o.number if o else None
        out.append(v)
    return {"items": out}


@router.post("/refunds/{refund_id}/approve")
def approve_refund(
    refund_id: uuid.UUID,
    ctx: TenantContext = Depends(require("refunds.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.refund_view(service.approve_refund(db, ctx, refund_id))


@router.post("/refunds/{refund_id}/reject")
def reject_refund(
    refund_id: uuid.UUID,
    body: ReasonIn,
    ctx: TenantContext = Depends(require("refunds.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.refund_view(service.reject_refund(db, ctx, refund_id, body.reason))


@router.post("/refunds/{refund_id}/retry")
def retry_refund(
    refund_id: uuid.UUID,
    ctx: TenantContext = Depends(require("refunds.create")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.refund_view(service.retry_refund(db, ctx, refund_id))
