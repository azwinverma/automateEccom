"""Merchant tenancy, stores, memberships and invitations (IAM-006..008)."""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.context import Actor, RequestMeta, TenantContext
from app.core.crypto import SealedSecret
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from app.core.security import hash_token, new_opaque_token
from app.domains.accounts.models import User
from app.domains.audit import service as audit
from app.domains.billing import plans
from app.domains.billing.service import entitlements, register_gauge
from app.domains.merchants.models import Invitation, Membership, Merchant, Store
from app.domains.merchants.rbac import ASSIGNABLE_ROLES, Role
from app.domains.platform import outbox

INVITATION_TTL = timedelta(days=7)
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,62}[a-z0-9])?$")
RESERVED_SLUGS = frozenset({"admin", "api", "app", "www", "help", "support", "billing", "status", "static"})


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")[:60]
    return slug or f"shop-{uuid.uuid4().hex[:6]}"  # Devanagari-only names produce an empty ASCII slug


def _validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug) or slug in RESERVED_SLUGS:
        raise ValidationFailed(
            "Slug must be 3-64 lowercase letters, numbers or hyphens",
            code="invalid_slug",
            details={"fields": [{"loc": ["body", "slug"]}]},
        )
    return slug


def _unique_merchant_slug(db: Session, base: str) -> str:
    slug, n = base, 1
    while db.scalar(select(Merchant.id).where(Merchant.slug == slug)) is not None:
        n += 1
        slug = f"{base[:58]}-{n}"
    return slug


def create_merchant(
    db: Session,
    *,
    owner: User,
    name: str,
    slug: str | None,
    country: str,
    currency: str,
    timezone: str,
    default_locale: str,
    meta: RequestMeta,
) -> Merchant:
    if slug:
        _validate_slug(slug)
        if db.scalar(select(Merchant.id).where(Merchant.slug == slug)) is not None:
            raise Conflict("This shop address is taken", code="slug_taken")
    else:
        slug = _unique_merchant_slug(db, slugify(name))
    actor = Actor(type="user", id=owner.id, display=owner.email)
    merchant = Merchant(
        name=name.strip(),
        slug=slug,
        country=country,
        currency=currency,
        timezone=timezone,
        default_locale=default_locale,
    )
    db.add(merchant)
    try:
        db.flush()
    except IntegrityError as e:
        raise Conflict("This shop address is taken", code="slug_taken") from e
    bind_tenant(db, merchant.id)
    db.add(Membership(merchant_id=merchant.id, user_id=owner.id, role=Role.OWNER.value))
    db.add(
        Store(
            merchant_id=merchant.id,
            name=merchant.name,
            slug=merchant.slug if len(merchant.slug) >= 3 else "main",
            default_currency=currency,
            is_default=True,
        )
    )
    audit.record(
        db,
        action="merchants.merchant_created",
        resource_type="merchant",
        resource_id=merchant.id,
        actor=actor,
        merchant_id=merchant.id,
        meta=meta,
        changes={"name": [None, merchant.name], "slug": [None, slug], "currency": [None, currency]},
    )
    outbox.publish(
        db,
        event_type="merchants.merchant_created",
        aggregate_type="merchant",
        aggregate_id=merchant.id,
        merchant_id=merchant.id,
        payload={"merchant_id": str(merchant.id), "owner_user_id": str(owner.id)},
    )
    plans.start_subscription(db, merchant.id, actor, meta)
    return merchant


def update_merchant(db: Session, ctx: TenantContext, **fields: Any) -> Merchant:
    m = db.get(Merchant, ctx.merchant_id)
    assert m is not None
    before = {k: getattr(m, k) for k in fields}
    for k, v in fields.items():
        if v is not None:
            setattr(m, k, v)
    changes = audit.diff(before, {k: getattr(m, k) for k in fields})
    if changes:
        audit.record(
            db,
            action="merchants.merchant_updated",
            resource_type="merchant",
            resource_id=m.id,
            actor=ctx.actor,
            merchant_id=m.id,
            meta=ctx.meta,
            changes=changes,
        )
    return m


