"""Retain: win-back and repeat reminders over the customer's own chat channel, with consent and limits."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.db import session_scope
from app.domains.integrations.sandbox import SandboxChannelAdapter
from app.domains.retention import service as retention
from tests.conftest import set_plan
from tests.test_channels import _dispatch
from tests.test_inbox import Chat
from tests.test_orders import item, order

API = "/api/v1"
# 10:00 in Kathmandu (UTC+5:45): inside send hours.
MORNING = datetime(2026, 11, 20, 4, 15, tzinfo=UTC)
NIGHT = datetime(2026, 11, 20, 17, 0, tzinfo=UTC)  # 22:45 in Kathmandu


def _customer_with_old_order(client, seller, chat: Chat, days_ago: int, *, status="delivered") -> str:
    """The chatting customer gets an order placed ``days_ago``."""
    conv = chat.conversation()
    cust_id = conv["customer"]["id"]
    _, vid = item(client, seller, sku=f"OLD-{uuid.uuid4().hex[:5]}")
    o = order(client, seller, vid).json()
    with session_scope() as db:
        db.execute(
            text("update orders set customer_id = :c, placed_at = :t, status = :s where id = :o"),
            {"c": cust_id, "t": MORNING - timedelta(days=days_ago), "s": status, "o": o["id"]},
        )
    return cust_id


def _run(seller, now=MORNING) -> dict:
    with session_scope() as db:
        out = retention.run_merchant(db, uuid.UUID(seller.merchant_id), now)
    _dispatch()
    return out


def _campaign(client, seller, **body) -> dict:
    r = client.post(f"{API}/retention/campaigns", headers=seller.h(), json={"name": "Come back", **body})
    assert r.status_code == 201, r.text
    return r.json()


def test_win_back_messages_lapsed_chat_customers_once_and_counts_the_order(client, seller):
    chat = Chat(client, seller, mode="assist")
    chat.say("Namaste")
    _customer_with_old_order(client, seller, chat, days_ago=75)
    c = _campaign(client, seller, kind="win_back", days=60)
    assert c["status"] == "draft" and "{name}" in c["message_en"]
    pre = client.post(f"{API}/retention/campaigns/{c['id']}/preview", headers=seller.h()).json()
    assert pre["audience"] == 1 and pre["reachable"] == 1 and "Reply STOP" in pre["sample_en"]
    assert _run(seller)["sent"] == 0  # a draft sends nothing
    client.post(f"{API}/retention/campaigns/{c['id']}/status", headers=seller.h(), json={"status": "active"})
    assert _run(seller, NIGHT)["sent"] == 0  # not at night
    before = len(SandboxChannelAdapter.sent)
    assert _run(seller)["sent"] == 1
    sent = [m for m in SandboxChannelAdapter.sent[before:] if m["thread"] == chat.thread]
    assert sent and sent[-1]["text"].startswith("Namaste Bikash!") and "Reply STOP" in sent[-1]["text"]
    assert _run(seller, MORNING + timedelta(days=8))["sent"] == 0  # once per lapse
    # The customer orders within 7 days: the campaign gets the credit.
    _, vid = item(client, seller, sku="NEW-1")
    o = order(client, seller, vid).json()
    with session_scope() as db:
        db.execute(
            text("update orders set customer_id = :c, placed_at = :t where id = :o"),
            {"c": chat.conversation()["customer"]["id"], "t": MORNING + timedelta(days=2), "o": o["id"]},
        )
    from app.domains.platform.outbox import publish

    with session_scope() as db:
        publish(
            db,
            event_type="orders.created",
            aggregate_type="order",
            aggregate_id=o["id"],
            merchant_id=uuid.UUID(seller.merchant_id),
            payload={"order_id": o["id"], "status": "new", "source": "seller"},
        )
    _dispatch()
    stats = client.get(f"{API}/retention/campaigns/{c['id']}", headers=seller.h()).json()["stats"]
    assert (
        stats["sent"] == 1 and stats["orders"] == 1 and stats["revenue_minor"] == o["total"]["amount_minor"]
    )


def test_stop_opts_out_and_campaigns_respect_it(client, seller):
    chat = Chat(client, seller, mode="assist")
    chat.say("Namaste")
    _customer_with_old_order(client, seller, chat, days_ago=90)
    before = len(SandboxChannelAdapter.sent)
    chat.say("STOP")
    confirm = [m for m in SandboxChannelAdapter.sent[before:] if m["thread"] == chat.thread]
    assert confirm and "won't send you offers" in confirm[-1]["text"]
    c = _campaign(client, seller, kind="win_back", days=60)
    client.post(f"{API}/retention/campaigns/{c['id']}/status", headers=seller.h(), json={"status": "active"})
    out = _run(seller)
    assert out["sent"] == 0 and out["skipped"] == 1
    stats = client.get(f"{API}/retention/campaigns/{c['id']}", headers=seller.h()).json()["stats"]
    assert stats["skipped"] == {"opted_out": 1}


def test_frequency_cap_and_daily_limit(client, seller):
    chat = Chat(client, seller, mode="assist")
    chat.say("Namaste")
    _customer_with_old_order(client, seller, chat, days_ago=40, status="delivered")
    a = _campaign(client, seller, kind="repeat_reminder", days=35)
    b = _campaign(client, seller, name="Broadcast", kind="broadcast", segment="all")
    for c in (a, b):
        client.post(
            f"{API}/retention/campaigns/{c['id']}/status", headers=seller.h(), json={"status": "active"}
        )
    out = _run(seller)
    assert out["sent"] == 1 and out["deferred"] == 1  # one message per customer per 7 days
    assert _run(seller, MORNING + timedelta(days=8))["sent"] == 1  # the other one, a week later
    rows = client.get(f"{API}/retention/campaigns", headers=seller.h()).json()["items"]
    assert {r["kind"]: r["stats"]["sent"] for r in rows} == {"repeat_reminder": 1, "broadcast": 1}
    assert next(r for r in rows if r["kind"] == "broadcast")["status"] == "completed"


def test_customers_without_a_chat_channel_are_never_cold_messaged(client, seller):
    set_plan(seller.merchant_id, "growth")
    _, vid = item(client, seller, sku="NOCHAT")
    o = order(client, seller, vid).json()
    with session_scope() as db:
        db.execute(
            text("update orders set placed_at = :t where id = :o"),
            {"t": MORNING - timedelta(days=100), "o": o["id"]},
        )
    c = _campaign(client, seller, kind="win_back", days=60)
    client.post(f"{API}/retention/campaigns/{c['id']}/status", headers=seller.h(), json={"status": "active"})
    out = _run(seller)
    assert out["sent"] == 0 and out["skipped"] == 1
    assert client.get(f"{API}/retention/campaigns/{c['id']}", headers=seller.h()).json()["stats"][
        "skipped"
    ] == {"no_chat_channel": 1}


def test_plan_permissions_and_validation(client, seller):
    from tests.test_returns import member

    set_plan(seller.merchant_id, "starter")
    r = client.post(f"{API}/retention/campaigns", headers=seller.h(), json={"name": "x", "kind": "win_back"})
    assert r.status_code == 402 or r.json()["error"]["code"] == "feature_not_in_plan"
    set_plan(seller.merchant_id, "growth")
    bad = client.post(
        f"{API}/retention/campaigns",
        headers=seller.h(),
        json={"name": "x", "kind": "win_back", "message_en": "Hi {first_name}"},
    )
    assert bad.json()["error"]["code"] == "bad_placeholder"
    c = _campaign(client, seller, kind="win_back")
    assert c["days"] == 60
    staff = member(client, seller, "staff", "staff-rt@example.com")
    assert (
        client.post(
            f"{API}/retention/campaigns/{c['id']}/status", headers=staff.h(), json={"status": "active"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{API}/retention/campaigns", headers=staff.h(), json={"name": "y", "kind": "win_back"}
        ).status_code
        == 403
    )


def test_kill_switch_stops_sending(client, seller):
    from tests.test_ops import _kill

    chat = Chat(client, seller, mode="assist")
    chat.say("Namaste")
    _customer_with_old_order(client, seller, chat, days_ago=70)
    c = _campaign(client, seller, kind="win_back", days=60)
    client.post(f"{API}/retention/campaigns/{c['id']}/status", headers=seller.h(), json={"status": "active"})
    _kill("ops.campaigns")
    assert _run(seller)["sent"] == 0
    _kill("ops.campaigns", on=False)
    assert _run(seller)["sent"] == 1
