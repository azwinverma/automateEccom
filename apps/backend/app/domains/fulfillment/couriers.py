"""Courier accounts, fulfillment settings, the delivery-fee table and rule-based courier options.

Phase 3 recommendation is rules only (spec 05): the merchant's default courier when it can take the
parcel, otherwise the cheapest option that fits (COD-capable for COD orders). Courier Brain (route
learning) replaces the rules in Phase 6 and must keep the same response shape.
"""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.crypto import SealedSecret
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.customers import nepal
from app.domains.fulfillment.models import CourierAccount, DeliveryFeeRule, FulfillmentSettings
from app.domains.integrations import registry
from app.domains.integrations.base import (
    Address,
    CourierAdapter,
    CourierCapability,
    IntegrationError,
    Money,
)
from app.domains.merchants.models import Merchant
from app.domains.orders.models import Order

log = structlog.get_logger(__name__)

INSIDE_VALLEY = frozenset({"kathmandu", "lalitpur", "bhaktapur"})


# ----------------------------------------------------------------------------- accounts
def _aad(a: CourierAccount, kind: str) -> str:
    return f"courier:{a.merchant_id}:{a.id}:{kind}"


def adapter_for(a: CourierAccount) -> CourierAdapter:
    creds: dict[str, str] = {}
    if a.credentials_sealed:
        creds.update(json.loads(SealedSecret(a.credentials_sealed).open(_aad(a, "credentials"))))
    if a.webhook_secret_sealed:
        creds["webhook_secret"] = SealedSecret(a.webhook_secret_sealed).open(_aad(a, "webhook"))
    return registry.courier(a.provider, credentials=creds, config={"account_id": str(a.id)})


def webhook_secret(a: CourierAccount) -> str | None:
    return SealedSecret(a.webhook_secret_sealed).open(_aad(a, "webhook")) if a.webhook_secret_sealed else None


def get_account(db: Session, ctx: TenantContext, account_id: uuid.UUID) -> CourierAccount:
    a = db.get(CourierAccount, account_id)
    if a is None or a.merchant_id != ctx.merchant_id or a.status == "disconnected":
        raise NotFound(code="courier_not_found")
    return a


def live_accounts(db: Session) -> list[CourierAccount]:
    return list(
        db.scalars(
            select(CourierAccount)
            .where(CourierAccount.status != "disconnected")
            .order_by(CourierAccount.is_default.desc(), CourierAccount.created_at)
        )
    )


@dataclass
class PickupInput:
    name: str | None = None
    phone: str | None = None
    district: str | None = None
    municipality: str | None = None
    area: str | None = None


def _apply_pickup(a: CourierAccount, p: PickupInput) -> None:
    district = nepal.district_code(p.district) if p.district else None
    if p.district and district is None:
        raise ValidationFailed(code="address_invalid", details={"fields": {"district": "unknown"}})
    phone = nepal.normalize_phone(p.phone) if p.phone else None
    if p.phone and phone is None:
        raise ValidationFailed(code="address_invalid", details={"fields": {"phone": "invalid"}})
    a.pickup_name, a.pickup_phone, a.pickup_district = p.name, phone, district
    a.pickup_municipality, a.pickup_area = p.municipality, p.area


def _make_default(db: Session, a: CourierAccount) -> None:
    db.execute(
        update(CourierAccount)
        .where(CourierAccount.merchant_id == a.merchant_id, CourierAccount.id != a.id)
        .values(is_default=False)
    )
    db.flush()
    a.is_default = True