# ----------------------------------------------------------------------------- stores
def create_store(db: Session, ctx: TenantContext, name: str, slug: str | None) -> Store:
    entitlements.check_gauge(db, ctx.merchant_id, "stores")
    slug = _validate_slug(slug) if slug else slugify(name)
    if db.scalar(select(Store.id).where(Store.slug == slug)) is not None:
        raise Conflict("A store with this address already exists", code="slug_taken")
    store = Store(merchant_id=ctx.merchant_id, name=name.strip(), slug=slug)
    db.add(store)
    db.flush()
    audit.record(
        db,
        action="stores.store_created",
        resource_type="store",
        resource_id=store.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"name": [None, store.name]},
    )
    return store


def update_store(
    db: Session, ctx: TenantContext, store_id: uuid.UUID, name: str | None, status: str | None
) -> Store:
    store = db.get(Store, store_id)
    if store is None or store.merchant_id != ctx.merchant_id:
        raise NotFound()
    if status == "archived" and store.is_default:
        raise Conflict("The default store cannot be archived", code="default_store")
    before = {"name": store.name, "status": store.status}
    if name is not None:
        store.name = name.strip()
    if status is not None:
        store.status = status
    changes = audit.diff(before, {"name": store.name, "status": store.status})
    if changes:
        audit.record(
            db,
            action="stores.store_updated",
            resource_type="store",
            resource_id=store.id,
            actor=ctx.actor,
            merchant_id=ctx.merchant_id,
            meta=ctx.meta,
            changes=changes,
        )
    return store


# ----------------------------------------------------------------------------- members
def _ensure_assignable(ctx: TenantContext, role: str) -> None:
    if ctx.role is None or Role(role) not in ASSIGNABLE_ROLES[Role(ctx.role)]:
        raise PermissionDenied(
            "You cannot assign this role", code="role_not_assignable", details={"role": role}
        )


def _active_owner_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.role == Role.OWNER.value, Membership.status == "active")
        )
        or 0
    )


def change_member_role(db: Session, ctx: TenantContext, membership_id: uuid.UUID, role: str) -> Membership:
    m = db.get(Membership, membership_id)
    if m is None or m.merchant_id != ctx.merchant_id or m.status != "active":
        raise NotFound()
    _ensure_assignable(ctx, role)
    # Non-owners may not modify owners.
    if m.role == Role.OWNER.value and ctx.role != Role.OWNER.value:
        raise PermissionDenied(code="role_not_assignable")
    if m.role == Role.OWNER.value and role != Role.OWNER.value and _active_owner_count(db) <= 1:
        raise Conflict("A shop must keep at least one owner", code="last_owner")
    old = m.role
    if old == role:
        return m
    m.role = role
    audit.record(
        db,
        action="team.member_role_changed",
        resource_type="membership",
        resource_id=m.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"role": [old, role]},
    )
    outbox.publish(
        db,
        event_type="merchants.member_role_changed",
        aggregate_type="membership",
        aggregate_id=m.id,
        merchant_id=ctx.merchant_id,
        payload={"membership_id": str(m.id), "old_role": old, "new_role": role},
    )
    return m


def remove_member(db: Session, ctx: TenantContext, membership_id: uuid.UUID) -> None:
    m = db.get(Membership, membership_id)
    if m is None or m.merchant_id != ctx.merchant_id or m.status != "active":
        raise NotFound()
    if m.role == Role.OWNER.value:
        if ctx.role != Role.OWNER.value:
            raise PermissionDenied(code="role_not_assignable")
        if _active_owner_count(db) <= 1:
            raise Conflict("A shop must keep at least one owner", code="last_owner")
    elif Role(m.role) not in ASSIGNABLE_ROLES[Role(ctx.role or "viewer")]:
        raise PermissionDenied(code="role_not_assignable")
    m.status = "removed"
    audit.record(
        db,
        action="team.member_removed",
        resource_type="membership",
        resource_id=m.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"user_id": str(m.user_id)},
    )
    outbox.publish(
        db,
        event_type="merchants.member_removed",
        aggregate_type="membership",
        aggregate_id=m.id,
        merchant_id=ctx.merchant_id,
        payload={"membership_id": str(m.id), "user_id": str(m.user_id)},
    )


