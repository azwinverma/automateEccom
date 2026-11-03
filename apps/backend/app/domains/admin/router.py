"""Internal operations console API (ADM-001/003/006/007/011 foundations). Staff + MFA session only.
Never returns secret values."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, request_meta, require_staff
from app.core.context import Actor
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.pagination import build_page, paginate_desc
from app.domains.accounts.models import User
from app.domains.ai.gateway import gateway
from app.domains.audit import service as audit
from app.domains.audit.models import AuditLog
from app.domains.billing.models import EntitlementOverride, MeteredResource
from app.domains.billing.service import entitlements
from app.domains.channels.models import ChannelConnection
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


def _merchant_or_404(db: Session, merchant_id: uuid.UUID) -> Merchant:
    m = db.get(Merchant, merchant_id)
    if m is None:
        raise NotFound()
    return m


def _override_view(o: EntitlementOverride) -> dict:
    return {
        "id": o.id,
        "resource_code": o.resource_code,
        "feature_code": o.feature_code,
        "enabled": o.enabled,
        "period": o.period,
        "limit_value": o.limit_value,
        "reason": o.reason,
        "expires_at": o.expires_at,
        "created_at": o.created_at,
        "active": o.expires_at is None or o.expires_at > utcnow(),
    }


@router.get("/merchants/{merchant_id}")
def merchant_detail(
    merchant_id: uuid.UUID,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    m = _merchant_or_404(db, merchant_id)
    member_rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.merchant_id == merchant_id)
        .order_by(Membership.created_at)
        .execution_options(skip_tenant_filter=True)
    ).all()
    connections = db.scalars(
        select(ChannelConnection)
        .where(ChannelConnection.merchant_id == merchant_id, ChannelConnection.status != "disconnected")
        .order_by(ChannelConnection.created_at)
        .execution_options(skip_tenant_filter=True)
    )
    overrides = db.scalars(
        select(EntitlementOverride)
        .where(EntitlementOverride.merchant_id == merchant_id)
        .order_by(EntitlementOverride.created_at.desc())
        .execution_options(skip_tenant_filter=True)
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
            "timezone": m.timezone,
            "default_locale": m.default_locale,
            "created_at": m.created_at,
        },
        "members": sum(1 for mb, _ in member_rows if mb.status == "active"),
        "team": [
            {
                "user_id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": mb.role,
                "status": mb.status,
                "mfa_enabled": u.mfa_enabled,
                "last_login_at": u.last_login_at,
            }
            for mb, u in member_rows
        ],
        "plan": ent.plan_code,
        "subscription_status": ent.subscription.status if ent.subscription else None,
        "usage": entitlements.usage_summary(db, merchant_id),
        "credit_balance": entitlements.balance(db, merchant_id),
        "connections": [
            {
                "id": c.id,
                "provider": c.provider,
                "display_name": c.display_name,
                "status": c.status,
                "last_healthy_at": c.last_healthy_at,
                "last_error_code": c.last_error_code,
                "consecutive_failures": c.consecutive_failures,
                "token_expires_at": c.token_expires_at,
            }
            for c in connections
        ],
        "overrides": [_override_view(o) for o in overrides],
    }


class StatusIn(BaseModel):
    status: Literal["active", "suspended"]
    reason: str = Field(min_length=5, max_length=300)


@router.post("/merchants/{merchant_id}/status")
def set_merchant_status(
    merchant_id: uuid.UUID,
    body: StatusIn,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    """Suspend (every seller request then gets 403 merchant_suspended) or reactivate a shop."""
    m = _merchant_or_404(db, merchant_id)
    if m.status == "closed":
        raise Conflict("A closed shop can't be changed here", code="merchant_closed")
    before = m.status
    m.status = body.status
    audit.record(
        db,
        action="admin.merchant_status_changed",
        resource_type="merchant",
        resource_id=m.id,
        actor=_staff_actor(p),
        merchant_id=m.id,
        meta=request_meta(request),
        changes={"status": {"from": before, "to": body.status}},
        metadata={"reason": body.reason},
    )
    return {"id": m.id, "status": m.status}


class OverrideIn(BaseModel):
    resource_code: str = Field(min_length=2, max_length=64)
    period: Literal["month", "day", "lifetime"]
    limit_value: int = Field(ge=0, le=10_000_000, strict=True)
    reason: str = Field(min_length=5, max_length=300)
    expires_at: datetime | None = None


@router.post("/merchants/{merchant_id}/overrides", status_code=201)
def create_override(
    merchant_id: uuid.UUID,
    body: OverrideIn,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    """Raise or lower one limit for one merchant (support goodwill, pilots). Wins over the plan."""
    _merchant_or_404(db, merchant_id)
    res = db.get(MeteredResource, body.resource_code)
    if res is None:
        raise ValidationFailed(code="unknown_resource", details={"resource_code": body.resource_code})
    if res.kind == "gauge" and body.period != "lifetime":
        raise ValidationFailed(code="gauge_period_lifetime", details={"resource_code": body.resource_code})
    if body.expires_at is not None and body.expires_at <= utcnow():
        raise ValidationFailed(code="expires_in_past")
    o = EntitlementOverride(
        merchant_id=merchant_id,
        resource_code=body.resource_code,
        period=body.period,
        limit_value=body.limit_value,
        reason=body.reason,
        created_by_user_id=p.user.id,
        expires_at=body.expires_at,
    )
    db.add(o)
    db.flush()
    audit.record(
        db,
        action="admin.entitlement_override_created",
        resource_type="entitlement_override",
        resource_id=o.id,
        actor=_staff_actor(p),
        merchant_id=merchant_id,
        meta=request_meta(request),
        metadata=body.model_dump(mode="json"),
    )
    return _override_view(o)


@router.delete("/merchants/{merchant_id}/overrides/{override_id}", status_code=204)
def end_override(
    merchant_id: uuid.UUID,
    override_id: uuid.UUID,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    """Ends an override now (kept for the record; expiry set to now rather than deleting the row)."""
    o = db.scalar(
        select(EntitlementOverride)
        .where(EntitlementOverride.id == override_id, EntitlementOverride.merchant_id == merchant_id)
        .execution_options(skip_tenant_filter=True)
    )
    if o is None:
        raise NotFound()
    if o.expires_at is None or o.expires_at > utcnow():
        o.expires_at = utcnow()
        audit.record(
            db,
            action="admin.entitlement_override_ended",
            resource_type="entitlement_override",
            resource_id=o.id,
            actor=_staff_actor(p),
            merchant_id=merchant_id,
            meta=request_meta(request),
        )
    return Response(status_code=204)


class CreditsIn(BaseModel):
    amount: int = Field(gt=0, le=1_000_000, strict=True)
    reason: str = Field(min_length=5, max_length=300)
    idempotency_key: str = Field(min_length=8, max_length=80)


@router.post("/merchants/{merchant_id}/credits", status_code=201)
def grant_credits(
    merchant_id: uuid.UUID,
    body: CreditsIn,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    """Goodwill credits. The key makes a double-click or retry grant once."""
    _merchant_or_404(db, merchant_id)
    tx = entitlements.grant_credits(
        db, merchant_id, body.amount, f"staff:{body.idempotency_key}", kind="grant", note=body.reason
    )
    audit.record(
        db,
        action="admin.credits_granted",
        resource_type="credit_transaction",
        resource_id=tx.id,
        actor=_staff_actor(p),
        merchant_id=merchant_id,
        meta=request_meta(request),
        metadata={"amount": body.amount, "reason": body.reason},
    )
    return {"transaction_id": tx.id, "balance": entitlements.balance(db, merchant_id)}


@router.get("/audit-logs")
def platform_audit(
    merchant_id: uuid.UUID | None = None,
    actor_type: str | None = Query(None, pattern="^(user|system|automation|ai|staff|webhook)$"),
    action: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    """Cross-merchant audit trail for staff (who did what, including other staff)."""
    stmt = select(AuditLog)
    if merchant_id:
        stmt = stmt.where(AuditLog.merchant_id == merchant_id)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action))
    rows = list(db.scalars(paginate_desc(stmt, AuditLog.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {
        "items": [
            {
                "id": a.id,
                "merchant_id": a.merchant_id,
                "occurred_at": a.occurred_at,
                "actor": {"type": a.actor_type, "id": a.actor_id, "display": a.actor_display},
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "request_id": a.request_id,
                "changes": a.changes,
                "metadata": a.meta,
            }
            for a in items
        ],
        "next_cursor": nxt,
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
