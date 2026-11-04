"""Order service (ORD-001…012).

* One ``Order`` for every source (chat, seller, channel, API); lines snapshot price/SKU/title.
* Status changes only through ``transition`` (the state machine below); each writes a timeline event.
* Stock: reserved when the order is confirmed, released on cancel, committed (off the shelf) when
  shipped. A short channel import is still imported (the sale happened) and flagged for review.
* Idempotency: ``source_key`` for chat/API/seller retries, (connection, external id) for imports.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, UsageLimitReached, ValidationFailed
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements
from app.domains.catalog.models import Product, Variant
from app.domains.customers import service as customers
from app.domains.customers.models import Customer
from app.domains.integrations.base import ExternalOrder
from app.domains.inventory import service as inventory
from app.domains.merchants.models import Merchant
from app.domains.orders.models import Order, OrderEvent, OrderLine
from app.domains.platform import outbox

log = structlog.get_logger(__name__)

# from-status → allowed next statuses (spec 12). Anything else is refused.
TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"pending_confirmation", "confirmed", "cancelled"}),
    "pending_confirmation": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"payment_pending", "cod_pending", "cancelled"}),
    "payment_pending": frozenset({"ready_to_ship", "cancelled"}),
    "cod_pending": frozenset({"ready_to_ship", "cancelled"}),
    "ready_to_ship": frozenset({"shipped", "cancelled"}),
    "shipped": frozenset({"delivered", "delivery_failed"}),
    "delivery_failed": frozenset({"shipped", "returned"}),
    "delivered": frozenset({"completed", "returned"}),
    "completed": frozenset({"returned"}),
    "cancelled": frozenset(),
    "returned": frozenset(),
}
OPEN_FOR_EDIT = frozenset(
    {"draft", "pending_confirmation", "confirmed", "payment_pending", "cod_pending", "ready_to_ship"}
)
RESERVED_STATUSES = frozenset({"confirmed", "payment_pending", "cod_pending", "ready_to_ship"})


def actor_source(actor: Actor) -> str:
    return {"user": "seller", "ai": "ai", "automation": "automation", "webhook": "channel"}.get(
        actor.type, actor.type
    )


# ----------------------------------------------------------------------------- inputs
@dataclass
class LineInput:
    variant_id: uuid.UUID
    quantity: int
    unit_price_minor: int | None = None  # None = catalog price now
    line_discount_minor: int = 0


@dataclass
class OrderInput:
    lines: list[LineInput]
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    address: customers.AddressInput | None = None
    address_id: uuid.UUID | None = None
    save_address: bool = True
    payment_method: str = "cod"
    delivery_fee_minor: int = 0
    discount_minor: int = 0
    tax_minor: int = 0
    notes: str | None = None
    source: str = "seller"
    source_key: str | None = None
    conversation_id: uuid.UUID | None = None
    confirm: bool = True


# ----------------------------------------------------------------------------- helpers
def _next_number(db: Session, merchant_id: uuid.UUID) -> int:
    key = int.from_bytes(
        hashlib.sha256(f"order_number:{merchant_id}".encode()).digest()[:8], "big", signed=True
    )
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
    last = db.scalar(select(func.max(Order.number)).where(Order.merchant_id == merchant_id))
    return (last or 1000) + 1


def _event(
    db: Session,
    order: Order,
    actor: Actor,
    kind: str,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
    provider: str | None = None,
    **data: Any,
) -> OrderEvent:
    ev = OrderEvent(
        merchant_id=order.merchant_id,
        order_id=order.id,
        kind=kind,
        from_status=from_status,
        to_status=to_status,
        actor_type=actor.type,
        actor_id=actor.id,
        actor_display=actor.display,
        automated=actor.type in ("system", "automation", "ai", "webhook"),
        source=actor_source(actor),
        provider=provider,
        data=data,
    )
    db.add(ev)
    return ev


def _recompute(db: Session, order: Order) -> None:
    lines = list(db.scalars(select(OrderLine).where(OrderLine.order_id == order.id)))
    order.subtotal_minor = sum(ln.total_minor for ln in lines)
    order.discount_minor = min(order.discount_minor, order.subtotal_minor)
    order.total_minor = (
        order.subtotal_minor - order.discount_minor + order.delivery_fee_minor + order.tax_minor
    )


def _lines(db: Session, order: Order) -> list[OrderLine]:
    return list(
        db.scalars(select(OrderLine).where(OrderLine.order_id == order.id).order_by(OrderLine.position))
    )


def get_order(db: Session, ctx: TenantContext, order_id: uuid.UUID, *, lock: bool = False) -> Order:
    stmt = select(Order).where(Order.id == order_id)
    if lock:
        stmt = stmt.with_for_update()
    o = db.scalar(stmt)
    if o is None or o.merchant_id != ctx.merchant_id:
        raise NotFound(code="order_not_found")
    return o


def _publish(db: Session, order: Order, event_type: str, **extra: Any) -> None:
    outbox.publish(
        db,
        event_type=event_type,
        aggregate_type="order",
        aggregate_id=order.id,
        merchant_id=order.merchant_id,
        payload={"order_id": str(order.id), "status": order.status, **extra},
    )


# ----------------------------------------------------------------------------- stock
def _reserve_all(db: Session, order: Order, actor: Actor) -> None:
    for ln in _lines(db, order):
        if ln.variant_id is None or ln.active_quantity <= 0:
            continue
        inventory.reserve(
            db,
            order.merchant_id,
            actor,
            ln.variant_id,
            ln.active_quantity,
            reference_type="order",
            reference_id=str(order.id),
        )


def _release_all(db: Session, order: Order, actor: Actor) -> None:
    for r in inventory.reservations_for(db, order.merchant_id, "order", str(order.id)):
        inventory.release(db, actor, r)


def _commit_all(db: Session, order: Order, actor: Actor) -> None:
    for r in inventory.reservations_for(db, order.merchant_id, "order", str(order.id)):
        inventory.commit(db, actor, r)


# ----------------------------------------------------------------------------- create
def _resolve_customer(db: Session, ctx: TenantContext, data: OrderInput) -> Customer:
    if data.customer_id:
        return customers.get_customer(db, ctx, data.customer_id)
    phone = data.customer_phone or (data.address.phone if data.address else None)
    existing = customers.by_phone(
        db, ctx.merchant_id, customers.nepal.normalize_phone(phone) if phone else None
    )
    if existing is not None:
        return existing
    name = data.customer_name or (data.address.recipient_name if data.address else None)
    if not name:
        raise ValidationFailed(
            details={"fields": [{"loc": ["body", "customer_name"], "type": "required", "msg": "required"}]}
        )
    return customers.create_customer(db, ctx, display_name=name, phone=phone)


def _apply_address(
    db: Session, ctx: TenantContext, order: Order, customer: Customer, data: OrderInput
) -> None:
    from app.domains.customers.models import CustomerAddress

    if data.address_id:
        a = db.get(CustomerAddress, data.address_id)
        if a is None or a.customer_id != customer.id or a.status != "active":
            raise NotFound(code="address_not_found")
        clean: dict[str, Any] = {
            k: getattr(a, k)
            for k in (
                "recipient_name",
                "phone",
                "province",
                "district",
                "municipality",
                "ward",
                "area",
                "landmark",
            )
        }
        completeness = a.completeness
    elif data.address:
        clean, completeness = customers.validate_address(data.address)
        if data.save_address:
            customers.add_address(db, ctx, customer.id, data.address)
    else:
        raise ValidationFailed(
            details={"fields": [{"loc": ["body", "address"], "type": "required", "msg": "required"}]}
        )
    order.ship_name, order.ship_phone = clean["recipient_name"], clean["phone"]
    order.ship_province, order.ship_district = clean["province"], clean["district"]
    order.ship_municipality, order.ship_ward = clean["municipality"], clean["ward"]
    order.ship_area, order.ship_landmark = clean["area"], clean["landmark"]
    order.address_completeness = completeness


def create_order(db: Session, ctx: TenantContext, data: OrderInput) -> Order:
    if data.source_key:
        existing = db.scalar(select(Order).where(Order.source_key == data.source_key))
        if existing is not None:
            return existing  # retried chat confirmation / API call
    if not data.lines:
        raise ValidationFailed("An order needs at least one item", code="order_empty")
    if data.payment_method not in ("cod", "prepaid"):
        raise ValidationFailed(code="payment_method_invalid")
    merged: dict[uuid.UUID, LineInput] = {}
    for ln in data.lines:
        if ln.quantity <= 0:
            raise ValidationFailed(code="quantity_invalid")
        if ln.variant_id in merged:
            merged[ln.variant_id].quantity += ln.quantity
        else:
            merged[ln.variant_id] = LineInput(
                ln.variant_id, ln.quantity, ln.unit_price_minor, ln.line_discount_minor
            )
    merchant = db.get(Merchant, ctx.merchant_id)
    assert merchant is not None
    customer = _resolve_customer(db, ctx, data)
    order = Order(
        merchant_id=ctx.merchant_id,
        number=_next_number(db, ctx.merchant_id),
        status="draft",
        source=data.source,
        source_key=data.source_key,
        conversation_id=data.conversation_id,
        customer_id=customer.id,
        currency=merchant.currency,
        payment_method=data.payment_method,
        delivery_fee_minor=data.delivery_fee_minor,
        discount_minor=data.discount_minor,
        tax_minor=data.tax_minor,
        notes=data.notes,
    )
    _apply_address(db, ctx, order, customer, data)
    db.add(order)
    db.flush()
    for pos, ln in enumerate(merged.values()):
        v = db.get(Variant, ln.variant_id)
        p = db.get(Product, v.product_id) if v else None
        if v is None or p is None or v.merchant_id != ctx.merchant_id:
            raise NotFound(code="variant_not_found", details={"variant_id": str(ln.variant_id)})
        if v.status != "active" or p.status == "archived":
            raise Conflict(
                f"{p.title} ({v.title}) isn't for sale",
                code="variant_not_sellable",
                details={"variant_id": str(v.id)},
            )
        db.add(
            OrderLine(
                merchant_id=ctx.merchant_id,
                order_id=order.id,
                position=pos,
                product_id=p.id,
                variant_id=v.id,
                sku=v.sku,
                title=p.title,
                variant_title=None if v.title == "Default" else v.title,
                unit_price_minor=v.price_minor if ln.unit_price_minor is None else ln.unit_price_minor,
                quantity=ln.quantity,
                line_discount_minor=ln.line_discount_minor,
            )
        )
    db.flush()
    _recompute(db, order)
    entitlements.record(
        db,
        ctx.merchant_id,
        "orders",
        1,
        f"order:{order.id}",
        reference_type="order",
        reference_id=str(order.id),
    )
    _event(db, order, ctx.actor, "created", to_status="draft", source_kind=data.source)
    audit.record(
        db,
        action="orders.order_created",
        resource_type="order",
        resource_id=order.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"number": order.number, "source": data.source, "total_minor": order.total_minor},
    )
    _publish(db, order, "orders.created", source=data.source)
    if data.confirm:
        transition(db, ctx, order.id, "confirmed")
    return order


# ----------------------------------------------------------------------------- state machine
def transition(
    db: Session,
    ctx: TenantContext,
    order_id: uuid.UUID,
    to: str,
    *,
    reason: str | None = None,
    expected_version: int | None = None,
    provider: str | None = None,
) -> Order:
    o = get_order(db, ctx, order_id, lock=True)
    if expected_version is not None and o.version != expected_version:
        raise Conflict(
            "This order changed. Reload to see the latest.",
            code="version_conflict",
            details={"current_version": o.version},
        )
    if to == o.status:
        return o
    if to not in TRANSITIONS.get(o.status, frozenset()):
        raise Conflict(
            f"An order that is {o.status} can't become {to}",
            code="invalid_transition",
            details={"from": o.status, "to": to, "allowed": sorted(TRANSITIONS.get(o.status, ()))},
        )
    if to == "ready_to_ship" and o.status == "payment_pending" and o.payment_status != "paid":
        raise Conflict("Payment isn't confirmed yet", code="payment_not_confirmed")
    if to == "cancelled" and not reason:
        reason = "cancelled"
    before = o.status
    # Side effects first: if stock can't be reserved the status doesn't change.
    if to == "confirmed":
        _reserve_all(db, o, ctx.actor)
        o.confirmed_at = utcnow()
    elif to == "cancelled":
        _release_all(db, o, ctx.actor)
        o.cancelled_at, o.cancel_reason = utcnow(), reason
    elif to == "shipped" and before == "ready_to_ship":
        _commit_all(db, o, ctx.actor)
    o.status = to
    _event(
        db, o, ctx.actor, "status_changed", from_status=before, to_status=to, provider=provider, reason=reason
    )
    _publish(db, o, "orders.status_changed", from_status=before)
    if to == "confirmed":
        # Payment track follows immediately: COD waits for delivery, prepaid waits for a verified payment.
        nxt = "cod_pending" if o.payment_method == "cod" else "payment_pending"
        o.payment_status = (
            "cod_pending"
            if o.payment_method == "cod"
            else ("paid" if o.payment_status == "paid" else "pending")
        )
        o.status = nxt
        _event(db, o, Actor.system("orders"), "status_changed", from_status="confirmed", to_status=nxt)
    if to == "delivered" and o.payment_method == "cod" and o.payment_status == "cod_pending":
        o.payment_status = "cod_collected"  # cash collected by the courier at the door; settlement is Phase 3
    return o


def cancel_lines(
    db: Session, ctx: TenantContext, order_id: uuid.UUID, items: list[tuple[uuid.UUID, int]], reason: str
) -> Order:
    """Partial cancel (ORD-010): fewer units of some lines; releases the matching stock."""
    o = get_order(db, ctx, order_id, lock=True)
    if o.status not in OPEN_FOR_EDIT:
        raise Conflict("Items can't be cancelled after the order has shipped", code="order_not_editable")
    lines = {ln.id: ln for ln in _lines(db, o)}
    changed = []
    for line_id, qty in items:
        ln = lines.get(line_id)
        if ln is None:
            raise NotFound(code="order_line_not_found")
        if qty <= 0 or qty > ln.active_quantity:
            raise ValidationFailed(
                code="quantity_invalid", details={"line_id": str(line_id), "max": ln.active_quantity}
            )
        ln.cancelled_quantity += qty
        changed.append({"line_id": str(line_id), "quantity": qty, "sku": ln.sku})
    db.flush()
    if all(ln.active_quantity == 0 for ln in lines.values()):
        _recompute(db, o)
        return transition(db, ctx, o.id, "cancelled", reason=reason)
    if o.status in RESERVED_STATUSES:
        for r in inventory.reservations_for(db, o.merchant_id, "order", str(o.id)):
            line = next((ln for ln in lines.values() if ln.variant_id == r.variant_id), None)
            if line is None or r.status != "active" or line.active_quantity == r.quantity:
                continue
            inventory.release(db, ctx.actor, r)
            if line.active_quantity > 0:
                inventory.reserve(
                    db,
                    o.merchant_id,
                    ctx.actor,
                    r.variant_id,
                    line.active_quantity,
                    reference_type="order",
                    reference_id=str(o.id),
                )
    _recompute(db, o)
    _event(db, o, ctx.actor, "lines_cancelled", reason=reason, items=changed)
    _publish(db, o, "orders.status_changed", from_status=o.status)
    return o


def add_note(db: Session, ctx: TenantContext, order_id: uuid.UUID, note: str) -> OrderEvent:
    o = get_order(db, ctx, order_id)
    return _event(db, o, ctx.actor, "note", note=note)


# ----------------------------------------------------------------------------- channel imports (ORD-005)
# Channel status → how far along our machine the order is. Imports never move an order backwards.
_PROGRESS = [
    "pending_confirmation",
    "confirmed",
    "cod_pending",
    "payment_pending",
    "ready_to_ship",
    "shipped",
    "delivered",
    "completed",
]


def import_external(
    db: Session, merchant_id: uuid.UUID, connection_id: uuid.UUID, provider: str, ext: ExternalOrder
) -> tuple[Order, bool]:
    """Create or update the Nivaro order for a channel order. Returns (order, created)."""
    from app.core.db import bind_tenant

    bind_tenant(db, merchant_id)
    actor = Actor(type="webhook", display=provider)
    ctx = TenantContext(merchant_id=merchant_id, actor=actor)
    o = db.scalar(
        select(Order)
        .where(Order.connection_id == connection_id, Order.external_order_id == ext.external_id)
        .with_for_update()
    )
    if o is not None:
        _follow_channel_status(db, ctx, o, ext, provider)
        return o, False

    cust = (
        customers.resolve_identity(
            db,
            merchant_id,
            provider=provider,
            external_id=ext.customer_external_id,
            display_name=ext.customer_name,
            phone=ext.customer_phone,
        )
        if ext.customer_external_id
        else (
            customers.by_phone(db, merchant_id, customers.nepal.normalize_phone(ext.customer_phone))
            if ext.customer_phone
            else None
        )
    )
    if cust is None:
        cust = Customer(
            merchant_id=merchant_id,
            display_name=ext.customer_name or "Customer",
            phone=customers.nepal.normalize_phone(ext.customer_phone),
            last_seen_at=utcnow(),
        )
        db.add(cust)
        db.flush()
    district = customers.nepal.district_code(ext.district_hint)
    o = Order(
        merchant_id=merchant_id,
        number=_next_number(db, merchant_id),
        status="pending_confirmation",
        source="channel",
        connection_id=connection_id,
        external_order_id=ext.external_id,
        external_number=ext.number,
        customer_id=cust.id,
        currency=ext.currency,
        payment_method=ext.payment_method,
        payment_status="paid" if ext.paid else "unpaid",
        delivery_fee_minor=ext.delivery_fee_minor,
        discount_minor=ext.discount_minor,
        ship_name=ext.customer_name,
        ship_phone=customers.nepal.normalize_phone(ext.customer_phone),
        ship_district=district,
        ship_province=customers.nepal.DISTRICTS[district][1] if district else None,
        ship_text=(ext.address_text or "")[:600] or None,
        address_completeness=0.3 if district else 0.1,
        placed_at=ext.placed_at or utcnow(),
    )
    db.add(o)
    db.flush()
    skus = [ln.sku for ln in ext.lines if ln.sku]
    by_sku = (
        {
            v.sku: v
            for v in db.scalars(
                select(Variant).where(Variant.merchant_id == merchant_id, Variant.sku.in_(skus))
            )
        }
        if skus
        else {}
    )
    unmatched = False
    for pos, ln in enumerate(ext.lines):
        v = by_sku.get(ln.sku) if ln.sku else None
        unmatched |= v is None
        db.add(
            OrderLine(
                merchant_id=merchant_id,
                order_id=o.id,
                position=pos,
                product_id=v.product_id if v else None,
                variant_id=v.id if v else None,
                sku=ln.sku,
                title=ln.title[:255],
                unit_price_minor=ln.unit_price_minor,
                quantity=ln.quantity,
                matched=v is not None,
            )
        )
    db.flush()
    _recompute(db, o)
    try:
        entitlements.record(
            db, merchant_id, "orders", 1, f"order:{o.id}", reference_type="order", reference_id=str(o.id)
        )
    except UsageLimitReached:
        log.warning(
            "order_import_over_limit", merchant_id=str(merchant_id), order_id=str(o.id)
        )  # the sale happened: import anyway
    _event(
        db,
        o,
        actor,
        "imported",
        to_status=o.status,
        provider=provider,
        external_id=ext.external_id,
        channel_status=ext.raw_status,
    )
    _publish(db, o, "orders.created", source="channel")
    if unmatched:
        o.needs_review = "unmatched_items"
    _follow_channel_status(db, ctx, o, ext, provider)
    if not district and o.needs_review is None and o.status not in ("cancelled",):
        o.needs_review = "address_incomplete"
    return o, True


def _follow_channel_status(
    db: Session, ctx: TenantContext, o: Order, ext: ExternalOrder, provider: str
) -> None:
    if ext.paid and o.payment_status in ("unpaid", "pending"):
        o.payment_status = "paid"
        _event(db, o, ctx.actor, "payment_recorded", provider=provider, method="channel")
    target = ext.status
    if target == "cancelled":
        if o.status not in ("cancelled", "returned") and "cancelled" in TRANSITIONS.get(o.status, ()):
            transition(db, ctx, o.id, "cancelled", reason="cancelled_on_channel", provider=provider)
        return
    if target not in _PROGRESS or o.status not in _PROGRESS:
        return
    while _PROGRESS.index(o.status) < _PROGRESS.index(target):
        step = {
            "pending_confirmation": "confirmed",
            "cod_pending": "ready_to_ship",
            "payment_pending": "ready_to_ship",
            "ready_to_ship": "shipped",
            "shipped": "delivered",
            "delivered": "completed",
        }.get(o.status)
        if step is None:
            break
        try:
            with db.begin_nested():  # a failed reservation leaves no partial holds behind
                transition(db, ctx, o.id, step, provider=provider)
        except inventory.OutOfStock:
            if step != "confirmed":
                break
            # The channel already sold it: keep the order (unreserved) and flag the stock gap.
            nxt = "cod_pending" if o.payment_method == "cod" else "payment_pending"
            _event(
                db,
                o,
                ctx.actor,
                "status_changed",
                from_status=o.status,
                to_status=nxt,
                provider=provider,
                reason="stock_short",
            )
            o.status, o.confirmed_at, o.needs_review = nxt, utcnow(), "stock_short"
            if o.payment_status == "unpaid":
                o.payment_status = "cod_pending" if o.payment_method == "cod" else "pending"
            continue
        except Conflict:
            break
        if o.status == "payment_pending" and o.payment_status != "paid":
            break


# ----------------------------------------------------------------------------- views
def order_view(db: Session, o: Order, *, detail: bool = False) -> dict[str, Any]:
    from app.domains.customers.nepal import DISTRICTS

    db.flush()  # the optimistic version increments on flush: the response must carry the new one

    c = db.get(Customer, o.customer_id) if o.customer_id else None
    out: dict[str, Any] = {
        "id": o.id,
        "number": o.number,
        "status": o.status,
        "source": o.source,
        "external_number": o.external_number,
        "connection_id": o.connection_id,
        "customer": {"id": c.id, "display_name": c.display_name, "phone": c.phone} if c else None,
        "currency": o.currency,
        "total": {"amount_minor": o.total_minor, "currency": o.currency},
        "payment_method": o.payment_method,
        "payment_status": o.payment_status,
        "needs_review": o.needs_review,
        "placed_at": o.placed_at,
        "updated_at": o.updated_at,
        "version": o.version,
        "allowed_transitions": sorted(TRANSITIONS.get(o.status, ())),
    }
    if detail:
        lines = _lines(db, o)
        out.update(
            {
                "lines": [
                    {
                        "id": ln.id,
                        "product_id": ln.product_id,
                        "variant_id": ln.variant_id,
                        "sku": ln.sku,
                        "title": ln.title,
                        "variant_title": ln.variant_title,
                        "unit_price": {"amount_minor": ln.unit_price_minor, "currency": o.currency},
                        "quantity": ln.quantity,
                        "cancelled_quantity": ln.cancelled_quantity,
                        "line_total": {"amount_minor": ln.total_minor, "currency": o.currency},
                        "matched": ln.matched,
                    }
                    for ln in lines
                ],
                "totals": {
                    k: {"amount_minor": getattr(o, f"{k}_minor"), "currency": o.currency}
                    for k in ("subtotal", "discount", "delivery_fee", "tax", "total")
                },
                "shipping": {
                    "recipient_name": o.ship_name,
                    "phone": o.ship_phone,
                    "province": o.ship_province,
                    "district": o.ship_district,
                    "district_name": DISTRICTS[o.ship_district][0] if o.ship_district in DISTRICTS else None,
                    "municipality": o.ship_municipality,
                    "ward": o.ship_ward,
                    "area": o.ship_area,
                    "landmark": o.ship_landmark,
                    "text": o.ship_text,
                    "completeness": o.address_completeness,
                },
                "notes": o.notes,
                "cancel_reason": o.cancel_reason,
                "conversation_id": o.conversation_id,
                "confirmed_at": o.confirmed_at,
                "cancelled_at": o.cancelled_at,
            }
        )
    return out


def timeline(db: Session, ctx: TenantContext, order_id: uuid.UUID) -> list[dict[str, Any]]:
    o = get_order(db, ctx, order_id)
    return [
        {
            "id": e.id,
            "kind": e.kind,
            "from_status": e.from_status,
            "to_status": e.to_status,
            "actor": {"type": e.actor_type, "id": e.actor_id, "display": e.actor_display},
            "automated": e.automated,
            "source": e.source,
            "provider": e.provider,
            "data": e.data,
            "at": e.created_at,
        }
        for e in db.scalars(select(OrderEvent).where(OrderEvent.order_id == o.id).order_by(OrderEvent.id))
    ]


# Merging customers moves their orders too.
@customers.merge_hook
def _merge_orders(db: Session, merchant_id: uuid.UUID, source: uuid.UUID, target: uuid.UUID) -> None:
    from sqlalchemy import update

    db.execute(
        update(Order)
        .where(Order.merchant_id == merchant_id, Order.customer_id == source)
        .values(customer_id=target)
    )


# ----------------------------------------------------------------------------- channel order intake
def import_from_channel(
    db: Session, connection_id: uuid.UUID, raw: dict[str, Any]
) -> tuple[Order, bool] | None:
    from app.domains.channels.models import ChannelConnection
    from app.domains.channels.service import adapter_for

    c = db.scalar(
        select(ChannelConnection)
        .where(ChannelConnection.id == connection_id)
        .execution_options(skip_tenant_filter=True)
    )
    if c is None:
        return None
    ext = adapter_for(c).normalize_order(raw)
    if ext is None:
        return None
    return import_external(db, c.merchant_id, c.id, c.provider, ext)


def _on_channel_order(db: Session, ev: Any) -> None:
    if ev.connection_id is not None:
        import_from_channel(db, ev.connection_id, ev.payload)


def _register_webhooks() -> None:
    from app.domains.channels.service import webhook_handler

    for topic in ("order.created", "order.updated"):
        webhook_handler(topic)(_on_channel_order)


_register_webhooks()