# ----------------------------------------------------------------------------- invitations
@register_gauge("team_members")
def team_size(db: Session, merchant_id: uuid.UUID) -> int:
    """Seats in use: active members plus live pending invitations."""
    members = (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.merchant_id == merchant_id, Membership.status == "active")
        )
        or 0
    )
    pending = (
        db.scalar(
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.merchant_id == merchant_id,
                Invitation.status == "pending",
                Invitation.expires_at > utcnow(),
            )
        )
        or 0
    )
    return members + pending


@register_gauge("stores")
def active_stores(db: Session, merchant_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Store)
            .where(Store.merchant_id == merchant_id, Store.status == "active")
        )
        or 0
    )


def create_invitation(db: Session, ctx: TenantContext, email: str, role: str) -> tuple[Invitation, str]:
    _ensure_assignable(ctx, role)
    email = email.strip()
    existing_member = db.scalar(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(func.lower(User.email) == email.lower(), Membership.status == "active")
    )
    if existing_member is not None:
        raise Conflict("This person is already on the team", code="already_member")
    if (
        db.scalar(
            select(Invitation.id).where(
                func.lower(Invitation.email) == email.lower(), Invitation.status == "pending"
            )
        )
        is not None
    ):
        raise Conflict("An invitation is already pending for this email", code="invitation_pending")
    entitlements.check_gauge(db, ctx.merchant_id, "team_members")
    token = new_opaque_token()
    inv = Invitation(
        merchant_id=ctx.merchant_id,
        email=email,
        role=role,
        token_hash=hash_token(token),
        invited_by_user_id=ctx.actor.id,
        expires_at=utcnow() + INVITATION_TTL,
    )
    db.add(inv)
    db.flush()
    inv.token_sealed = SealedSecret.seal(token, f"invitation:{inv.id}").blob
    audit.record(
        db,
        action="team.invitation_created",
        resource_type="invitation",
        resource_id=inv.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"role": role},
    )
    outbox.publish(
        db,
        event_type="merchants.invitation_created",
        aggregate_type="invitation",
        aggregate_id=inv.id,
        merchant_id=ctx.merchant_id,
        payload={"invitation_id": str(inv.id), "role": role},
    )
    return inv, token


def revoke_invitation(db: Session, ctx: TenantContext, invitation_id: uuid.UUID) -> None:
    inv = db.get(Invitation, invitation_id)
    if inv is None or inv.merchant_id != ctx.merchant_id:
        raise NotFound()
    if inv.status != "pending":
        return
    inv.status = "revoked"
    inv.token_sealed = None
    audit.record(
        db,
        action="team.invitation_revoked",
        resource_type="invitation",
        resource_id=inv.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )


def accept_invitation(db: Session, user: User, token: str, meta: RequestMeta) -> Membership:
    inv = db.scalar(
        select(Invitation)
        .where(Invitation.token_hash == hash_token(token))
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if inv is None or inv.status != "pending":
        raise NotFound("Invitation not found or already used", code="invitation_invalid")
    if inv.expires_at < utcnow():
        inv.status = "expired"
        inv.token_sealed = None
        raise NotFound("Invitation has expired", code="invitation_expired")
    if inv.email.lower() != user.email.lower():
        # Invitations are bound to the invited email to stop forwarded-link takeovers.
        raise PermissionDenied(
            "This invitation was sent to a different email", code="invitation_email_mismatch"
        )
    bind_tenant(db, inv.merchant_id)
    m = db.scalar(select(Membership).where(Membership.user_id == user.id))
    if m is None:
        m = Membership(
            merchant_id=inv.merchant_id,
            user_id=user.id,
            role=inv.role,
            invited_by_user_id=inv.invited_by_user_id,
        )
        db.add(m)
    else:
        m.status, m.role = "active", inv.role
    inv.status = "accepted"
    inv.accepted_at = utcnow()
    inv.accepted_by_user_id = user.id
    inv.token_sealed = None
    db.flush()
    audit.record(
        db,
        action="team.invitation_accepted",
        resource_type="membership",
        resource_id=m.id,
        actor=Actor(type="user", id=user.id, display=user.email),
        merchant_id=inv.merchant_id,
        meta=meta,
        metadata={"role": inv.role, "invitation_id": str(inv.id)},
    )
    return m
