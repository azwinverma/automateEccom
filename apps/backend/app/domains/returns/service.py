"""Returns, exchanges and refunds (RET-001…011, PAY-007).

* Eligibility is computed from the merchant's policy and recorded on the request. Hard failures
  (not delivered, nothing left to return, exchange to another product) refuse the request; soft ones
  (window passed, final sale, missing evidence) can be overridden by someone with returns.approve,
  with a reason, audited.
* Abuse signals (RET-011) use this merchant's own operational facts only (never names, gender,
  location-derived traits or other merchants' data). Any signal turns automation off for the request.
* Exchanges reserve the replacement stock at approval (reference = the return) and create the
  replacement order once the returned item is inspected.
* Refunds are idempotent (Idempotency-Key), provider-tracked, never exceed what was paid, and above
  the policy threshold wait for someone with refunds.approve.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, NotFound, PermissionDenied, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.automation.policy import log_action
from app.domains.catalog.models import Product, Variant
from app.domains.customers import service as customers
from app.domains.integrations import registry
from app.domains.integrations.base import IntegrationError, Money, PaymentCapability
from app.domains.inventory import service as inventory
from app.domains.orders import service as orders
from app.domains.orders.models import Order, OrderEvent, OrderLine
from app.domains.payments.models import Payment
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler
from app.domains.returns.models import (
    OPEN_RETURN_STATUSES,
    RETURN_REASONS,
    SHOP_FAULT_REASONS,
    Refund,
    ReturnLine,
    ReturnPolicy,
    ReturnRequest,
)

log = structlog.get_logger(__name__)

RETURNABLE_ORDER_STATUSES = ("delivered", "completed")
SOFT_CHECKS = frozenset({"within_window", "not_final_sale", "evidence"})
COUNTED_STATUSES = (
    "requested",
    "approved",
    "in_transit",
    "received",
    "inspected",
    "refunded",
    "exchanged",
    "closed",
)
OPEN_REFUND = ("pending_approval", "processing", "succeeded")


# ----------------------------------------------------------------------------- policy (RET-001)
def get_policy(db: Session, merchant_id: uuid.UUID) -> ReturnPolicy:
    row = db.scalar(select(ReturnPolicy).where(ReturnPolicy.merchant_id == merchant_id))
    if row is not None:
        return row
    db.execute(
        pg_insert(ReturnPolicy)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            window_days=7,
            allow_refund=True,
            allow_exchange=True,
            evidence_reasons=list(SHOP_FAULT_REASONS),
            return_shipping_fee_minor=0,
            auto_approve=False,
            auto_refund_max_minor=0,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["merchant_id"])
    )
    row = db.scalar(select(ReturnPolicy).where(ReturnPolicy.merchant_id == merchant_id))
    assert row is not None
    return row


POLICY_FIELDS = (
    "window_days",
    "allow_refund",
    "allow_exchange",
    "evidence_reasons",
    "return_shipping_fee_minor",
    "auto_approve",
    "auto_refund_max_minor",
    "notes",
)


def update_policy(db: Session, ctx: TenantContext, fields: dict[str, Any]) -> ReturnPolicy:
    p = get_policy(db, ctx.merchant_id)
    if "evidence_reasons" in fields:
        bad = [r for r in fields["evidence_reasons"] if r not in RETURN_REASONS]
        if bad:
            raise ValidationFailed(code="return_reason_invalid", details={"reasons": bad})
        fields["evidence_reasons"] = sorted(set(fields["evidence_reasons"]))
    before = {k: getattr(p, k) for k in fields if k in POLICY_FIELDS}
    for k, v in fields.items():
        if k in POLICY_FIELDS:
            setattr(p, k, v)
    changes = audit.diff(before, {k: getattr(p, k) for k in before})
    if changes:
        audit.record(
            db,
            action="returns.policy_updated",
            resource_type="merchant",
            resource_id=ctx.merchant_id,
            actor=ctx.actor,
            merchant_id=ctx.merchant_id,
            meta=ctx.meta,
            changes=changes,
        )
    return p


def policy_view(p: ReturnPolicy) -> dict[str, Any]:
    return {k: getattr(p, k) for k in POLICY_FIELDS}


# ----------------------------------------------------------------------------- facts
def get_return(db: Session, ctx: TenantContext, return_id: uuid.UUID, *, lock: bool = False) -> ReturnRequest:
    stmt = select(ReturnRequest).where(ReturnRequest.id == return_id)
    if lock:
        stmt = stmt.with_for_update()
    r = db.scalar(stmt)
    if r is None or r.merchant_id != ctx.merchant_id:
        raise NotFound(code="return_not_found")
    return r


def _lines(db: Session, r: ReturnRequest) -> list[ReturnLine]:
    return list(db.scalars(select(ReturnLine).where(ReturnLine.return_id == r.id).order_by(ReturnLine.id)))


def delivered_at(db: Session, o: Order) -> datetime | None:
    from app.domains.fulfillment.models import Shipment

    at = db.scalar(
        select(func.max(Shipment.delivered_at)).where(
            Shipment.order_id == o.id, Shipment.direction == "outbound"
        )
    )
    if at is not None:
        return at
    return db.scalar(
        select(func.max(OrderEvent.created_at)).where(
            OrderEvent.order_id == o.id, OrderEvent.to_status == "delivered"
        )
    )


def returnable_quantities(
    db: Session, o: Order, *, exclude_return: uuid.UUID | None = None
) -> dict[uuid.UUID, int]:
    taken = dict(
        db.execute(
            select(ReturnLine.order_line_id, func.sum(ReturnLine.quantity))
            .join(ReturnRequest, ReturnRequest.id == ReturnLine.return_id)
            .where(
                ReturnRequest.order_id == o.id,
                ReturnRequest.status.in_(COUNTED_STATUSES),
                ReturnRequest.id != (exclude_return or uuid.UUID(int=0)),
            )
            .group_by(ReturnLine.order_line_id)
        ).all()
    )
    return {
        ln.id: ln.active_quantity - int(taken.get(ln.id, 0))
        for ln in db.scalars(select(OrderLine).where(OrderLine.order_id == o.id))
    }


def _unit_refund(o: Order, ln: OrderLine) -> int:
    """What the customer paid per unit: line price net of the line discount and its share of the
    order discount. Delivery fee is handled separately."""
    if not ln.active_quantity:
        return 0
    per_unit = ln.total_minor // ln.active_quantity
    if o.discount_minor and o.subtotal_minor:
        per_unit = per_unit * (o.subtotal_minor - o.discount_minor) // o.subtotal_minor
    return max(0, per_unit)


def paid_minor(db: Session, o: Order) -> int:
    """Money the shop actually received for this order (refunds can never exceed it)."""
    if o.payment_method == "cod":
        return o.total_minor if o.payment_status in ("cod_collected", "refunded") else 0
    online = db.scalar(
        select(func.coalesce(func.sum(func.coalesce(Payment.paid_minor, Payment.amount_minor)), 0)).where(
            Payment.order_id == o.id, Payment.status.in_(("paid", "refunded"))
        )
    )
    return int(online or 0)


def refunded_minor(db: Session, order_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(
                Refund.order_id == order_id, Refund.status.in_(OPEN_REFUND)
            )
        )
        or 0
    )


# ----------------------------------------------------------------------------- eligibility (RET-002)
@dataclass
class LineIn:
    order_line_id: uuid.UUID
    quantity: int
    reason: str
    reason_note: str | None = None
    evidence_asset_ids: list[uuid.UUID] = field(default_factory=list)
    exchange_variant_id: uuid.UUID | None = None


def check_eligibility(
    db: Session, o: Order, lines: list[LineIn], resolution: str, policy: ReturnPolicy
) -> tuple[bool, bool, list[dict[str, Any]]]:
    """Returns (eligible, hard_ok, checks). hard_ok=False means it can't be created at all."""
    checks: list[dict[str, Any]] = []

    def add(code: str, ok: bool, **detail: Any) -> None:
        checks.append({"code": code, "ok": ok, "soft": code in SOFT_CHECKS, **detail})

    add("order_delivered", o.status in RETURNABLE_ORDER_STATUSES, status=o.status)
    at = delivered_at(db, o)
    if at is not None:
        deadline = at + timedelta(days=policy.window_days)
        add(
            "within_window",
            utcnow() <= deadline,
            deadline=deadline.isoformat(),
            window_days=policy.window_days,
        )
    left = returnable_quantities(db, o)
    order_lines = {ln.id: ln for ln in db.scalars(select(OrderLine).where(OrderLine.order_id == o.id))}
    qty_ok, final_sale, evidence_missing, exchange_bad, exchange_stock = True, [], [], [], []
    for li in lines:
        ln = order_lines.get(li.order_line_id)
        if ln is None or li.quantity <= 0 or li.quantity > left.get(li.order_line_id, 0):
            qty_ok = False
            continue
        p = db.get(Product, ln.product_id) if ln.product_id else None
        if p is not None and p.final_sale:
            final_sale.append(ln.title)
        if li.reason in policy.evidence_reasons and not li.evidence_asset_ids:
            evidence_missing.append(ln.title)
        if resolution == "exchange":
            v = db.get(Variant, li.exchange_variant_id) if li.exchange_variant_id else None
            if (
                v is None
                or v.product_id != ln.product_id
                or v.status != "active"
                or v.price_minor != ln.unit_price_minor
            ):
                exchange_bad.append(ln.title)
            else:
                avail = inventory.availability(db, o.merchant_id, [v.id])[v.id]
                if avail.tracked and avail.available < li.quantity:
                    exchange_stock.append(ln.title)
    add("quantity_available", qty_ok)
    add("not_final_sale", not final_sale, items=final_sale)
    add("evidence", not evidence_missing, items=evidence_missing)
    allowed = policy.allow_exchange if resolution == "exchange" else policy.allow_refund
    add("resolution_allowed", allowed, resolution=resolution)
    if resolution == "exchange":
        add("exchange_same_product", not exchange_bad, items=exchange_bad)
        add("exchange_in_stock", not exchange_stock, items=exchange_stock)
    hard_ok = all(c["ok"] for c in checks if not c["soft"])
    eligible = all(c["ok"] for c in checks)
    return eligible, hard_ok, checks