def connect(
    db: Session,
    ctx: TenantContext,
    provider: str,
    display_name: str | None,
    credentials: dict[str, str],
    pickup: PickupInput,
    make_default: bool,
) -> CourierAccount:
    try:
        cls_adapter = registry.courier(provider)
    except registry.AdapterNotAvailable as e:
        raise NotFound(code="provider_not_available") from e
    missing = [f for f in cls_adapter.auth_fields if not credentials.get(f)]
    if missing:
        raise ValidationFailed(code="credentials_missing", details={"fields": missing})
    a = CourierAccount(
        id=uuid7(),
        merchant_id=ctx.merchant_id,
        provider=provider,
        display_name=(display_name or cls_adapter.display_name)[:120],
        capabilities=sorted(c.value for c in cls_adapter.capabilities),
        connected_by_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
    )
    _apply_pickup(a, pickup)
    known = {k: v for k, v in credentials.items() if k in cls_adapter.auth_fields}
    if known:
        a.credentials_sealed = SealedSecret.seal(json.dumps(known), _aad(a, "credentials")).blob
    if CourierCapability.WEBHOOKS in cls_adapter.capabilities:
        a.webhook_secret_sealed = SealedSecret.seal(secrets.token_urlsafe(32), _aad(a, "webhook")).blob
    try:
        adapter_for(a).verify_credentials()
    except IntegrationError as e:
        raise ValidationFailed(
            "The courier rejected these details",
            code="courier_credentials_invalid",
            details={"error": e.code},
        ) from e
    db.add(a)
    db.flush()
    has_default = db.scalar(
        select(CourierAccount.id).where(
            CourierAccount.is_default.is_(True),
            CourierAccount.status != "disconnected",
            CourierAccount.id != a.id,
        )
    )
    if make_default or has_default is None:
        _make_default(db, a)
    audit.record(
        db,
        action="fulfillment.courier_connected",
        resource_type="courier_account",
        resource_id=a.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": provider},
    )
    return a


def update_account(
    db: Session,
    ctx: TenantContext,
    account_id: uuid.UUID,
    *,
    display_name: str | None,
    pickup: PickupInput | None,
    make_default: bool | None,
) -> CourierAccount:
    a = get_account(db, ctx, account_id)
    if display_name:
        a.display_name = display_name[:120]
    if pickup is not None:
        _apply_pickup(a, pickup)
    if make_default:
        _make_default(db, a)
    return a


def disconnect(db: Session, ctx: TenantContext, account_id: uuid.UUID) -> None:
    from app.domains.fulfillment.models import LIVE_STATUSES, Shipment

    a = get_account(db, ctx, account_id)
    live = db.scalar(
        select(Shipment.id)
        .where(Shipment.courier_account_id == a.id, Shipment.status.in_(LIVE_STATUSES))
        .limit(1)
    )
    if live is not None:
        raise Conflict(
            "This courier still has parcels on the way. Finish or cancel them first.",
            code="courier_has_live_shipments",
        )
    a.status, a.is_default, a.disconnected_at = "disconnected", False, utcnow()
    a.credentials_sealed = a.webhook_secret_sealed = None
    audit.record(
        db,
        action="fulfillment.courier_disconnected",
        resource_type="courier_account",
        resource_id=a.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )


def account_view(a: CourierAccount, base_url: str | None = None) -> dict[str, Any]:
    return {
        "id": a.id,
        "provider": a.provider,
        "display_name": a.display_name,
        "status": a.status,
        "is_default": a.is_default,
        "capabilities": a.capabilities,
        "manual": CourierCapability.MANUAL_UPDATES.value in a.capabilities,
        "pickup": {
            "name": a.pickup_name,
            "phone": a.pickup_phone,
            "district": a.pickup_district,
            "district_name": nepal.DISTRICTS[a.pickup_district][0]
            if a.pickup_district in nepal.DISTRICTS
            else None,
            "municipality": a.pickup_municipality,
            "area": a.pickup_area,
        },
        "pickup_complete": bool(a.pickup_name and a.pickup_phone and a.pickup_district),
        "webhook_path": f"/webhooks/couriers/{a.provider}/{a.id}" if a.webhook_secret_sealed else None,
        "last_error_code": a.last_error_code,
        "created_at": a.created_at,
    }


