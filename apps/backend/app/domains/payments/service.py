"""Payments (PAY-002…005, 008, 009).

* A client redirect is never trusted: an online payment counts only after ``verify`` asks the provider
  (``verify_payment``) and the confirmed amount equals the order total. Webhooks only trigger ``verify``.
* A mismatch (paid less or more) is held for the seller (``payment_mismatch`` exception), never
  auto-accepted.
* Sellers can record payments made outside Nivaro (bank transfer, eSewa/Khalti to their own account).
* A paid order moves to ready_to_ship automatically (R1, recorded as automated in the timeline).
* COD records follow the order: requested → approved → handed_to_courier → settlement_pending (cash
  with the courier after delivery) → settled (Phase 3 courier settlement).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.channels.models import WebhookEvent
from app.domains.integrations import registry
from app.domains.integrations.base import IntegrationError, Money, PaymentStatus
from app.domains.orders import service as orders
from app.domains.orders.models import Order
from app.domains.payments.models import CODRecord, Payment
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)
MANUAL_METHODS = ("bank_transfer", "esewa", "khalti", "fonepay", "cash", "other")


def _order(db: Session, ctx: TenantContext, order_id: uuid.UUID) -> Order:
    return orders.get_order(db, ctx, order_id, lock=True)


def _payment_confirmed(db: Session, ctx: TenantContext, o: Order, p: Payment) -> None:
    o.payment_status = "paid"
    orders._event(
        db,
        o,
        ctx.actor,
        "payment_recorded",
        provider=p.provider,
        payment_id=str(p.id),
        method=p.method,
        amount_minor=p.paid_minor,
    )
    if o.status == "payment_pending":
        orders.transition(
            db,
            TenantContext(merchant_id=o.merchant_id, actor=Actor.system("payments")),
            o.id,
            "ready_to_ship",
        )


# ----------------------------------------------------------------------------- online
def start_online_payment(
    db: Session, ctx: TenantContext, order_id: uuid.UUID, return_url: str | None
) -> Payment:
    o = _order(db, ctx, order_id)
    if o.payment_method != "prepaid" or o.status != "payment_pending":
        raise Conflict("This order isn't waiting for an online payment", code="payment_not_expected")
    if o.payment_status == "paid":
        raise Conflict("Already paid", code="already_paid")
    pending = db.scalar(
        select(Payment).where(Payment.order_id == o.id, Payment.kind == "online", Payment.status == "pending")
    )
    if pending is not None:
        return pending  # same link again (double tap, page refresh)
    code = get_settings().payment_provider
    try:
        if not code:
            raise registry.AdapterNotAvailable("no payment provider")
        adapter = registry.payment(code)
    except registry.AdapterNotAvailable as e:
        raise Conflict(
            "Online payments aren't set up yet. Record the payment yourself or switch to cash on delivery.",
            code="payment_provider_not_configured",
        ) from e
    attempt = (
        db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.order_id == o.id, Payment.kind == "online")
        )
        or 0
    ) + 1
    key = f"pay:{o.id}:{attempt}"
    try:
        res = adapter.create_payment(
            Money(o.total_minor, o.currency),
            reference=f"order-{o.number}",
            return_url=return_url,
            idempotency_key=key,
        )
    except IntegrationError as e:
        raise AppError(
            "The payment provider didn't respond. Try again shortly.", code="payment_provider_unavailable"
        ) from e
    p = Payment(
        merchant_id=o.merchant_id,
        order_id=o.id,
        kind="online",
        provider=code,
        method="wallet",
        status="pending",
        amount_minor=o.total_minor,
        currency=o.currency,
        provider_payment_id=res.provider_payment_id,
        redirect_url=res.redirect_url,
        idempotency_key=key,
    )
    db.add(p)
    db.flush()
    orders._event(db, o, ctx.actor, "payment_started", provider=code, payment_id=str(p.id))
    return p


def verify(db: Session, payment_id: uuid.UUID) -> Payment:
    """Ask the provider what really happened. Safe to call repeatedly (redirect, webhook, poll)."""
    p = db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if p is None:
        raise NotFound(code="payment_not_found")
    if p.status != "pending" or p.kind != "online" or not p.provider_payment_id:
        return p
    bind_tenant(db, p.merchant_id)
    ctx = TenantContext(merchant_id=p.merchant_id, actor=Actor.system("payments"))
    o = orders.get_order(db, ctx, p.order_id, lock=True)
    try:
        res = registry.payment(p.provider).verify_payment(
            p.provider_payment_id, Money(p.amount_minor, p.currency)
        )
    except IntegrationError as e:
        log.warning("payment_verify_failed", payment_id=str(p.id), error=e.code)
        return p  # stays pending; the next webhook/poll retries
    if res.status in (PaymentStatus.CAPTURED, PaymentStatus.AUTHORIZED):
        paid = res.amount.amount_minor if res.amount else None
        p.paid_minor, p.verified_at = paid, utcnow()
        if paid is None or paid != o.total_minor or (res.amount and res.amount.currency != o.currency):
            p.status, p.failure_code = "needs_review", "amount_mismatch"
            o.needs_review = "payment_mismatch"
            orders._event(
                db,
                o,
                ctx.actor,
                "payment_mismatch",
                provider=p.provider,
                expected_minor=o.total_minor,
                paid_minor=paid,
            )
            return p
        p.status = "paid"
        if o.status == "cancelled":
            o.needs_review = "paid_after_cancel"  # refund decision is the seller's (Phase 4 refunds)
            orders._event(db, o, ctx.actor, "payment_after_cancel", provider=p.provider, paid_minor=paid)
            return p
        _payment_confirmed(db, ctx, o, p)
    elif res.status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
        p.status, p.failure_code = "failed", res.raw_status or "payment_failed"
        if o.payment_status == "pending":
            o.payment_status = "failed"
        orders._event(
            db,
            o,
            ctx.actor,
            "payment_failed",
            provider=p.provider,
            payment_id=str(p.id),
            reason=p.failure_code,
        )
    return p


# ----------------------------------------------------------------------------- seller actions
def record_manual(
    db: Session,
    ctx: TenantContext,
    order_id: uuid.UUID,
    *,
    amount_minor: int,
    method: str,
    reference: str | None,
    key: str,
) -> Payment:
    o = _order(db, ctx, order_id)
    existing = db.scalar(select(Payment).where(Payment.idempotency_key == f"manual:{key}"))
    if existing is not None:
        return existing
    if o.payment_status == "paid":
        raise Conflict("Already paid", code="already_paid")
    if o.status in ("cancelled", "returned", "draft"):
        raise Conflict("This order can't take a payment", code="payment_not_expected")
    if method not in MANUAL_METHODS:
        raise ValidationFailed(code="payment_method_invalid")
    if amount_minor != o.total_minor:
        raise ValidationFailed(
            "The amount must match the order total",
            code="amount_mismatch",
            details={"total_minor": o.total_minor},
        )
    p = Payment(
        merchant_id=o.merchant_id,
        order_id=o.id,
        kind="manual",
        provider="manual",
        method=method,
        status="paid",
        amount_minor=amount_minor,
        paid_minor=amount_minor,
        currency=o.currency,
        reference=reference,
        idempotency_key=f"manual:{key}",
        verified_at=utcnow(),
        recorded_by_user_id=ctx.actor.id,
    )
    db.add(p)
    db.flush()
    for other in db.scalars(select(Payment).where(Payment.order_id == o.id, Payment.status == "pending")):
        other.status = "cancelled"
    if o.payment_method == "cod":  # paid in advance after all: no cash to collect
        o.payment_method = "prepaid"
        cod = db.scalar(select(CODRecord).where(CODRecord.order_id == o.id))
        if cod is not None and cod.status in ("requested", "approved"):
            cod.status = "cancelled"
        if o.status == "cod_pending":
            o.status = "payment_pending"
    if o.needs_review == "payment_mismatch":
        o.needs_review = None
    _payment_confirmed(db, ctx, o, p)
    audit.record(
        db,
        action="payments.manual_payment_recorded",
        resource_type="order",
        resource_id=o.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"method": method, "amount_minor": amount_minor, "reference": reference},
    )
    return p


def switch_to_cod(db: Session, ctx: TenantContext, order_id: uuid.UUID) -> Order:
    """A prepaid payment keeps failing: deliver it as cash on delivery instead (PAY-009)."""
    o = _order(db, ctx, order_id)
    if o.status != "payment_pending" or o.payment_status == "paid":
        raise Conflict(
            "Only unpaid orders waiting for payment can switch to cash on delivery",
            code="payment_not_expected",
        )
    for p in db.scalars(select(Payment).where(Payment.order_id == o.id, Payment.status == "pending")):
        p.status = "cancelled"
    before = o.status
    o.payment_method, o.payment_status, o.status = "cod", "cod_pending", "cod_pending"
    orders._event(
        db,
        o,
        ctx.actor,
        "status_changed",
        from_status=before,
        to_status="cod_pending",
        reason="switched_to_cod",
    )
    orders._publish(db, o, "orders.status_changed", from_status=before)
    return o


# ----------------------------------------------------------------------------- COD
_COD_FOR_STATUS = {
    "cod_pending": "requested",
    "ready_to_ship": "approved",
    "shipped": "handed_to_courier",
    "delivered": "settlement_pending",  # cash collected by the courier, owed to the seller
    "completed": "settlement_pending",
    "delivery_failed": "failed_delivery",
    "returned": "returned_to_origin",
    "cancelled": "cancelled",
}
_COD_FINAL = frozenset({"settled"})


@handler("orders.status_changed", name="payments.cod_follow_order")
def _cod_follow_order(db: Session, ev: OutboxEvent) -> None:
    o = db.scalar(
        select(Order)
        .where(Order.id == uuid.UUID(ev.payload["order_id"]))
        .execution_options(skip_tenant_filter=True)
    )
    if o is None or o.payment_method != "cod":
        return
    bind_tenant(db, o.merchant_id)
    target = _COD_FOR_STATUS.get(o.status)
    if target is None:
        return
    db.execute(
        pg_insert(CODRecord)
        .values(
            id=uuid7(),
            merchant_id=o.merchant_id,
            order_id=o.id,
            status="requested",
            amount_minor=o.total_minor,
            collected_minor=0,
            currency=o.currency,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["order_id"])
    )
    rec = db.scalar(select(CODRecord).where(CODRecord.order_id == o.id).with_for_update())
    assert rec is not None
    if rec.status in _COD_FINAL:
        return
    rec.amount_minor = o.total_minor  # partial cancels change what's collected
    rec.status = target
    rec.collected_minor = o.total_minor if target == "settlement_pending" else 0


def cod_summary(db: Session, ctx: TenantContext) -> dict[str, Any]:
    rows = db.execute(
        select(CODRecord.status, func.count(), func.coalesce(func.sum(CODRecord.amount_minor), 0)).group_by(
            CODRecord.status
        )
    ).all()
    by = {s: (int(n), int(total)) for s, n, total in rows}

    def bucket(*statuses: str) -> dict[str, int]:
        return {
            "count": sum(by.get(s, (0, 0))[0] for s in statuses),
            "amount_minor": sum(by.get(s, (0, 0))[1] for s in statuses),
        }

    return {
        "outstanding": bucket("requested", "approved", "handed_to_courier"),
        "pending_settlement": bucket("settlement_pending", "cash_collected", "delivered"),
        "settled": bucket("settled"),
        "failed_delivery": bucket("failed_delivery"),
        "return_exposure": bucket("returned_to_origin"),
    }


# ----------------------------------------------------------------------------- webhooks
def ingest_payment_webhook(
    db: Session, provider: str, headers: dict[str, str], body: bytes
) -> dict[str, int]:
    secret = get_settings().payment_webhook_secrets.get(provider)
    try:
        if secret is None:
            raise registry.AdapterNotAvailable(provider)
        adapter = registry.payment(provider, credentials={"webhook_secret": secret.get_secret_value()})
    except registry.AdapterNotAvailable as e:
        raise NotFound(code="provider_not_available") from e
    if not adapter.verify_webhook(headers, body):
        raise AppError("Invalid signature", code="webhook_signature_invalid")
    try:
        events = adapter.parse_webhook(headers, body)
    except (ValueError, KeyError) as e:
        raise ValidationFailed("Malformed webhook", code="webhook_malformed") from e
    stats = {"accepted": 0, "duplicates": 0}
    for ev in events:
        pid = str(ev.payload.get("payment_id", ""))
        p = db.scalar(
            select(Payment)
            .where(Payment.provider == provider, Payment.provider_payment_id == pid)
            .execution_options(skip_tenant_filter=True)
        )
        inserted = db.execute(
            pg_insert(WebhookEvent)
            .values(
                id=uuid7(),
                provider=provider,
                external_event_id=ev.external_event_id,
                event_type=ev.event_type,
                merchant_id=p.merchant_id if p else None,
                payload=ev.payload,
                status="received",
                received_at=utcnow(),
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
            merchant_id=p.merchant_id if p else None,
            payload={"webhook_event_id": str(inserted)},
        )
        stats["accepted"] += 1
    return stats


def _on_payment_webhook(db: Session, ev: WebhookEvent) -> None:
    p = db.scalar(
        select(Payment).where(
            Payment.provider == ev.provider,
            Payment.provider_payment_id == str(ev.payload.get("payment_id", "")),
        )
    )
    if p is not None:
        verify(db, p.id)  # the webhook body is a hint; the provider's answer is the truth


def _register() -> None:
    from app.domains.channels.service import webhook_handler

    for t in ("payment.succeeded", "payment.failed", "payment.updated"):
        webhook_handler(t)(_on_payment_webhook)


_register()


def payment_view(p: Payment) -> dict[str, Any]:
    return {
        "id": p.id,
        "order_id": p.order_id,
        "kind": p.kind,
        "provider": p.provider,
        "method": p.method,
        "status": p.status,
        "amount": {"amount_minor": p.amount_minor, "currency": p.currency},
        "paid_minor": p.paid_minor,
        "redirect_url": p.redirect_url if p.status == "pending" else None,
        "reference": p.reference,
        "failure_code": p.failure_code,
        "created_at": p.created_at,
        "verified_at": p.verified_at,
    }
