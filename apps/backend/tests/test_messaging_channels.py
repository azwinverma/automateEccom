"""Converse over real messaging channels the seller connects themselves: Telegram and WhatsApp Cloud."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.core.db import session_scope
from app.domains.integrations import messaging
from tests.conftest import onboard, set_plan
from tests.test_channels import _dispatch
from tests.test_inbox import kurta

API = "/api/v1"
BOT_TOKEN = "7012345678:AAH-test-bot-token-0123456789abcdef"
WA_TOKEN = "EAAG-test-whatsapp-permanent-token-0123456789"
APP_SECRET = "meta-app-secret-0123456789abcdef"


class FakeProviders:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.webhook: dict | None = None
        self.subscribed = False

    def __call__(self, req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if "api.telegram.org" in url:
            if f"/bot{BOT_TOKEN}/" not in url:
                return httpx.Response(404, json={"ok": False, "error_code": 404, "description": "Not Found"})
            body = json.loads(req.content or b"{}")
            if url.endswith("/getMe"):
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "result": {"id": 7012345678, "username": "thamel_threads_bot", "is_bot": True},
                    },
                )
            if url.endswith("/setWebhook"):
                self.webhook = body
                return httpx.Response(200, json={"ok": True, "result": True})
            if url.endswith("/sendMessage"):
                self.sent.append({"to": str(body["chat_id"]), "text": body["text"]})
                return httpx.Response(200, json={"ok": True, "result": {"message_id": len(self.sent) + 100}})
        if "graph.facebook.com" in url:
            if req.headers.get("authorization") != f"Bearer {WA_TOKEN}":
                return httpx.Response(
                    401, json={"error": {"code": 190, "message": "Invalid OAuth access token"}}
                )
            if req.method == "GET" and url.split("?")[0].endswith("/1098765432"):
                return httpx.Response(
                    200,
                    json={
                        "id": "1098765432",
                        "display_phone_number": "+977 980-0000000",
                        "verified_name": "Thamel Threads",
                    },
                )
            if url.endswith("/subscribed_apps"):
                self.subscribed = True
                return httpx.Response(200, json={"success": True})
            if url.endswith("/1098765432/messages"):
                body = json.loads(req.content)
                if body["to"] == "9779800000999":  # customer last wrote > 24 h ago
                    return httpx.Response(
                        400, json={"error": {"code": 131047, "message": "Re-engagement message"}}
                    )
                self.sent.append({"to": body["to"], "text": body["text"]["body"]})
                return httpx.Response(200, json={"messages": [{"id": f"wamid.{len(self.sent)}"}]})
        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch):
    f = FakeProviders()
    monkeypatch.setattr(messaging, "transport_override", httpx.MockTransport(f))
    return f


def _connect(client, s, provider, fields):
    return client.post(
        f"{API}/channels/connect-messaging", headers=s.h(), json={"provider": provider, "fields": fields}
    )


def test_telegram_bot_connects_and_the_sales_agent_answers_customers(client, seller, fake):
    set_plan(seller.merchant_id, "growth")
    client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "smart"})
    kurta(client, seller)
    assert (
        _connect(client, seller, "telegram", {"bot_token": "123:wrong-token-value"}).json()["error"]["code"]
        == "invalid_api_keys"
    )
    r = _connect(client, seller, "telegram", {"bot_token": BOT_TOKEN})
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["display_name"] == "Telegram @thamel_threads_bot" and c["capabilities"] == ["messages"]
    assert BOT_TOKEN not in r.text
    _dispatch()  # channels.connected → setWebhook with our per-connection secret
    assert fake.webhook and fake.webhook["url"].endswith(f"/webhooks/telegram/{c['id']}")
    secret = fake.webhook["secret_token"]
    with session_scope() as db:
        sealed = db.execute(
            text("select access_token_sealed from channel_connections where id = :i"), {"i": c["id"]}
        ).scalar()
    assert BOT_TOKEN not in sealed
    update = {
        "update_id": 5001,
        "message": {
            "message_id": 11,
            "from": {"id": 4242, "first_name": "Bikash", "last_name": "Rai"},
            "chat": {"id": 4242, "type": "private"},
            "date": 1763600000,
            "text": "Dhaka kurta XL cha?",
        },
    }
    path = f"/webhooks/telegram/{c['id']}"
    assert (
        client.post(path, json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "forged"}).status_code
        == 401
    )
    ok = client.post(path, json=update, headers={"X-Telegram-Bot-Api-Secret-Token": secret})
    assert ok.status_code == 200 and ok.json()["accepted"] == 1
    assert (
        client.post(path, json=update, headers={"X-Telegram-Bot-Api-Secret-Token": secret}).json()[
            "duplicates"
        ]
        == 1
    )
    _dispatch()
    _dispatch()
    assert fake.sent and fake.sent[-1]["to"] == "4242" and "Rs 2,450" in fake.sent[-1]["text"]
    conv = client.get(f"{API}/conversations", params={"status": "all"}, headers=seller.h()).json()["items"][0]
    assert conv["customer"]["display_name"] == "Bikash Rai"
    # Group chats aren't customer conversations.
    group = {
        **update,
        "update_id": 5002,
        "message": {**update["message"], "chat": {"id": -100, "type": "group"}},
    }
    assert (
        client.post(path, json=group, headers={"X-Telegram-Bot-Api-Secret-Token": secret}).json()["accepted"]
        == 0
    )


def _wa_body(msg_id: str, wa_id: str, text_: str) -> bytes:
    return json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA-1",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "1098765432"},
                                "contacts": [{"wa_id": wa_id, "profile": {"name": "Sita Gurung"}}],
                                "messages": [
                                    {
                                        "from": wa_id,
                                        "id": msg_id,
                                        "timestamp": "1763600000",
                                        "type": "text",
                                        "text": {"body": text_},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
    ).encode()


def test_whatsapp_cloud_with_the_sellers_own_app(client, seller, fake):
    set_plan(seller.merchant_id, "growth")
    client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "smart"})
    kurta(client, seller)
    missing = _connect(client, seller, "whatsapp_cloud", {"access_token": WA_TOKEN}).json()["error"]
    assert missing["code"] == "missing_fields" and set(missing["details"]["fields"]) == {
        "app_secret",
        "phone_number_id",
    }
    fields = {
        "access_token": WA_TOKEN,
        "app_secret": APP_SECRET,
        "phone_number_id": "1098765432",
        "business_account_id": "WABA-1",
    }
    r = _connect(client, seller, "whatsapp_cloud", fields)
    assert r.status_code == 201, r.text
    c = r.json()
    assert "Thamel Threads" in c["display_name"] and WA_TOKEN not in r.text and APP_SECRET not in r.text
    _dispatch()
    assert fake.subscribed
    setup = client.get(f"{API}/channels/{c['id']}/webhook-setup", headers=seller.h()).json()
    path = f"/webhooks/whatsapp_cloud/{c['id']}"
    assert setup["callback_url"].endswith(path)
    # Meta's one-time verification.
    q = {"hub.mode": "subscribe", "hub.challenge": "12345", "hub.verify_token": setup["verify_token"]}
    assert client.get(path, params=q).text == "12345"
    assert client.get(path, params={**q, "hub.verify_token": "nope"}).status_code == 403
    body = _wa_body("wamid.IN1", "9779800000001", "Dhaka kurta XL cha?")
    good = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert (
        client.post(
            path,
            content=body,
            headers={"X-Hub-Signature-256": "sha256=00", "Content-Type": "application/json"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            path, content=body, headers={"X-Hub-Signature-256": good, "Content-Type": "application/json"}
        ).json()["accepted"]
        == 1
    )
    _dispatch()
    _dispatch()
    assert fake.sent[-1]["to"] == "9779800000001" and "Rs 2,450" in fake.sent[-1]["text"]


def test_whatsapp_reply_outside_24h_window_fails_plainly(client, seller, fake):

    set_plan(seller.merchant_id, "growth")
    fields = {"access_token": WA_TOKEN, "app_secret": APP_SECRET, "phone_number_id": "1098765432"}
    c = _connect(client, seller, "whatsapp_cloud", fields).json()
    _dispatch()
    body = _wa_body("wamid.IN9", "9779800000999", "hello")
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    client.post(
        f"/webhooks/whatsapp_cloud/{c['id']}",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    _dispatch()
    conv = client.get(f"{API}/conversations", params={"status": "all"}, headers=seller.h()).json()["items"][0]
    r = client.post(
        f"{API}/conversations/{conv['id']}/messages", headers=seller.h(), json={"text": "Namaste!"}
    )
    assert r.status_code == 201, r.text
    _dispatch()
    with session_scope() as db:
        m = db.execute(
            text(
                "select status, error_code from messages where direction = 'out' order by created_at desc limit 1"
            )
        ).one()
    assert (m.status, m.error_code) == ("failed", "outside_reply_window")


def test_one_bot_one_shop(client, seller, fake):
    assert _connect(client, seller, "telegram", {"bot_token": BOT_TOKEN}).status_code == 201
    other = onboard(client, shop="Patan Crafts")
    r = _connect(client, other, "telegram", {"bot_token": BOT_TOKEN})
    assert r.status_code == 409 and r.json()["error"]["code"] == "account_in_use"
    assert uuid.UUID(seller.merchant_id)