# ----------------------------------------------------------------------------- settings
def get_settings_row(db: Session, merchant_id: uuid.UUID) -> FulfillmentSettings:
    row = db.scalar(select(FulfillmentSettings).where(FulfillmentSettings.merchant_id == merchant_id))
    if row is not None:
        return row
    db.execute(
        pg_insert(FulfillmentSettings)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            notify_customers=True,
            default_weight_grams=500,
            recovery_wait_hours=24,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["merchant_id"])
    )
    row = db.scalar(select(FulfillmentSettings).where(FulfillmentSettings.merchant_id == merchant_id))
    assert row is not None
    return row


def settings_view(s: FulfillmentSettings) -> dict[str, Any]:
    return {
        "notify_customers": s.notify_customers,
        "default_weight_grams": s.default_weight_grams,
        "recovery_wait_hours": s.recovery_wait_hours,
    }


# ----------------------------------------------------------------------------- delivery fees
@dataclass
class FeeRuleInput:
    scope: str
    fee_minor: int
    district: str | None = None
    free_over_minor: int | None = None


def fee_rules(db: Session) -> list[DeliveryFeeRule]:
    order = {"default": 0, "inside_valley": 1, "district": 2}
    rows = list(db.scalars(select(DeliveryFeeRule)))
    return sorted(rows, key=lambda r: (order[r.scope], r.district or ""))


def replace_fee_rules(db: Session, ctx: TenantContext, rules: list[FeeRuleInput]) -> list[DeliveryFeeRule]:
    m = db.get(Merchant, ctx.merchant_id)
    assert m is not None
    seen: set[tuple[str, str | None]] = set()
    clean: list[DeliveryFeeRule] = []
    for i, r in enumerate(rules):
        district = None
        if r.scope == "district":
            district = nepal.district_code(r.district or "")
            if district is None:
                raise ValidationFailed(
                    code="address_invalid", details={"index": i, "fields": {"district": "unknown"}}
                )
        key = (r.scope, district)
        if key in seen:
            raise ValidationFailed(
                "Each area can have one rule", code="fee_rule_duplicate", details={"index": i}
            )
        seen.add(key)
        clean.append(
            DeliveryFeeRule(
                merchant_id=ctx.merchant_id,
                scope=r.scope,
                district=district,
                fee_minor=r.fee_minor,
                free_over_minor=r.free_over_minor,
                currency=m.currency,
            )
        )
    for old in db.scalars(select(DeliveryFeeRule)):
        db.delete(old)
    db.flush()
    db.add_all(clean)
    audit.record(
        db,
        action="fulfillment.delivery_fees_updated",
        resource_type="merchant",
        resource_id=ctx.merchant_id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"rules": len(clean)},
    )
    return clean


def quote_fee(db: Session, district: str | None, subtotal_minor: int = 0) -> dict[str, Any] | None:
    """What to charge the customer for delivery. None when the merchant hasn't set a fee table."""
    rules = {(r.scope, r.district): r for r in fee_rules(db)}
    if not rules:
        return None
    code = nepal.district_code(district) if district else None
    rule = (
        rules.get(("district", code))
        or (rules.get(("inside_valley", None)) if code in INSIDE_VALLEY else None)
        or rules.get(("default", None))
    )
    if rule is None:
        return None
    free = rule.free_over_minor is not None and subtotal_minor >= rule.free_over_minor
    return {
        "fee_minor": 0 if free else rule.fee_minor,
        "currency": rule.currency,
        "rule": rule.scope,
        "district": code,
        "free_delivery": free,
        "free_over_minor": rule.free_over_minor,
    }


def fee_rule_view(r: DeliveryFeeRule) -> dict[str, Any]:
    return {
        "scope": r.scope,
        "district": r.district,
        "district_name": nepal.DISTRICTS[r.district][0] if r.district in nepal.DISTRICTS else None,
        "fee_minor": r.fee_minor,
        "free_over_minor": r.free_over_minor,
        "currency": r.currency,
    }


