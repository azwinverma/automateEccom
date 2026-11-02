from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.channels.models import ChannelConnection, ChannelListing, WebhookEvent
from app.domains.integrations.base import IntegrationError
from app.domains.integrations.sandbox import SandboxChannelAdapter
from app.domains.platform.models import OutboxEvent
from tests.conftest import onboard

API = "/api/v1"
REDIRECT = "http://localhost:3010/channels/callback"
SECRET = b"dev-sandbox-webhook-secret"


def _dispatch(due_now: bool = False) -> None:
    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch

    if due_now:  # make delayed retries due
        with session_scope() as db:
            db.execute(
                update(OutboxEvent).where(OutboxEvent.status == "pending").values(available_at=utcnow())
            )
    for _ in range(4):
        if not any(dispatch_batch().values()):
            break


def connect(client, s, reconnect_id: str | None = None) -> dict:
    r = client.post(
        f"{API}/channels/connect",
        headers=s.h(),
        json={
            "provider": "sandbox_channel",
            "redirect_uri": REDIRECT,
            "reconnect_connection_id": reconnect_id,
        },
    )
    assert r.status_code == 200, r.text
    consent = client.get(r.json()["authorize_url"], follow_redirects=False)
    assert consent.status_code == 302
    q = parse_qs(urlparse(consent.headers["location"]).query)
    cb = client.post(
        f"{API}/channels/oauth/callback",
        headers=s.h(),
        json={"provider": "sandbox_channel", "state": q["state"][0], "code": q["code"][0]},
    )
    assert cb.status_code == 201, cb.text
    return cb.json() | {"_state": q["state"][0], "_code": q["code"][0]}


def live_product(client, s) -> dict:
    p = client.post(
        f"{API}/catalog/products",
        headers=s.h(),
        json={"title": "Pashmina Shawl", "variants": [{"price_minor": 650000, "sku": "PASH-01"}]},
    ).json()
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=s.h(), json={"status": "active"})
    _dispatch()  # settle catalog events first so tests observe only the publish they trigger
    return p


def listing(client, s, pid) -> dict:
    return client.get(f"{API}/catalog/products/{pid}/listings", headers=s.h()).json()["items"][0]


def sign(body: bytes) -> dict[str, str]:
    return {
        "X-Sandbox-Signature": hmac.new(SECRET, body, hashlib.sha256).hexdigest(),
        "Content-Type": "application/json",
    }


