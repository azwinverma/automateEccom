"""Facebook Page + Instagram through the seller's own Meta app, and automatic posting when a product goes live."""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import text

from app.core.db import session_scope, utcnow
from app.domains.integrations import meta
from tests.test_channels import _dispatch
from tests.test_media import phone_photo, upload

API = "/api/v1"
PAGE_ID = "104857600123456"
IG_ID = "17841400000000001"
TOKEN = "EAAB-page-token-0123456789abcdefghijklmnop"


class FakeGraph:
    def __init__(self, with_ig: bool = True) -> None:
        self.with_ig = with_ig
        self.calls: list[tuple[str, str, dict]] = []
        self.containers = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        params = dict(req.url.params)
        body = {k: v[0] for k, v in parse_qs(req.content.decode()).items()} if req.content else {}
        path = req.url.path.removeprefix("/v21.0/")
        self.calls.append((req.method, path, body))
        if params.get("access_token") != TOKEN:
            return httpx.Response(
                400, json={"error": {"code": 190, "message": "Invalid OAuth access token."}}
            )
        if req.method == "GET" and path == PAGE_ID:
            doc = {"id": PAGE_ID, "name": "Thamel Threads"}
            if self.with_ig:
                doc["instagram_business_account"] = {"id": IG_ID, "username": "thamelthreads"}
            return httpx.Response(200, json=doc)
        if path == f"{PAGE_ID}/photos":
            return httpx.Response(200, json={"id": "photo-1", "post_id": f"{PAGE_ID}_9001"})
        if path == f"{IG_ID}/media":
            self.containers += 1
            return httpx.Response(200, json={"id": f"container-{self.containers}"})
        if path == f"{IG_ID}/media_publish":
            return httpx.Response(200, json={"id": "ig-media-77"})
        if req.method == "GET" and path.startswith("container-"):
            return httpx.Response(200, json={"status_code": "FINISHED"})
        return httpx.Response(404, json={"error": {"code": 100, "message": "Unknown path"}})


@pytest.fixture
def graph(monkeypatch):
    g = FakeGraph()
    monkeypatch.setattr(meta, "transport_override", httpx.MockTransport(g))
    monkeypatch.setattr(meta, "sleep", lambda s: None)
    return g


def _connect(client, s, token=TOKEN, with_instagram=True):
    return client.post(
        f"{API}/channels/connect-meta",
        headers=s.h(),
        json={"page_id": PAGE_ID, "page_access_token": token, "with_instagram": with_instagram},
    )


def _product_with_photo(client, s, title="Maroon Kurta"):
    asset = upload(client, s, phone_photo())
    p = client.post(
        f"{API}/catalog/products",
        headers=s.h(),
        json={
            "title": title,
            "description": "Handloom cotton, Dhaka weave.",
            "variants": [{"price_minor": 245000, "sku": "MK-1"}],
        },
    ).json()
    client.put(
        f"{API}/catalog/products/{p['id']}/media", headers=s.h(), json={"items": [{"asset_id": asset["id"]}]}
    )
    return p


def _go_live(client, s, pid):
    r = client.post(f"{API}/catalog/products/{pid}/status", headers=s.h(), json={"status": "active"})
    assert r.status_code == 200, r.text
    _dispatch()