# ----------------------------------------------------------------------------- addresses
def origin_address(a: CourierAccount) -> Address:
    return Address(
        name=a.pickup_name or "",
        phone=a.pickup_phone or "",
        line1=", ".join(x for x in (a.pickup_area, a.pickup_municipality) if x),
        city=a.pickup_municipality or "",
        district=a.pickup_district,
        province=nepal.DISTRICTS[a.pickup_district][1] if a.pickup_district in nepal.DISTRICTS else None,
        area=a.pickup_area,
    )


def destination_address(o: Order) -> Address:
    muni = o.ship_municipality or ""
    line1 = ", ".join(
        str(x) for x in (o.ship_area, f"{muni}-{o.ship_ward}" if muni and o.ship_ward else muni) if x
    ) or (o.ship_text or "")
    return Address(
        name=o.ship_name or "",
        phone=o.ship_phone or "",
        line1=line1,
        city=muni,
        district=o.ship_district,
        province=o.ship_province,
        area=o.ship_area,
        landmark=o.ship_landmark,
    )


def cod_due(o: Order) -> int:
    """Cash the courier must collect: the order total for unpaid COD orders, else nothing."""
    return o.total_minor if o.payment_method == "cod" and o.payment_status in ("cod_pending", "unpaid") else 0


# ----------------------------------------------------------------------------- options (FUL-002)
def courier_options(db: Session, ctx: TenantContext, o: Order, weight_grams: int) -> dict[str, Any]:
    cod_minor = cod_due(o)
    dest = destination_address(o)
    options: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    for a in live_accounts(db):
        base = {
            "courier_account_id": a.id,
            "provider": a.provider,
            "display_name": a.display_name,
            "is_default": a.is_default,
        }
        if CourierCapability.MANUAL_UPDATES.value in a.capabilities:
            options.append(
                {
                    **base,
                    "service_code": None,
                    "price": None,
                    "eta_days_min": None,
                    "eta_days_max": None,
                    "cod_supported": True,
                    "manual": True,
                }
            )
            continue
        if not (a.pickup_name and a.pickup_phone and a.pickup_district):
            unavailable.append({**base, "reason": "pickup_address_missing"})
            continue
        if not o.ship_district:
            unavailable.append({**base, "reason": "address_incomplete"})
            continue
        try:
            quotes = adapter_for(a).get_rates(
                origin_address(a), dest, weight_grams, Money(cod_minor, o.currency) if cod_minor else None
            )
        except IntegrationError as e:
            log.warning("courier_rates_failed", provider=a.provider, error=e.code)
            unavailable.append({**base, "reason": "courier_unavailable"})
            continue
        for q in quotes:
            if cod_minor and not q.cod_supported:
                continue
            options.append(
                {
                    **base,
                    "service_code": q.service_code,
                    "price": {"amount_minor": q.price.amount_minor, "currency": q.price.currency},
                    "eta_days_min": q.eta_days_min,
                    "eta_days_max": q.eta_days_max,
                    "cod_supported": q.cod_supported,
                    "manual": False,
                }
            )
    priced = [x for x in options if x["price"] is not None]
    pick: dict[str, Any] | None = None
    reason: str | None = None
    default_priced = sorted((x for x in priced if x["is_default"]), key=lambda x: x["price"]["amount_minor"])
    if default_priced:
        pick, reason = default_priced[0], "default_courier"
    elif priced:
        pick = min(priced, key=lambda x: (x["price"]["amount_minor"], x["eta_days_max"] or 99))
        reason = "only_option" if len(priced) == 1 else "cheapest"
    elif options:
        pick, reason = options[0], "only_option" if len(options) == 1 else "default_courier"
    for x in options:
        x["recommended"] = x is pick
    return {
        "weight_grams": weight_grams,
        "cod_amount_minor": cod_minor,
        "options": options,
        "unavailable": unavailable,
        "recommendation": (
            {
                "courier_account_id": pick["courier_account_id"],
                "service_code": pick["service_code"],
                "reason": reason,
                "method": "rules",  # Courier Brain (Phase 6) will say "route_history"
            }
            if pick
            else None
        ),
    }