# ----------------------------------------------------------------------------- connect
def test_oauth_connect_flow_seals_tokens_and_reports_capabilities(client, seller):
    c = connect(client, seller)
    assert c["status"] == "connected" and c["provider"] == "sandbox_channel"
    assert "product_listing" in c["capabilities"] and "refunds" not in c["capabilities"]
    assert not any("sbx-at-" in str(v) for v in c.values())  # tokens never leave the server
    with session_scope() as db:
        row = db.get(ChannelConnection, uuid.UUID(c["id"]))
        assert row.access_token_sealed and "sbx-at-" not in row.access_token_sealed
    # State is single use.
    r = client.post(
        f"{API}/channels/oauth/callback",
        headers=seller.h(),
        json={"provider": "sandbox_channel", "state": c["_state"], "code": c["_code"]},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "oauth_state_invalid"


def test_oauth_state_is_bound_to_merchant_and_user(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    r = client.post(
        f"{API}/channels/connect",
        headers=a.h(),
        json={"provider": "sandbox_channel", "redirect_uri": REDIRECT},
    ).json()
    q = parse_qs(urlparse(client.get(r["authorize_url"], follow_redirects=False).headers["location"]).query)
    stolen = client.post(
        f"{API}/channels/oauth/callback",
        headers=b.h(),
        json={"provider": "sandbox_channel", "state": q["state"][0], "code": q["code"][0]},
    )
    assert stolen.status_code == 400 and stolen.json()["error"]["code"] == "oauth_state_invalid"


def test_channel_limit_and_bad_redirect(client, seller):
    r = client.post(
        f"{API}/channels/connect",
        headers=seller.h(),
        json={"provider": "sandbox_channel", "redirect_uri": "http://evil.example/cb"},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_redirect_uri"
    connect(client, seller)
    connect(client, seller)  # starter allows 2
    r = client.post(
        f"{API}/channels/connect",
        headers=seller.h(),
        json={"provider": "sandbox_channel", "redirect_uri": REDIRECT},
    )
    assert r.status_code == 402 and r.json()["error"]["details"]["resource"] == "channels"


# ----------------------------------------------------------------------------- publish
def test_publish_then_product_update_resyncs_same_listing(client, seller):
    SandboxChannelAdapter.published.clear()
    c = connect(client, seller)
    p = live_product(client, seller)
    r = client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    assert r.status_code == 202 and r.json()["items"][0]["status"] == "pending"
    _dispatch()
    first = listing(client, seller, p["id"])
    assert first["status"] == "published" and first["external_id"].startswith("sbx-listing-")
    client.patch(
        f"{API}/catalog/products/{p['id']}/variants/{p['variants'][0]['id']}",
        headers=seller.h(),
        json={"price_minor": 599000},
    )
    _dispatch()
    second = listing(client, seller, p["id"])
    assert second["status"] == "published" and second["external_id"] == first["external_id"]
    assert second["published_product_version"] > first["published_product_version"]
    assert len(SandboxChannelAdapter.published) == 1  # updated in place, no duplicate listing
    assert SandboxChannelAdapter.published[first["external_id"]]["variants"][0]["price_minor"] == 599000


def test_only_live_products_publish_and_archive_unpublishes(client, seller):
    c = connect(client, seller)
    draft = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={"title": "Draft", "variants": [{"price_minor": 100}]},
    ).json()
    r = client.post(
        f"{API}/catalog/products/{draft['id']}/publish",
        headers=seller.h(),
        json={"connection_ids": [c["id"]]},
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "product_not_active"
    p = live_product(client, seller)
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    ext = listing(client, seller, p["id"])["external_id"]
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=seller.h(), json={"status": "archived"})
    _dispatch()
    assert listing(client, seller, p["id"])["status"] == "unpublished"
    assert ext not in SandboxChannelAdapter.published


def test_transient_failure_retries_with_backoff(client, seller):
    c = connect(client, seller)
    p = live_product(client, seller)
    SandboxChannelAdapter.failures.push(IntegrationError("rate_limited", retryable=True))
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    lst = listing(client, seller, p["id"])
    assert lst["status"] == "out_of_sync" and lst["last_error_code"] == "rate_limited"
    _dispatch(due_now=True)
    assert listing(client, seller, p["id"])["status"] == "published"


def test_auth_failure_expires_connection_and_reconnect_recovers(client, seller):
    c = connect(client, seller)
    p = live_product(client, seller)
    SandboxChannelAdapter.failures.push(IntegrationError("token_revoked", auth=True))
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    conns = client.get(f"{API}/channels", headers=seller.h()).json()["items"]
    assert conns[0]["status"] == "expired" and conns[0]["needs_reconnect"] is True
    assert listing(client, seller, p["id"])["status"] == "failed"
    with session_scope() as db:
        assert db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "channels.connection_expired"))
    # Reconnect must land on the same account; waiting listings are retried automatically.
    with session_scope() as db:
        acct = db.get(ChannelConnection, uuid.UUID(c["id"])).external_account_id
    original_exchange = SandboxChannelAdapter.exchange_code

    def same_account(self, code, redirect_uri):
        t = original_exchange(self, code, redirect_uri)
        t.external_account_id = acct
        return t

    SandboxChannelAdapter.exchange_code = same_account  # type: ignore[method-assign]
    try:
        again = connect(client, seller, reconnect_id=c["id"])
    finally:
        SandboxChannelAdapter.exchange_code = original_exchange  # type: ignore[method-assign]
    assert again["id"] == c["id"] and again["status"] == "connected"
    _dispatch()
    assert listing(client, seller, p["id"])["status"] == "published"


