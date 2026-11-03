"""Inventory service (INV-001…009).

Every change goes through ``_apply``: lock the level row, check invariants, write one immutable ledger
entry, update the level, and publish ``inventory.level_changed`` (drives channel stock sync and
low-stock alerts). Reservations are idempotent per (reference, variant) so a retried order never
reserves twice, and they lock the level row so concurrent orders can't oversell.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements
from app.domains.catalog.models import Product, Variant
from app.domains.inventory.models import (
    InventoryLedgerEntry,
    InventoryLevel,
    InventoryLocation,
    InventoryReservation,
)
from app.domains.platform import outbox


class OutOfStock(Conflict):
    code = "out_of_stock"
    message = "Not enough stock"


# ----------------------------------------------------------------------------- locations
def default_location(db: Session, merchant_id: uuid.UUID) -> InventoryLocation:
    loc = db.scalar(
        select(InventoryLocation).where(
            InventoryLocation.merchant_id == merchant_id,
            InventoryLocation.is_default.is_(True),
            InventoryLocation.status == "active",
        )
    )
    if loc is not None:
        return loc
    db.execute(
        pg_insert(InventoryLocation)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            name="Main stock",
            code="main",
            is_default=True,
            status="active",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing()
    )
    loc = db.scalar(
        select(InventoryLocation).where(
            InventoryLocation.merchant_id == merchant_id, InventoryLocation.code == "main"
        )
    )
    assert loc is not None
    if loc.status != "active" or not loc.is_default:
        raise Conflict("No active default stock location", code="no_default_location")
    return loc


def create_location(db: Session, ctx: TenantContext, name: str, district: str | None) -> InventoryLocation:
    default_location(db, ctx.merchant_id)  # the first location always exists
    entitlements.require_feature(db, ctx.merchant_id, "inventory.multi_location")
    code = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "location"
    if db.scalar(select(InventoryLocation).where(InventoryLocation.code == code)):
        code = f"{code[:31]}-{uuid.uuid4().hex[:8]}"
    loc = InventoryLocation(merchant_id=ctx.merchant_id, name=name.strip(), code=code, district=district)
    db.add(loc)
    db.flush()
    audit.record(
        db,
        action="inventory.location_created",
        resource_type="inventory_location",
        resource_id=loc.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )
    return loc


def _location(db: Session, merchant_id: uuid.UUID, location_id: uuid.UUID | None) -> InventoryLocation:
    if location_id is None:
        return default_location(db, merchant_id)
    loc = db.get(InventoryLocation, location_id)
    if loc is None or loc.merchant_id != merchant_id or loc.status != "active":
        raise NotFound(code="location_not_found")
    return loc


def _variant(db: Session, merchant_id: uuid.UUID, variant_id: uuid.UUID) -> Variant:
    v = db.get(Variant, variant_id)
    if v is None or v.merchant_id != merchant_id:
        raise NotFound(code="variant_not_found")
    return v


# ----------------------------------------------------------------------------- core
def _level(
    db: Session, merchant_id: uuid.UUID, variant_id: uuid.UUID, location_id: uuid.UUID
) -> InventoryLevel:
    """Locked level row, created on first touch (that's what makes a variant 'tracked')."""
    db.flush()  # populate_existing below must not discard pending changes
    db.execute(
        pg_insert(InventoryLevel)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            variant_id=variant_id,
            location_id=location_id,
            on_hand=0,
            reserved=0,
            damaged=0,
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["variant_id", "location_id"])
    )
    lvl = db.scalar(
        select(InventoryLevel)
        .where(InventoryLevel.variant_id == variant_id, InventoryLevel.location_id == location_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert lvl is not None
    return lvl


def _apply(
    db: Session,
    actor: Actor,
    lvl: InventoryLevel,
    kind: str,
    *,
    on_hand: int = 0,
    reserved: int = 0,
    damaged: int = 0,
    reason: str | None = None,
    reference: tuple[str, str] | None = None,
    key: str | None = None,
) -> InventoryLedgerEntry | None:
    if key and db.scalar(
        select(InventoryLedgerEntry.id).where(
            InventoryLedgerEntry.merchant_id == lvl.merchant_id, InventoryLedgerEntry.idempotency_key == key
        )
    ):
        return None  # already applied (retry)
    before_available = lvl.available
    new_on_hand, new_reserved, new_damaged = (
        lvl.on_hand + on_hand,
        lvl.reserved + reserved,
        lvl.damaged + damaged,
    )
    if new_on_hand < 0 or new_damaged < 0:
        raise ValidationFailed("Stock can't go below zero", code="stock_negative")
    if new_reserved < 0:
        raise Conflict("Nothing reserved to release", code="reservation_underflow")
    if new_reserved > new_on_hand:
        raise OutOfStock(details={"variant_id": str(lvl.variant_id), "available": lvl.available})
    lvl.on_hand, lvl.reserved, lvl.damaged = new_on_hand, new_reserved, new_damaged
    entry = InventoryLedgerEntry(
        merchant_id=lvl.merchant_id,
        variant_id=lvl.variant_id,
        location_id=lvl.location_id,
        kind=kind,
        on_hand_delta=on_hand,
        reserved_delta=reserved,
        damaged_delta=damaged,
        on_hand_after=new_on_hand,
        reserved_after=new_reserved,
        reason=reason,
        reference_type=reference[0] if reference else None,
        reference_id=reference[1] if reference else None,
        actor_type=actor.type,
        actor_id=actor.id,
        idempotency_key=key,
    )
    db.add(entry)
    if lvl.available != before_available:
        low = (
            lvl.low_stock_threshold is not None
            and lvl.available <= lvl.low_stock_threshold < before_available
        )
        outbox.publish(
            db,
            event_type="inventory.level_changed",
            aggregate_type="variant",
            aggregate_id=lvl.variant_id,
            merchant_id=lvl.merchant_id,
            payload={
                "variant_id": str(lvl.variant_id),
                "location_id": str(lvl.location_id),
                "available": lvl.available,
                "low_stock": bool(low),
            },
        )
    return entry


# ----------------------------------------------------------------------------- seller operations
def receive(
    db: Session,
    ctx: TenantContext,
    variant_id: uuid.UUID,
    qty: int,
    *,
    location_id: uuid.UUID | None = None,
    reason: str | None = None,
    key: str | None = None,
) -> InventoryLevel:
    if qty <= 0:
        raise ValidationFailed("Quantity must be positive", code="quantity_invalid")
    _variant(db, ctx.merchant_id, variant_id)
    lvl = _level(db, ctx.merchant_id, variant_id, _location(db, ctx.merchant_id, location_id).id)
    _apply(db, ctx.actor, lvl, "receive", on_hand=qty, reason=reason, key=key)
    return lvl


def adjust(
    db: Session,
    ctx: TenantContext,
    variant_id: uuid.UUID,
    delta: int,
    reason: str,
    *,
    location_id: uuid.UUID | None = None,
    key: str | None = None,
) -> InventoryLevel:
    if delta == 0:
        raise ValidationFailed("Adjustment can't be zero", code="quantity_invalid")
    _variant(db, ctx.merchant_id, variant_id)
    lvl = _level(db, ctx.merchant_id, variant_id, _location(db, ctx.merchant_id, location_id).id)
    _apply(db, ctx.actor, lvl, "adjust", on_hand=delta, reason=reason, key=key)
    return lvl


def count(
    db: Session,
    ctx: TenantContext,
    variant_id: uuid.UUID,
    counted: int,
    *,
    location_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> InventoryLevel:
    """Stock count: set on-hand to what was physically counted (can't go below what's reserved)."""
    if counted < 0:
        raise ValidationFailed("Count can't be negative", code="quantity_invalid")
    _variant(db, ctx.merchant_id, variant_id)
    lvl = _level(db, ctx.merchant_id, variant_id, _location(db, ctx.merchant_id, location_id).id)
    delta = counted - lvl.on_hand
    if delta:
        _apply(db, ctx.actor, lvl, "count", on_hand=delta, reason=reason or "stock count")
    return lvl


def mark_damaged(
    db: Session,
    ctx: TenantContext,
    variant_id: uuid.UUID,
    qty: int,
    reason: str,
    *,
    location_id: uuid.UUID | None = None,
) -> InventoryLevel:
    if qty <= 0:
        raise ValidationFailed("Quantity must be positive", code="quantity_invalid")
    lvl = _level(db, ctx.merchant_id, variant_id, _location(db, ctx.merchant_id, location_id).id)
    _apply(db, ctx.actor, lvl, "damage", on_hand=-qty, damaged=qty, reason=reason)
    return lvl


def transfer(
    db: Session, ctx: TenantContext, variant_id: uuid.UUID, qty: int, from_id: uuid.UUID, to_id: uuid.UUID
) -> tuple[InventoryLevel, InventoryLevel]:
    if qty <= 0:
        raise ValidationFailed("Quantity must be positive", code="quantity_invalid")
    if from_id == to_id:
        raise ValidationFailed("Pick two different locations", code="same_location")
    src, dst = _location(db, ctx.merchant_id, from_id), _location(db, ctx.merchant_id, to_id)
    ref = ("transfer", str(uuid7()))
    # Lock in a fixed order (by location id) so two opposite transfers can't deadlock.
    first, second = sorted([src.id, dst.id], key=str)
    levels = {lid: _level(db, ctx.merchant_id, variant_id, lid) for lid in (first, second)}
    _apply(db, ctx.actor, levels[src.id], "transfer_out", on_hand=-qty, reference=ref)
    _apply(db, ctx.actor, levels[dst.id], "transfer_in", on_hand=qty, reference=ref)
    return levels[src.id], levels[dst.id]


def set_threshold(
    db: Session,
    ctx: TenantContext,
    variant_id: uuid.UUID,
    threshold: int | None,
    *,
    location_id: uuid.UUID | None = None,
) -> InventoryLevel:
    _variant(db, ctx.merchant_id, variant_id)
    lvl = _level(db, ctx.merchant_id, variant_id, _location(db, ctx.merchant_id, location_id).id)
    lvl.low_stock_threshold = threshold
    return lvl


# ----------------------------------------------------------------------------- reservations
def reserve(
    db: Session,
    merchant_id: uuid.UUID,
    actor: Actor,
    variant_id: uuid.UUID,
    qty: int,
    *,
    reference_type: str,
    reference_id: str,
    expires_at: datetime | None = None,
) -> InventoryReservation | None:
    """Reserve stock for an order line. Untracked variants (no stock recorded) return None.

    Picks the default location, else the location with the most available stock."""
    existing = db.scalar(
        select(InventoryReservation).where(
            InventoryReservation.merchant_id == merchant_id,
            InventoryReservation.reference_type == reference_type,
            InventoryReservation.reference_id == reference_id,
            InventoryReservation.variant_id == variant_id,
        )
    )
    if existing is not None and existing.status in ("active", "committed"):
        return existing
    levels = list(db.scalars(select(InventoryLevel).where(InventoryLevel.variant_id == variant_id)))
    if not levels:
        return None
    default = default_location(db, merchant_id)
    levels.sort(key=lambda lv: (lv.location_id != default.id, -lv.available))
    lvl = _level(db, merchant_id, variant_id, levels[0].location_id)
    if lvl.available < qty:
        total = sum(lv.available for lv in levels)
        raise OutOfStock(
            details={"variant_id": str(variant_id), "available": max(0, total), "requested": qty}
        )
    _apply(db, actor, lvl, "reserve", reserved=qty, reference=(reference_type, reference_id))
    if existing is not None:  # released earlier, reserved again (e.g. order re-confirmed)
        existing.status, existing.quantity, existing.location_id, existing.expires_at = (
            "active",
            qty,
            lvl.location_id,
            expires_at,
        )
        db.flush()
        return existing
    r = InventoryReservation(
        merchant_id=merchant_id,
        variant_id=variant_id,
        location_id=lvl.location_id,
        quantity=qty,
        reference_type=reference_type,
        reference_id=reference_id,
        expires_at=expires_at,
    )
    db.add(r)
    db.flush()
    return r


def _locked_reservation(db: Session, r: InventoryReservation) -> InventoryReservation:
    db.flush()  # populate_existing below must not discard pending changes to this row
    locked = db.scalar(
        select(InventoryReservation)
        .where(InventoryReservation.id == r.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert locked is not None
    return locked


def release(db: Session, actor: Actor, r: InventoryReservation, status: str = "released") -> None:
    r = _locked_reservation(db, r)
    if r.status != "active":
        return
    lvl = _level(db, r.merchant_id, r.variant_id, r.location_id)
    _apply(db, actor, lvl, "release", reserved=-r.quantity, reference=(r.reference_type, r.reference_id))
    r.status = status


def commit(db: Session, actor: Actor, r: InventoryReservation) -> None:
    """Goods left the shelf (shipped/handed over): on-hand and reserved both drop."""
    r = _locked_reservation(db, r)
    if r.status != "active":
        return
    lvl = _level(db, r.merchant_id, r.variant_id, r.location_id)
    _apply(
        db,
        actor,
        lvl,
        "commit",
        on_hand=-r.quantity,
        reserved=-r.quantity,
        reference=(r.reference_type, r.reference_id),
    )
    r.status = "committed"


def return_to_stock(db: Session, actor: Actor, r: InventoryReservation, qty: int | None = None) -> None:
    lvl = _level(db, r.merchant_id, r.variant_id, r.location_id)
    _apply(
        db,
        actor,
        lvl,
        "return_to_stock",
        on_hand=qty or r.quantity,
        reference=(r.reference_type, r.reference_id),
    )


def reservations_for(
    db: Session, merchant_id: uuid.UUID, reference_type: str, reference_id: str
) -> list[InventoryReservation]:
    return list(
        db.scalars(
            select(InventoryReservation).where(
                InventoryReservation.merchant_id == merchant_id,
                InventoryReservation.reference_type == reference_type,
                InventoryReservation.reference_id == reference_id,
            )
        )
    )


def release_expired(db: Session, limit: int = 200) -> int:
    rows = list(
        db.scalars(
            select(InventoryReservation)
            .where(InventoryReservation.status == "active", InventoryReservation.expires_at < utcnow())
            .limit(limit)
            .execution_options(skip_tenant_filter=True)
        )
    )
    for r in rows:
        release(db, Actor.system("inventory"), r, status="expired")
    return len(rows)


# ----------------------------------------------------------------------------- reads
@dataclass
class Availability:
    tracked: bool
    on_hand: int = 0
    reserved: int = 0
    available: int = 0
    as_of: datetime | None = None


def availability(
    db: Session, merchant_id: uuid.UUID, variant_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Availability]:
    out = {vid: Availability(tracked=False) for vid in variant_ids}
    if not variant_ids:
        return out
    rows = db.execute(
        select(
            InventoryLevel.variant_id,
            func.sum(InventoryLevel.on_hand),
            func.sum(InventoryLevel.reserved),
            func.max(InventoryLevel.updated_at),
        )
        .where(InventoryLevel.merchant_id == merchant_id, InventoryLevel.variant_id.in_(variant_ids))
        .group_by(InventoryLevel.variant_id)
    ).all()
    for vid, on_hand, reserved, as_of in rows:
        out[vid] = Availability(True, int(on_hand), int(reserved), int(on_hand) - int(reserved), as_of)
    return out


def product_stock(db: Session, ctx: TenantContext, product_id: uuid.UUID) -> dict[str, Any]:
    p = db.get(Product, product_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound(code="product_not_found")
    variants = list(
        db.scalars(
            select(Variant)
            .where(Variant.product_id == p.id, Variant.status == "active")
            .order_by(Variant.position)
        )
    )
    levels = list(
        db.scalars(select(InventoryLevel).where(InventoryLevel.variant_id.in_([v.id for v in variants])))
    )
    locs = {loc.id: loc for loc in db.scalars(select(InventoryLocation))}
    by_variant: dict[uuid.UUID, list[InventoryLevel]] = {}
    for lv in levels:
        by_variant.setdefault(lv.variant_id, []).append(lv)
    return {
        "product_id": p.id,
        "variants": [
            {
                "variant_id": v.id,
                "title": v.title,
                "sku": v.sku,
                "tracked": v.id in by_variant,
                "on_hand": sum(lv.on_hand for lv in by_variant.get(v.id, [])),
                "reserved": sum(lv.reserved for lv in by_variant.get(v.id, [])),
                "available": sum(lv.available for lv in by_variant.get(v.id, [])),
                "locations": [
                    {
                        "location_id": lv.location_id,
                        "location": locs[lv.location_id].name if lv.location_id in locs else None,
                        "on_hand": lv.on_hand,
                        "reserved": lv.reserved,
                        "damaged": lv.damaged,
                        "available": lv.available,
                        "low_stock_threshold": lv.low_stock_threshold,
                        "low": lv.low_stock_threshold is not None and lv.available <= lv.low_stock_threshold,
                    }
                    for lv in by_variant.get(v.id, [])
                ],
            }
            for v in variants
        ],
    }


def ledger(
    db: Session, ctx: TenantContext, variant_id: uuid.UUID, limit: int, cursor: str | None
) -> tuple[list[InventoryLedgerEntry], str | None]:
    from app.core.pagination import build_page, paginate_desc

    _variant(db, ctx.merchant_id, variant_id)
    stmt = select(InventoryLedgerEntry).where(InventoryLedgerEntry.variant_id == variant_id)
    rows = list(db.scalars(paginate_desc(stmt, InventoryLedgerEntry.id, limit, cursor)))
    return build_page(rows, limit)


def low_stock(
    db: Session, merchant_id: uuid.UUID, limit: int = 100
) -> list[tuple[InventoryLevel, Variant, Product]]:
    return list(
        db.execute(
            select(InventoryLevel, Variant, Product)
            .join(Variant, Variant.id == InventoryLevel.variant_id)
            .join(Product, Product.id == Variant.product_id)
            .where(
                InventoryLevel.merchant_id == merchant_id,
                InventoryLevel.low_stock_threshold.is_not(None),
                InventoryLevel.on_hand - InventoryLevel.reserved <= InventoryLevel.low_stock_threshold,
                Product.status != "archived",
                Variant.status == "active",
            )
            .limit(limit)
        ).all()
    )
