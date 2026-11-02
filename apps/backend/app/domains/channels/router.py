from __future__ import annotations

import secrets
import uuid
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, request_meta, require, require_staff
from app.core.config import Environment, get_settings
from app.core.context import TenantContext
from app.core.errors import NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.channels import service
from app.domains.channels.models import ChannelConnection, ChannelListing, WebhookEvent
from app.domains.integrations import registry

router = APIRouter(prefix="/channels", tags=["channels"])
listings_router = APIRouter(prefix="/catalog", tags=["channels"])
webhooks_router = APIRouter(tags=["webhooks"])
admin_router = APIRouter(prefix="/admin/webhooks", tags=["admin"])
dev_router = APIRouter(include_in_schema=False)


class ConnectIn(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    redirect_uri: str = Field(min_length=10, max_length=500)
    reconnect_connection_id: uuid.UUID | None = None


class CallbackIn(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    state: str = Field(min_length=20, max_length=200)
    code: str = Field(min_length=1, max_length=2000)


class PublishIn(BaseModel):
    connection_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


@router.get("/providers")
def providers(ctx: TenantContext = Depends(require("channels.read"))) -> dict[str, Any]:
    return {"items": registry.available("channel")}


@router.get("")
def list_connections(
    ctx: TenantContext = Depends(require("channels.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    rows = db.scalars(
        select(ChannelConnection)
        .where(ChannelConnection.status != "disconnected")
        .order_by(ChannelConnection.created_at)
    )
    return {"items": [service.connection_view(c) for c in rows]}


@router.post("/connect")
def connect(
    body: ConnectIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    url = service.start_connect(db, ctx, body.provider, body.redirect_uri, body.reconnect_connection_id)
    return {"authorize_url": url}


@router.post("/oauth/callback", status_code=201)
def oauth_callback(
    body: CallbackIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.connection_view(service.complete_connect(db, ctx, body.provider, body.state, body.code))


@router.post("/{connection_id}/health")
def health(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require("channels.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.connection_view(service.check_health(db, ctx, connection_id))


@router.delete("/{connection_id}", status_code=204)
def disconnect(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.disconnect(db, ctx, connection_id)
    return Response(status_code=204)


# ----------------------------------------------------------------------------- listings
@listings_router.post("/products/{product_id}/publish", status_code=202)
def publish(
    product_id: uuid.UUID,
    body: PublishIn,
    ctx: TenantContext = Depends(require("catalog.publish")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    rows = service.request_publish(db, ctx, product_id, body.connection_ids)
    return {"items": [service.listing_view(r) for r in rows]}


@listings_router.get("/products/{product_id}/listings")
def listings(
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    rows = db.execute(
        select(ChannelListing, ChannelConnection)
        .join(ChannelConnection, ChannelConnection.id == ChannelListing.connection_id)
        .where(ChannelListing.product_id == product_id)
    ).all()
    return {"items": [service.listing_view(lst, c) for lst, c in rows]}


@listings_router.delete("/products/{product_id}/listings/{connection_id}", status_code=202)
def unpublish(
    product_id: uuid.UUID,
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.publish")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.listing_view(service.unpublish(db, ctx, product_id, connection_id))


# ----------------------------------------------------------------------------- public webhook gateway
@webhooks_router.post("/webhooks/{provider}")
async def receive_webhook(provider: str, request: Request) -> JSONResponse:
    s = get_settings()
    secret = s.channel_webhook_secrets.get(provider)
    if secret is None:
        raise NotFound(code="provider_not_available")
    body = await request.body()
    if len(body) > s.webhook_max_bytes:
        raise ValidationFailed("Payload too large", code="payload_too_large")
    from starlette.concurrency import run_in_threadpool

    def _ingest() -> dict[str, int]:
        from app.core.db import session_scope

        with session_scope() as db:
            return service.ingest_webhook(
                db, provider, dict(request.headers), body, secret.get_secret_value()
            )

    try:
        stats = await run_in_threadpool(_ingest)
    except Exception as e:
        if getattr(e, "code", None) == "webhook_signature_invalid":
            return JSONResponse(
                {
                    "error": {
                        "code": "webhook_signature_invalid",
                        "message": "Invalid signature",
                        "details": {},
                        "request_id": request.state.request_id,
                    }
                },
                status_code=401,
            )
        raise
    return JSONResponse({"received": True, **stats})


# ----------------------------------------------------------------------------- admin webhook explorer
@admin_router.get("")
def list_webhooks(
    status: str | None = Query(None, pattern="^(received|processed|ignored|failed|dead)$"),
    provider: str | None = None,
    limit: int = Query(50, le=200),
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(WebhookEvent).order_by(WebhookEvent.received_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(WebhookEvent.status == status)
    if provider:
        stmt = stmt.where(WebhookEvent.provider == provider)
    return {
        "items": [
            {
                "id": e.id,
                "provider": e.provider,
                "event_type": e.event_type,
                "status": e.status,
                "merchant_id": e.merchant_id,
                "attempts": e.attempts,
                "duplicates": e.duplicate_count,
                "last_error": e.last_error,
                "received_at": e.received_at,
            }
            for e in db.scalars(stmt)
        ]
    }


@admin_router.post("/{event_id}/replay")
def replay(
    event_id: uuid.UUID,
    request: Request,
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.core.context import Actor

    ev = service.replay_webhook(db, event_id)
    audit.record(
        db,
        action="admin.webhook_replayed",
        resource_type="webhook_event",
        resource_id=ev.id,
        actor=Actor(type="staff", id=p.user.id, display=p.user.email),
        merchant_id=ev.merchant_id,
        meta=request_meta(request),
    )
    return {"id": ev.id, "status": ev.status}


# ----------------------------------------------------------------------------- dev sandbox consent screen
@dev_router.get("/_dev/channels/sandbox/authorize")
def sandbox_authorize(state: str, redirect_uri: str, deny: bool = False) -> RedirectResponse:
    if get_settings().environment in (Environment.PRODUCTION, Environment.STAGING):
        raise NotFound()
    params = (
        {"state": state, "error": "access_denied"}
        if deny
        else {"state": state, "code": f"sbx-code-{secrets.token_hex(6)}"}
    )
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{sep}{urlencode(params)}", status_code=302)