def test_cannot_publish_to_another_merchants_connection(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    ca = connect(client, a)
    pb = live_product(client, b)
    r = client.post(
        f"{API}/catalog/products/{pb['id']}/publish", headers=b.h(), json={"connection_ids": [ca["id"]]}
    )
    assert r.status_code == 404


# ----------------------------------------------------------------------------- token refresh
def test_token_refresh_and_revocation(client, seller):
    from app.domains.channels.service import refresh_due_tokens

    c = connect(client, seller)
    with session_scope() as db:
        db.execute(update(ChannelConnection).values(token_expires_at=utcnow() + timedelta(minutes=2)))
    with session_scope() as db:
        assert refresh_due_tokens(db) == {"refreshed": 1, "expired": 0, "retry": 0}
        conn = db.get(ChannelConnection, uuid.UUID(c["id"]))
        assert conn.token_expires_at > utcnow() + timedelta(minutes=30)
    SandboxChannelAdapter.failures.push(IntegrationError("timeout", retryable=True))
    with session_scope() as db:
        db.execute(update(ChannelConnection).values(token_expires_at=utcnow()))
    with session_scope() as db:
        assert refresh_due_tokens(db) == {
            "refreshed": 0,
            "expired": 0,
            "retry": 1,
        }  # transient: try again later
    SandboxChannelAdapter.failures.push(IntegrationError("invalid_grant", auth=True))
    with session_scope() as db:
        assert refresh_due_tokens(db) == {"refreshed": 0, "expired": 1, "retry": 0}
    assert client.get(f"{API}/channels", headers=seller.h()).json()["items"][0]["status"] == "expired"


# ----------------------------------------------------------------------------- webhooks
def _webhook(client, payload: dict, headers: dict | None = None):
    body = json.dumps(payload).encode()
    return client.post("/webhooks/sandbox_channel", content=body, headers=headers or sign(body))


def test_webhook_signature_dedupe_and_deauthorization(client, seller):
    c = connect(client, seller)
    with session_scope() as db:
        acct = db.get(ChannelConnection, uuid.UUID(c["id"])).external_account_id
    evt = {"id": "evt_001", "type": "account.deauthorized", "account_id": acct, "data": {}}
    bad = _webhook(client, evt, headers={"X-Sandbox-Signature": "0" * 64})
    assert bad.status_code == 401
    with session_scope() as db:
        assert db.scalar(select(WebhookEvent)) is None  # unverified payloads are never stored
    ok = _webhook(client, evt)
    dup = _webhook(client, evt)
    assert ok.json() == {"received": True, "accepted": 1, "duplicates": 0}
    assert dup.json() == {"received": True, "accepted": 0, "duplicates": 1}
    _dispatch()
    with session_scope() as db:
        rows = db.scalars(select(WebhookEvent)).all()
        assert len(rows) == 1 and rows[0].status == "processed" and rows[0].duplicate_count == 1
    assert client.get(f"{API}/channels", headers=seller.h()).json()["items"][0]["status"] == "expired"


def test_webhook_unknown_type_ignored_and_failing_handler_dead_letters(client, seller, monkeypatch):
    from app.domains.channels import service

    c = connect(client, seller)
    with session_scope() as db:
        acct = db.get(ChannelConnection, uuid.UUID(c["id"])).external_account_id
    _webhook(client, {"id": "evt_x", "type": "something.new", "account_id": acct, "data": {}})
    _webhook(client, {"id": "evt_y", "type": "order.created", "account_id": "unknown-account", "data": {}})

    def boom(db, ev):
        raise RuntimeError("downstream bug")

    monkeypatch.setitem(service._WEBHOOK_HANDLERS, "order.created", boom)
    monkeypatch.setattr(service, "MAX_WEBHOOK_ATTEMPTS", 2)
    _webhook(client, {"id": "evt_z", "type": "order.created", "account_id": acct, "data": {"n": 1}})
    _dispatch()
    _dispatch(due_now=True)
    with session_scope() as db:
        by_id = {e.external_event_id: e for e in db.scalars(select(WebhookEvent))}
    assert by_id["evt_x"].status == "ignored"
    assert by_id["evt_y"].status == "ignored" and "no connection" in by_id["evt_y"].last_error
    assert by_id["evt_z"].status == "dead" and by_id["evt_z"].attempts == 2
    assert "downstream bug" in by_id["evt_z"].last_error
    # Fix deployed → staff replays the dead event.
    monkeypatch.setitem(service._WEBHOOK_HANDLERS, "order.created", lambda db, ev: None)
    with session_scope() as db:
        service.replay_webhook(db, by_id["evt_z"].id)
    _dispatch()
    with session_scope() as db:
        assert db.get(WebhookEvent, by_id["evt_z"].id).status == "processed"


def test_listing_rows_are_tenant_scoped(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    ca = connect(client, a)
    pa = live_product(client, a)
    client.post(
        f"{API}/catalog/products/{pa['id']}/publish", headers=a.h(), json={"connection_ids": [ca["id"]]}
    )
    assert client.get(f"{API}/catalog/products/{pa['id']}/listings", headers=b.h()).json()["items"] == []
    with session_scope() as db:
        assert db.scalar(select(ChannelListing)).merchant_id == uuid.UUID(a.merchant_id)
