"""Messenger + Instagram DMs through Nivaro's Meta app: one-click connect, app webhook, agent replies."""

from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.domains.integrations import meta
from tests.conftest import set_plan
from tests.test_channels import _dispatch
from tests.test_inbox import kurta

API = "/api/v1"
APP_SECRET = "nivaro-meta-app-secret-0123456789"
PAGE_ID = "104857600999999"
IG_ID = "17841400000000999"
PAGE_TOKEN = "EAAB-page-token-from-oauth-000000000000"


class FakeMeta:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.subscribed: list[str] = []
        self.approved = True

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path.removeprefix("/v21.0/")
        q = dict(req.url.params)
        if path == "oauth/access_token":
            if q.get("client_secret") != APP_SECRET:
                return httpx.Response(400, json={"error": {"code": 1}})
            if q.get("grant_type") == "fb_exchange_token":
                return httpx.Response(200, json={"access_token": "long-user-token"})
            return httpx.Response(200, json={"access_token": "short-user-token"})
        if path == "me/accounts" and q.get("access_token") == "long-user-token":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": PAGE_ID,
                            "name": "Thamel Threads",
                            "access_token": PAGE_TOKEN,
                            "instagram_business_account": {"id": IG_ID, "username": "thamelthreads"},
                        }
                    ]
                },
            )
        if path == f"{PAGE_ID}/subscribed_apps" and q.get("access_token") == PAGE_TOKEN:
            self.subscribed.append(parse_qs(req.content.decode())["subscribed_fields"][0])
            return httpx.Response(200, json={"success": True})
        if path == "me/messages" and q.get("access_token") == PAGE_TOKEN:
            if not self.approved:
                return httpx.Response(
                    400, json={"error": {"code": 10, "error_subcode": 2018108, "message": "needs approval"}}
                )
            body = json.loads(req.content)
            self.sent.append({"to": body["recipient"]["id"], "text": body["message"]["text"]})
            return httpx.Response(
                200, json={"recipient_id": body["recipient"]["id"], "message_id": f"m_{len(self.sent)}"}
            )
        return httpx.Response(404, json={"error": {"code": 100}})


@pytest.fixture
def fb(monkeypatch):
    f = FakeMeta()
    monkeypatch.setattr(meta, "transport_override", httpx.MockTransport(f))
    s = get_settings()
    monkeypatch.setattr(s, "meta_app_id", "123456789012345")
    monkeypatch.setattr(s, "meta_app_secret", SecretStr(APP_SECRET))
    monkeypatch.setattr(s, "meta_verify_token", SecretStr("verify-me-please"))
    return f


def _one_click(client, s, with_instagram=True):
    start = client.post(
        f"{API}/channels/meta/oauth/start",
        headers=s.h(),
        json={"redirect_uri": "http://localhost:3010/settings/channels/meta"},
    )
    assert start.status_code == 200, start.text
    url = urlparse(start.json()["authorize_url"])
    q = parse_qs(url.query)
    assert (
        url.netloc == "www.facebook.com"
        and "pages_messaging" in q["scope"][0]
        and "instagram_manage_messages" in q["scope"][0]
    )
    pages = client.post(
        f"{API}/channels/meta/oauth/pages", headers=s.h(), json={"state": q["state"][0], "code": "the-code"}
    )
    assert pages.status_code == 200, pages.text
    body = pages.json()
    assert body["pages"] == [{"id": PAGE_ID, "name": "Thamel Threads", "instagram": "thamelthreads"}]
    assert PAGE_TOKEN not in pages.text  # Page tokens never reach the browser
    r = client.post(
        f"{API}/channels/meta/oauth/connect",
        headers=s.h(),
        json={"selection": body["selection"], "page_id": PAGE_ID, "with_instagram": with_instagram},
    )
    assert r.status_code == 201, r.text
    return r.json()["items"], body["selection"]


def _signed(body: dict) -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"X-Hub-Signature-256": sig, "Content-Type": "application/json"}


def _dm(obj: str, account: str, sender: str, mid: str, text: str) -> dict:
    return {
        "object": obj,
        "entry": [
            {
                "id": account,
                "time": 1,
                "messaging": [
                    {
                        "sender": {"id": sender},
                        "recipient": {"id": account},
                        "timestamp": 1,
                        "message": {"mid": mid, "text": text},
                    }
                ],
            }
        ],
    }


