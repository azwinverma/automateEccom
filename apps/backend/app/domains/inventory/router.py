from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.domains.inventory import service
from app.domains.inventory.models import InventoryLedgerEntry, InventoryLevel, InventoryLocation

router = APIRouter(tags=["inventory"])

Qty = Field(gt=0, le=1_000_000, strict=True)


class LocationIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    district: str | None = Field(default=None, max_length=30)


class ReceiveIn(BaseModel):
    quantity: int = Qty
    location_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=300)


class AdjustIn(BaseModel):
    delta: int = Field(ge=-1_000_000, le=1_000_000, strict=True)
    reason: str = Field(min_length=2, max_length=300)
    location_id: uuid.UUID | None = None


class CountIn(BaseModel):
    counted: int = Field(ge=0, le=1_000_000, strict=True)
    location_id: uuid.UUID | None = None


class DamageIn(BaseModel):
    quantity: int = Qty
    reason: str = Field(min_length=2, max_length=300)
    location_id: uuid.UUID | None = None


class TransferIn(BaseModel):
    quantity: int = Qty
    from_location_id: uuid.UUID
    to_location_id: uuid.UUID


class ThresholdIn(BaseModel):
    threshold: int | None = Field(default=None, ge=0, le=1_000_000, strict=True)
    location_id: uuid.UUID | None = None


def level_view(lv: InventoryLevel) -> dict[str, Any]:
    return {
        "variant_id": lv.variant_id,
        "location_id": lv.location_id,
        "on_hand": lv.on_hand,
        "reserved": lv.reserved,
        "damaged": lv.damaged,
        "available": lv.available,
        "low_stock_threshold": lv.low_stock_threshold,
    }


def location_view(loc: InventoryLocation) -> dict[str, Any]:
    return {
        "id": loc.id,
        "name": loc.name,
        "code": loc.code,
        "district": loc.district,
        "is_default": loc.is_default,
    }


@router.get("/inventory/locations")
def locations(
    ctx: TenantContext = Depends(require("inventory.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    service.default_location(db, ctx.merchant_id)
    rows = db.scalars(
        select(InventoryLocation)
        .where(InventoryLocation.status == "active")
        .order_by(InventoryLocation.is_default.desc(), InventoryLocation.name)
    )
    return {"items": [location_view(loc) for loc in rows]}


@router.post("/inventory/locations", status_code=201)
def create_location(
    body: LocationIn,
    ctx: TenantContext = Depends(require("inventory.transfer")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return location_view(service.create_location(db, ctx, body.name, body.district))


@router.get("/catalog/products/{product_id}/stock")
def product_stock(
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inventory.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.product_stock(db, ctx, product_id)


@router.post("/inventory/variants/{variant_id}/receive")
def receive(
    variant_id: uuid.UUID,
    body: ReceiveIn,
    ctx: TenantContext = Depends(require("inventory.adjust")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key = f"receive:{idem}" if idem else None
    return level_view(
        service.receive(
            db, ctx, variant_id, body.quantity, location_id=body.location_id, reason=body.reason, key=key
        )
    )


@router.post("/inventory/variants/{variant_id}/adjust")
def adjust(
    variant_id: uuid.UUID,
    body: AdjustIn,
    ctx: TenantContext = Depends(require("inventory.adjust")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key = f"adjust:{idem}" if idem else None
    return level_view(
        service.adjust(db, ctx, variant_id, body.delta, body.reason, location_id=body.location_id, key=key)
    )


@router.post("/inventory/variants/{variant_id}/count")
def count(
    variant_id: uuid.UUID,
    body: CountIn,
    ctx: TenantContext = Depends(require("inventory.adjust")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return level_view(service.count(db, ctx, variant_id, body.counted, location_id=body.location_id))


@router.post("/inventory/variants/{variant_id}/damage")
def damage(
    variant_id: uuid.UUID,
    body: DamageIn,
    ctx: TenantContext = Depends(require("inventory.adjust")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return level_view(
        service.mark_damaged(db, ctx, variant_id, body.quantity, body.reason, location_id=body.location_id)
    )


@router.post("/inventory/variants/{variant_id}/transfer")
def transfer(
    variant_id: uuid.UUID,
    body: TransferIn,
    ctx: TenantContext = Depends(require("inventory.transfer")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    src, dst = service.transfer(
        db, ctx, variant_id, body.quantity, body.from_location_id, body.to_location_id
    )
    return {"from": level_view(src), "to": level_view(dst)}


@router.put("/inventory/variants/{variant_id}/threshold")
def threshold(
    variant_id: uuid.UUID,
    body: ThresholdIn,
    ctx: TenantContext = Depends(require("inventory.adjust")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return level_view(
        service.set_threshold(db, ctx, variant_id, body.threshold, location_id=body.location_id)
    )


@router.get("/inventory/variants/{variant_id}/ledger")
def ledger(
    variant_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("inventory.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    rows, nxt = service.ledger(db, ctx, variant_id, limit, cursor)

    def view(e: InventoryLedgerEntry) -> dict[str, Any]:
        return {
            "id": e.id,
            "kind": e.kind,
            "location_id": e.location_id,
            "on_hand_delta": e.on_hand_delta,
            "reserved_delta": e.reserved_delta,
            "damaged_delta": e.damaged_delta,
            "on_hand_after": e.on_hand_after,
            "reserved_after": e.reserved_after,
            "reason": e.reason,
            "reference": {"type": e.reference_type, "id": e.reference_id} if e.reference_type else None,
            "actor_type": e.actor_type,
            "created_at": e.created_at,
        }

    return {"items": [view(e) for e in rows], "next_cursor": nxt}


@router.get("/inventory/low-stock")
def low_stock(
    ctx: TenantContext = Depends(require("inventory.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return {
        "items": [
            {
                "product_id": p.id,
                "product_title": p.title,
                "variant_id": v.id,
                "variant_title": v.title,
                "sku": v.sku,
                **level_view(lv),
            }
            for lv, v, p in service.low_stock(db, ctx.merchant_id)
        ]
    }
