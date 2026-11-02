from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, get_principal, get_tenant, request_meta, require
from app.api.idempotent import run_idempotent
from app.core.context import TenantContext
from app.core.pagination import build_page, paginate_desc
from app.domains.accounts.models import User
from app.domains.merchants import service
from app.domains.merchants.models import Invitation, Membership, Merchant, Store
from app.domains.merchants.rbac import Role

router = APIRouter(tags=["merchants"])
_TZ = available_timezones()


class MerchantIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=64)
    country: str = Field(default="NP", pattern=r"^[A-Z]{2}$")
    currency: str = Field(default="NPR", pattern=r"^[A-Z]{3}$")
    timezone: str = "Asia/Kathmandu"
    default_locale: Literal["en", "ne"] = "ne"

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        if v not in _TZ:
            raise ValueError("unknown timezone")
        return v


class MerchantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    country: str
    currency: str
    timezone: str
    default_locale: str
    status: str
    automation_mode: str
    brand_tone: str
    brand_emoji: str
    brand_avoid_words: list[str]
    brand_sample_caption: str | None
    created_at: datetime

    @staticmethod
    def of(m: Merchant) -> MerchantOut:
        return MerchantOut(
            id=m.id,
            name=m.name,
            slug=m.slug,
            country=m.country,
            currency=m.currency,
            timezone=m.timezone,
            default_locale=m.default_locale,
            status=m.status,
            automation_mode=m.automation_mode,
            brand_tone=m.brand_tone,
            brand_emoji=m.brand_emoji,
            brand_avoid_words=m.brand_avoid_words,
            brand_sample_caption=m.brand_sample_caption,
            created_at=m.created_at,
        )


