from __future__ import annotations

import secrets
import uuid
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, request_meta, require, require_staff
from app.core.config import Environment, get_settings
from app.core.context import TenantContext
from app.core.errors import NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.catalog import service as catalog_service
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


class KeysIn(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    store_url: str = Field(min_length=10, max_length=300)
    consumer_key: SecretStr = Field(min_length=10, max_length=200)
    consumer_secret: SecretStr = Field(min_length=10, max_length=200)


@router.post("/connect-with-keys", status_code=201)
def connect_with_keys(
    body: KeysIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    c = service.connect_with_keys(
        db,
        ctx,
        body.provider,
        body.store_url,
        body.consumer_key.get_secret_value(),
        body.consumer_secret.get_secret_value(),
    )
    return service.connection_view(c)


class MessagingIn(BaseModel):
    provider: str = Field(pattern="^(telegram|whatsapp_cloud)$")
    # bot_token (Telegram); access_token, app_secret, phone_number_id, business_account_id (WhatsApp)
    fields: dict[str, SecretStr] = Field(max_length=6)


@router.post("/connect-messaging", status_code=201)
def connect_messaging(
    body: MessagingIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Connect a Telegram bot or the seller's own WhatsApp Business app. Secrets are sealed at once."""
    fields = {k: v.get_secret_value() for k, v in body.fields.items()}
    return service.connection_view(service.connect_messaging(db, ctx, body.provider, fields))


class MetaIn(BaseModel):
    page_id: str = Field(pattern=r"^\d{5,25}$")
    page_access_token: SecretStr = Field(min_length=20, max_length=600)
    with_instagram: bool = True


@router.post("/connect-meta", status_code=201)
def connect_meta(
    body: MetaIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Facebook Page (and its linked Instagram account) through the seller's own Meta app."""
    conns = service.connect_meta(
        db, ctx, body.page_id, body.page_access_token.get_secret_value(), body.with_instagram
    )
    return {"items": [service.connection_view(c) for c in conns]}


class MetaStartIn(BaseModel):
    redirect_uri: str = Field(min_length=10, max_length=500)


class MetaPagesIn(BaseModel):
    state: str = Field(min_length=20, max_length=200)
    code: str = Field(min_length=1, max_length=2000)


class MetaPickIn(BaseModel):
    selection: str = Field(min_length=20, max_length=200)
    page_id: str = Field(pattern=r"^\d{5,25}$")
    with_instagram: bool = True


@router.get("/meta/status")
def meta_status(ctx: TenantContext = Depends(require("channels.read"))) -> dict[str, Any]:
    from app.domains.integrations import meta

    return {"one_click_available": meta.app_configured()}


@router.post("/meta/oauth/start")
def meta_oauth_start(
    body: MetaStartIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return {"authorize_url": service.meta_start(db, ctx, body.redirect_uri)}


@router.post("/meta/oauth/pages")
def meta_oauth_pages(
    body: MetaPagesIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.meta_pages(db, ctx, body.state, body.code)


@router.post("/meta/oauth/connect", status_code=201)
def meta_oauth_connect(
    body: MetaPickIn,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    conns = service.meta_connect(db, ctx, body.selection, body.page_id, body.with_instagram)
    return {"items": [service.connection_view(c) for c in conns]}


@router.get("/{connection_id}/webhook-setup")
def webhook_setup(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.webhook_setup(db, ctx, connection_id)


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


@router.post("/{connection_id}/reconcile", status_code=202)
def reconcile(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require("channels.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Queue a check of every live listing on this channel against the channel's own copy (CHN-012)."""
    return service.connection_view(service.request_reconcile(db, ctx, connection_id))


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
    # Same ownership rule as every product route: a foreign or unknown product is 404, not an empty list.
    catalog_service.get_product(db, ctx, product_id)
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


class ResolveDriftIn(BaseModel):
    action: str = Field(pattern="^(push|accept)$")


@listings_router.post("/products/{product_id}/listings/{connection_id}/resolve-drift")
def resolve_drift(
    product_id: uuid.UUID,
    connection_id: uuid.UUID,
    body: ResolveDriftIn,
    ctx: TenantContext = Depends(require("catalog.publish")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.listing_view(service.resolve_drift(db, ctx, product_id, connection_id, body.action))


# ----------------------------------------------------------------------------- public webhook gateway
# Meta's app-level webhook first: /webhooks/meta must not be read as /webhooks/{provider}.
@webhooks_router.get("/webhooks/meta", include_in_schema=False)
def verify_meta_webhook(request: Request) -> Response:
    """Meta's callback check for Nivaro's app-level webhook (Messenger + Instagram DMs)."""
    from app.core.security import constant_time_equals

    token = get_settings().meta_verify_token
    q = request.query_params
    if (
        token is None
        or q.get("hub.mode") != "subscribe"
        or not constant_time_equals(q.get("hub.verify_token", ""), token.get_secret_value())
    ):
        return Response(status_code=403)
    return Response(q.get("hub.challenge", "")[:200], media_type="text/plain")


@webhooks_router.post("/webhooks/meta", include_in_schema=False)
async def receive_meta_webhook(request: Request) -> JSONResponse:
    """Messenger and Instagram DMs for every connected shop, signed with Nivaro's app secret."""
    from starlette.concurrency import run_in_threadpool

    from app.domains.integrations import meta

    body = await request.body()
    if len(body) > get_settings().webhook_max_bytes:
        raise ValidationFailed("Payload too large", code="payload_too_large")
    if not meta.verify_app_signature(dict(request.headers), body):
        from app.core.metrics import INTEGRATION_CALLS

        INTEGRATION_CALLS.labels("meta", "webhook", "bad_signature").inc()
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

    def _ingest() -> dict[str, int]:
        from app.core.db import session_scope

        with session_scope() as db:
            return service.ingest_meta_webhook(db, body)

    return JSONResponse({"received": True, **(await run_in_threadpool(_ingest))})


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


@webhooks_router.get("/webhooks/{provider}/{connection_id}", include_in_schema=False)
def verify_connection_webhook(provider: str, connection_id: uuid.UUID, request: Request) -> Response:
    """Meta's one-time callback check: echo hub.challenge only if hub.verify_token is this connection's."""
    from app.core.db import session_scope
    from app.core.security import constant_time_equals

    q = request.query_params
    with session_scope() as db:
        found = service.connection_webhook_secret(db, connection_id)
    if (
        found is None
        or found[0].provider != provider
        or q.get("hub.mode") != "subscribe"
        or not constant_time_equals(q.get("hub.verify_token", ""), found[1])
    ):
        return Response(status_code=403)
    return Response(q.get("hub.challenge", "")[:200], media_type="text/plain")


@webhooks_router.post("/webhooks/{provider}/{connection_id}")
async def receive_connection_webhook(
    provider: str, connection_id: uuid.UUID, request: Request
) -> JSONResponse:
    """Per-connection webhooks (e.g. WooCommerce): verified with that connection's own secret."""
    s = get_settings()
    body = await request.body()
    if len(body) > s.webhook_max_bytes:
        raise ValidationFailed("Payload too large", code="payload_too_large")
    from starlette.concurrency import run_in_threadpool

    def _ingest() -> dict[str, int] | None:
        from app.core.db import session_scope

        with session_scope() as db:
            found = service.connection_webhook_secret(db, connection_id)
            if found is None or found[0].provider != provider:
                return None
            conn, secret = found
            return service.ingest_webhook(db, provider, dict(request.headers), body, secret, connection=conn)

    if request.headers.get("x-wc-webhook-topic") is None and b"webhook_id" in body:
        return JSONResponse({"received": True, "ping": True})  # WooCommerce delivery-URL ping on creation
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
    if stats is None:
        raise NotFound()
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
