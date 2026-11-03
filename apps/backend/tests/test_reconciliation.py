"""CHN-012: listings are compared with the channel's copy; drift is reported, never silently overwritten."""

from __future__ import annotations

from app.core.db import session_scope
from app.domains.channels.service import reconcile_all
from app.domains.integrations.base import IntegrationError
from app.domains.integrations.sandbox import SandboxChannelAdapter
from tests.conftest import onboard
from tests.test_channels import API, _dispatch, connect, listing, live_product


def published(client, s) -> tuple[dict, dict, dict]:
    conn = connect(client, s)
    p = live_product(client, s)
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=s.h(), json={"connection_ids": [conn["id"]]}
    )
    _dispatch()
    lst = listing(client, s, p["id"])
    assert lst["status"] == "published" and lst["drift"] is None
    return conn, p, lst


def run() -> dict[str, int]:
    with session_scope() as db:
        return reconcile_all(db)


def exceptions(client, s) -> list[dict]:
    return [
        e
        for e in client.get(f"{API}/exceptions", headers=s.h()).json()["items"]
        if e["type"] == "listing_drift"
    ]


def test_in_sync_listing_has_no_drift(client, seller):
    _, p, _ = published(client, seller)
    stats = run()
    assert stats["checked"] >= 1 and stats["drift"] == 0
    lst = listing(client, seller, p["id"])
    assert lst["drift"] is None and lst["last_reconciled_at"]


def test_price_changed_on_channel_is_reported_not_overwritten(client, seller):
    _, p, lst = published(client, seller)
    SandboxChannelAdapter.published[lst["external_id"]]["variants"][0]["price_minor"] = 600000
    assert run()["drift"] == 1
    after = listing(client, seller, p["id"])
    assert after["drift"]["code"] == "price_changed"
    assert after["drift"]["details"]["prices"] == [
        {"sku": "PASH-01", "expected_minor": 650000, "channel_minor": 600000}
    ]
    # Never auto-overwritten: the channel still has the seller's edit.
    assert SandboxChannelAdapter.published[lst["external_id"]]["variants"][0]["price_minor"] == 600000
    exc = exceptions(client, seller)
    assert (
        len(exc) == 1
        and exc[0]["action"] == "resolve_drift"
        and exc[0]["details"]["drift_code"] == "price_changed"
    )
    run()  # same drift again: no duplicate event
    from sqlalchemy import func, select

    from app.domains.platform.models import OutboxEvent

    with session_scope() as db:
        n = db.scalar(
            select(func.count())
            .select_from(OutboxEvent)
            .where(OutboxEvent.event_type == "listings.drift_detected")
        )
    assert n == 1


def test_push_overwrites_channel_and_clears_drift(client, seller):
    conn, p, lst = published(client, seller)
    SandboxChannelAdapter.published[lst["external_id"]]["variants"][0]["price_minor"] = 1
    run()
    r = client.post(
        f"{API}/catalog/products/{p['id']}/listings/{conn['id']}/resolve-drift",
        headers=seller.h(),
        json={"action": "push"},
    )
    assert r.status_code == 200 and r.json()["drift"] is None
    _dispatch()
    assert SandboxChannelAdapter.published[lst["external_id"]]["variants"][0]["price_minor"] == 650000
    assert listing(client, seller, p["id"])["status"] == "published"
    assert exceptions(client, seller) == []
    assert run()["drift"] == 0


def test_deleted_on_channel_push_recreates_and_accept_unpublishes(client, seller):
    conn, p, lst = published(client, seller)
    SandboxChannelAdapter.published.pop(lst["external_id"])
    run()
    assert listing(client, seller, p["id"])["drift"]["code"] == "missing_on_channel"
    url = f"{API}/catalog/products/{p['id']}/listings/{conn['id']}/resolve-drift"
    client.post(url, headers=seller.h(), json={"action": "push"})
    _dispatch()
    again = listing(client, seller, p["id"])
    assert again["status"] == "published" and again["external_id"] in SandboxChannelAdapter.published

    SandboxChannelAdapter.published.pop(again["external_id"])
    run()
    r = client.post(url, headers=seller.h(), json={"action": "accept"})
    assert r.json()["status"] == "unpublished" and r.json()["desired_state"] == "unpublished"
    assert (
        client.post(url, headers=seller.h(), json={"action": "accept"}).json()["error"]["code"] == "no_drift"
    )


def test_hidden_on_channel_and_self_healing(client, seller):
    _, p, lst = published(client, seller)
    doc = SandboxChannelAdapter.published[lst["external_id"]]
    doc["_visible"] = False
    run()
    assert listing(client, seller, p["id"])["drift"]["code"] == "hidden_on_channel"
    doc["_visible"] = True  # seller fixed it on the channel themselves
    assert run()["cleared"] == 1
    assert listing(client, seller, p["id"])["drift"] is None


def test_variant_sku_removed_on_channel(client, seller):
    _, p, lst = published(client, seller)
    SandboxChannelAdapter.published[lst["external_id"]]["variants"][0]["sku"] = "RENAMED"
    run()
    d = listing(client, seller, p["id"])["drift"]
    assert d["code"] == "variants_changed"
    assert d["details"] == {"missing_skus": ["PASH-01"], "extra_skus": ["RENAMED"]}


def test_provider_auth_failure_during_reconcile_expires_connection(client, seller):
    _, p, _ = published(client, seller)
    SandboxChannelAdapter.failures.push(IntegrationError("invalid_token", auth=True))
    stats = run()
    assert stats["skipped"] >= 1
    c = client.get(f"{API}/channels", headers=seller.h()).json()["items"][0]
    assert c["status"] == "expired"
    assert listing(client, seller, p["id"])["drift"] is None  # an outage is not drift


def test_manual_reconcile_and_tenant_isolation(client):
    a = onboard(client, shop="Asan Goods")
    b = onboard(client, shop="Patan Goods")
    conn, p, lst = published(client, a)
    SandboxChannelAdapter.published[lst["external_id"]]["variants"][0]["price_minor"] = 5
    # Another merchant can't trigger a check or resolve drift on a's listing.
    assert client.post(f"{API}/channels/{conn['id']}/reconcile", headers=b.h()).status_code == 404
    r = client.post(f"{API}/channels/{conn['id']}/reconcile", headers=a.h())
    assert r.status_code == 202
    _dispatch()
    assert listing(client, a, p["id"])["drift"]["code"] == "price_changed"
    resolve = f"{API}/catalog/products/{p['id']}/listings/{conn['id']}/resolve-drift"
    assert client.post(resolve, headers=b.h(), json={"action": "push"}).status_code == 404
    assert client.post(resolve, headers=a.h(), json={"action": "nope"}).status_code == 400
    assert exceptions(client, b) == []