# ----------------------------------------------------------------------------- abuse signals (RET-011)
def abuse_signals(db: Session, o: Order, refund_due: int, current: uuid.UUID) -> list[dict[str, Any]]:
    """Merchant-scoped operational facts only. Prohibited: names, gender, religion, caste, ethnicity,
    inferred sensitive traits and other merchants' data (same rule as COD Intelligence, spec 12)."""
    out: list[dict[str, Any]] = []
    if o.customer_id is None:
        return out
    since90 = utcnow() - timedelta(days=90)
    recent = db.scalar(
        select(func.count())
        .select_from(ReturnRequest)
        .where(
            ReturnRequest.customer_id == o.customer_id,
            ReturnRequest.created_at >= since90,
            ReturnRequest.status.in_(COUNTED_STATUSES),
            ReturnRequest.id != current,
        )
    )
    if recent and recent >= 2:
        out.append({"code": "frequent_returns", "count": int(recent), "days": 90})
    since180 = utcnow() - timedelta(days=180)
    delivered = (
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.customer_id == o.customer_id,
                Order.placed_at >= since180,
                Order.status.in_(("delivered", "completed", "returned")),
            )
        )
        or 0
    )
    returned_orders = (
        db.scalar(
            select(func.count(func.distinct(ReturnRequest.order_id))).where(
                ReturnRequest.customer_id == o.customer_id,
                ReturnRequest.created_at >= since180,
                ReturnRequest.status.in_(COUNTED_STATUSES),
                ReturnRequest.id != current,
            )
        )
        or 0
    )
    if delivered >= 3 and (returned_orders + 1) / delivered >= 0.5:
        out.append(
            {
                "code": "high_return_rate",
                "returned": int(returned_orders) + 1,
                "orders": int(delivered),
                "days": 180,
            }
        )
    avg, n = db.execute(
        select(func.coalesce(func.avg(Order.total_minor), 0), func.count()).where(
            Order.placed_at >= since90, Order.status.not_in(("cancelled", "draft"))
        )
    ).one()
    if int(n) >= 10 and refund_due >= 2 * float(avg):
        out.append({"code": "high_value", "amount_minor": refund_due, "average_order_minor": int(avg)})
    return out


