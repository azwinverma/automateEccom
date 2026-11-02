"""Internal operations console API (ADM-001/003/006/007/011 foundations). Staff + MFA session only.
Never returns secret values."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, request_meta, require_staff
from app.core.context import Actor
from app.core.errors import NotFound
from app.domains.ai.gateway import gateway
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements
from app.domains.merchants.models import Membership, Merchant
from app.domains.platform import outbox
from app.domains.platform.models import FeatureFlag, OutboxEvent

router = APIRouter(prefix="/admin", tags=["admin"])


def _staff_actor(p: Principal) -> Actor:
    return Actor(type="staff", id=p.user.id, display=p.user.email)


@router.get("/merchants")
def search_merchants(
    q: str | None = Query(None, max_length=100),
    limit: int = Query(25, ge=1, le=100),
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    stmt = select(Merchant).order_by(Merchant.created_at.desc()).limit(limit)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Merchant.name).like(like), func.lower(Merchant.slug).like(like)))
    return {
        "items": [
            {"id": m.id, "name": m.name, "slug": m.slug, "status": m.status, "created_at": m.created_at}
            for m in db.scalars(stmt)
        ]
    }


@router.get("/merchants/{merchant_id}")
def merchant_detail(
    merchant_id: uuid.UUID,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    m = db.get(Merchant, merchant_id)
    if m is None:
        raise NotFound()
    members = (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.merchant_id == merchant_id, Membership.status == "active")
        )
        or 0
    )
    ent = entitlements.resolve(db, merchant_id)
    return {
        "merchant": {
            "id": m.id,
            "name": m.name,
            "slug": m.slug,
            "status": m.status,
            "country": m.country,
            "currency": m.currency,
            "created_at": m.created_at,
        },
        "members": members,
        "plan": ent.plan_code,
        "subscription_status": ent.subscription.status if ent.subscription else None,
        "usage": entitlements.usage_summary(db, merchant_id),
        "credit_balance": entitlements.balance(db, merchant_id),
    }


@router.get("/ai/providers")
def ai_providers(p: Principal = Depends(require_staff)) -> dict:
    return {"items": gateway.provider_health()}


@router.get("/outbox")
def list_outbox(
    status: str = Query("dead", pattern="^(pending|dispatched|dead)$"),
    limit: int = Query(50, le=200),
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    rows = db.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.status == status)
        .order_by(OutboxEvent.created_at.desc())
        .limit(limit)
    )
    return {
        "items": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "merchant_id": e.merchant_id,
                "status": e.status,
                "attempts": e.attempts,
                "last_error": e.last_error,
                "created_at": e.created_at,
                "available_at": e.available_at,
            }
            for e in rows
        ]
    }


@router.post("/outbox/{event_id}/retry")
def retry_outbox(
    event_id: uuid.UUID,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    ev = outbox.requeue(db, event_id)
    audit.record(
        db,
        action="admin.outbox_replayed",
        resource_type="outbox_event",
        resource_id=ev.id,
        actor=_staff_actor(p),
        merchant_id=ev.merchant_id,
        meta=request_meta(request),
        metadata={"event_type": ev.event_type},
    )
    return {"id": ev.id, "status": ev.status}


@router.get("/feature-flags")
def list_flags(
    p: Principal = Depends(require_staff), db: Session = Depends(get_db, scope="function")
) -> dict:
    return {
        "items": [
            {
                "key": f.key,
                "description": f.description,
                "default_enabled": f.default_enabled,
                "rollout_percentage": f.rollout_percentage,
                "kill_switch": f.kill_switch,
            }
            for f in db.scalars(select(FeatureFlag).order_by(FeatureFlag.key))
        ]
    }


class FlagIn(BaseModel):
    description: str = Field(default="", max_length=500)
    default_enabled: bool = False
    rollout_percentage: int = Field(default=0, ge=0, le=100)
    kill_switch: bool = False


@router.put("/feature-flags/{key}")
def upsert_flag(
    key: str,
    body: FlagIn,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    f = db.get(FeatureFlag, key)
    before = None
    if f is None:
        f = FeatureFlag(key=key)
        db.add(f)
    else:
        before = {
            "default_enabled": f.default_enabled,
            "rollout_percentage": f.rollout_percentage,
            "kill_switch": f.kill_switch,
        }
    for k, v in body.model_dump().items():
        setattr(f, k, v)
    audit.record(
        db,
        action="admin.feature_flag_updated",
        resource_type="feature_flag",
        resource_id=key,
        actor=_staff_actor(p),
        merchant_id=None,
        meta=request_meta(request),
        changes=audit.diff(before or {}, body.model_dump(exclude={"description"})),
    )
    return {"key": key, **body.model_dump()}
