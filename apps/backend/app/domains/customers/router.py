from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.domains.customers import nepal, service

router = APIRouter(tags=["customers"])


class CustomerIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=24)
    email: EmailStr | None = None
    locale: str | None = Field(default=None, pattern="^(en|ne)$")
    notes: str | None = Field(default=None, max_length=2000)


class CustomerPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=24)
    email: EmailStr | None = None
    locale: str | None = Field(default=None, pattern="^(en|ne)$")
    notes: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = Field(default=None, max_length=20)


class AddressIn(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=7, max_length=24)
    province: str = Field(default="", max_length=20)
    district: str = Field(min_length=2, max_length=30)
    municipality: str = Field(min_length=2, max_length=120)
    ward: int = Field(ge=1, le=nepal.MAX_WARD, strict=True)
    area: str | None = Field(default=None, max_length=160)
    landmark: str | None = Field(default=None, max_length=200)
    label: str | None = Field(default=None, max_length=40)
    is_default: bool = False


class MergeIn(BaseModel):
    source_id: uuid.UUID


@router.get("/reference/nepal")
def nepal_reference() -> dict[str, Any]:
    """Provinces and districts for address forms (public reference data)."""
    return {
        "provinces": [{"code": c, "name": n, "name_ne": ne} for c, (n, ne) in nepal.PROVINCES.items()],
        "districts": [{"code": c, "name": n, "province": p} for c, (n, p) in sorted(nepal.DISTRICTS.items())],
        "max_ward": nepal.MAX_WARD,
    }


@router.get("/customers")
def list_customers(
    q: str | None = Query(None, max_length=100),
    segment: str | None = Query(None, pattern="^(new|repeat|inactive)$"),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("customers.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    items, nxt = service.search(db, ctx, q, limit, cursor, segment)
    return {"items": [service.customer_view(db, c) for c in items], "next_cursor": nxt}


@router.post("/customers", status_code=201)
def create_customer(
    body: CustomerIn,
    ctx: TenantContext = Depends(require("customers.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    c = service.create_customer(db, ctx, **body.model_dump())
    return service.customer_view(db, c, detail=True)


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: uuid.UUID,
    ctx: TenantContext = Depends(require("customers.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.customer_view(db, service.get_customer(db, ctx, customer_id), detail=True)


@router.patch("/customers/{customer_id}")
def patch_customer(
    customer_id: uuid.UUID,
    body: CustomerPatch,
    ctx: TenantContext = Depends(require("customers.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    c = service.update_customer(db, ctx, customer_id, body.model_dump(exclude_unset=True))
    return service.customer_view(db, c, detail=True)


@router.post("/customers/{customer_id}/addresses", status_code=201)
def add_address(
    customer_id: uuid.UUID,
    body: AddressIn,
    ctx: TenantContext = Depends(require("customers.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.address_view(
        service.add_address(db, ctx, customer_id, service.AddressInput(**body.model_dump()))
    )


@router.delete("/customers/{customer_id}/addresses/{address_id}", status_code=204)
def archive_address(
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    ctx: TenantContext = Depends(require("customers.write")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.archive_address(db, ctx, customer_id, address_id)
    return Response(status_code=204)


@router.post("/customers/{customer_id}/merge")
def merge_customers(
    customer_id: uuid.UUID,
    body: MergeIn,
    ctx: TenantContext = Depends(require("customers.merge")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Merge ``source_id`` into this customer: identities, addresses, orders and chats move here."""
    c = service.merge(db, ctx, source_id=body.source_id, target_id=customer_id)
    return service.customer_view(db, c, detail=True)