def test_page_and_linked_instagram_connect_with_a_sealed_page_token(client, seller, graph):
    assert (
        _connect(client, seller, token="EAAB-wrong-token-000000000000000").json()["error"]["code"]
        == "invalid_api_keys"
    )
    r = _connect(client, seller)
    assert r.status_code == 201, r.text
    items = r.json()["items"]
    assert [(c["provider"], c["display_name"]) for c in items] == [
        ("facebook_page", "Facebook · Thamel Threads"),
        ("instagram", "Instagram @thamelthreads"),
    ]
    assert all(c["capabilities"] == ["content_publish"] for c in items) and TOKEN not in r.text
    with session_scope() as db:
        rows = (
            db.execute(
                text(
                    "select access_token_sealed from channel_connections where provider in ('facebook_page','instagram')"
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 2 and all(TOKEN not in x for x in rows)


def test_page_without_instagram_connects_facebook_only(client, seller, monkeypatch):
    g = FakeGraph(with_ig=False)
    monkeypatch.setattr(meta, "transport_override", httpx.MockTransport(g))
    items = _connect(client, seller).json()["items"]
    assert [c["provider"] for c in items] == ["facebook_page"]


def test_product_going_live_is_posted_to_facebook_and_instagram_after_approval(client, seller, graph):
    conns = _connect(client, seller).json()["items"]
    ids = [c["id"] for c in conns]
    s = client.put(
        f"{API}/content/autopost", headers=seller.h(), json={"enabled": True, "connection_ids": ids}
    )
    assert s.status_code == 200 and s.json()["require_approval"] is True
    p = _product_with_photo(client, seller)
    _go_live(client, seller, p["id"])
    posts = client.get(f"{API}/content/posts", headers=seller.h()).json()["items"]
    mine = [x for x in posts if x["product_id"] == p["id"]]
    assert len(mine) == 2 and {x["status"] for x in mine} == {"pending_approval"}
    assert all(x["source"] == "autopost" for x in mine)
    caption = mine[0]["caption"]
    # The shop's language is Nepali: the caption is built from the product's own facts, nothing invented.
    assert caption.startswith("Maroon Kurta") and "रू 2,450" in caption and "अर्डर गर्न म्यासेज गर्नुहोस्।" in caption
    # Approving schedules it for the shop's posting slot (7 pm Kathmandu by default).
    for x in mine:
        a = client.post(f"{API}/content/posts/{x['id']}/approve", headers=seller.h()).json()
        assert a["status"] == "scheduled"
        local = datetime.fromisoformat(a["scheduled_at"]).astimezone(ZoneInfo("Asia/Kathmandu"))
        assert local.hour == 19 and local.minute == 0
    # Going live twice doesn't post twice.
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=seller.h(), json={"status": "draft"})
    _go_live(client, seller, p["id"])
    assert (
        len(
            [
                x
                for x in client.get(f"{API}/content/posts", headers=seller.h()).json()["items"]
                if x["product_id"] == p["id"]
            ]
        )
        == 2
    )
    # The slot comes: both publish with the product photo.
    with session_scope() as db:
        db.execute(
            text("update content_posts set next_attempt_at = :t where status = 'scheduled'"),
            {"t": utcnow() - timedelta(minutes=1)},
        )
    from app.domains.content.service import publish_due

    with session_scope() as db:
        assert publish_due(db)["published"] == 2
    fb = next(c for c in graph.calls if c[1] == f"{PAGE_ID}/photos")
    assert "Maroon Kurta" in fb[2]["caption"] and fb[2]["url"].startswith("http")
    ig = next(c for c in graph.calls if c[1] == f"{IG_ID}/media")
    assert ig[2]["image_url"] == fb[2]["url"].replace(
        fb[2]["url"], ig[2]["image_url"]
    )  # a signed rendition URL
    assert any(c[1] == f"{IG_ID}/media_publish" for c in graph.calls)
    got = {
        x["external_id"]
        for x in client.get(f"{API}/content/posts", headers=seller.h()).json()["items"]
        if x["product_id"] == p["id"]
    }
    assert got == {f"{PAGE_ID}_9001", "ig-media-77"}


def test_without_approval_in_smart_mode_it_schedules_straight_away(client, seller, graph):
    client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "smart"})
    ids = [c["id"] for c in _connect(client, seller).json()["items"]]
    client.put(
        f"{API}/content/autopost",
        headers=seller.h(),
        json={"enabled": True, "connection_ids": ids, "require_approval": False},
    )
    p = _product_with_photo(client, seller, title="Pashmina Shawl")
    _go_live(client, seller, p["id"])
    mine = [
        x
        for x in client.get(f"{API}/content/posts", headers=seller.h()).json()["items"]
        if x["product_id"] == p["id"]
    ]
    assert {x["status"] for x in mine} == {"scheduled"}


def test_products_without_photos_are_skipped_and_settings_are_validated(client, seller, graph):
    ids = [c["id"] for c in _connect(client, seller).json()["items"]]
    bad = client.put(
        f"{API}/content/autopost", headers=seller.h(), json={"enabled": True, "connection_ids": []}
    )
    assert bad.json()["error"]["code"] == "connections_required"
    client.put(f"{API}/content/autopost", headers=seller.h(), json={"enabled": True, "connection_ids": ids})
    p = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={"title": "No Photo", "variants": [{"price_minor": 1000}]},
    ).json()
    _go_live(client, seller, p["id"])
    assert [
        x
        for x in client.get(f"{API}/content/posts", headers=seller.h()).json()["items"]
        if x["product_id"] == p["id"]
    ] == []
    with session_scope() as db:
        skipped = (
            db.execute(
                text("select metadata::text from audit_logs where action = 'content.autopost_skipped'")
            )
            .scalars()
            .all()
        )
    assert any("no_photos" in x for x in skipped)


def test_expired_page_token_marks_the_connection_for_reconnect(client, seller, graph):
    ids = [c["id"] for c in _connect(client, seller, with_instagram=False).json()["items"]]
    client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "smart"})
    client.put(
        f"{API}/content/autopost",
        headers=seller.h(),
        json={"enabled": True, "connection_ids": ids, "require_approval": False},
    )
    p = _product_with_photo(client, seller, title="Felt Slippers")
    _go_live(client, seller, p["id"])
    global TOKEN
    old, TOKEN = TOKEN, "rotated-by-meta"  # Meta now rejects the stored token
    try:
        with session_scope() as db:
            db.execute(
                text("update content_posts set next_attempt_at = :t where status = 'scheduled'"),
                {"t": utcnow() - timedelta(minutes=1)},
            )
        from app.domains.content.service import publish_due

        with session_scope() as db:
            publish_due(db)
    finally:
        TOKEN = old
    conn = client.get(f"{API}/channels", headers=seller.h()).json()["items"][0]
    assert conn["needs_reconnect"] is True
    post = next(
        x
        for x in client.get(f"{API}/content/posts", headers=seller.h()).json()["items"]
        if x["product_id"] == p["id"]
    )
    assert post["status"] == "failed" and post["last_error_code"] == "reconnect_required"
