"""Customer identity resolution, addresses and duplicate merge (CRM-001…004, ORD-012).

Identity resolution: a channel identity (provider + external id) maps to one customer. When a phone
number becomes known (typed in chat, an order, an import), the identity joins the existing customer
with that phone instead of creating a duplicate. Merging moves everything owned by the source customer
to the target via registered merge hooks (orders, conversations…), and is audited.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.customers import nepal
from app.domains.customers.models import Customer, CustomerAddress, CustomerIdentity

MergeHook = Callable[[Session, uuid.UUID, uuid.UUID, uuid.UUID], None]  # (db, merchant, source, target)
MERGE_HOOKS: list[MergeHook] = []


def merge_hook(fn: MergeHook) -> MergeHook:
    """Other domains register how to re-point their rows when two customers are merged."""
    MERGE_HOOKS.append(fn)
    return fn


def _fields_error(errors: dict[str, str], prefix: str = "body") -> ValidationFailed:
    return ValidationFailed(
        details={"fields": [{"loc": [prefix, k], "type": v, "msg": v} for k, v in errors.items()]}
    )


def get_customer(db: Session, ctx: TenantContext, customer_id: uuid.UUID) -> Customer:
    c = db.get(Customer, customer_id)
    if c is None or c.merchant_id != ctx.merchant_id:
        raise NotFound(code="customer_not_found")
    if c.status == "merged" and c.merged_into_id:
        return get_customer(db, ctx, c.merged_into_id)
    return c


def by_phone(db: Session, merchant_id: uuid.UUID, phone: str | None) -> Customer | None:
    if not phone:
        return None
    return db.scalar(
        select(Customer).where(
            Customer.merchant_id == merchant_id, Customer.phone == phone, Customer.status == "active"
        )
    )


def create_customer(
    db: Session,
    ctx: TenantContext,
    *,
    display_name: str,
    phone: str | None = None,
    email: str | None = None,
    locale: str | None = None,
    notes: str | None = None,
) -> Customer:
    normalized = nepal.normalize_phone(phone) if phone else None
    if phone and normalized is None:
        raise _fields_error({"phone": "invalid_phone"})
    if by_phone(db, ctx.merchant_id, normalized):
        raise Conflict("A customer with this phone number already exists", code="customer_phone_exists")
    c = Customer(
        merchant_id=ctx.merchant_id,
        display_name=display_name.strip(),
        phone=normalized,
        email=email.lower().strip() if email else None,
        locale=locale,
        notes=notes,
        last_seen_at=utcnow(),
    )
    db.add(c)
    db.flush()
    audit.record(
        db,
        action="customers.customer_created",
        resource_type="customer",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )
    return c


def update_customer(
    db: Session, ctx: TenantContext, customer_id: uuid.UUID, fields: dict[str, Any]
) -> Customer:
    c = get_customer(db, ctx, customer_id)
    if "phone" in fields:
        raw = fields["phone"]
        normalized = nepal.normalize_phone(raw) if raw else None
        if raw and normalized is None:
            raise _fields_error({"phone": "invalid_phone"})
        other = by_phone(db, ctx.merchant_id, normalized)
        if other is not None and other.id != c.id:
            raise Conflict(
                "Another customer has this phone number; merge them instead",
                code="customer_phone_exists",
                details={"customer_id": str(other.id)},
            )
        fields["phone"] = normalized
    before = {k: getattr(c, k) for k in fields}
    for k, v in fields.items():
        setattr(c, k, v)
    audit.record(
        db,
        action="customers.customer_updated",
        resource_type="customer",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes=audit.diff(before, fields),
    )
    return c


def resolve_identity(
    db: Session,
    merchant_id: uuid.UUID,
    *,
    provider: str,
    external_id: str,
    display_name: str | None = None,
    phone: str | None = None,
) -> Customer:
    """Find or create the customer behind a channel identity. A known phone links to that customer."""
    ident = db.scalar(
        select(CustomerIdentity).where(
            CustomerIdentity.merchant_id == merchant_id,
            CustomerIdentity.provider == provider,
            CustomerIdentity.external_id == external_id,
        )
    )
    phone = nepal.normalize_phone(phone) if phone else None
    if ident is not None:
        c = db.get(Customer, ident.customer_id)
        assert c is not None
        if c.status == "merged" and c.merged_into_id:
            c = db.get(Customer, c.merged_into_id)
            assert c is not None
            ident.customer_id = c.id
        if phone and c.phone is None and by_phone(db, merchant_id, phone) is None:
            c.phone = phone
        c.last_seen_at = utcnow()
        return c
    c = by_phone(db, merchant_id, phone)
    if c is None:
        c = Customer(
            merchant_id=merchant_id,
            display_name=(display_name or "").strip() or "Customer",
            phone=phone,
            last_seen_at=utcnow(),
        )
        db.add(c)
        db.flush()
    db.add(
        CustomerIdentity(
            merchant_id=merchant_id,
            customer_id=c.id,
            provider=provider,
            external_id=external_id,
            display_name=display_name,
        )
    )
    db.flush()
    return c


def attach_phone(db: Session, ctx: TenantContext, customer: Customer, phone: str) -> Customer:
    """A phone learned later (e.g. typed in chat): if another customer owns it, merge into that one."""
    normalized = nepal.normalize_phone(phone)
    if normalized is None or customer.phone == normalized:
        return customer
    owner = by_phone(db, ctx.merchant_id, normalized)
    if owner is None:
        if customer.phone is None:
            customer.phone = normalized
        return customer
    if owner.id == customer.id:
        return customer
    return merge(db, ctx, source_id=customer.id, target_id=owner.id, reason="same_phone")


@dataclass
class AddressInput:
    recipient_name: str
    phone: str
    province: str
    district: str
    municipality: str
    ward: int
    area: str | None = None
    landmark: str | None = None
    label: str | None = None
    is_default: bool = False


def validate_address(data: AddressInput) -> tuple[dict[str, Any], float]:
    raw = {
        "recipient_name": data.recipient_name.strip(),
        "phone": data.phone,
        "province": (data.province or "").strip().lower(),
        "district": nepal.district_code(data.district) or (data.district or "").strip().lower(),
        "municipality": data.municipality.strip(),
        "ward": data.ward,
        "area": (data.area or "").strip() or None,
        "landmark": (data.landmark or "").strip() or None,
    }
    # The province can be derived from the district when it's missing (sellers often type only the district).
    if not raw["province"] and raw["district"] in nepal.DISTRICTS:
        raw["province"] = nepal.DISTRICTS[raw["district"]][1]
    check = nepal.check_address(raw)
    if not check.ok:
        raise _fields_error(check.errors)
    raw["phone"] = nepal.normalize_phone(str(raw["phone"]))
    return raw, check.completeness


def add_address(
    db: Session, ctx: TenantContext, customer_id: uuid.UUID, data: AddressInput
) -> CustomerAddress:
    c = get_customer(db, ctx, customer_id)
    clean, completeness = validate_address(data)
    has_any = db.scalar(
        select(func.count())
        .select_from(CustomerAddress)
        .where(CustomerAddress.customer_id == c.id, CustomerAddress.status == "active")
    )
    make_default = data.is_default or not has_any
    if make_default:
        db.execute(
            update(CustomerAddress).where(CustomerAddress.customer_id == c.id).values(is_default=False)
        )
    a = CustomerAddress(
        merchant_id=ctx.merchant_id,
        customer_id=c.id,
        label=data.label,
        completeness=completeness,
        is_default=make_default,
        **clean,
    )
    db.add(a)
    db.flush()
    return a


def archive_address(db: Session, ctx: TenantContext, customer_id: uuid.UUID, address_id: uuid.UUID) -> None:
    a = db.get(CustomerAddress, address_id)
    if (
        a is None
        or a.merchant_id != ctx.merchant_id
        or a.customer_id != get_customer(db, ctx, customer_id).id
    ):
        raise NotFound(code="address_not_found")
    a.status, a.is_default = "archived", False


def merge(
    db: Session, ctx: TenantContext, *, source_id: uuid.UUID, target_id: uuid.UUID, reason: str = "manual"
) -> Customer:
    if source_id == target_id:
        raise ValidationFailed("Pick two different customers", code="merge_same_customer")
    source, target = get_customer(db, ctx, source_id), get_customer(db, ctx, target_id)
    if source.id == target.id:
        return target
    for model in (CustomerIdentity, CustomerAddress):
        db.execute(update(model).where(model.customer_id == source.id).values(customer_id=target.id))
    for hook in MERGE_HOOKS:
        hook(db, ctx.merchant_id, source.id, target.id)
    if target.phone is None and source.phone:
        phone, source.phone = source.phone, None
        db.flush()
        target.phone = phone
    target.email = target.email or source.email
    target.tags = sorted(set(target.tags) | set(source.tags))
    source.status, source.merged_into_id = "merged", target.id
    audit.record(
        db,
        action="customers.customers_merged",
        resource_type="customer",
        resource_id=target.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"source_id": str(source.id), "reason": reason},
    )
    return target


SEGMENTS = ("new", "repeat", "inactive")
INACTIVE_AFTER_DAYS = 90


def search(
    db: Session, ctx: TenantContext, q: str | None, limit: int, cursor: str | None, segment: str | None = None
) -> tuple[list[Customer], str | None]:
    """CRM-013 segments (rule-based, from real orders): new = at most one non-cancelled order;
    repeat = 2+ orders; inactive = has ordered but nothing in the last 90 days."""
    from datetime import timedelta

    from app.core.pagination import build_page, paginate_desc
    from app.domains.orders.models import Order

    stmt = select(Customer).where(Customer.status == "active")
    if segment in SEGMENTS:
        live = (
            select(Order.customer_id, func.count().label("n"), func.max(Order.placed_at).label("last"))
            .where(Order.merchant_id == ctx.merchant_id, Order.status != "cancelled")
            .group_by(Order.customer_id)
            .subquery()
        )
        stmt = stmt.outerjoin(live, live.c.customer_id == Customer.id)
        if segment == "new":
            stmt = stmt.where(func.coalesce(live.c.n, 0) <= 1)
        elif segment == "repeat":
            stmt = stmt.where(live.c.n >= 2)
        else:
            stmt = stmt.where(live.c.last < utcnow() - timedelta(days=INACTIVE_AFTER_DAYS))
    if q:
        like = f"%{q.strip().lower()}%"
        digits = "".join(ch for ch in q if ch.isdigit())
        conds = [func.lower(Customer.display_name).like(like), func.lower(Customer.email).like(like)]
        if len(digits) >= 4:
            conds.append(Customer.phone.like(f"%{digits[-10:]}%"))
        stmt = stmt.where(or_(*conds))
    rows = list(db.scalars(paginate_desc(stmt, Customer.id, limit, cursor)))
    return build_page(rows, limit)


def address_view(a: CustomerAddress) -> dict[str, Any]:
    d = nepal.DISTRICTS.get(a.district)
    return {
        "id": a.id,
        "label": a.label,
        "recipient_name": a.recipient_name,
        "phone": a.phone,
        "province": a.province,
        "district": a.district,
        "district_name": d[0] if d else a.district,
        "municipality": a.municipality,
        "ward": a.ward,
        "area": a.area,
        "landmark": a.landmark,
        "completeness": a.completeness,
        "is_default": a.is_default,
    }


def customer_view(db: Session, c: Customer, detail: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": c.id,
        "display_name": c.display_name,
        "phone": c.phone,
        "email": c.email,
        "locale": c.locale,
        "tags": c.tags,
        "last_seen_at": c.last_seen_at,
        "created_at": c.created_at,
    }
    if detail:
        out["notes"] = c.notes
        out["identities"] = [
            {"provider": i.provider, "external_id": i.external_id, "display_name": i.display_name}
            for i in db.scalars(select(CustomerIdentity).where(CustomerIdentity.customer_id == c.id))
        ]
        out["addresses"] = [
            address_view(a)
            for a in db.scalars(
                select(CustomerAddress)
                .where(CustomerAddress.customer_id == c.id, CustomerAddress.status == "active")
                .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
            )
        ]
    return out
