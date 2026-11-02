"""Channel connections, OAuth, token refresh, webhook gateway and listing publishing.

Connection lifecycle: connected ⇄ expired (token refresh failed / provider rejected credentials; seller
must reconnect) → disconnected (seller removed it). Expired connections never publish; listings wait.

Webhook gateway (CHN-010/011): verify signature → record raw event (dedupe on provider event id) →
respond fast → process asynchronously via the outbox → route to domain handlers by event type.

Listing publishing (CAT-010): a ChannelListing tracks desired vs actual state per connection. Product
changes mark listings ``out_of_sync`` and re-queue a publish; attempts are idempotent per product
version so provider retries never create duplicate listings.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.crypto import SealedSecret
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.core.metrics import INTEGRATION_CALLS
from app.core.security import hash_token, new_opaque_token
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements, register_gauge
from app.domains.catalog.models import Product
from app.domains.channels.models import ChannelConnection, ChannelListing, OAuthState, WebhookEvent
from app.domains.integrations import registry
from app.domains.integrations.base import ChannelAdapter, ChannelCapability, IntegrationError, OAuthTokens
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)
OAUTH_STATE_TTL = timedelta(minutes=10)
REFRESH_AHEAD = timedelta(minutes=10)
MAX_PUBLISH_ATTEMPTS = 6
MAX_WEBHOOK_ATTEMPTS = 8


@register_gauge("channels")
def channel_count(db: Session, merchant_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ChannelConnection)
            .where(ChannelConnection.merchant_id == merchant_id, ChannelConnection.status != "disconnected")
        )
        or 0
    )


# ----------------------------------------------------------------------------- tokens
def _aad(c: ChannelConnection, kind: str) -> str:
    return f"channel:{c.merchant_id}:{c.id}:{kind}"


def _store_tokens(c: ChannelConnection, t: OAuthTokens) -> None:
    c.access_token_sealed = SealedSecret.seal(t.access_token, _aad(c, "access")).blob
    if t.refresh_token:
        c.refresh_token_sealed = SealedSecret.seal(t.refresh_token, _aad(c, "refresh")).blob
    c.token_expires_at = t.expires_at
    if t.scopes:
        c.scopes = t.scopes


def adapter_for(c: ChannelConnection) -> ChannelAdapter:
    creds: dict[str, str] = {}
    if c.access_token_sealed:
        creds["access_token"] = SealedSecret(c.access_token_sealed).open(_aad(c, "access"))
    return registry.channel(
        c.provider, credentials=creds, config={"external_account_id": c.external_account_id}
    )


def _get(db: Session, ctx: TenantContext, connection_id: uuid.UUID) -> ChannelConnection:
    c = db.get(ChannelConnection, connection_id)
    if c is None or c.merchant_id != ctx.merchant_id or c.status == "disconnected":
        raise NotFound()
    return c


def _mark_expired(db: Session, c: ChannelConnection, code: str) -> None:
    if c.status == "expired":
        return
    c.status, c.last_error_code = "expired", code
    audit.record(
        db,
        action="channels.connection_expired",
        resource_type="channel_connection",
        resource_id=c.id,
        actor=Actor.system("channels"),
        merchant_id=c.merchant_id,
        metadata={"error_code": code},
    )
    outbox.publish(
        db,
        event_type="channels.connection_expired",
        aggregate_type="channel_connection",
        aggregate_id=c.id,
        merchant_id=c.merchant_id,
        payload={"connection_id": str(c.id), "provider": c.provider, "error_code": code},
    )


# ----------------------------------------------------------------------------- connect (OAuth)
def start_connect(
    db: Session, ctx: TenantContext, provider: str, redirect_uri: str, reconnect_id: uuid.UUID | None = None
) -> str:
    if not redirect_uri.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValidationFailed("redirect_uri must be https", code="invalid_redirect_uri")
    try:
        adapter = registry.channel(provider)
    except registry.AdapterNotAvailable as e:
        raise NotFound("This channel isn't available", code="provider_not_available") from e
    if reconnect_id is None:
        entitlements.check_gauge(db, ctx.merchant_id, "channels")
    else:
        existing = _get(db, ctx, reconnect_id)
        if existing.provider != provider:
            raise ValidationFailed("Reconnect must use the same channel", code="provider_mismatch")
    state = new_opaque_token()
    db.add(
        OAuthState(
            merchant_id=ctx.merchant_id,
            user_id=ctx.actor.id,
            provider=provider,
            redirect_uri=redirect_uri,
            state_hash=hash_token(state),
            reconnect_connection_id=reconnect_id,
            expires_at=utcnow() + OAUTH_STATE_TTL,
        )
    )
    db.flush()
    return adapter.authorize_url(state, redirect_uri)


def complete_connect(
    db: Session, ctx: TenantContext, provider: str, state: str, code: str
) -> ChannelConnection:
    st = db.scalar(select(OAuthState).where(OAuthState.state_hash == hash_token(state)).with_for_update())
    if (
        st is None
        or st.merchant_id != ctx.merchant_id
        or st.user_id != ctx.actor.id
        or st.provider != provider
        or st.used_at is not None
        or st.expires_at < utcnow()
    ):
        raise ValidationFailed(
            "This connection link is invalid or expired. Start again.", code="oauth_state_invalid"
        )
    st.used_at = utcnow()
    adapter = registry.channel(provider)
    try:
        tokens = adapter.exchange_code(code, st.redirect_uri)
    except IntegrationError as e:
        INTEGRATION_CALLS.labels(provider, "oauth_exchange", e.code).inc()
        raise AppError(
            "The channel did not accept the connection. Try again.",
            code="oauth_exchange_failed",
            details={"provider_code": e.code},
        ) from e
    account = tokens.external_account_id or "default"
    c = None
    if st.reconnect_connection_id:
        c = db.get(ChannelConnection, st.reconnect_connection_id)
        if c is not None and c.external_account_id != account:
            raise Conflict(
                "You signed in to a different account than the one being reconnected",
                code="reconnect_account_mismatch",
            )
    if c is None:
        c = db.scalar(
            select(ChannelConnection).where(
                ChannelConnection.merchant_id == ctx.merchant_id,
                ChannelConnection.provider == provider,
                ChannelConnection.external_account_id == account,
                ChannelConnection.status != "disconnected",
            )
        )
    action = "channels.reconnected" if c is not None else "channels.connected"
    if c is None:
        c = ChannelConnection(
            id=uuid7(),
            merchant_id=ctx.merchant_id,
            provider=provider,
            display_name=f"{adapter.display_name} ({account})",
            external_account_id=account,
            store_id=st.store_id,
            connected_by_user_id=ctx.actor.id,
        )
        db.add(c)
    c.status, c.last_error_code, c.consecutive_failures = "connected", None, 0
    c.capabilities = sorted(cap.value for cap in adapter.capabilities)
    c.last_healthy_at = utcnow()
    _store_tokens(c, tokens)
    db.flush()
    audit.record(
        db,
        action=action,
        resource_type="channel_connection",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": provider, "account": account, "scopes": c.scopes},
    )
    outbox.publish(
        db,
        event_type="channels.connected",
        aggregate_type="channel_connection",
        aggregate_id=c.id,
        merchant_id=ctx.merchant_id,
        payload={"connection_id": str(c.id), "provider": provider},
    )
    # Listings waiting on a reconnect can now be retried.
    for listing in db.scalars(
        select(ChannelListing).where(
            ChannelListing.connection_id == c.id, ChannelListing.status.in_(("failed", "out_of_sync"))
        )
    ):
        _queue_publish(db, listing)
    return c


def disconnect(db: Session, ctx: TenantContext, connection_id: uuid.UUID) -> None:
    c = _get(db, ctx, connection_id)
    c.status, c.disconnected_at = "disconnected", utcnow()
    c.access_token_sealed = c.refresh_token_sealed = None  # crypto-shred
    audit.record(
        db,
        action="channels.disconnected",
        resource_type="channel_connection",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": c.provider},
    )


def refresh_due_tokens(db: Session, limit: int = 100) -> dict[str, int]:
    """CHN-004 (periodic). Refresh before expiry; credential rejection → expired (seller reconnects);
    transient failure → try again next run."""
    stats = {"refreshed": 0, "expired": 0, "retry": 0}
    rows = db.scalars(
        select(ChannelConnection)
        .where(
            ChannelConnection.status == "connected",
            ChannelConnection.token_expires_at.is_not(None),
            ChannelConnection.token_expires_at < utcnow() + REFRESH_AHEAD,
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
        .execution_options(skip_tenant_filter=True)
    ).all()
    for c in rows:
        if not c.refresh_token_sealed:
            _mark_expired(db, c, "no_refresh_token")
            stats["expired"] += 1
            continue
        try:
            rt = SealedSecret(c.refresh_token_sealed).open(_aad(c, "refresh"))
            tokens = registry.channel(
                c.provider, config={"external_account_id": c.external_account_id}
            ).refresh_tokens(rt)
            _store_tokens(c, tokens)
            c.consecutive_failures = 0
            stats["refreshed"] += 1
        except IntegrationError as e:
            INTEGRATION_CALLS.labels(c.provider, "token_refresh", e.code).inc()
            if e.auth or not e.retryable:
                _mark_expired(db, c, e.code)
                stats["expired"] += 1
            else:
                c.consecutive_failures += 1
                c.last_error_code = e.code
                stats["retry"] += 1
    return stats


def check_health(db: Session, ctx: TenantContext, connection_id: uuid.UUID) -> ChannelConnection:
    c = _get(db, ctx, connection_id)
    c.last_health_check_at = utcnow()
    try:
        ok = adapter_for(c).health_check()
    except IntegrationError as e:
        if e.auth:
            _mark_expired(db, c, e.code)
            return c
        ok = False
        c.last_error_code = e.code
    if ok:
        c.last_healthy_at, c.consecutive_failures = utcnow(), 0
    else:
        c.consecutive_failures += 1
    return c


def connection_view(c: ChannelConnection) -> dict[str, Any]:
    return {
        "id": c.id,
        "provider": c.provider,
        "display_name": c.display_name,
        "status": c.status,
        "external_account_id": c.external_account_id,
        "capabilities": c.capabilities,
        "scopes": c.scopes,
        "token_expires_at": c.token_expires_at,
        "last_healthy_at": c.last_healthy_at,
        "last_error_code": c.last_error_code,
        "needs_reconnect": c.status == "expired",
        "created_at": c.created_at,
    }


# ----------------------------------------------------------------------------- webhook gateway
WebhookHandler = Callable[[Session, WebhookEvent], None]
_WEBHOOK_HANDLERS: dict[str, WebhookHandler] = {}


def webhook_handler(event_type: str) -> Callable[[WebhookHandler], WebhookHandler]:
    def deco(fn: WebhookHandler) -> WebhookHandler:
        _WEBHOOK_HANDLERS[event_type] = fn
        return fn

    return deco


def ingest_webhook(
    db: Session, provider: str, headers: dict[str, str], body: bytes, webhook_secret: str
) -> dict[str, int]:
    """Called by the public webhook endpoint. Returns counts; raises on bad signature."""
    try:
        adapter = registry.channel(provider, credentials={"webhook_secret": webhook_secret})
    except registry.AdapterNotAvailable as e:
        raise NotFound(code="provider_not_available") from e
    if not adapter.verify_webhook(headers, body):
        INTEGRATION_CALLS.labels(provider, "webhook", "bad_signature").inc()
        raise AppError("Invalid signature", code="webhook_signature_invalid")
    try:
        events = adapter.parse_webhook(headers, body)
    except (ValueError, KeyError) as e:
        raise ValidationFailed("Malformed webhook", code="webhook_malformed") from e
    stats = {"accepted": 0, "duplicates": 0}
    for ev in events:
        conn = None
        if ev.external_account_id:
            conn = db.scalar(
                select(ChannelConnection)
                .where(
                    ChannelConnection.provider == provider,
                    ChannelConnection.external_account_id == ev.external_account_id,
                    ChannelConnection.status != "disconnected",
                )
                .execution_options(skip_tenant_filter=True)
            )
        inserted = db.execute(
            pg_insert(WebhookEvent)
            .values(
                id=uuid7(),
                provider=provider,
                external_event_id=ev.external_event_id,
                event_type=ev.event_type,
                merchant_id=conn.merchant_id if conn else None,
                connection_id=conn.id if conn else None,
                external_account_id=ev.external_account_id,
                payload=ev.payload,
                status="received",
                received_at=utcnow(),
                occurred_at=ev.occurred_at,
                attempts=0,
                duplicate_count=0,
            )
            .on_conflict_do_nothing(index_elements=["provider", "external_event_id"])
            .returning(WebhookEvent.id)
        ).scalar_one_or_none()
        if inserted is None:
            db.execute(
                update(WebhookEvent)
                .where(
                    WebhookEvent.provider == provider, WebhookEvent.external_event_id == ev.external_event_id
                )
                .values(duplicate_count=WebhookEvent.duplicate_count + 1)
            )
            stats["duplicates"] += 1
            continue
        outbox.publish(
            db,
            event_type="webhooks.received",
            aggregate_type="webhook_event",
            aggregate_id=inserted,
            merchant_id=conn.merchant_id if conn else None,
            payload={"webhook_event_id": str(inserted)},
        )
        stats["accepted"] += 1
    INTEGRATION_CALLS.labels(provider, "webhook", "accepted").inc(stats["accepted"])
    return stats


def process_webhook(db: Session, webhook_event_id: uuid.UUID) -> WebhookEvent | None:
    ev = db.scalar(select(WebhookEvent).where(WebhookEvent.id == webhook_event_id).with_for_update())
    if ev is None or ev.status in ("processed", "ignored"):
        return ev
    ev.attempts += 1
    fn = _WEBHOOK_HANDLERS.get(ev.event_type)
    if ev.merchant_id is None:
        ev.status, ev.last_error = "ignored", "no connection for account"
        return ev
    if fn is None:
        ev.status, ev.last_error = "ignored", f"no handler for {ev.event_type}"
        return ev
    bind_tenant(db, ev.merchant_id)
    try:
        with db.begin_nested():  # handler side effects roll back alone; the failure record below persists
            fn(db, ev)
    except Exception as e:
        ev.last_error = f"{type(e).__name__}: {e}"[:1000]
        if ev.attempts >= MAX_WEBHOOK_ATTEMPTS:
            ev.status = "dead"  # visible in admin webhook explorer; replayable
            log.error("webhook_dead", webhook_event_id=str(ev.id), event_type=ev.event_type)
        else:
            ev.status = "failed"
            outbox.publish(
                db,
                event_type="webhooks.received",
                aggregate_type="webhook_event",
                aggregate_id=ev.id,
                merchant_id=ev.merchant_id,
                payload={"webhook_event_id": str(ev.id)},
                delay_seconds=min(2**ev.attempts * 10, 3600),
            )
        return ev
    ev.status, ev.processed_at, ev.last_error = "processed", utcnow(), None
    return ev


@handler("webhooks.received")
def _on_webhook(db: Session, ev: OutboxEvent) -> None:
    process_webhook(db, uuid.UUID(ev.payload["webhook_event_id"]))


@webhook_handler("account.deauthorized")
def _deauthorized(db: Session, ev: WebhookEvent) -> None:
    """Provider told us the seller revoked access (e.g. removed the app on the platform)."""
    if ev.connection_id:
        c = db.get(ChannelConnection, ev.connection_id)
        if c is not None:
            _mark_expired(db, c, "deauthorized_by_platform")


def replay_webhook(db: Session, webhook_event_id: uuid.UUID) -> WebhookEvent:
    ev = db.get(WebhookEvent, webhook_event_id)
    if ev is None:
        raise NotFound()
    ev.status, ev.attempts, ev.last_error = "received", 0, None
    outbox.publish(
        db,
        event_type="webhooks.received",
        aggregate_type="webhook_event",
        aggregate_id=ev.id,
        merchant_id=ev.merchant_id,
        payload={"webhook_event_id": str(ev.id)},
    )
    return ev


# ----------------------------------------------------------------------------- listings (publish)
def _queue_publish(db: Session, listing: ChannelListing, delay_seconds: int = 0) -> None:
    outbox.publish(
        db,
        event_type="listings.sync_requested",
        aggregate_type="channel_listing",
        aggregate_id=listing.id,
        merchant_id=listing.merchant_id,
        payload={"listing_id": str(listing.id)},
        delay_seconds=delay_seconds,
    )


def request_publish(
    db: Session, ctx: TenantContext, product_id: uuid.UUID, connection_ids: list[uuid.UUID]
) -> list[ChannelListing]:
    p = db.get(Product, product_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound()
    if p.status != "active":
        raise Conflict("Only live (active) products can be published to channels", code="product_not_active")
    out = []
    for cid in dict.fromkeys(connection_ids):
        c = _get(db, ctx, cid)
        if ChannelCapability.PRODUCT_LISTING.value not in c.capabilities:
            raise Conflict(
                f"{c.display_name} doesn't support product listings",
                code="capability_not_supported",
                details={"connection_id": str(c.id), "capability": "product_listing"},
            )
        listing = db.scalar(
            select(ChannelListing).where(
                ChannelListing.connection_id == c.id, ChannelListing.product_id == p.id
            )
        )
        if listing is None:
            listing = ChannelListing(merchant_id=ctx.merchant_id, connection_id=c.id, product_id=p.id)
            db.add(listing)
        listing.desired_state, listing.status, listing.attempts = "published", "pending", 0
        db.flush()
        _queue_publish(db, listing)
        out.append(listing)
    audit.record(
        db,
        action="channels.publish_requested",
        resource_type="product",
        resource_id=p.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"connections": [str(c) for c in connection_ids]},
    )
    return out


def unpublish(
    db: Session, ctx: TenantContext, product_id: uuid.UUID, connection_id: uuid.UUID
) -> ChannelListing:
    listing = db.scalar(
        select(ChannelListing).where(
            ChannelListing.product_id == product_id, ChannelListing.connection_id == connection_id
        )
    )
    if listing is None or listing.merchant_id != ctx.merchant_id:
        raise NotFound()
    listing.desired_state, listing.status, listing.attempts = "unpublished", "unpublishing", 0
    _queue_publish(db, listing)
    audit.record(
        db,
        action="channels.unpublish_requested",
        resource_type="channel_listing",
        resource_id=listing.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )
    return listing


def _listing_payload(db: Session, listing: ChannelListing) -> dict[str, Any]:
    from app.domains.catalog.service import product_detail

    ctx = TenantContext(merchant_id=listing.merchant_id, actor=Actor.system("channels"))
    d = product_detail(db, ctx, listing.product_id)
    return {
        "title": listing.title_override or d["title"],
        "title_ne": d["title_ne"],
        "handle": d["handle"],
        "description": d["description"],
        "description_ne": d["description_ne"],
        "brand": d["brand"],
        "tags": d["tags"],
        "options": d["options"],
        "variants": [
            {
                "sku": v["sku"],
                "barcode": v["barcode"],
                "options": v["options"],
                "price_minor": listing.price_override_minor or v["price"]["amount_minor"],
                "compare_at_minor": (v["compare_at"] or {}).get("amount_minor"),
                "currency": v["price"]["currency"],
                "weight_grams": v["weight_grams"],
            }
            for v in d["variants"]
            if v["status"] == "active"
        ],
        "images": [m["asset_id"] for m in d["media"]],
    }


def sync_listing(db: Session, listing_id: uuid.UUID) -> ChannelListing | None:
    """Reconcile one listing to its desired state. Idempotent per product version."""
    listing = db.scalar(
        select(ChannelListing)
        .where(ChannelListing.id == listing_id)
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if listing is None:
        return None
    bind_tenant(db, listing.merchant_id)
    c = db.get(ChannelConnection, listing.connection_id)
    p = db.get(Product, listing.product_id)
    assert c is not None and p is not None
    if c.status != "connected":
        listing.status, listing.last_error_code = "failed", "reconnect_required"
        return listing  # retried automatically after the seller reconnects
    want_live = listing.desired_state == "published" and p.status == "active"
    if want_live and listing.status == "published" and listing.published_product_version == p.version:
        return listing  # already in sync (duplicate delivery)
    listing.attempts += 1
    adapter = adapter_for(c)
    try:
        if want_live:
            listing.status = "publishing"
            ext = adapter.publish_listing(
                _listing_payload(db, listing),
                idempotency_key=f"listing:{listing.id}:v{p.version}",
                external_id=listing.external_id,
            )
            listing.external_id, listing.status = ext, "published"
            listing.published_product_version = p.version
        else:
            if listing.external_id:
                adapter.unpublish_listing(
                    listing.external_id, idempotency_key=f"unlisting:{listing.id}:v{p.version}"
                )
            listing.status = "unpublished"
        listing.last_error_code, listing.last_synced_at, listing.attempts = None, utcnow(), 0
        INTEGRATION_CALLS.labels(c.provider, "listing_sync", "ok").inc()
    except IntegrationError as e:
        INTEGRATION_CALLS.labels(c.provider, "listing_sync", e.code).inc()
        listing.last_error_code = e.code
        if e.auth:
            _mark_expired(db, c, e.code)
            listing.status = "failed"
        elif e.retryable and listing.attempts < MAX_PUBLISH_ATTEMPTS:
            listing.status = "out_of_sync"
            _queue_publish(db, listing, delay_seconds=min(2**listing.attempts * 15, 3600))
        else:
            listing.status = "failed"
            outbox.publish(
                db,
                event_type="listings.sync_failed",
                aggregate_type="channel_listing",
                aggregate_id=listing.id,
                merchant_id=listing.merchant_id,
                payload={"listing_id": str(listing.id), "error_code": e.code},
            )
    return listing


@handler("listings.sync_requested")
def _on_sync_requested(db: Session, ev: OutboxEvent) -> None:
    sync_listing(db, uuid.UUID(ev.payload["listing_id"]))


def _resync_product(db: Session, ev: OutboxEvent) -> None:
    pid = uuid.UUID(ev.payload["product_id"])
    for listing in db.scalars(
        select(ChannelListing)
        .where(ChannelListing.product_id == pid, ChannelListing.desired_state == "published")
        .execution_options(skip_tenant_filter=True)
    ):
        if listing.status in ("published", "failed", "pending"):
            listing.status = "out_of_sync"
            _queue_publish(db, listing)


for _evt in ("catalog.product_updated", "catalog.variant_updated", "catalog.product_status_changed"):
    handler(_evt, name=f"channels.resync_on.{_evt}")(_resync_product)


def listing_view(listing: ChannelListing, c: ChannelConnection | None = None) -> dict[str, Any]:
    return {
        "id": listing.id,
        "connection_id": listing.connection_id,
        "product_id": listing.product_id,
        "provider": c.provider if c else None,
        "status": listing.status,
        "desired_state": listing.desired_state,
        "external_id": listing.external_id,
        "last_error_code": listing.last_error_code,
        "last_synced_at": listing.last_synced_at,
        "published_product_version": listing.published_product_version,
    }