# ----------------------------------------------------------------------------- create
def _publish(db: Session, r: ReturnRequest, before: str) -> None:
    outbox.publish(
        db,
        event_type="returns.status_changed",
        aggregate_type="return",
        aggregate_id=r.id,
        merchant_id=r.merchant_id,
        payload={"return_id": str(r.id), "status": r.status, "from_status": before},
    )


def _order_event(db: Session, r: ReturnRequest, actor: Actor, kind: str, **data: Any) -> None:
    o = db.get(Order, r.order_id)
    assert o is not None
    orders._event(db, o, actor, kind, return_id=str(r.id), return_number=r.number, **data)


def _compute_due(
    db: Session, o: Order, r: ReturnRequest, lines: list[ReturnLine], policy: ReturnPolicy
) -> None:
    items = sum(ln.unit_refund_minor * ln.quantity for ln in lines if ln.condition != "missing")
    shop_fault = any(ln.reason in SHOP_FAULT_REASONS for ln in lines)
    r.customer_pays_shipping = not shop_fault
    r.return_shipping_fee_minor = 0 if shop_fault else policy.return_shipping_fee_minor
    # The shop's mistake on the whole order: the original delivery charge comes back too.
    whole = all(v == 0 for v in returnable_quantities(db, o).values())
    delivery_back = o.delivery_fee_minor if shop_fault and whole else 0
    due = items + delivery_back - r.return_shipping_fee_minor if r.resolution == "refund" else 0
    r.refund_due_minor = max(0, due)


