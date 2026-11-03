"""FastAPI dependencies: DB session, authentication, tenant resolution, permission checks."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import Actor, RequestMeta, TenantContext
from app.core.db import bind_tenant, session_factory
from app.core.errors import NotAuthenticated, NotFound, PermissionDenied
from app.core.tracing import current_trace_id
from app.domains.accounts.models import AuthSession, User
from app.domains.accounts.service import authenticate_access_token
from app.domains.merchants.models import Membership, Merchant
from app.domains.merchants.rbac import permissions_for


def get_db() -> Iterator[Session]:
    """Request unit of work. MUST be declared with ``scope="function"`` so the commit happens before
    the response is sent: with FastAPI's default ("request") scope the client can act on a response
    whose data isn't committed yet, or be told "success" for a commit that then fails.
    Enforced by tests/test_platform.py::test_db_dependency_commits_before_response."""
    db = session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def client_ip(request: Request) -> str | None:
    hops = get_settings().trusted_proxy_count
    if hops > 0:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            parts = [p.strip() for p in fwd.split(",")]
            if len(parts) >= hops:
                return parts[-hops]
    return request.client.host if request.client else None


def request_meta(request: Request) -> RequestMeta:
    return RequestMeta(
        request_id=getattr(request.state, "request_id", None),
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        source="api",
        trace_id=current_trace_id(),
    )


@dataclass
class Principal:
    user: User
    session: AuthSession

    @property
    def actor(self) -> Actor:
        return Actor(type="user", id=self.user.id, display=self.user.email)


def get_principal(request: Request, db: Session = Depends(get_db, scope="function")) -> Principal:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise NotAuthenticated()
    user, session = authenticate_access_token(db, token)
    request.state.user_id = str(user.id)
    return Principal(user, session)


def get_tenant(
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db, scope="function"),
    x_merchant_id: Annotated[str | None, Header(alias="X-Merchant-Id")] = None,
) -> TenantContext:
    if not x_merchant_id:
        raise NotFound("X-Merchant-Id header is required", code="merchant_required")
    try:
        merchant_id = uuid.UUID(x_merchant_id)
    except ValueError as e:
        raise NotFound(code="merchant_not_found") from e
    row = db.execute(
        select(Membership, Merchant)
        .join(Merchant, Merchant.id == Membership.merchant_id)
        .where(
            Membership.merchant_id == merchant_id,
            Membership.user_id == principal.user.id,
            Membership.status == "active",
        )
    ).first()
    if row is None:
        # 404 (not 403) so the existence of other tenants is not revealed.
        raise NotFound(code="merchant_not_found")
    membership, merchant = row
    if merchant.status != "active":
        raise PermissionDenied("This shop is suspended", code="merchant_suspended")
    bind_tenant(db, merchant_id)
    request.state.merchant_id = str(merchant_id)
    return TenantContext(
        merchant_id=merchant_id,
        actor=principal.actor,
        role=membership.role,
        permissions=permissions_for(membership.role),
        meta=request_meta(request),
    )


def require(permission: str) -> Callable[..., TenantContext]:
    def checker(ctx: TenantContext = Depends(get_tenant)) -> TenantContext:
        if not ctx.has(permission):
            raise PermissionDenied(details={"permission": permission})
        return ctx

    return checker


def require_staff(principal: Principal = Depends(get_principal)) -> Principal:
    if not principal.user.is_platform_staff:
        raise NotFound()
    if get_settings().staff_require_mfa and "mfa" not in principal.session.amr:
        raise PermissionDenied("Staff access requires an MFA-verified session", code="mfa_required")
    return principal