@router.post("/merchants", status_code=201, response_model=MerchantOut)
def create_merchant(
    body: MerchantIn,
    request: Request,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> MerchantOut:
    return run_idempotent(
        db,
        key=idem,
        owner=f"user:{p.user.id}",
        scope="merchants.create",
        body=body.model_dump(),
        status_code=201,
        fn=lambda: MerchantOut.of(
            service.create_merchant(
                db,
                owner=p.user,
                name=body.name,
                slug=body.slug,
                country=body.country,
                currency=body.currency,
                timezone=body.timezone,
                default_locale=body.default_locale,
                meta=request_meta(request),
            )
        ),
    )


@router.get("/merchant", response_model=MerchantOut)
def get_merchant(
    ctx: TenantContext = Depends(require("merchant.read")), db: Session = Depends(get_db, scope="function")
) -> MerchantOut:
    m = db.get(Merchant, ctx.merchant_id)
    assert m is not None
    return MerchantOut.of(m)


class MerchantPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    timezone: str | None = None
    default_locale: Literal["en", "ne"] | None = None
    automation_mode: Literal["assisted", "smart", "autopilot"] | None = None
    brand_tone: Literal["friendly", "premium", "playful", "minimal"] | None = None
    brand_emoji: Literal["none", "light", "lots"] | None = None
    brand_avoid_words: list[str] | None = Field(default=None, max_length=30)
    brand_sample_caption: str | None = Field(default=None, max_length=600)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        if v is not None and v not in _TZ:
            raise ValueError("unknown timezone")
        return v


@router.patch("/merchant", response_model=MerchantOut)
def patch_merchant(
    body: MerchantPatch,
    ctx: TenantContext = Depends(require("merchant.update")),
    db: Session = Depends(get_db, scope="function"),
) -> MerchantOut:
    if body.automation_mode == "autopilot":
        from app.domains.billing.service import entitlements

        entitlements.require_feature(db, ctx.merchant_id, "automation.autopilot")
    return MerchantOut.of(service.update_merchant(db, ctx, **body.model_dump(exclude_none=True)))


# ----------------------------------------------------------------------------- stores
class StoreOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    default_currency: str
    is_default: bool
    created_at: datetime

    @staticmethod
    def of(s: Store) -> StoreOut:
        return StoreOut(
            id=s.id,
            name=s.name,
            slug=s.slug,
            status=s.status,
            default_currency=s.default_currency,
            is_default=s.is_default,
            created_at=s.created_at,
        )


@router.get("/stores")
def list_stores(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("store.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    rows = list(db.scalars(paginate_desc(select(Store), Store.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {"items": [StoreOut.of(s) for s in items], "next_cursor": nxt}


class StoreIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=64)


@router.post("/stores", status_code=201, response_model=StoreOut)
def create_store(
    body: StoreIn,
    ctx: TenantContext = Depends(require("store.create")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StoreOut:
    return run_idempotent(
        db,
        key=idem,
        owner=f"merchant:{ctx.merchant_id}",
        scope="stores.create",
        body=body.model_dump(),
        status_code=201,
        fn=lambda: StoreOut.of(service.create_store(db, ctx, body.name, body.slug)),
    )


class StorePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: Literal["active", "archived"] | None = None


@router.patch("/stores/{store_id}", response_model=StoreOut)
def patch_store(
    store_id: uuid.UUID,
    body: StorePatch,
    ctx: TenantContext = Depends(require("store.update")),
    db: Session = Depends(get_db, scope="function"),
) -> StoreOut:
    return StoreOut.of(service.update_store(db, ctx, store_id, body.name, body.status))


# ----------------------------------------------------------------------------- team
class MemberUser(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str


class MemberOut(BaseModel):
    id: uuid.UUID
    user: MemberUser
    role: str
    status: str
    joined_at: datetime


@router.get("/members")
def list_members(
    ctx: TenantContext = Depends(require("team.read")), db: Session = Depends(get_db, scope="function")
) -> dict:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.status == "active")
        .order_by(Membership.created_at)
    ).all()
    return {
        "items": [
            MemberOut(
                id=m.id,
                user=MemberUser(id=u.id, email=u.email, full_name=u.full_name),
                role=m.role,
                status=m.status,
                joined_at=m.created_at,
            )
            for m, u in rows
        ]
    }


class RoleIn(BaseModel):
    role: Role


@router.patch("/members/{membership_id}")
def change_role(
    membership_id: uuid.UUID,
    body: RoleIn,
    ctx: TenantContext = Depends(require("team.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    m = service.change_member_role(db, ctx, membership_id, body.role.value)
    return {"id": m.id, "role": m.role}


@router.delete("/members/{membership_id}", status_code=204)
def remove_member(
    membership_id: uuid.UUID,
    ctx: TenantContext = Depends(require("team.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.remove_member(db, ctx, membership_id)
    return Response(status_code=204)


class InvitationIn(BaseModel):
    email: EmailStr
    role: Role


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    @staticmethod
    def of(i: Invitation) -> InvitationOut:
        return InvitationOut(
            id=i.id,
            email=i.email,
            role=i.role,
            status=i.status,
            expires_at=i.expires_at,
            created_at=i.created_at,
        )


@router.get("/invitations")
def list_invitations(
    ctx: TenantContext = Depends(require("team.manage")), db: Session = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(
        select(Invitation).where(Invitation.status == "pending").order_by(Invitation.created_at.desc())
    )
    return {"items": [InvitationOut.of(i) for i in rows]}


@router.post("/invitations", status_code=201, response_model=InvitationOut)
def create_invitation(
    body: InvitationIn,
    ctx: TenantContext = Depends(require("team.manage")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> InvitationOut:
    from app.core import ratelimit

    ratelimit.hit(f"invite:{ctx.merchant_id}", limit=50, window_seconds=3600)
    return run_idempotent(
        db,
        key=idem,
        owner=f"merchant:{ctx.merchant_id}",
        scope="invitations.create",
        body=body.model_dump(mode="json"),
        status_code=201,
        fn=lambda: InvitationOut.of(service.create_invitation(db, ctx, body.email, body.role.value)[0]),
    )


@router.delete("/invitations/{invitation_id}", status_code=204)
def revoke_invitation(
    invitation_id: uuid.UUID,
    ctx: TenantContext = Depends(require("team.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.revoke_invitation(db, ctx, invitation_id)
    return Response(status_code=204)


class AcceptIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


@router.post("/invitations/accept")
def accept_invitation(
    body: AcceptIn,
    request: Request,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    m = service.accept_invitation(db, p.user, body.token, request_meta(request))
    return {"membership": {"id": m.id, "merchant_id": m.merchant_id, "role": m.role}}


@router.get("/permissions/me")
def my_permissions(ctx: TenantContext = Depends(get_tenant)) -> dict:
    return {"role": ctx.role, "permissions": sorted(ctx.permissions)}
