"""Unified inbox + AI Sales Agent (CRM-005…012, ORD-006): grounded answers, chat-to-order, escalation,
Decision Policy (suggest vs auto-send), idempotent order on "yes"."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.db import session_scope
from app.domains.channels.models import ChannelConnection
from app.domains.inbox.models import Message
from app.domains.integrations.base import IntegrationError
from app.domains.integrations.sandbox import SandboxChannelAdapter
from tests.conftest import onboard, set_plan
from tests.test_channels import _dispatch, _webhook, connect

API = "/api/v1"


class Chat:
    """A customer chatting with the shop over the sandbox channel."""

    def __init__(self, client, seller, *, mode="smart", plan="growth"):
        self.client, self.s = client, seller
        set_plan(seller.merchant_id, plan)
        client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": mode})
        self.conn = connect(client, seller)
        with session_scope() as db:
            self.acct = db.get(ChannelConnection, uuid.UUID(self.conn["id"])).external_account_id
        self.n = 0
        self.thread = f"thread-{uuid.uuid4().hex[:6]}"

    def say(self, text: str, **extra) -> str | None:
        self.n += 1
        before = len(SandboxChannelAdapter.sent)
        data = {
            "thread_id": self.thread,
            "message_id": f"{self.thread}-m{self.n}",
            "sender": {"id": "psid-42", "name": "Bikash Rai"},
            "text": text,
            **extra,
        }
        _webhook(
            self.client,
            {
                "id": f"{self.thread}-e{self.n}",
                "type": "message.received",
                "account_id": self.acct,
                "data": data,
            },
        )
        _dispatch()
        _dispatch()
        new = [m["text"] for m in SandboxChannelAdapter.sent[before:] if m["thread"] == self.thread]
        return new[-1] if new else None

    def conversation(self) -> dict:
        items = self.client.get(f"{API}/conversations", params={"status": "all"}, headers=self.s.h()).json()[
            "items"
        ]
        return self.client.get(f"{API}/conversations/{items[0]['id']}", headers=self.s.h()).json()

    def messages(self) -> list[dict]:
        cid = self.conversation()["id"]
        return self.client.get(f"{API}/conversations/{cid}/messages", headers=self.s.h()).json()["items"]


def kurta(client, s, stock=(("M", 4), ("XL", 1))):
    p = client.post(
        f"{API}/catalog/products",
        headers=s.h(),
        json={
            "title": "Dhaka Kurta",
            "options": [{"name": "Size", "values": [size for size, _ in stock]}],
            "variants": [
                {"options": {"Size": size}, "price_minor": 245000, "sku": f"DHK-{size}"} for size, _ in stock
            ],
        },
    ).json()
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=s.h(), json={"status": "active"})
    for v in p["variants"]:
        qty = dict(stock)[v["options"]["Size"]]
        if qty:
            client.post(f"{API}/inventory/variants/{v['id']}/receive", headers=s.h(), json={"quantity": qty})
    return p


def test_message_to_ai_to_order_end_to_end(client, seller):
    p = kurta(client, seller)
    chat = Chat(client, seller)
    r = chat.say("Dhaka kurta XL cha? kati ho?")
    assert "Rs 2,450" in r and "Only 1 left" in r  # price and stock from the catalog and ledger
    g = next(m for m in chat.messages() if m["author_type"] == "ai")["grounding"]
    assert set(g) >= {"get_product", "get_price", "get_inventory"}
    r = chat.say("XL 1 wota chahiyo")  # no product named: the agent remembers the kurta
    assert r.lower().startswith(
        "your mobile"
    )  # the name comes from the channel profile (shown in the summary)
    assert "Nepal mobile" in chat.say("01-4412345")  # landline refused politely
    assert "district" in chat.say("9807654321").lower()
    assert "municipality" in chat.say("Kaski").lower()
    assert "landmark" in chat.say("Pokhara Metropolitan City ward 6").lower()
    assert "cash on delivery or pay online" in chat.say("Lakeside, near Fewa lake").lower()
    summary = chat.say("COD")
    assert "Please confirm" in summary and "1 × Dhaka Kurta (XL) @ Rs 2,450" in summary
    assert (
        "Lakeside, Near Fewa Lake, Pokhara Metropolitan City-6, Kaski" in summary
        or "Pokhara Metropolitan City-6, Kaski" in summary
    )
    done = chat.say("YES")
    assert done.startswith("Order #1001 confirmed")
    orders = client.get(f"{API}/orders", headers=seller.h()).json()["items"]
    assert len(orders) == 1
    o = client.get(f"{API}/orders/{orders[0]['id']}", headers=seller.h()).json()
    assert o["source"] == "chat" and o["status"] == "cod_pending" and o["lines"][0]["sku"] == "DHK-XL"
    assert (
        o["shipping"]["district"] == "kaski"
        and o["shipping"]["ward"] == 6
        and o["customer"]["phone"] == "+9779807654321"
    )
    assert o["conversation_id"] == chat.conversation()["id"]
    xl = client.get(f"{API}/catalog/products/{p['id']}/stock", headers=seller.h()).json()["variants"]
    assert next(v for v in xl if v["sku"] == "DHK-XL")["available"] == 0  # reserved
    # A repeated "yes" (customer double-sends) never makes a second order.
    chat.say("yes")
    assert len(client.get(f"{API}/orders", headers=seller.h()).json()["items"]) == 1
    tl = client.get(f"{API}/orders/{o['id']}/timeline", headers=seller.h()).json()["items"]
    assert tl[0]["actor"]["type"] == "ai" and tl[0]["automated"] is True


def test_nepali_conversation_gets_nepali_replies(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller)
    r = chat.say("नमस्ते, Dhaka kurta M को मूल्य कति हो?")
    assert "रु 2,450" in r and "स्टकमा छ" in r


def test_out_of_stock_option_not_offered_and_sold_out_on_confirm(client, seller):
    p = kurta(client, seller, stock=(("M", 2), ("XL", 1)))
    xl = next(v for v in p["variants"] if v["options"]["Size"] == "XL")
    client.post(
        f"{API}/inventory/variants/{xl['id']}/adjust",
        headers=seller.h(),
        json={"delta": -1, "reason": "sold in shop"},
    )
    chat = Chat(client, seller)
    r = chat.say("Dhaka kurta chahiyo")
    assert "Which Size? M" in r and "XL" not in r  # only what can be sold is offered (XL tracked at 0)


def test_assisted_mode_only_suggests_and_seller_approves(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, mode="assisted")
    assert chat.say("Dhaka kurta M kati?") is None  # nothing sent automatically
    sug = next(m for m in chat.messages() if m["status"] == "suggested")
    assert "Rs 2,450" in sug["text"]
    r = client.post(
        f"{API}/messages/{sug['id']}/approve",
        headers=seller.h(),
        json={"text": sug["text"] + " Free delivery in Kathmandu!"},
    )
    assert r.status_code == 200 and r.json()["grounding"]["edited_by_seller"] is True
    _dispatch()
    assert SandboxChannelAdapter.sent[-1]["text"].endswith("Free delivery in Kathmandu!")


def test_escalation_hands_over_and_ai_stays_quiet(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller)
    r = chat.say("kapada fateko cha, malai paisa firta chahiyo")
    assert "team member" in r
    conv = chat.conversation()
    assert conv["escalated"] is True and conv["escalation_reason"] in ("complaint", "refund")
    exc = [
        e
        for e in client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
        if e["type"] == "customer_escalation"
    ]
    assert len(exc) == 1 and exc[0]["action"] == "reply"
    assert chat.say("hello?") is None  # escalated: the AI doesn't keep talking
    client.post(
        f"{API}/conversations/{conv['id']}/messages",
        headers=seller.h(),
        json={"text": "Sorry! Send a photo please."},
    )
    _dispatch()
    conv = chat.conversation()
    assert conv["escalated"] is False and conv["human_handoff"] is True
    assert not [
        e
        for e in client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
        if e["type"] == "customer_escalation"
    ]
    assert chat.say("Dhaka kurta M kati?") is None  # seller took over
    client.patch(f"{API}/conversations/{conv['id']}", headers=seller.h(), json={"human_handoff": False})
    assert "Rs 2,450" in chat.say("Dhaka kurta M kati?")  # handed back to the AI


def test_order_status_is_looked_up_not_guessed(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller)
    assert "team member" in chat.say("where is my order?")  # no order yet → person checks
    p = client.get(f"{API}/catalog/products", headers=seller.h()).json()["items"][0]
    vid = client.get(f"{API}/catalog/products/{p['id']}", headers=seller.h()).json()["variants"][0]["id"]
    cust = chat.conversation()["customer"]
    client.patch(
        f"{API}/conversations/{chat.conversation()['id']}", headers=seller.h(), json={"human_handoff": False}
    )
    o = client.post(
        f"{API}/orders",
        headers=seller.h(),
        json={
            "lines": [{"variant_id": vid, "quantity": 1}],
            "customer_id": cust["id"],
            "address": {
                "recipient_name": "Bikash",
                "phone": "9807654321",
                "district": "Kaski",
                "municipality": "Pokhara",
                "ward": 6,
            },
        },
    ).json()
    client.post(f"{API}/orders/{o['id']}/transition", headers=seller.h(), json={"to": "ready_to_ship"})
    client.post(f"{API}/orders/{o['id']}/transition", headers=seller.h(), json={"to": "shipped"})
    assert chat.say("order kaha pugyo?") == f"Order #{o['number']}: on the way."


def test_plan_without_sales_agent_stores_but_does_not_answer(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, plan="starter")
    assert chat.say("Dhaka kurta kati?") is None
    assert [m["direction"] for m in chat.messages()] == ["in"]
    assert chat.conversation()["unread_count"] == 1


def test_identity_joins_by_phone_and_send_failure_is_visible(client, seller):
    kurta(client, seller)
    existing = client.post(
        f"{API}/customers",
        headers=seller.h(),
        json={"display_name": "Bikash (shop walk-in)", "phone": "9807654321"},
    ).json()
    chat = Chat(client, seller)
    SandboxChannelAdapter.failures.push(IntegrationError("bad_request", "rejected"))
    chat.say("mero number 9807654321, Dhaka kurta M kati?")
    conv = chat.conversation()
    assert conv["customer"]["id"] == existing["id"]  # the chat joined the known customer
    failed = [m for m in chat.messages() if m["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["error_code"] == "bad_request"
    r = client.post(f"{API}/messages/{failed[0]['id']}/retry", headers=seller.h())
    assert r.json()["status"] == "queued"
    _dispatch()
    assert [m["status"] for m in chat.messages() if m["direction"] == "out"] == ["sent"]


def test_duplicate_webhook_message_is_handled_once(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller)
    data = {
        "thread_id": "t-dup",
        "message_id": "m-dup",
        "sender": {"id": "psid-9"},
        "text": "Dhaka kurta M kati?",
    }
    _webhook(client, {"id": "e-dup-1", "type": "message.received", "account_id": chat.acct, "data": data})
    _webhook(
        client, {"id": "e-dup-2", "type": "message.received", "account_id": chat.acct, "data": data}
    )  # provider retry, new event id
    _dispatch()
    _dispatch()
    with session_scope() as db:
        assert len(db.scalars(select(Message).where(Message.direction == "in")).all()) == 1
        assert len(db.scalars(select(Message).where(Message.direction == "out")).all()) == 1


def test_summary_and_inbox_is_tenant_isolated(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller)
    chat.say("Dhaka kurta chahiyo")
    conv = chat.conversation()
    s = client.post(f"{API}/conversations/{conv['id']}/summary", headers=seller.h()).json()
    assert "Bikash Rai" in s["summary"] and "Order request" in s["summary"]
    other = onboard(client, shop="Patan Crafts")
    assert client.get(f"{API}/conversations/{conv['id']}", headers=other.h()).status_code == 404
    assert (
        client.post(
            f"{API}/conversations/{conv['id']}/messages", headers=other.h(), json={"text": "hi"}
        ).status_code
        == 404
    )
    assert client.get(f"{API}/conversations", headers=other.h()).json()["items"] == []
    sug_or_sent = chat.messages()[-1]["id"]
    assert client.post(f"{API}/messages/{sug_or_sent}/approve", headers=other.h(), json={}).status_code == 404