def test_one_click_connect_brings_messenger_and_instagram_dms_into_the_inbox(client, seller, fb):
    set_plan(seller.merchant_id, "growth")
    client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "smart"})
    kurta(client, seller)
    assert client.get(f"{API}/channels/meta/status", headers=seller.h()).json() == {
        "one_click_available": True
    }
    items, selection = _one_click(client, seller)
    assert [(c["provider"], sorted(c["capabilities"])) for c in items] == [
        ("facebook_page", ["content_publish", "messages"]),
        ("instagram", ["content_publish", "messages"]),
    ]
    assert fb.subscribed == ["messages,messaging_postbacks"]
    # The selection is one-time.
    again = client.post(
        f"{API}/channels/meta/oauth/connect",
        headers=seller.h(),
        json={"selection": selection, "page_id": PAGE_ID},
    )
    assert again.json()["error"]["code"] == "meta_selection_expired"
    # Meta's callback check, then a signed Messenger DM.
    ok = client.get(
        "/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me-please", "hub.challenge": "42"},
    )
    assert ok.text == "42"
    assert (
        client.get(
            "/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"}
        ).status_code
        == 403
    )
    raw, headers = _signed(_dm("page", PAGE_ID, "psid-777", "mid.1", "Dhaka kurta XL cha?"))
    assert (
        client.post(
            "/webhooks/meta", content=raw, headers={**headers, "X-Hub-Signature-256": "sha256=00"}
        ).status_code
        == 401
    )
    assert client.post("/webhooks/meta", content=raw, headers=headers).json()["accepted"] == 1
    _dispatch()
    _dispatch()
    assert fb.sent[-1]["to"] == "psid-777" and "Rs 2,450" in fb.sent[-1]["text"]
    # Instagram DM to the linked account.
    raw, headers = _signed(_dm("instagram", IG_ID, "igsid-55", "mid.ig1", "Dhaka kurta M cha?"))
    assert client.post("/webhooks/meta", content=raw, headers=headers).json()["accepted"] == 1
    _dispatch()
    _dispatch()
    assert fb.sent[-1]["to"] == "igsid-55"
    convs = client.get(f"{API}/conversations", params={"status": "all"}, headers=seller.h()).json()["items"]
    assert {c["provider"] for c in convs} >= {"facebook_page", "instagram"}


def test_echoes_and_unknown_pages_are_ignored(client, seller, fb):
    _one_click(client, seller)
    echo = _dm("page", PAGE_ID, "psid-1", "mid.e", "our own reply")
    echo["entry"][0]["messaging"][0]["message"]["is_echo"] = True
    raw, headers = _signed(echo)
    assert client.post("/webhooks/meta", content=raw, headers=headers).json()["accepted"] == 0
    raw, headers = _signed(_dm("page", "999999999999", "psid-2", "mid.u", "hello"))
    assert (
        client.post("/webhooks/meta", content=raw, headers=headers).json()["accepted"] == 1
    )  # stored, unrouted
    _dispatch()
    assert (
        client.get(f"{API}/conversations", params={"status": "all"}, headers=seller.h()).json()["items"] == []
    )


def test_replies_before_meta_approval_fail_plainly(client, seller, fb):
    from sqlalchemy import text

    from app.core.db import session_scope

    set_plan(seller.merchant_id, "growth")
    _one_click(client, seller, with_instagram=False)
    fb.approved = False
    raw, headers = _signed(_dm("page", PAGE_ID, "psid-9", "mid.9", "hello"))
    client.post("/webhooks/meta", content=raw, headers=headers)
    _dispatch()
    conv = client.get(f"{API}/conversations", params={"status": "all"}, headers=seller.h()).json()["items"][0]
    client.post(f"{API}/conversations/{conv['id']}/messages", headers=seller.h(), json={"text": "Namaste!"})
    _dispatch()
    with session_scope() as db:
        m = db.execute(
            text(
                "select status, error_code from messages where direction = 'out' order by created_at desc limit 1"
            )
        ).one()
    assert (m.status, m.error_code) == ("failed", "messaging_not_approved")


def test_one_click_is_hidden_until_the_app_is_configured(client, seller):
    assert client.get(f"{API}/channels/meta/status", headers=seller.h()).json() == {
        "one_click_available": False
    }
    r = client.post(
        f"{API}/channels/meta/oauth/start",
        headers=seller.h(),
        json={"redirect_uri": "http://localhost:3010/x"},
    )
    assert r.json()["error"]["code"] == "meta_app_not_configured"


def test_pasted_page_token_connections_cannot_receive_dms(client, seller, monkeypatch):
    from tests.test_autopost_meta import FakeGraph, _connect

    monkeypatch.setattr(meta, "transport_override", httpx.MockTransport(FakeGraph()))
    items = _connect(client, seller).json()["items"]
    assert all(c["capabilities"] == ["content_publish"] for c in items)