def create(
    db: Session,
    ctx: TenantContext,
    order_id: uuid.UUID,
    lines: list[LineIn],
    resolution: str,
    idempotency_key: str,
    *,
    note: str | None = None,
    source: str = "seller",
) -> ReturnRequest:
    existing = db.scalar(select(ReturnRequest).where(ReturnRequest.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    if not lines:
        raise ValidationFailed("Pick at least one item", code="return_empty")
    if any(li.reason not in RETURN_REASONS for li in lines):
        raise ValidationFailed(code="return_reason_invalid")
    o = orders.get_order(db, ctx, order_id, lock=True)  # serialises returns for this order
    policy = get_policy(db, ctx.merchant_id)
    eligible, hard_ok, checks = check_eligibility(db, o, lines, resolution, policy)
    if not hard_ok:
        raise Conflict(
            "This order can't be returned like this",
            code="return_not_eligible",
            details={"checks": [c for c in checks if not c["ok"]]},
        )
    count = (
        db.scalar(select(func.count()).select_from(ReturnRequest).where(ReturnRequest.order_id == o.id)) or 0
    )
    r = ReturnRequest(
        id=uuid7(),
        merchant_id=ctx.merchant_id,
        number=f"R-{o.number}-{count + 1}",
        order_id=o.id,
        customer_id=o.customer_id,
        resolution=resolution,
        source=source,
        idempotency_key=idempotency_key,
        eligibility={"checks": checks, "policy_window_days": policy.window_days},
        eligible=eligible,
        currency=o.currency,
        note=note,
        created_by_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
    )
    db.add(r)
    db.flush()
    order_lines = {ln.id: ln for ln in db.scalars(select(OrderLine).where(OrderLine.order_id == o.id))}
    rows = []
    for li in lines:
        ln = order_lines[li.order_line_id]
        row = ReturnLine(
            merchant_id=ctx.merchant_id,
            return_id=r.id,
            order_line_id=ln.id,
            variant_id=ln.variant_id,
            quantity=li.quantity,
            unit_refund_minor=_unit_refund(o, ln),
            reason=li.reason,
            reason_note=(li.reason_note or "")[:500] or None,
            evidence_asset_ids=li.evidence_asset_ids,
            exchange_variant_id=li.exchange_variant_id if resolution == "exchange" else None,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    _compute_due(db, o, r, rows, policy)
    r.signals = abuse_signals(db, o, r.refund_due_minor, r.id)
    _order_event(db, r, ctx.actor, "return_requested", resolution=resolution)
    audit.record(
        db,
        action="returns.requested",
        resource_type="return",
        resource_id=r.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"order_number": o.number, "eligible": eligible, "signals": [s["code"] for s in r.signals]},
    )
    _publish(db, r, "none")
    if policy.auto_approve:
        from app.domains.automation import policy as decision_policy

        rec = decision_policy.decide(
            db,
            ctx.merchant_id,
            decision_policy.Proposal(
                action="approve_return",
                risk_class="R2",
                source="returns",
                confidence=1.0 if eligible and not r.signals else 0.4,
                impact_minor=r.refund_due_minor,
                currency=r.currency,
                threshold_key="return_approve_minor",
                enabled=True,  # the returns policy's auto-approve is the merchant's opt-in
                inputs={
                    "return_id": str(r.id),
                    "eligible": eligible,
                    "signals": [x["code"] for x in r.signals],
                },
            ),
        )
        if rec.decision == "AUTO_EXECUTE":
            auto = TenantContext(
                merchant_id=ctx.merchant_id, actor=Actor(type="automation", display="Return policy")
            )
            _approve(db, auto, r, None, by="automation")
            decision_policy.resolve(db, rec, "executed")
    return r


# ----------------------------------------------------------------------------- decide
def _approve(
    db: Session, ctx: TenantContext, r: ReturnRequest, override_reason: str | None, *, by: str
) -> None:
    before = r.status
    if r.resolution == "exchange":
        for ln in _lines(db, r):
            if ln.exchange_variant_id is None:
                continue
            try:
                inventory.reserve(
                    db,
                    r.merchant_id,
                    ctx.actor,
                    ln.exchange_variant_id,
                    ln.quantity,
                    reference_type="return",
                    reference_id=str(r.id),
                )
            except inventory.OutOfStock as e:
                raise Conflict(
                    "The replacement is out of stock", code="exchange_out_of_stock", details=e.details
                ) from e
    r.status, r.decided_at, r.decided_by = "approved", utcnow(), by
    r.decided_by_user_id = ctx.actor.id if ctx.actor.type == "user" else None
    r.override_reason = override_reason
    log_action(
        db,
        r.merchant_id,
        "returns",
        "approve_return",
        ctx.actor,
        key=f"ret:{r.id}:decision",
        resource_type="return",
        resource_id=r.id,
    )
    _order_event(db, r, ctx.actor, "return_approved", override=bool(override_reason))
    audit.record(
        db,
        action="returns.approved",
        resource_type="return",
        resource_id=r.id,
        actor=ctx.actor,
        merchant_id=r.merchant_id,
        meta=ctx.meta,
        metadata={"override_reason": override_reason, "by": by},
    )
    _publish(db, r, before)


def approve(
    db: Session, ctx: TenantContext, return_id: uuid.UUID, *, override_reason: str | None
) -> ReturnRequest:
    r = get_return(db, ctx, return_id, lock=True)
    if r.status == "approved":
        return r
    if r.status != "requested":
        raise Conflict("Only a new request can be approved", code="return_not_pending")
    if not r.eligible and not (override_reason and len(override_reason.strip()) >= 3):
        raise ValidationFailed(
            "This return is outside your policy. Give a reason to approve it anyway.",
            code="override_reason_required",
            details={"checks": [c for c in r.eligibility.get("checks", []) if not c["ok"]]},
        )
    _approve(db, ctx, r, override_reason.strip() if override_reason and not r.eligible else None, by="seller")
    return r


def reject(db: Session, ctx: TenantContext, return_id: uuid.UUID, reason: str) -> ReturnRequest:
    r = get_return(db, ctx, return_id, lock=True)
    if r.status != "requested":
        raise Conflict("Only a new request can be rejected", code="return_not_pending")
    before = r.status
    r.status, r.rejection_reason, r.decided_at, r.decided_by = "rejected", reason[:300], utcnow(), "seller"
    r.decided_by_user_id = ctx.actor.id
    log_action(
        db,
        r.merchant_id,
        "returns",
        "reject_return",
        ctx.actor,
        key=f"ret:{r.id}:decision",
        resource_type="return",
        resource_id=r.id,
    )
    _order_event(db, r, ctx.actor, "return_rejected", reason=reason[:300])
    audit.record(
        db,
        action="returns.rejected",
        resource_type="return",
        resource_id=r.id,
        actor=ctx.actor,
        merchant_id=r.merchant_id,
        meta=ctx.meta,
        metadata={"reason": reason[:300]},
    )
    _publish(db, r, before)
    return r


def _release_exchange(db: Session, r: ReturnRequest, actor: Actor) -> None:
    for res in inventory.reservations_for(db, r.merchant_id, "return", str(r.id)):
        if res.status == "active":
            inventory.release(db, actor, res)


def cancel(db: Session, ctx: TenantContext, return_id: uuid.UUID, reason: str | None) -> ReturnRequest:
    from app.domains.fulfillment import service as fulfillment
    from app.domains.fulfillment.models import Shipment

    r = get_return(db, ctx, return_id, lock=True)
    if r.status == "cancelled":
        return r
    if r.status not in ("requested", "approved"):
        raise Conflict("The item is already on its way back", code="return_not_cancellable")
    s = db.scalar(select(Shipment).where(Shipment.return_id == r.id, Shipment.status != "cancelled"))
    if s is not None:
        fulfillment.cancel(db, ctx, s.id, reason="return_cancelled")
    _release_exchange(db, r, ctx.actor)
    before = r.status
    r.status, r.closed_at = "cancelled", utcnow()
    _order_event(db, r, ctx.actor, "return_cancelled", reason=reason)
    _publish(db, r, before)
    return r


# ----------------------------------------------------------------------------- the item comes back (RET-006)
def book_pickup(
    db: Session,
    ctx: TenantContext,
    return_id: uuid.UUID,
    courier_account_id: uuid.UUID,
    idempotency_key: str,
    **kw: Any,
) -> Any:
    from app.domains.fulfillment import service as fulfillment

    r = get_return(db, ctx, return_id, lock=True)
    if r.status != "approved":
        raise Conflict("Approve the return before booking its pickup", code="return_not_approved")
    s = fulfillment.book_return(db, ctx, r, courier_account_id, idempotency_key, **kw)
    _order_event(
        db, r, ctx.actor, "return_pickup_booked", shipment_id=str(s.id), tracking_number=s.tracking_number
    )
    return s


def mark_received(db: Session, ctx: TenantContext, return_id: uuid.UUID) -> ReturnRequest:
    r = get_return(db, ctx, return_id, lock=True)
    return _received(db, ctx.actor, r)


def _received(db: Session, actor: Actor, r: ReturnRequest) -> ReturnRequest:
    if r.status in ("received", "inspected", "refunded", "exchanged", "closed"):
        return r
    if r.status not in ("approved", "in_transit"):
        raise Conflict("Approve the return first", code="return_not_approved")
    before = r.status
    r.status, r.received_at = "received", utcnow()
    _order_event(db, r, actor, "return_received")
    _publish(db, r, before)
    return r


def on_return_parcel(db: Session, s: Any) -> None:
    """Called by fulfillment when a return pickup moves."""
    r = db.get(ReturnRequest, s.return_id)
    if r is None:
        return
    actor = Actor(type="webhook", display=s.courier_name or s.provider)
    if s.status in ("picked_up", "in_transit", "out_for_delivery") and r.status == "approved":
        before = r.status
        r.status = "in_transit"
        _publish(db, r, before)
    elif s.status == "delivered":
        _received(db, actor, r)


# ----------------------------------------------------------------------------- inspection (RET-007/008)
@dataclass
class InspectIn:
    line_id: uuid.UUID
    condition: str
    restock: int = 0
    note: str | None = None


def inspect(db: Session, ctx: TenantContext, return_id: uuid.UUID, items: list[InspectIn]) -> ReturnRequest:
    r = get_return(db, ctx, return_id, lock=True)
    if r.status != "received":
        raise Conflict("Inspect the item once it has arrived", code="return_not_received")
    lines = {ln.id: ln for ln in _lines(db, r)}
    if {i.line_id for i in items} != set(lines):
        raise ValidationFailed("Inspect every returned item", code="inspection_incomplete")
    for i in items:
        ln = lines[i.line_id]
        if i.restock < 0 or i.restock > ln.quantity or (i.condition != "resellable" and i.restock):
            raise ValidationFailed(
                code="restock_invalid", details={"line_id": str(ln.id), "max": ln.quantity}
            )
        ln.condition, ln.inspection_note = i.condition, (i.note or "")[:500] or None
        if i.restock and ln.variant_id:
            inventory.receive(
                db, ctx, ln.variant_id, i.restock, reason=f"return {r.number}", key=f"return-restock:{ln.id}"
            )
            ln.restocked_quantity = i.restock
    o = db.get(Order, r.order_id)
    assert o is not None
    policy = get_policy(db, r.merchant_id)
    before = r.status
    r.status, r.inspected_at = "inspected", utcnow()
    db.flush()
    _compute_due(db, o, r, list(lines.values()), policy)
    _order_event(
        db, r, ctx.actor, "return_inspected", conditions={str(k): v.condition for k, v in lines.items()}
    )
    _publish(db, r, before)
    if r.resolution == "exchange":
        _create_exchange(db, ctx, r, o, list(lines.values()))
    elif r.refund_due_minor == 0:
        r.status, r.closed_at = "closed", utcnow()
        _publish(db, r, "inspected")
        _maybe_order_returned(db, ctx, o)
    else:
        _maybe_auto_refund(db, r, o, policy)
    return r


def _create_exchange(
    db: Session, ctx: TenantContext, r: ReturnRequest, o: Order, lines: list[ReturnLine]
) -> None:
    """The replacement ships at no charge; its stock was reserved at approval (now moved to the order)."""
    _release_exchange(db, r, ctx.actor)
    order_lines = {ln.id: ln for ln in db.scalars(select(OrderLine).where(OrderLine.order_id == o.id))}
    swap = [ln for ln in lines if ln.exchange_variant_id and ln.condition != "missing"]
    if not swap:
        r.status, r.closed_at = "closed", utcnow()
        return
    subtotal = sum(order_lines[ln.order_line_id].unit_price_minor * ln.quantity for ln in swap)
    data = orders.OrderInput(
        lines=[
            orders.LineInput(
                ln.exchange_variant_id,
                ln.quantity,
                unit_price_minor=order_lines[ln.order_line_id].unit_price_minor,
            )
            for ln in swap
            if ln.exchange_variant_id
        ],
        customer_id=o.customer_id,
        address=customers.AddressInput(
            recipient_name=o.ship_name or "",
            phone=o.ship_phone or "",
            province=o.ship_province or "",
            district=o.ship_district or "",
            municipality=o.ship_municipality or "",
            ward=o.ship_ward or 0,
            area=o.ship_area,
            landmark=o.ship_landmark,
        ),
        save_address=False,
        payment_method="cod",  # total is zero: nothing to collect
        discount_minor=subtotal,
        delivery_fee_minor=0,
        notes=f"Exchange for return {r.number} (order #{o.number})",
        source="seller",
        source_key=f"exchange:{r.id}",
        confirm=True,
    )
    try:
        with db.begin_nested():
            ex = orders.create_order(db, ctx, data)
    except AppError as e:
        raise Conflict(
            "Couldn't create the replacement order (check the delivery address and stock)",
            code="exchange_order_failed",
            details={"error": e.code},
        ) from e
    r.exchange_order_id, r.status, r.closed_at = ex.id, "exchanged", utcnow()
    _order_event(
        db, r, ctx.actor, "exchange_created", exchange_order_id=str(ex.id), exchange_number=ex.number
    )
    _publish(db, r, "inspected")
    _maybe_order_returned(db, ctx, o)


def _maybe_order_returned(db: Session, ctx: TenantContext, o: Order) -> None:
    """Everything sold has come back: the order is returned."""
    db.flush()
    if o.status in RETURNABLE_ORDER_STATUSES and all(v == 0 for v in returnable_quantities(db, o).values()):
        open_returns = db.scalar(
            select(func.count())
            .select_from(ReturnRequest)
            .where(ReturnRequest.order_id == o.id, ReturnRequest.status.in_(OPEN_RETURN_STATUSES))
        )
        if not open_returns:
            try:
                with db.begin_nested():
                    orders.transition(db, ctx, o.id, "returned")
            except AppError as e:
                log.warning("order_returned_transition_failed", order_id=str(o.id), code=e.code)


# ----------------------------------------------------------------------------- refunds (PAY-007, RET-009/010)
def _original_payment(db: Session, o: Order) -> Payment | None:
    return db.scalar(
        select(Payment)
        .where(Payment.order_id == o.id, Payment.kind == "online", Payment.status.in_(("paid", "refunded")))
        .order_by(Payment.id.desc())
    )


def _refundable_by_provider(p: Payment | None) -> bool:
    if p is None:
        return False
    try:
        return registry.payment(p.provider).supports(PaymentCapability.REFUND)
    except registry.AdapterNotAvailable:
        return False


def request_refund(
    db: Session,
    ctx: TenantContext,
    order_id: uuid.UUID,
    amount_minor: int,
    method: str,
    idempotency_key: str,
    *,
    return_id: uuid.UUID | None = None,
    reference: str | None = None,
    reason: str | None = None,
    automated: bool = False,
) -> Refund:
    existing = db.scalar(select(Refund).where(Refund.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    o = orders.get_order(db, ctx, order_id, lock=True)  # serialises refunds per order: no over-refund
    r = get_return(db, ctx, return_id, lock=True) if return_id else None
    if r is not None and r.order_id != o.id:
        raise NotFound(code="return_not_found")
    if r is not None and r.status != "inspected":
        raise Conflict("Refund once the returned item has been inspected", code="return_not_inspected")
    remaining = paid_minor(db, o) - refunded_minor(db, o.id)
    if amount_minor <= 0 or amount_minor > remaining:
        raise ValidationFailed(
            "That's more than the customer paid (minus earlier refunds)",
            code="refund_exceeds_paid",
            details={"refundable_minor": max(0, remaining)},
        )
    pay = _original_payment(db, o) if method == "original_payment" else None
    if method == "original_payment" and pay is None:
        raise ValidationFailed(
            "This order wasn't paid online. Record how you sent the money instead.",
            code="refund_method_unavailable",
        )
    if pay is not None and not _refundable_by_provider(pay):
        raise ValidationFailed(
            "Refund this payment from your gateway's own dashboard, then record the refund here.",
            code="refund_via_gateway_dashboard",
        )
    policy = get_policy(db, ctx.merchant_id)
    needs_approval = amount_minor > policy.auto_refund_max_minor and not ctx.has("refunds.approve")
    if automated:
        needs_approval = amount_minor > policy.auto_refund_max_minor
    if not automated and not ctx.has("refunds.create"):
        raise PermissionDenied(code="permission_denied", details={"permission": "refunds.create"})
    ref = Refund(
        id=uuid7(),
        merchant_id=ctx.merchant_id,
        order_id=o.id,
        return_id=r.id if r else None,
        payment_id=pay.id if pay else None,
        amount_minor=amount_minor,
        currency=o.currency,
        method=method,
        provider=pay.provider if pay else None,
        reference=(reference or "").strip()[:120] or None,
        status="pending_approval" if needs_approval else "processing",
        reason=(reason or "")[:300] or None,
        idempotency_key=idempotency_key,
        requested_by_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
    )
    db.add(ref)
    db.flush()
    orders._event(
        db, o, ctx.actor, "refund_requested", refund_id=str(ref.id), amount_minor=amount_minor, method=method
    )
    audit.record(
        db,
        action="refunds.requested",
        resource_type="refund",
        resource_id=ref.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={
            "order_number": o.number,
            "amount_minor": amount_minor,
            "method": method,
            "needs_approval": needs_approval,
        },
    )
    if not needs_approval:
        if not automated:
            ref.approved_by_user_id, ref.approved_at = ctx.actor.id, utcnow()
        _execute(db, ctx, ref, o)
    return ref


def _execute(db: Session, ctx: TenantContext, ref: Refund, o: Order) -> None:
    if ref.method == "original_payment":
        pay = db.get(Payment, ref.payment_id) if ref.payment_id else None
        assert pay is not None and pay.provider_payment_id
        try:
            adapter = registry.payment(pay.provider)
            if not adapter.supports(PaymentCapability.REFUND):
                raise IntegrationError("capability_not_supported", pay.provider)
            ref.provider_refund_id = adapter.refund(
                pay.provider_payment_id,
                Money(ref.amount_minor, ref.currency),
                idempotency_key=f"refund:{ref.id}",
            )
        except (IntegrationError, registry.AdapterNotAvailable) as e:
            ref.status, ref.failure_code = "failed", getattr(e, "code", "provider_unavailable")
            orders._event(db, o, ctx.actor, "refund_failed", refund_id=str(ref.id), error=ref.failure_code)
            return
    ref.status, ref.completed_at, ref.failure_code = "succeeded", utcnow(), None
    log_action(
        db,
        ref.merchant_id,
        "refunds",
        "issue_refund",
        ctx.actor,
        key=f"refund:{ref.id}",
        resource_type="refund",
        resource_id=ref.id,
        human_intervened=ref.approved_by_user_id is not None and ctx.actor.type != "user",
    )
    db.flush()  # the sums below must include this refund (sessions don't autoflush)
    orders._event(
        db,
        o,
        ctx.actor,
        "refund_succeeded",
        refund_id=str(ref.id),
        amount_minor=ref.amount_minor,
        method=ref.method,
        provider=ref.provider,
        reference=ref.reference,
    )
    if refunded_minor(db, o.id) >= paid_minor(db, o) > 0:
        o.payment_status = "refunded"
    if ref.return_id:
        r = db.get(ReturnRequest, ref.return_id)
        if r is not None and r.status == "inspected":
            done = int(
                db.scalar(
                    select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(
                        Refund.return_id == r.id, Refund.status == "succeeded"
                    )
                )
                or 0
            )
            if done >= r.refund_due_minor:
                before = r.status
                r.status, r.closed_at = "refunded", utcnow()
                _publish(db, r, before)
                _maybe_order_returned(db, ctx, o)


def approve_refund(db: Session, ctx: TenantContext, refund_id: uuid.UUID) -> Refund:
    ref = _get_refund(db, ctx, refund_id)
    if ref.status != "pending_approval":
        return ref
    o = orders.get_order(db, ctx, ref.order_id, lock=True)
    if ref.amount_minor > paid_minor(db, o) - refunded_minor(db, o.id) + ref.amount_minor:
        raise ValidationFailed(code="refund_exceeds_paid")
    ref.status, ref.approved_by_user_id, ref.approved_at = "processing", ctx.actor.id, utcnow()
    audit.record(
        db,
        action="refunds.approved",
        resource_type="refund",
        resource_id=ref.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"amount_minor": ref.amount_minor},
    )
    _execute(db, ctx, ref, o)
    return ref


def reject_refund(db: Session, ctx: TenantContext, refund_id: uuid.UUID, reason: str) -> Refund:
    ref = _get_refund(db, ctx, refund_id)
    if ref.status != "pending_approval":
        raise Conflict("Only a refund waiting for approval can be rejected", code="refund_not_pending")
    ref.status, ref.failure_code = "rejected", "rejected_by_approver"
    ref.reason = f"{ref.reason or ''} | rejected: {reason}"[:300]
    audit.record(
        db,
        action="refunds.rejected",
        resource_type="refund",
        resource_id=ref.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"reason": reason[:300]},
    )
    return ref


def retry_refund(db: Session, ctx: TenantContext, refund_id: uuid.UUID) -> Refund:
    ref = _get_refund(db, ctx, refund_id)
    if ref.status != "failed":
        return ref
    o = orders.get_order(db, ctx, ref.order_id, lock=True)
    ref.status = "processing"
    _execute(db, ctx, ref, o)  # same idempotency key at the provider: never refunds twice
    return ref


def _get_refund(db: Session, ctx: TenantContext, refund_id: uuid.UUID) -> Refund:
    ref = db.scalar(select(Refund).where(Refund.id == refund_id).with_for_update())
    if ref is None or ref.merchant_id != ctx.merchant_id:
        raise NotFound(code="refund_not_found")
    return ref


def _maybe_auto_refund(db: Session, r: ReturnRequest, o: Order, policy: ReturnPolicy) -> None:
    """RET-010: only to the original online payment, within the threshold, and with no abuse signal."""
    if (
        r.refund_due_minor <= 0
        or r.refund_due_minor > policy.auto_refund_max_minor
        or r.signals
        or not _refundable_by_provider(_original_payment(db, o))
    ):
        return
    from app.domains.automation import policy as decision_policy

    rec = decision_policy.decide(
        db,
        r.merchant_id,
        decision_policy.Proposal(
            action="issue_refund",
            risk_class="R2",
            source="returns",
            impact_minor=r.refund_due_minor,
            currency=r.currency,
            enabled=True,  # within the returns policy's own auto-refund limit (checked above)
            inputs={"return_id": str(r.id), "order_id": str(o.id)},
        ),
    )
    if rec.decision != "AUTO_EXECUTE":
        return
    ctx = TenantContext(merchant_id=r.merchant_id, actor=Actor(type="automation", display="Return policy"))
    try:
        with db.begin_nested():
            request_refund(
                db,
                ctx,
                o.id,
                min(r.refund_due_minor, paid_minor(db, o) - refunded_minor(db, o.id)),
                "original_payment",
                f"auto-refund:{r.id}",
                return_id=r.id,
                reason="auto: within policy",
                automated=True,
            )
        decision_policy.resolve(db, rec, "executed")
    except AppError as e:
        log.warning("auto_refund_skipped", return_id=str(r.id), code=e.code)


# ----------------------------------------------------------------------------- customer messages
@handler("returns.status_changed", name="returns.notify_customer")
def _notify(db: Session, ev: OutboxEvent) -> None:
    from app.domains.fulfillment.couriers import get_settings_row
    from app.domains.fulfillment.service import _conversation_for
    from app.domains.inbox import service as inbox
    from app.domains.returns.notify import message

    r = db.scalar(
        select(ReturnRequest)
        .where(ReturnRequest.id == uuid.UUID(ev.payload["return_id"]))
        .execution_options(skip_tenant_filter=True)
    )
    if r is None or r.status != ev.payload["status"]:
        return
    bind_tenant(db, r.merchant_id)
    o = db.get(Order, r.order_id)
    if o is None or not get_settings_row(db, r.merchant_id).notify_customers:
        return
    conv = _conversation_for(db, o)
    if conv is None:
        return
    text = message(r, o, conv.locale)
    if text:
        inbox.queue_reply(
            db,
            conv,
            text,
            author="system",
            intent="return_update",
            grounding={"return": str(r.id), "status": r.status},
        )


# ----------------------------------------------------------------------------- views
def return_view(db: Session, r: ReturnRequest, *, detail: bool = False) -> dict[str, Any]:
    o = db.get(Order, r.order_id)
    out: dict[str, Any] = {
        "id": r.id,
        "number": r.number,
        "order_id": r.order_id,
        "order_number": o.number if o else None,
        "customer_name": o.ship_name if o else None,
        "status": r.status,
        "resolution": r.resolution,
        "source": r.source,
        "eligible": r.eligible,
        "signals": r.signals,
        "refund_due": {"amount_minor": r.refund_due_minor, "currency": r.currency},
        "return_shipping_fee_minor": r.return_shipping_fee_minor,
        "customer_pays_shipping": r.customer_pays_shipping,
        "created_at": r.created_at,
        "decided_at": r.decided_at,
        "received_at": r.received_at,
        "closed_at": r.closed_at,
        "exchange_order_id": r.exchange_order_id,
    }
    if detail:
        from app.domains.fulfillment import service as fulfillment
        from app.domains.fulfillment.models import Shipment

        order_lines = {
            ln.id: ln for ln in db.scalars(select(OrderLine).where(OrderLine.order_id == r.order_id))
        }
        variants: dict[uuid.UUID, Variant] = {}
        out["lines"] = []
        for ln in _lines(db, r):
            ol = order_lines.get(ln.order_line_id)
            ex = None
            if ln.exchange_variant_id:
                v = variants.get(ln.exchange_variant_id) or db.get(Variant, ln.exchange_variant_id)
                ex = {"variant_id": ln.exchange_variant_id, "title": v.title if v else None}
            out["lines"].append(
                {
                    "id": ln.id,
                    "order_line_id": ln.order_line_id,
                    "title": ol.title if ol else None,
                    "variant_title": ol.variant_title if ol else None,
                    "sku": ol.sku if ol else None,
                    "quantity": ln.quantity,
                    "unit_refund_minor": ln.unit_refund_minor,
                    "reason": ln.reason,
                    "reason_note": ln.reason_note,
                    "evidence_asset_ids": ln.evidence_asset_ids,
                    "exchange": ex,
                    "condition": ln.condition,
                    "restocked_quantity": ln.restocked_quantity,
                    "inspection_note": ln.inspection_note,
                }
            )
        out["eligibility"] = r.eligibility
        out["override_reason"] = r.override_reason
        out["rejection_reason"] = r.rejection_reason
        out["note"] = r.note
        out["refunds"] = [
            refund_view(x)
            for x in db.scalars(select(Refund).where(Refund.return_id == r.id).order_by(Refund.id))
        ]
        s = db.scalar(select(Shipment).where(Shipment.return_id == r.id).order_by(Shipment.id.desc()))
        out["pickup"] = fulfillment.shipment_view(db, s, detail=True, order=o) if s else None
        out["refundable_minor"] = max(0, paid_minor(db, o) - refunded_minor(db, o.id)) if o else 0
        out["actions"] = _actions(db, r, o)
    return out


def _actions(db: Session, r: ReturnRequest, o: Order | None) -> list[str]:
    acts = []
    if r.status == "requested":
        acts += ["approve", "reject", "cancel"]
    if r.status == "approved":
        acts += ["book_pickup", "mark_received", "cancel"]
    if r.status == "in_transit":
        acts.append("mark_received")
    if r.status == "received":
        acts.append("inspect")
    if r.status == "inspected" and r.resolution == "refund":
        acts.append("refund")
    return acts


def refund_view(x: Refund) -> dict[str, Any]:
    return {
        "id": x.id,
        "order_id": x.order_id,
        "return_id": x.return_id,
        "amount": {"amount_minor": x.amount_minor, "currency": x.currency},
        "method": x.method,
        "provider": x.provider,
        "provider_refund_id": x.provider_refund_id,
        "reference": x.reference,
        "status": x.status,
        "reason": x.reason,
        "failure_code": x.failure_code,
        "created_at": x.created_at,
        "approved_at": x.approved_at,
        "completed_at": x.completed_at,
    }
