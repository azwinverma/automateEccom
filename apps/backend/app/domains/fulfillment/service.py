"""Shipments (FUL-003…008): booking, labels, pickup, tracking, failed-delivery recovery.

* One live shipment per order. Booking locks the order row, so a double tap can't book twice with the
  courier; the Idempotency-Key is forwarded to the courier as well.
* Every status change, from the courier (webhook or poll) or the seller, goes through ``apply_update``:
  deduped per event, newest-event-wins (late webhooks are kept in history but don't move the parcel
  backwards), terminal states are final. The order follows the parcel through the order state machine.
* Failed delivery: an attempt record is opened, the customer is asked for a time/corrected address
  (where permitted), their reply is captured from the inbox, and a reattempt is requested
  automatically only in smart/autopilot mode. No reply within the wait window → escalated to the seller.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.channels.models import WebhookEvent
from app.domains.customers import nepal
from app.domains.customers import service as customers
from app.domains.fulfillment import couriers, notify
from app.domains.fulfillment.models import (
    LIVE_STATUSES,
    TERMINAL_STATUSES,
    CourierAccount,
    DeliveryAttempt,
    Shipment,
    ShipmentEvent,
)
from app.domains.integrations.base import (
    FAILURE_REASONS,
    SHIPMENT_STATUSES,
    CourierCapability,
    IntegrationError,
    Money,
    TrackingUpdate,
)
from app.domains.inventory import service as inventory
from app.domains.merchants.models import Merchant
from app.domains.orders import service as orders
from app.domains.orders.models import Order, OrderLine
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)

BOOKABLE_ORDER_STATUSES = frozenset({"cod_pending", "ready_to_ship"})
CANCELLABLE = frozenset({"booked", "pickup_requested"})
MANUAL_STATUSES = frozenset(
    {
        "picked_up",
        "in_transit",
        "out_for_delivery",
        "delivered",
        "delivery_failed",
        "returning",
        "returned_to_origin",
        "lost",
    }
)
OPEN_RECOVERY = ("open", "awaiting_customer", "customer_replied", "escalated")
# Where the order should be once the parcel reaches a status (order state machine, spec 12).
ORDER_TARGET = {
    "picked_up": "shipped",
    "in_transit": "shipped",
    "out_for_delivery": "shipped",
    "delivered": "delivered",
    "delivery_failed": "delivery_failed",
    "returning": "delivery_failed",
    "returned_to_origin": "returned",
}
ORDER_PATHS: dict[str, dict[str, list[str]]] = {
    "shipped": {"ready_to_ship": ["shipped"], "delivery_failed": ["shipped"]},
    "delivered": {
        "ready_to_ship": ["shipped", "delivered"],
        "shipped": ["delivered"],
        "delivery_failed": ["shipped", "delivered"],
    },
    "delivery_failed": {"ready_to_ship": ["shipped", "delivery_failed"], "shipped": ["delivery_failed"]},
    "returned": {
        "ready_to_ship": ["shipped", "delivery_failed", "returned"],
        "shipped": ["delivery_failed", "returned"],
        "delivery_failed": ["returned"],
    },
}
POLL_EVERY = timedelta(minutes=30)
POLL_EVERY_WITH_WEBHOOKS = timedelta(hours=6)
STUCK_AFTER = timedelta(days=4)


# ----------------------------------------------------------------------------- lookups
def get_shipment(db: Session, ctx: TenantContext, shipment_id: uuid.UUID, *, lock: bool = False) -> Shipment:
    stmt = select(Shipment).where(Shipment.id == shipment_id)
    if lock:
        stmt = stmt.with_for_update()
    s = db.scalar(stmt)
    if s is None or s.merchant_id != ctx.merchant_id:
        raise NotFound(code="shipment_not_found")
    return s


def _account(db: Session, s: Shipment) -> CourierAccount:
    a = db.get(CourierAccount, s.courier_account_id)
    assert a is not None
    return a


def _is_manual(a: CourierAccount) -> bool:
    return CourierCapability.MANUAL_UPDATES.value in a.capabilities


def _courier_error(e: IntegrationError) -> AppError:
    if e.code == "already_picked_up":
        return Conflict("The courier already has this parcel", code="shipment_already_picked_up")
    if e.auth:
        return Conflict(
            "The courier rejected our credentials. Reconnect it in Settings.",
            code="courier_reconnect_required",
        )
    return AppError("The courier didn't accept the request. Try again shortly.", code="courier_unavailable")


# ----------------------------------------------------------------------------- booking (FUL-003/004)
@dataclass
class BookInput:
    courier_account_id: uuid.UUID
    weight_grams: int | None = None
    service_code: str | None = None
    tracking_number: str | None = None  # manual couriers
    courier_name: str | None = None  # manual couriers: "Pathao", "own rider"…
    notes: str | None = None


def book(
    db: Session, ctx: TenantContext, order_id: uuid.UUID, data: BookInput, idempotency_key: str
) -> Shipment:
    existing = db.scalar(select(Shipment).where(Shipment.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    o = orders.get_order(db, ctx, order_id, lock=True)  # serialises bookings for this order
    live = db.scalar(
        select(Shipment).where(
            Shipment.order_id == o.id, Shipment.status != "cancelled", Shipment.direction == "outbound"
        )
    )
    if live is not None:
        raise Conflict(
            "This order already has a shipment", code="shipment_exists", details={"shipment_id": str(live.id)}
        )
    if o.status not in BOOKABLE_ORDER_STATUSES:
        raise Conflict(
            "Only orders that are ready to ship can be booked with a courier",
            code="order_not_ready_to_ship",
            details={"status": o.status},
        )
    a = couriers.get_account(db, ctx, data.courier_account_id)
    settings = couriers.get_settings_row(db, ctx.merchant_id)
    weight = data.weight_grams or settings.default_weight_grams
    cod_minor = couriers.cod_due(o)
    s = Shipment(
        id=uuid7(),
        merchant_id=ctx.merchant_id,
        order_id=o.id,
        courier_account_id=a.id,
        provider=a.provider,
        status="booked",
        weight_grams=weight,
        cod_amount_minor=cod_minor,
        currency=o.currency,
        origin_district=a.pickup_district,
        destination_district=o.ship_district,
        idempotency_key=idempotency_key,
        booked_by_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
        notes=data.notes,
    )
    if _is_manual(a):
        s.courier_name = (data.courier_name or a.display_name)[:80]
        s.tracking_number = (data.tracking_number or "").strip()[:80] or None
    else:
        if not (a.pickup_name and a.pickup_phone and a.pickup_district):
            raise ValidationFailed(
                "Add a pickup address for this courier first", code="pickup_address_missing"
            )
        if not o.ship_district or not o.ship_phone:
            raise ValidationFailed("The delivery address is incomplete", code="address_incomplete")
        adapter = couriers.adapter_for(a)
        dest = couriers.destination_address(o)
        cod = Money(cod_minor, o.currency) if cod_minor else None
        quote = None
        try:
            quotes = adapter.get_rates(couriers.origin_address(a), dest, weight, cod)
            quote = next((q for q in quotes if q.service_code == (data.service_code or q.service_code)), None)
            if data.service_code and quote is None:
                raise ValidationFailed(code="courier_service_unavailable")
            if quote is not None and cod and not quote.cod_supported:
                raise ValidationFailed(
                    "This service can't collect cash on delivery", code="courier_service_no_cod"
                )
            res = adapter.create_shipment(
                couriers.origin_address(a),
                dest,
                weight,
                cod,
                reference=f"#{o.number}",
                idempotency_key=f"shipment:{ctx.merchant_id}:{idempotency_key}",
                service_code=quote.service_code if quote else data.service_code,
                description=_description(db, o),
            )
        except IntegrationError as e:
            log.warning("courier_booking_failed", provider=a.provider, error=e.code)
            if e.auth:
                a.status, a.last_error_code = "error", e.code
            raise _courier_error(e) from e
        s.courier_name = a.display_name
        s.service_code = quote.service_code if quote else data.service_code
        s.provider_shipment_id, s.tracking_number, s.label_url = (
            res.provider_shipment_id,
            res.tracking_number,
            res.label_url,
        )
        if quote is not None:
            s.charge_minor, s.eta_days_min, s.eta_days_max = (
                quote.price.amount_minor,
                quote.eta_days_min,
                quote.eta_days_max,
            )
    if o.status == "cod_pending":  # booking a parcel means it's packed and ready
        orders.transition(db, ctx, o.id, "ready_to_ship")
    db.add(s)
    db.flush()
    _local_event(db, s, "booked", ctx, description=s.courier_name)
    orders._event(
        db,
        o,
        ctx.actor,
        "shipment_booked",
        provider=s.provider,
        shipment_id=str(s.id),
        tracking_number=s.tracking_number,
        courier=s.courier_name,
    )
    audit.record(
        db,
        action="fulfillment.shipment_booked",
        resource_type="shipment",
        resource_id=s.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"order_number": o.number, "provider": s.provider, "cod_minor": cod_minor},
    )
    return s


def book_return(
    db: Session,
    ctx: TenantContext,
    r: Any,
    account_id: uuid.UUID,
    idempotency_key: str,
    *,
    tracking_number: str | None = None,
    courier_name: str | None = None,
) -> Shipment:
    """RET-006: the courier collects the returned item from the customer and brings it to the shop."""
    existing = db.scalar(select(Shipment).where(Shipment.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    live = db.scalar(select(Shipment).where(Shipment.return_id == r.id, Shipment.status != "cancelled"))
    if live is not None:
        raise Conflict(
            "This return already has a pickup", code="shipment_exists", details={"shipment_id": str(live.id)}
        )
    o = db.get(Order, r.order_id)
    assert o is not None
    a = couriers.get_account(db, ctx, account_id)
    weight = couriers.get_settings_row(db, ctx.merchant_id).default_weight_grams
    s = Shipment(
        id=uuid7(),
        merchant_id=ctx.merchant_id,
        order_id=o.id,
        direction="return",
        return_id=r.id,
        courier_account_id=a.id,
        provider=a.provider,
        status="booked",
        weight_grams=weight,
        cod_amount_minor=0,
        currency=o.currency,
        origin_district=o.ship_district,
        destination_district=a.pickup_district,
        idempotency_key=idempotency_key,
        booked_by_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
        notes=f"Return {r.number}",
    )
    if _is_manual(a):
        s.courier_name = (courier_name or a.display_name)[:80]
        s.tracking_number = (tracking_number or "").strip()[:80] or None
    else:
        if not (a.pickup_name and a.pickup_phone and a.pickup_district):
            raise ValidationFailed(
                "Add a pickup address for this courier first", code="pickup_address_missing"
            )
        if not o.ship_district or not o.ship_phone:
            raise ValidationFailed("The customer's address is incomplete", code="address_incomplete")
        try:
            res = couriers.adapter_for(a).create_shipment(
                couriers.destination_address(o),  # from the customer…
                couriers.origin_address(a),  # …back to the shop
                weight,
                None,
                reference=r.number,
                idempotency_key=f"shipment:{ctx.merchant_id}:{idempotency_key}",
                description=f"Return {r.number}",
            )
        except IntegrationError as e:
            raise _courier_error(e) from e
        s.courier_name = a.display_name
        s.provider_shipment_id, s.tracking_number, s.label_url = (
            res.provider_shipment_id,
            res.tracking_number,
            res.label_url,
        )
    db.add(s)
    db.flush()
    _local_event(db, s, "booked", ctx, description=s.courier_name)
    audit.record(
        db,
        action="fulfillment.return_pickup_booked",
        resource_type="shipment",
        resource_id=s.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"return": r.number, "provider": s.provider},
    )
    return s


def _description(db: Session, o: Order) -> str:
    lines = db.scalars(select(OrderLine).where(OrderLine.order_id == o.id).order_by(OrderLine.position))
    return ", ".join(f"{ln.active_quantity} x {ln.title}" for ln in lines if ln.active_quantity)[:200]


def request_pickup(db: Session, ctx: TenantContext, shipment_ids: list[uuid.UUID]) -> list[Shipment]:
    """FUL-005: one pickup request per courier for the selected booked parcels."""
    rows = [get_shipment(db, ctx, sid, lock=True) for sid in dict.fromkeys(shipment_ids)]
    by_account: dict[uuid.UUID, list[Shipment]] = {}
    for s in rows:
        if s.status != "booked":
            raise Conflict(
                "Pickup can only be requested for booked parcels",
                code="shipment_not_booked",
                details={"shipment_id": str(s.id)},
            )
        by_account.setdefault(s.courier_account_id, []).append(s)
    for account_id, group in by_account.items():
        a = db.get(CourierAccount, account_id)
        assert a is not None
        reference = None
        if not _is_manual(a):
            try:
                res = couriers.adapter_for(a).request_pickup(
                    [s.provider_shipment_id or "" for s in group],
                    idempotency_key="pickup:" + ",".join(sorted(str(s.id) for s in group)),
                )
                reference = res.reference
            except IntegrationError as e:
                raise _courier_error(e) from e
        for s in group:
            s.pickup_reference, s.pickup_requested_at = reference, utcnow()
            _apply(db, s, _local_update(s, "pickup_requested"), "seller", ctx)
    return rows


def cancel(db: Session, ctx: TenantContext, shipment_id: uuid.UUID, *, reason: str | None = None) -> Shipment:
    s = get_shipment(db, ctx, shipment_id, lock=True)
    if s.status == "cancelled":
        return s
    if s.status not in CANCELLABLE:
        raise Conflict("The courier already has this parcel", code="shipment_already_picked_up")
    a = _account(db, s)
    if not _is_manual(a) and s.provider_shipment_id:
        try:
            couriers.adapter_for(a).cancel(s.provider_shipment_id, idempotency_key=f"cancel:{s.id}")
        except IntegrationError as e:
            raise _courier_error(e) from e
    s.cancelled_at = utcnow()
    _apply(db, s, _local_update(s, "cancelled", description=reason), "seller", ctx)
    return s


def label(db: Session, ctx: TenantContext, shipment_id: uuid.UUID) -> dict[str, Any]:
    """FUL-004: the courier's label when it provides one, otherwise the data for Nivaro's printable label."""
    s = get_shipment(db, ctx, shipment_id)
    o = db.get(Order, s.order_id)
    a = _account(db, s)
    m = db.get(Merchant, s.merchant_id)
    assert o is not None and m is not None
    dest = couriers.destination_address(o)
    shop = {
        "name": a.pickup_name or m.name,
        "phone": a.pickup_phone,
        "address": ", ".join(
            x for x in (a.pickup_area, a.pickup_municipality, _district_name(a.pickup_district)) if x
        ),
    }
    customer = {
        "name": dest.name,
        "phone": dest.phone,
        "address": ", ".join(x for x in (dest.line1, _district_name(o.ship_district)) if x),
        "landmark": o.ship_landmark,
    }
    return {
        "shipment_id": s.id,
        "direction": s.direction,
        "provider_label_url": s.label_url,
        "courier": s.courier_name or a.display_name,
        "service_code": s.service_code,
        "tracking_number": s.tracking_number,
        "order_number": o.number,
        "shop": m.name,
        "from": {**customer, "landmark": None} if s.direction == "return" else shop,
        "to": {**shop, "landmark": None} if s.direction == "return" else customer,
        "cod_amount": {"amount_minor": s.cod_amount_minor, "currency": s.currency},
        "weight_grams": s.weight_grams,
        "contents": _description(db, o),
        "booked_at": s.created_at,
    }


def _district_name(code: str | None) -> str | None:
    return nepal.DISTRICTS[code][0] if code in nepal.DISTRICTS else None


# ----------------------------------------------------------------------------- tracking (FUL-006)
def _local_update(
    s: Shipment, status: str, *, description: str | None = None, failure_reason: str | None = None
) -> TrackingUpdate:
    return TrackingUpdate(
        event_id=f"local:{uuid7()}",
        status=status,
        occurred_at=max(utcnow(), s.last_event_at) if s.last_event_at else utcnow(),
        description=description,
        failure_reason=failure_reason,
    )


def _local_event(
    db: Session, s: Shipment, status: str, ctx: TenantContext, *, description: str | None = None
) -> None:
    db.add(
        ShipmentEvent(
            merchant_id=s.merchant_id,
            shipment_id=s.id,
            event_key=f"local:{uuid7()}",
            status=status,
            description=description,
            source="seller" if ctx.actor.type == "user" else "system",
            actor_user_id=ctx.actor.id,
            occurred_at=utcnow(),
        )
    )
    s.last_event_at = utcnow()


def apply_update(db: Session, s: Shipment, u: TrackingUpdate, source: str) -> str | None:
    """Courier-originated update. Returns the new status when the parcel moved, else None."""
    a = _account(db, s)
    ctx = TenantContext(merchant_id=s.merchant_id, actor=Actor(type="webhook", display=a.display_name))
    return _apply(db, s, u, source, ctx)


def _apply(db: Session, s: Shipment, u: TrackingUpdate, source: str, ctx: TenantContext) -> str | None:
    if u.status not in SHIPMENT_STATUSES:
        log.warning("courier_status_unknown", provider=s.provider, status=u.status)
        return None
    reason = (
        u.failure_reason
        if u.failure_reason in FAILURE_REASONS
        else ("other" if u.status == "delivery_failed" else None)
    )
    ev_id = db.execute(
        pg_insert(ShipmentEvent)
        .values(
            id=uuid7(),
            merchant_id=s.merchant_id,
            shipment_id=s.id,
            event_key=u.event_id[:200],
            status=u.status,
            raw_status=(u.raw_status or "")[:80] or None,
            description=(u.description or "")[:500] or None,
            location=(u.location or "")[:160] or None,
            failure_reason=reason,
            source=source,
            actor_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
            applied=True,
            occurred_at=u.occurred_at,
            created_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["shipment_id", "event_key"])
        .returning(ShipmentEvent.id)
    ).scalar_one_or_none()
    if ev_id is None:
        return None  # duplicate delivery of the same courier event
    late = s.last_event_at is not None and u.occurred_at < s.last_event_at
    if s.status in TERMINAL_STATUSES or late or u.status == s.status:
        if s.status in TERMINAL_STATUSES or late:
            ev = db.get(ShipmentEvent, ev_id)
            if ev is not None:
                ev.applied = False
        return None
    before = s.status
    s.status, s.last_event_at = u.status, u.occurred_at
    now = u.occurred_at
    if u.status in ("picked_up", "in_transit", "out_for_delivery") and s.picked_up_at is None:
        s.picked_up_at = now
    if u.status == "delivered":
        s.delivered_at = now
        _resolve_attempts(db, s, "delivered")
    elif u.status == "delivery_failed":
        _open_attempt(db, s, reason or "other", now)
    elif u.status == "returning":
        for att in _open_attempts(db, s):
            att.recovery_status = "returning"
    elif u.status == "returned_to_origin":
        s.returned_at = now
        _resolve_attempts(db, s, "returned")
    elif u.status == "cancelled":
        s.cancelled_at = s.cancelled_at or now
    _sync_order(db, s, ctx)
    outbox.publish(
        db,
        event_type="fulfillment.shipment_status_changed",
        aggregate_type="shipment",
        aggregate_id=s.id,
        merchant_id=s.merchant_id,
        payload={"shipment_id": str(s.id), "status": s.status, "from_status": before},
    )
    return s.status


def _sync_order(db: Session, s: Shipment, ctx: TenantContext) -> None:
    if s.direction == "return":
        from app.domains.returns.service import on_return_parcel

        on_return_parcel(db, s)
        return
    target = ORDER_TARGET.get(s.status)
    if target is None:
        return
    o = db.get(Order, s.order_id)
    if o is None or o.status == target:
        return
    for step in ORDER_PATHS[target].get(o.status, []):
        try:
            with db.begin_nested():
                orders.transition(db, ctx, o.id, step, provider=s.provider)
        except AppError as e:  # e.g. the order was cancelled meanwhile: the parcel history still records it
            log.warning("order_follow_shipment_failed", order_id=str(o.id), to=step, code=e.code)
            return


def _open_attempts(db: Session, s: Shipment) -> list[DeliveryAttempt]:
    return list(
        db.scalars(
            select(DeliveryAttempt).where(
                DeliveryAttempt.shipment_id == s.id,
                DeliveryAttempt.recovery_status.not_in(("resolved",)),
            )
        )
    )


def _resolve_attempts(db: Session, s: Shipment, resolution: str) -> None:
    for att in _open_attempts(db, s):
        att.recovery_status, att.resolved_at, att.resolution = "resolved", utcnow(), resolution


def _open_attempt(db: Session, s: Shipment, reason: str, at: datetime) -> DeliveryAttempt:
    _resolve_attempts(db, s, "failed_again")
    s.attempt_count += 1
    o = db.get(Order, s.order_id)
    att = DeliveryAttempt(
        merchant_id=s.merchant_id,
        shipment_id=s.id,
        order_id=s.order_id,
        conversation_id=o.conversation_id if o else None,
        attempt_no=s.attempt_count,
        failure_reason=reason,
        failed_at=at,
        recovery_status="open",
    )
    db.add(att)
    db.flush()
    return att


# ----------------------------------------------------------------------------- seller actions
def manual_update(
    db: Session,
    ctx: TenantContext,
    shipment_id: uuid.UUID,
    status: str,
    *,
    failure_reason: str | None,
    note: str | None,
) -> Shipment:
    """Own rider / courier without an API: the seller records what happened."""
    s = get_shipment(db, ctx, shipment_id, lock=True)
    if not _is_manual(_account(db, s)):
        raise Conflict("This courier reports its own tracking", code="shipment_tracked_by_courier")
    if status not in MANUAL_STATUSES:
        raise ValidationFailed(code="shipment_status_invalid")
    if status == "delivery_failed" and failure_reason not in FAILURE_REASONS:
        raise ValidationFailed("Say why the delivery failed", code="failure_reason_required")
    if s.status in TERMINAL_STATUSES:
        raise Conflict("This shipment is finished", code="shipment_closed")
    _apply(db, s, _local_update(s, status, description=note, failure_reason=failure_reason), "seller", ctx)
    return s


def set_tracking(
    db: Session, ctx: TenantContext, shipment_id: uuid.UUID, tracking_number: str, courier_name: str | None
) -> Shipment:
    s = get_shipment(db, ctx, shipment_id, lock=True)
    if not _is_manual(_account(db, s)):
        raise Conflict("This courier assigns the tracking number", code="shipment_tracked_by_courier")
    s.tracking_number = tracking_number.strip()[:80] or None
    if courier_name:
        s.courier_name = courier_name[:80]
    return s


def request_reattempt(
    db: Session,
    ctx: TenantContext,
    shipment_id: uuid.UUID,
    *,
    note: str | None,
    address: customers.AddressInput | None = None,
    by: str = "seller",
) -> Shipment:
    s = get_shipment(db, ctx, shipment_id, lock=True)
    if s.status not in ("delivery_failed",):
        raise Conflict("A reattempt can be requested after a failed delivery", code="reattempt_not_possible")
    o = db.get(Order, s.order_id)
    assert o is not None
    if address is not None:  # corrected address from the customer: update the order's snapshot
        clean, completeness = customers.validate_address(address)
        _set_order_address(o, clean, completeness)
        orders._event(db, o, ctx.actor, "address_corrected", district=clean["district"])
        s.destination_district = o.ship_district
    a = _account(db, s)
    if not _is_manual(a):
        try:
            couriers.adapter_for(a).request_reattempt(
                s.provider_shipment_id or "",
                note,
                couriers.destination_address(o) if address is not None else None,
                idempotency_key=f"reattempt:{s.id}:{s.attempt_count}",
            )
        except IntegrationError as e:
            raise _courier_error(e) from e
    for att in _open_attempts(db, s):
        att.recovery_status, att.reattempt_requested_at = "reattempt_requested", utcnow()
        att.reattempt_note, att.reattempt_by = (note or "")[:500] or None, by
    _apply(
        db,
        s,
        _local_update(s, "reattempt_requested", description=note),
        "seller" if by == "seller" else "system",
        ctx,
    )
    return s


def _set_order_address(o: Order, clean: dict[str, Any], completeness: float) -> None:
    o.ship_name, o.ship_phone = clean["recipient_name"], clean["phone"]
    o.ship_province, o.ship_district = clean["province"], clean["district"]
    o.ship_municipality, o.ship_ward = clean["municipality"], clean["ward"]
    o.ship_area, o.ship_landmark = clean["area"], clean["landmark"]
    o.address_completeness = completeness


def return_to_sender(
    db: Session, ctx: TenantContext, shipment_id: uuid.UUID, *, reason: str | None
) -> Shipment:
    s = get_shipment(db, ctx, shipment_id, lock=True)
    if s.status not in ("delivery_failed", "reattempt_requested"):
        raise Conflict("Only a parcel that couldn't be delivered can be returned", code="return_not_possible")
    a = _account(db, s)
    if not _is_manual(a):
        try:
            couriers.adapter_for(a).request_return(
                s.provider_shipment_id or "", idempotency_key=f"return:{s.id}"
            )
        except IntegrationError as e:
            raise _courier_error(e) from e
    _apply(db, s, _local_update(s, "returning", description=reason), "seller", ctx)
    return s


def confirm_received_back(db: Session, ctx: TenantContext, shipment_id: uuid.UUID) -> Shipment:
    """The returned parcel is back with the seller: its items go back on the shelf (once)."""
    s = get_shipment(db, ctx, shipment_id, lock=True)
    if s.status != "returned_to_origin":
        raise Conflict("The parcel hasn't been returned yet", code="shipment_not_returned")
    if s.return_received_at is not None:
        return s
    s.return_received_at = utcnow()
    o = db.get(Order, s.order_id)
    assert o is not None
    for r in inventory.reservations_for(db, s.merchant_id, "order", str(o.id)):
        if r.status == "committed":
            inventory.return_to_stock(db, ctx.actor, r)
    orders._event(db, o, ctx.actor, "returned_to_stock", shipment_id=str(s.id))
    audit.record(
        db,
        action="fulfillment.return_received",
        resource_type="shipment",
        resource_id=s.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"order_number": o.number},
    )
    return s


def refresh(db: Session, ctx: TenantContext, shipment_id: uuid.UUID) -> Shipment:
    s = get_shipment(db, ctx, shipment_id, lock=True)
    a = _account(db, s)
    if CourierCapability.TRACKING.value not in a.capabilities or not s.tracking_number:
        raise Conflict("This courier doesn't offer tracking", code="tracking_not_supported")
    try:
        _poll_one(db, s, a)
    except IntegrationError as e:
        raise _courier_error(e) from e
    return s


def _poll_one(db: Session, s: Shipment, a: CourierAccount) -> int:
    updates = couriers.adapter_for(a).track(s.tracking_number or "")
    s.last_polled_at = utcnow()
    moved = 0
    for u in sorted(updates, key=lambda x: x.occurred_at):
        if apply_update(db, s, u, "courier_poll"):
            moved += 1
    return moved


def poll_due(db: Session, limit: int = 200) -> dict[str, int]:
    """Worker: poll couriers for live parcels (webhook couriers too, as a slow safety net)."""
    now = utcnow()
    rows = db.execute(
        select(Shipment.id, Shipment.merchant_id)
        .join(CourierAccount, CourierAccount.id == Shipment.courier_account_id)
        .where(
            Shipment.status.in_(LIVE_STATUSES),
            Shipment.tracking_number.is_not(None),
            CourierAccount.capabilities.contains([CourierCapability.TRACKING.value]),
            CourierAccount.status == "connected",
            or_(
                Shipment.last_polled_at.is_(None),
                Shipment.last_polled_at < now - POLL_EVERY,
            ),
        )
        .order_by(Shipment.last_polled_at.asc().nulls_first())
        .limit(limit)
        .execution_options(skip_tenant_filter=True)
    ).all()
    stats = {"polled": 0, "moved": 0, "failed": 0}
    for sid, mid in rows:
        bind_tenant(db, mid)
        s = db.scalar(select(Shipment).where(Shipment.id == sid).with_for_update(skip_locked=True))
        if s is None:
            continue
        a = _account(db, s)
        if (
            CourierCapability.WEBHOOKS.value in a.capabilities
            and s.last_polled_at
            and s.last_polled_at > now - POLL_EVERY_WITH_WEBHOOKS
        ):
            continue
        try:
            with db.begin_nested():
                stats["moved"] += _poll_one(db, s, a)
            stats["polled"] += 1
        except IntegrationError as e:
            stats["failed"] += 1
            s.last_polled_at = now
            if e.auth:
                a.status, a.last_error_code = "error", e.code
            log.warning("courier_poll_failed", provider=a.provider, error=e.code)
    return stats


# ----------------------------------------------------------------------------- webhooks
def ingest_courier_webhook(
    db: Session, provider: str, account_id: uuid.UUID, headers: dict[str, str], body: bytes
) -> dict[str, int]:
    a = db.scalar(
        select(CourierAccount)
        .where(CourierAccount.id == account_id)
        .execution_options(skip_tenant_filter=True)
    )
    if a is None or a.provider != provider or a.status == "disconnected":
        raise NotFound(code="provider_not_available")
    adapter = couriers.adapter_for(a)
    if not adapter.verify_webhook(headers, body):
        raise AppError("Invalid signature", code="webhook_signature_invalid")
    try:
        updates = adapter.parse_tracking_webhook(headers, body)
    except (ValueError, KeyError, TypeError) as e:
        raise ValidationFailed("Malformed webhook", code="webhook_malformed") from e
    stats = {"accepted": 0, "duplicates": 0}
    for u in updates:
        inserted = db.execute(
            pg_insert(WebhookEvent)
            .values(
                id=uuid7(),
                provider=provider,
                external_event_id=f"{a.id}:{u.event_id}"[:200],
                event_type="shipment.updated",
                merchant_id=a.merchant_id,
                external_account_id=str(a.id),
                payload=_update_payload(u),
                status="received",
                received_at=utcnow(),
                occurred_at=u.occurred_at,
                attempts=0,
                duplicate_count=0,
            )
            .on_conflict_do_nothing(index_elements=["provider", "external_event_id"])
            .returning(WebhookEvent.id)
        ).scalar_one_or_none()
        if inserted is None:
            stats["duplicates"] += 1
            continue
        outbox.publish(
            db,
            event_type="webhooks.received",
            aggregate_type="webhook_event",
            aggregate_id=inserted,
            merchant_id=a.merchant_id,
            payload={"webhook_event_id": str(inserted)},
        )
        stats["accepted"] += 1
    return stats


def _update_payload(u: TrackingUpdate) -> dict[str, Any]:
    return {
        "event_id": u.event_id,
        "tracking_number": u.tracking_number,
        "status": u.status,
        "occurred_at": u.occurred_at.isoformat(),
        "raw_status": u.raw_status,
        "description": u.description,
        "location": u.location,
        "failure_reason": u.failure_reason,
        "cod_collected_minor": u.cod_collected_minor,
    }


def _on_shipment_webhook(db: Session, ev: WebhookEvent) -> None:
    p = ev.payload
    s = db.scalar(
        select(Shipment)
        .where(
            Shipment.courier_account_id == uuid.UUID(str(ev.external_account_id)),
            Shipment.tracking_number == str(p.get("tracking_number")),
        )
        .with_for_update()
    )
    if s is None:
        log.info("courier_webhook_unknown_parcel", provider=ev.provider)
        return
    apply_update(
        db,
        s,
        TrackingUpdate(
            event_id=str(p["event_id"]),
            status=str(p["status"]),
            occurred_at=datetime.fromisoformat(str(p["occurred_at"])),
            raw_status=p.get("raw_status"),
            description=p.get("description"),
            location=p.get("location"),
            failure_reason=p.get("failure_reason"),
            cod_collected_minor=p.get("cod_collected_minor"),
        ),
        "courier_webhook",
    )


def _register_webhooks() -> None:
    from app.domains.channels.service import webhook_handler

    webhook_handler("shipment.updated")(_on_shipment_webhook)


_register_webhooks()


# ----------------------------------------------------------------- order cancelled → cancel booking
@handler("orders.status_changed", name="fulfillment.cancel_with_order")
def _cancel_with_order(db: Session, ev: OutboxEvent) -> None:
    if ev.payload.get("status") != "cancelled":
        return
    s = db.scalar(
        select(Shipment)
        .where(
            Shipment.order_id == uuid.UUID(ev.payload["order_id"]),
            Shipment.status.in_(CANCELLABLE),
            Shipment.direction == "outbound",
        )
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if s is None:
        return
    bind_tenant(db, s.merchant_id)
    ctx = TenantContext(merchant_id=s.merchant_id, actor=Actor.system("fulfillment"))
    try:
        cancel(db, ctx, s.id, reason="order_cancelled")
    except AppError as e:
        log.warning("shipment_cancel_with_order_failed", shipment_id=str(s.id), code=e.code)


# ----------------------------------------------------------------------------- notifications (FUL-007)
def _conversation_for(db: Session, o: Order) -> Any:
    from app.domains.channels.models import ChannelConnection
    from app.domains.inbox.models import Conversation

    if o.conversation_id is None:
        return None
    conv = db.get(Conversation, o.conversation_id)
    if conv is None or conv.connection_id is None:
        return None
    c = db.get(ChannelConnection, conv.connection_id)
    return conv if c is not None and c.status == "connected" else None


def _send(db: Session, s: Shipment, o: Order, kind: str, text: str) -> bool:
    from app.domains.inbox import service as inbox

    if kind in s.notified:
        return False
    conv = _conversation_for(db, o)
    if conv is None or not couriers.get_settings_row(db, s.merchant_id).notify_customers:
        return False
    inbox.queue_reply(
        db,
        conv,
        text,
        author="system",
        intent="shipping_update",
        grounding={"shipment": str(s.id), "kind": kind},
    )
    s.notified = [*s.notified, kind]
    orders._event(
        db, o, Actor.system("fulfillment"), "customer_notified", notification=kind, shipment_id=str(s.id)
    )
    return True


@handler("fulfillment.shipment_status_changed", name="fulfillment.notify_customer")
def _notify_customer(db: Session, ev: OutboxEvent) -> None:
    s = db.scalar(
        select(Shipment)
        .where(Shipment.id == uuid.UUID(ev.payload["shipment_id"]))
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if s is None or s.status != ev.payload["status"] or s.direction == "return":
        return  # moved on (only the current state is worth telling), or a return pickup (returns notify)
    bind_tenant(db, s.merchant_id)
    o = db.get(Order, s.order_id)
    if o is None:
        return
    from app.domains.inbox.models import Conversation

    conv = db.get(Conversation, o.conversation_id) if o.conversation_id else None
    locale = conv.locale if conv else "en"
    courier = s.courier_name or _account(db, s).display_name
    if s.status in ("picked_up", "in_transit") and "out_for_delivery" not in s.notified:
        _send(
            db,
            s,
            o,
            "shipped",
            notify.shipped(locale, o.number, courier, s.tracking_number, s.cod_amount_minor),
        )
    elif s.status == "out_for_delivery":
        kind = f"out_for_delivery:{s.attempt_count}"
        _send(db, s, o, kind, notify.out_for_delivery(locale, o.number, s.cod_amount_minor))
    elif s.status == "delivered":
        m = db.get(Merchant, s.merchant_id)
        _send(
            db, s, o, "delivered", notify.text("delivered", locale, number=o.number, shop=m.name if m else "")
        )
    elif s.status == "delivery_failed":
        att = db.scalar(
            select(DeliveryAttempt).where(
                DeliveryAttempt.shipment_id == s.id, DeliveryAttempt.attempt_no == s.attempt_count
            )
        )
        if att is None or att.recovery_status != "open":
            return
        if _send(
            db,
            s,
            o,
            f"delivery_failed:{att.attempt_no}",
            notify.delivery_failed(locale, o.number, att.failure_reason),
        ):
            att.recovery_status, att.customer_contacted_at = "awaiting_customer", utcnow()


# ----------------------------------------------------------------------------- recovery (FUL-008)
def capture_customer_reply(db: Session, conv: Any, msg: Any) -> bool:
    """Called by the Sales Agent before anything else: a reply to our failed-delivery question is
    recorded on the attempt (and acted on per the Decision Policy) instead of being treated as a new
    sales question. Returns True when the message was handled here."""
    att = db.scalar(
        select(DeliveryAttempt)
        .where(
            DeliveryAttempt.conversation_id == conv.id, DeliveryAttempt.recovery_status == "awaiting_customer"
        )
        .order_by(DeliveryAttempt.failed_at.desc())
        .limit(1)
        .with_for_update()
    )
    if att is None:
        return False
    from app.domains.inbox import service as inbox

    att.customer_reply, att.customer_replied_at = (msg.text or "")[:1000], utcnow()
    att.recovery_status = "customer_replied"
    msg.intent = conv.last_intent = "delivery_followup"
    s = db.get(Shipment, att.shipment_id)
    o = db.get(Order, att.order_id)
    assert s is not None and o is not None
    a = _account(db, s)
    merchant = db.get(Merchant, s.merchant_id)
    auto = (
        merchant is not None
        and merchant.automation_mode in ("smart", "autopilot")
        and CourierCapability.REATTEMPT.value in a.capabilities
        and s.status == "delivery_failed"
    )
    ctx = TenantContext(
        merchant_id=s.merchant_id, actor=Actor(type="automation", display="Delivery recovery")
    )
    if auto:
        try:
            with db.begin_nested():
                request_reattempt(
                    db, ctx, s.id, note=f"Customer: {att.customer_reply}"[:500], by="automation"
                )
            kind = "reattempt_requested"
        except AppError as e:
            log.warning("auto_reattempt_failed", shipment_id=str(s.id), code=e.code)
            kind = "reply_noted"
    else:
        kind = "reply_noted"
    inbox.queue_reply(
        db,
        conv,
        notify.text(kind, conv.locale, number=o.number),
        author="system",
        intent="delivery_followup",
        grounding={"delivery_attempt": str(att.id), "action": kind},
    )
    orders._event(
        db,
        o,
        ctx.actor,
        "customer_replied_delivery",
        attempt=att.attempt_no,
        auto_reattempt=kind == "reattempt_requested",
    )
    return True


def escalate_stale(db: Session) -> int:
    """Worker: no reply (or nobody to message) within the wait window → the seller takes over."""
    from app.domains.fulfillment.models import FulfillmentSettings

    now = utcnow()
    rows = db.execute(
        select(DeliveryAttempt, func.coalesce(FulfillmentSettings.recovery_wait_hours, 24))
        .outerjoin(FulfillmentSettings, FulfillmentSettings.merchant_id == DeliveryAttempt.merchant_id)
        .where(DeliveryAttempt.recovery_status.in_(("open", "awaiting_customer")))
        .with_for_update(of=DeliveryAttempt, skip_locked=True)
        .execution_options(skip_tenant_filter=True)
    ).all()
    n = 0
    for att, hours in rows:
        if att.failed_at < now - timedelta(hours=int(hours)):
            att.recovery_status, att.escalated_at = "escalated", now
            n += 1
    return n


# ----------------------------------------------------------------------------- views
def shipment_view(
    db: Session, s: Shipment, *, detail: bool = False, order: Order | None = None
) -> dict[str, Any]:
    o = order or db.get(Order, s.order_id)
    a = _account(db, s)
    out: dict[str, Any] = {
        "id": s.id,
        "order_id": s.order_id,
        "order_number": o.number if o else None,
        "customer_name": o.ship_name if o else None,
        "direction": s.direction,
        "return_id": s.return_id,
        "destination_district": s.destination_district,
        "destination_district_name": _district_name(s.destination_district),
        "courier_account_id": s.courier_account_id,
        "provider": s.provider,
        "courier_name": s.courier_name or a.display_name,
        "manual": _is_manual(a),
        "service_code": s.service_code,
        "status": s.status,
        "tracking_number": s.tracking_number,
        "has_provider_label": bool(s.label_url),
        "weight_grams": s.weight_grams,
        "cod_amount": {"amount_minor": s.cod_amount_minor, "currency": s.currency},
        "charge": {"amount_minor": s.charge_minor, "currency": s.currency}
        if s.charge_minor is not None
        else None,
        "eta_days_min": s.eta_days_min,
        "eta_days_max": s.eta_days_max,
        "attempt_count": s.attempt_count,
        "pickup_reference": s.pickup_reference,
        "created_at": s.created_at,
        "pickup_requested_at": s.pickup_requested_at,
        "picked_up_at": s.picked_up_at,
        "delivered_at": s.delivered_at,
        "returned_at": s.returned_at,
        "return_received_at": s.return_received_at,
        "last_event_at": s.last_event_at,
        "stuck": s.status in LIVE_STATUSES and (s.last_event_at or s.created_at) < utcnow() - STUCK_AFTER,
        "actions": _actions(s, a),
    }
    if detail:
        events = db.scalars(
            select(ShipmentEvent)
            .where(ShipmentEvent.shipment_id == s.id)
            .order_by(ShipmentEvent.occurred_at, ShipmentEvent.id)
        )
        out["events"] = [
            {
                "id": e.id,
                "status": e.status,
                "raw_status": e.raw_status,
                "description": e.description,
                "location": e.location,
                "failure_reason": e.failure_reason,
                "source": e.source,
                "applied": e.applied,
                "occurred_at": e.occurred_at,
            }
            for e in events
        ]
        attempts = db.scalars(
            select(DeliveryAttempt)
            .where(DeliveryAttempt.shipment_id == s.id)
            .order_by(DeliveryAttempt.attempt_no)
        )
        out["attempts"] = [attempt_view(x) for x in attempts]
    return out


def _actions(s: Shipment, a: CourierAccount) -> list[str]:
    manual = _is_manual(a)
    acts: list[str] = []
    if s.status == "booked":
        acts.append("request_pickup")
    if s.status in CANCELLABLE:
        acts.append("cancel")
    if s.status == "delivery_failed":
        acts += ["reattempt", "return_to_sender"]
    if s.status == "reattempt_requested":
        acts.append("return_to_sender")
    if s.status == "returned_to_origin" and s.return_received_at is None:
        acts.append("confirm_received_back")
    if manual and s.status not in TERMINAL_STATUSES:
        acts += ["update_status", "set_tracking"]
    if not manual and CourierCapability.TRACKING.value in a.capabilities and s.status in LIVE_STATUSES:
        acts.append("refresh")
    return acts


def attempt_view(x: DeliveryAttempt) -> dict[str, Any]:
    return {
        "id": x.id,
        "attempt_no": x.attempt_no,
        "failure_reason": x.failure_reason,
        "failed_at": x.failed_at,
        "recovery_status": x.recovery_status,
        "customer_contacted_at": x.customer_contacted_at,
        "customer_reply": x.customer_reply,
        "customer_replied_at": x.customer_replied_at,
        "reattempt_requested_at": x.reattempt_requested_at,
        "reattempt_note": x.reattempt_note,
        "reattempt_by": x.reattempt_by,
        "escalated_at": x.escalated_at,
        "resolved_at": x.resolved_at,
        "resolution": x.resolution,
    }


BUCKETS: dict[str, tuple[str, ...]] = {
    "to_pickup": ("booked", "pickup_requested"),
    "in_transit": ("picked_up", "in_transit", "out_for_delivery", "reattempt_requested"),
    "attention": ("delivery_failed", "returning", "lost"),
    "delivered": ("delivered",),
    "returned": ("returned_to_origin",),
    "cancelled": ("cancelled",),
}


def counts(db: Session) -> dict[str, int]:
    rows = dict(db.execute(select(Shipment.status, func.count()).group_by(Shipment.status)).all())
    return {k: int(sum(rows.get(s, 0) for s in v)) for k, v in BUCKETS.items()}
