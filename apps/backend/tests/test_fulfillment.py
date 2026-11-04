"""Phase 3 (FUL-001…008, FUL-010, PAY-002/010): couriers, delivery fees, booking, labels, pickup,
tracking (signed webhooks + polling), the order following the parcel, failed-delivery recovery with
the customer, return to sender, own-rider deliveries and COD settlement reconciliation."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import timedelta

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.fulfillment import couriers as courier_svc
from app.domains.fulfillment.models import CourierAccount, DeliveryAttempt
from app.domains.integrations.sandbox import SandboxChannelAdapter, SandboxCourierAdapter
from app.domains.payments.models import CODRecord
from tests.conftest import onboard
from tests.test_channels import _dispatch
from tests.test_inbox import Chat, kurta
from tests.test_orders import available, item, order

API = "/api/v1"
PICKUP = {
    "name": "Thamel Threads",
    "phone": "9801234567",
    "district": "Kathmandu",
    "municipality": "Kathmandu Metropolitan City",
    "area": "Thamel",
}


def sandbox_courier(client, s, **extra) -> dict:
    r = client.post(
        f"{API}/couriers", headers=s.h(), json={"provider": "sandbox_courier", "pickup": PICKUP, **extra}
    )
    assert r.status_code == 201, r.text
    return r.json()


def manual_courier(client, s, **extra) -> dict:
    r = client.post(
        f"{API}/couriers",
        headers=s.h(),
        json={"provider": "manual", "display_name": "Own rider", **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()


def book(client, s, oid, account_id, key=None, **extra):
    return client.post(
        f"{API}/orders/{oid}/shipments",
        headers=s.h(**{"Idempotency-Key": key or uuid.uuid4().hex}),
        json={"courier_account_id": account_id, **extra},
    )


def courier_event(client, s, account_id, tracking, status, **extra):
    r = client.post(
        f"{API}/_dev/couriers/sandbox/{account_id}/simulate",
        headers=s.h(),
        json={"tracking_number": tracking, "status": status, **extra},
    )
    assert r.status_code == 200, r.text
    _dispatch()
    _dispatch()
    return r.json()


def get_order(client, s, oid):
    return client.get(f"{API}/orders/{oid}", headers=s.h()).json()


def cod_record(oid) -> CODRecord:
    with session_scope() as db:
        rec = db.scalar(
            select(CODRecord)
            .where(CODRecord.order_id == uuid.UUID(oid))
            .execution_options(skip_tenant_filter=True)
        )
        assert rec is not None
        db.expunge(rec)
        return rec


def shipped_cod_order(client, s, courier, *, stock=5, price=245000, sku="KURTA-M"):
    p, vid = item(client, s, sku=sku, price=price, stock=stock)
    o = order(client, s, vid).json()
    shp = book(client, s, o["id"], courier["id"]).json()
    return p, o, shp


# ----------------------------------------------------------------------------- couriers + fees
def test_connect_couriers_default_and_providers(client, seller):
    providers = client.get(f"{API}/couriers/providers", headers=seller.h()).json()["items"]
    codes = {p["code"]: p for p in providers}
    assert {"manual", "sandbox_courier"} <= set(codes)
    assert "reattempt" in codes["sandbox_courier"]["capabilities"] and codes["manual"]["sandbox"] is False
    a = sandbox_courier(client, seller)
    assert a["is_default"] is True and a["pickup_complete"] and a["pickup"]["district"] == "kathmandu"
    assert a["webhook_path"] == f"/webhooks/couriers/sandbox_courier/{a['id']}"
    b = manual_courier(client, seller, is_default=True)
    items = client.get(f"{API}/couriers", headers=seller.h()).json()["items"]
    assert [x["id"] for x in items if x["is_default"]] == [b["id"]]  # exactly one default
    bad = client.post(
        f"{API}/couriers",
        headers=seller.h(),
        json={"provider": "sandbox_courier", "pickup": {"district": "Atlantis"}},
    )
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "address_invalid"
    # Credentials are sealed: the API never returns them, and staff (viewer) can't connect couriers.
    with session_scope() as db:
        row = db.get(CourierAccount, uuid.UUID(a["id"]))
        assert (
            row is not None
            and row.webhook_secret_sealed
            and "dev" not in (row.webhook_secret_sealed or "")[:5]
        )


def test_delivery_fee_table_district_beats_valley_beats_default(client, seller):
    r = client.put(
        f"{API}/fulfillment/delivery-fees",
        headers=seller.h(),
        json={
            "rules": [
                {"scope": "default", "fee_minor": 17500},
                {"scope": "inside_valley", "fee_minor": 10000, "free_over_minor": 500000},
                {"scope": "district", "district": "Kaski", "fee_minor": 15000},
            ]
        },
    )
    assert r.status_code == 200, r.text
    q = lambda d, sub=0: client.get(  # noqa: E731
        f"{API}/fulfillment/delivery-fee", params={"district": d, "subtotal_minor": sub}, headers=seller.h()
    ).json()["quote"]
    assert q("Lalitpur")["fee_minor"] == 10000 and q("Lalitpur")["rule"] == "inside_valley"
    assert q("Lalitpur", 600000)["fee_minor"] == 0 and q("Lalitpur", 600000)["free_delivery"] is True
    assert q("kaski")["fee_minor"] == 15000 and q("Jhapa")["fee_minor"] == 17500
    dup = client.put(
        f"{API}/fulfillment/delivery-fees",
        headers=seller.h(),
        json={"rules": [{"scope": "default", "fee_minor": 1}, {"scope": "default", "fee_minor": 2}]},
    )
    assert dup.json()["error"]["code"] == "fee_rule_duplicate"
    assert len(client.get(f"{API}/fulfillment/delivery-fees", headers=seller.h()).json()["items"]) == 3


def test_chat_order_summary_charges_the_merchants_delivery_fee(client, seller):
    client.put(
        f"{API}/fulfillment/delivery-fees",
        headers=seller.h(),
        json={
            "rules": [
                {"scope": "default", "fee_minor": 17500},
                {"scope": "district", "district": "Kaski", "fee_minor": 15000},
            ]
        },
    )
    kurta(client, seller)
    chat = Chat(client, seller)
    order_by_chat(chat)
    summary = next(
        m["text"]
        for m in reversed(chat.messages())
        if m["direction"] == "out" and "Please confirm" in m["text"]
    )
    assert "Delivery: Rs 150" in summary and "Total: Rs 2,600" in summary
    oid = client.get(f"{API}/orders", headers=seller.h()).json()["items"][0]["id"]
    o = get_order(client, seller, oid)
    assert (
        o["totals"]["delivery_fee"]["amount_minor"] == 15000
        and o["totals"]["total"]["amount_minor"] == 260000
    )


# ----------------------------------------------------------------------------- rates + booking
def test_rates_recommend_default_and_skip_services_that_cannot_collect_cod(client, seller):
    a = sandbox_courier(client, seller)
    manual_courier(client, seller)
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()  # COD, Lalitpur (inside the valley)
    r = client.get(f"{API}/couriers/rates", params={"order_id": o["id"]}, headers=seller.h()).json()
    services = [(x["provider"], x["service_code"]) for x in r["options"]]
    assert ("sandbox_courier", "standard") in services and ("sandbox_courier", "express") not in services
    assert r["cod_amount_minor"] == o["totals"]["total"]["amount_minor"]
    rec = r["recommendation"]
    assert (
        rec["courier_account_id"] == a["id"]
        and rec["reason"] == "default_courier"
        and rec["method"] == "rules"
    )
    std = next(x for x in r["options"] if x["service_code"] == "standard")
    assert std["price"]["amount_minor"] == 10000 and std["recommended"] is True
    # Prepaid orders may use the same-day service.
    _, vid2 = item(client, seller, sku="PRE-2")
    pre = order(client, seller, vid2, payment_method="prepaid").json()
    r2 = client.get(f"{API}/couriers/rates", params={"order_id": pre["id"]}, headers=seller.h()).json()
    assert any(x["service_code"] == "express" for x in r2["options"])


def test_booking_is_idempotent_one_live_shipment_and_moves_order_to_ready(client, seller):
    a = sandbox_courier(client, seller)
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    assert o["status"] == "cod_pending"
    r = book(client, seller, o["id"], a["id"], key="key-0001", weight_grams=800)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["status"] == "booked" and s["tracking_number"].startswith("SBX") and s["weight_grams"] == 800
    assert s["cod_amount"]["amount_minor"] == o["totals"]["total"]["amount_minor"]
    assert s["charge"]["amount_minor"] == 10000 and s["destination_district"] == "lalitpur"
    again = book(client, seller, o["id"], a["id"], key="key-0001", weight_grams=800)
    assert again.json()["id"] == s["id"]  # double tap: same booking
    second = book(client, seller, o["id"], a["id"], key="key-0002")
    assert second.status_code == 409 and second.json()["error"]["code"] == "shipment_exists"
    assert get_order(client, seller, o["id"])["status"] == "ready_to_ship"
    assert len(SandboxCourierAdapter.booked) == 1  # the courier was asked once
    no_key = client.post(
        f"{API}/orders/{o['id']}/shipments", headers=seller.h(), json={"courier_account_id": a["id"]}
    )
    assert no_key.json()["error"]["code"] == "idempotency_key_required"
    label = client.get(f"{API}/shipments/{s['id']}/label", headers=seller.h()).json()
    assert label["tracking_number"] == s["tracking_number"] and label["order_number"] == o["number"]
    assert label["to"]["name"] == "Sita Shrestha" and "Pulchowk" in label["to"]["address"]
    assert label["cod_amount"]["amount_minor"] == s["cod_amount"]["amount_minor"] and label["from"]["phone"]


def test_cannot_book_unready_orders_and_pickup_then_cancel_rules(client, seller):
    a = sandbox_courier(client, seller)
    _, vid = item(client, seller)
    pre = order(client, seller, vid, payment_method="prepaid").json()  # unpaid prepaid
    r = book(client, seller, pre["id"], a["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "order_not_ready_to_ship"
    _, o, s = shipped_cod_order(client, seller, a, sku="C-2")
    p = client.post(f"{API}/shipments/pickup", headers=seller.h(), json={"shipment_ids": [s["id"]]}).json()[
        "items"
    ][0]
    assert p["status"] == "pickup_requested" and p["pickup_reference"].startswith("SBX-PU-")
    again = client.post(f"{API}/shipments/pickup", headers=seller.h(), json={"shipment_ids": [s["id"]]})
    assert again.json()["error"]["code"] == "shipment_not_booked"
    c = client.post(
        f"{API}/shipments/{s['id']}/cancel", headers=seller.h(), json={"reason": "customer changed address"}
    )
    assert c.json()["status"] == "cancelled"
    assert get_order(client, seller, o["id"])["status"] == "ready_to_ship"  # can be re-booked
    assert book(client, seller, o["id"], a["id"]).status_code == 201


def test_cancelling_the_order_cancels_the_booking(client, seller):
    a = sandbox_courier(client, seller)
    _, o, s = shipped_cod_order(client, seller, a)
    r = client.post(
        f"{API}/orders/{o['id']}/transition",
        headers=seller.h(),
        json={"to": "cancelled", "reason": "customer cancelled"},
    )
    assert r.status_code == 200, r.text
    _dispatch()
    assert client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()["status"] == "cancelled"


# ----------------------------------------------------------------------------- tracking
def test_courier_webhooks_drive_the_order_to_delivered_and_cod_awaits_settlement(client, seller):
    a = sandbox_courier(client, seller)
    p, o, s = shipped_cod_order(client, seller, a, stock=3)
    assert available(client, seller, p["id"]) == 2  # 1 reserved
    t = s["tracking_number"]
    courier_event(client, seller, a["id"], t, "picked_up", location="Kathmandu hub")
    d = get_order(client, seller, o["id"])
    assert d["status"] == "shipped"
    assert cod_record(o["id"]).status == "handed_to_courier"
    courier_event(client, seller, a["id"], t, "in_transit")
    courier_event(client, seller, a["id"], t, "out_for_delivery")
    ev = courier_event(client, seller, a["id"], t, "delivered")
    assert get_order(client, seller, o["id"])["status"] == "delivered"
    rec = cod_record(o["id"])
    assert rec.status == "settlement_pending" and rec.collected_minor == o["totals"]["total"]["amount_minor"]
    detail = client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()
    assert [e["status"] for e in detail["events"]] == [
        "booked",
        "picked_up",
        "in_transit",
        "out_for_delivery",
        "delivered",
    ]
    assert detail["events"][1]["source"] == "courier_webhook" and detail["delivered_at"]
    # A replayed webhook is a duplicate; a forged one is refused.
    with session_scope() as db:
        acct = db.get(CourierAccount, uuid.UUID(a["id"]))
        secret = courier_svc.webhook_secret(acct)
    raw = json.dumps(ev["event"]).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    url = f"/webhooks/couriers/sandbox_courier/{a['id']}"
    assert client.post(url, content=raw, headers={"X-Sandbox-Signature": sig}).json()["duplicates"] == 1
    forged = client.post(url, content=raw, headers={"X-Sandbox-Signature": "0" * 64})
    assert forged.status_code == 401
    tl = client.get(f"{API}/orders/{o['id']}/timeline", headers=seller.h()).json()["items"]
    shipped = next(e for e in tl if e.get("to_status") == "shipped")
    assert shipped["provider"] == "sandbox_courier" and shipped["automated"] is True


def test_late_webhook_is_kept_in_history_but_never_moves_the_parcel_back(client, seller):
    a = sandbox_courier(client, seller)
    _, _o, s = shipped_cod_order(client, seller, a)
    t = s["tracking_number"]
    courier_event(client, seller, a["id"], t, "out_for_delivery")
    # An older "in_transit" event arrives after the newer one.
    old = SandboxCourierAdapter.simulate(t, "in_transit")
    old["occurred_at"] = (utcnow() - timedelta(hours=3)).isoformat()
    old["event_id"] = "late-1"
    with session_scope() as db:
        secret = courier_svc.webhook_secret(db.get(CourierAccount, uuid.UUID(a["id"])))
    raw = json.dumps(old).encode()
    client.post(
        f"/webhooks/couriers/sandbox_courier/{a['id']}",
        content=raw,
        headers={"X-Sandbox-Signature": hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()},
    )
    _dispatch()
    d = client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()
    assert d["status"] == "out_for_delivery"
    late = next(e for e in d["events"] if e["status"] == "in_transit")
    assert late["applied"] is False


def test_polling_picks_up_courier_updates_without_webhooks(client, seller):
    from app.domains.fulfillment.service import poll_due

    a = sandbox_courier(client, seller)
    _, o, s = shipped_cod_order(client, seller, a)
    SandboxCourierAdapter.simulate(s["tracking_number"], "picked_up")
    SandboxCourierAdapter.simulate(s["tracking_number"], "delivered")
    with session_scope() as db:
        stats = poll_due(db)
    assert stats["polled"] == 1 and stats["moved"] == 2
    _dispatch()
    assert get_order(client, seller, o["id"])["status"] == "delivered"
    with session_scope() as db:
        assert poll_due(db)["polled"] == 0  # delivered parcels aren't polled again


# ----------------------------------------------------------------------------- failed delivery recovery
def order_by_chat(chat):
    chat.say("Dhaka kurta XL cha? kati ho?")
    chat.say("XL 1 wota chahiyo")
    chat.say("9807654321")
    chat.say("Kaski")
    chat.say("Pokhara Metropolitan City ward 6")
    chat.say("Lakeside, near Fewa lake")
    chat.say("COD")
    return chat.say("YES")


def test_failed_delivery_asks_customer_and_auto_reattempts_in_smart_mode(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, mode="smart")
    assert order_by_chat(chat).startswith("Order #1001 confirmed")
    oid = client.get(f"{API}/orders", headers=seller.h()).json()["items"][0]["id"]
    a = sandbox_courier(client, seller)
    s = book(client, seller, oid, a["id"]).json()
    t = s["tracking_number"]
    courier_event(client, seller, a["id"], t, "picked_up")
    shipped_msg = [m for m in SandboxChannelAdapter.sent if m["thread"] == chat.thread][-1]["text"]
    assert "on its way with Sandbox courier" in shipped_msg and t in shipped_msg and "Rs 2,450" in shipped_msg
    courier_event(client, seller, a["id"], t, "delivery_failed", failure_reason="customer_unreachable")
    asked = [m for m in SandboxChannelAdapter.sent if m["thread"] == chat.thread][-1]["text"]
    assert "couldn't deliver your order #1001" in asked and "couldn't reach your phone" in asked
    assert get_order(client, seller, oid)["status"] == "delivery_failed"
    reply = chat.say("Sorry! Tomorrow after 3pm please, call 9807654321")
    assert "asked the courier to deliver order #1001 again" in reply
    assert SandboxCourierAdapter.requests[-1][0] == "reattempt" and "Tomorrow after 3pm" in (
        SandboxCourierAdapter.requests[-1][2] or ""
    )
    d = client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()
    att = d["attempts"][0]
    assert d["status"] == "reattempt_requested" and att["recovery_status"] == "reattempt_requested"
    assert att["reattempt_by"] == "automation" and att["customer_reply"].startswith("Sorry! Tomorrow")
    courier_event(client, seller, a["id"], t, "out_for_delivery")
    assert get_order(client, seller, oid)["status"] == "shipped"
    courier_event(client, seller, a["id"], t, "delivered")
    d = client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()
    assert (
        d["attempts"][0]["resolution"] == "delivered"
        and get_order(client, seller, oid)["status"] == "delivered"
    )
    assert (
        "has been delivered"
        in [m for m in SandboxChannelAdapter.sent if m["thread"] == chat.thread][-1]["text"]
    )
    # The reply never reached the Sales Agent as a new product question.
    assert not any(m["intent"] == "product_question" for m in chat.messages()[-6:] if m["direction"] == "in")


def test_assisted_mode_hands_the_reply_to_the_seller_and_no_reply_escalates(client, seller):
    from app.domains.fulfillment.service import escalate_stale

    kurta(client, seller)
    chat = Chat(client, seller, mode="assisted")
    order_by_chat(chat)  # assisted: replies wait for approval, but the order is still taken on YES
    orders = client.get(f"{API}/orders", headers=seller.h()).json()["items"]
    assert len(orders) == 1
    oid = orders[0]["id"]
    a = sandbox_courier(client, seller)
    s = book(client, seller, oid, a["id"]).json()
    courier_event(client, seller, a["id"], s["tracking_number"], "picked_up")
    courier_event(
        client, seller, a["id"], s["tracking_number"], "delivery_failed", failure_reason="address_incorrect"
    )
    chat.say("Near the white temple, opposite Hotel Barahi")
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    item_ = next(e for e in ex if e["type"] == "delivery_failed")
    assert item_["action"] == "request_reattempt" and "white temple" in item_["details"]["customer_reply"]
    assert not any(r[0] == "reattempt" for r in SandboxCourierAdapter.requests)  # nothing automatic
    r = client.post(
        f"{API}/shipments/{s['id']}/reattempt",
        headers=seller.h(),
        json={"note": "Landmark: white temple, opposite Hotel Barahi"},
    )
    assert r.json()["status"] == "reattempt_requested" and r.json()["attempts"][0]["reattempt_by"] == "seller"
    assert not any(
        e["type"] == "delivery_failed"
        for e in client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    )
    # Second failure, the customer never answers → escalated after the wait window.
    courier_event(client, seller, a["id"], s["tracking_number"], "out_for_delivery")
    courier_event(
        client,
        seller,
        a["id"],
        s["tracking_number"],
        "delivery_failed",
        failure_reason="customer_unavailable",
    )
    with session_scope() as db:
        db.execute(
            update(DeliveryAttempt)
            .values(failed_at=utcnow() - timedelta(hours=30))
            .execution_options(skip_tenant_filter=True)
        )
    with session_scope() as db:
        assert escalate_stale(db) == 1
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    esc = next(e for e in ex if e["type"] == "delivery_failed")
    assert esc["severity"] == "urgent" and esc["action"] == "call_customer"
    d = client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()
    assert [x["resolution"] for x in d["attempts"]] == ["failed_again", None] and d["attempt_count"] == 2


def test_seller_order_without_chat_opens_recovery_for_a_call_and_return_restocks(client, seller):
    a = sandbox_courier(client, seller)
    p, o, s = shipped_cod_order(client, seller, a, stock=2)
    t = s["tracking_number"]
    courier_event(client, seller, a["id"], t, "picked_up")
    assert available(client, seller, p["id"]) == 1
    courier_event(client, seller, a["id"], t, "delivery_failed", failure_reason="customer_refused")
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    e = next(x for x in ex if x["type"] == "delivery_failed")
    assert e["action"] == "call_customer" and e["details"]["phone"] == "+9779841234567"
    r = client.post(f"{API}/shipments/{s['id']}/return", headers=seller.h(), json={"reason": "refused twice"})
    assert r.json()["status"] == "returning" and SandboxCourierAdapter.requests[-1][0] == "return"
    courier_event(client, seller, a["id"], t, "returned_to_origin")
    d = get_order(client, seller, o["id"])
    assert d["status"] == "returned" and cod_record(o["id"]).status == "returned_to_origin"
    assert any(
        x["type"] == "return_to_receive"
        for x in client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    )
    back = client.post(f"{API}/shipments/{s['id']}/received-back", headers=seller.h())
    assert back.status_code == 200 and back.json()["return_received_at"]
    assert available(client, seller, p["id"]) == 2  # back on the shelf, once
    client.post(f"{API}/shipments/{s['id']}/received-back", headers=seller.h())
    assert available(client, seller, p["id"]) == 2


# ----------------------------------------------------------------------------- own rider
def test_own_rider_flow_and_cash_handover_settles_cod(client, seller):
    m = manual_courier(client, seller)
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    r = book(client, seller, o["id"], m["id"], courier_name="Ram (rider)")
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["manual"] is True and s["courier_name"] == "Ram (rider)" and "update_status" in s["actions"]

    def st(status, **kw):
        return client.post(
            f"{API}/shipments/{s['id']}/status", headers=seller.h(), json={"status": status, **kw}
        )

    assert st("delivery_failed").json()["error"]["code"] == "failure_reason_required"
    assert st("picked_up").json()["status"] == "picked_up"
    _dispatch()
    assert get_order(client, seller, o["id"])["status"] == "shipped"
    assert st("delivered").json()["status"] == "delivered"
    _dispatch()
    assert get_order(client, seller, o["id"])["status"] == "delivered"
    waiting = client.get(f"{API}/cod/awaiting", headers=seller.h()).json()["items"]
    assert [w["order_number"] for w in waiting] == [o["number"]]
    cash = client.post(
        f"{API}/cod/settlements/cash",
        headers=seller.h(),
        json={"courier_account_id": m["id"], "shipment_ids": [s["id"]], "reference": "Ram 4 Nov"},
    )
    assert cash.status_code == 201, cash.text
    assert (
        cash.json()["status"] == "confirmed"
        and cash.json()["net_minor"] == o["totals"]["total"]["amount_minor"]
    )
    assert cod_record(o["id"]).status == "settled"
    assert client.get(f"{API}/cod/awaiting", headers=seller.h()).json()["items"] == []
    sandbox = sandbox_courier(client, seller)
    other = client.post(
        f"{API}/cod/settlements/cash",
        headers=seller.h(),
        json={"courier_account_id": sandbox["id"], "shipment_ids": [s["id"]]},
    )
    assert other.json()["error"]["code"] == "courier_sends_statements"


# ----------------------------------------------------------------------------- COD settlement
def delivered(client, s, a, n=1):
    out = []
    for i in range(n):
        _, o, shp = shipped_cod_order(client, s, a, sku=f"SET-{i}")
        courier_event(client, s, a["id"], shp["tracking_number"], "picked_up")
        courier_event(client, s, a["id"], shp["tracking_number"], "delivered")
        out.append((o, shp))
    return out


def test_courier_statement_reconciles_and_confirm_settles_cod(client, seller):
    a = sandbox_courier(client, seller)
    rows = delivered(client, seller, a, n=2)
    ov = client.get(f"{API}/cod/overview", headers=seller.h()).json()
    total = sum(o["totals"]["total"]["amount_minor"] for o, _ in rows)
    assert ov["awaiting_by_age"]["d0_7"] == {"count": 2, "amount_minor": total}
    assert ov["awaiting_by_courier"][0]["amount_minor"] == total
    r = client.post(
        f"{API}/_dev/couriers/sandbox/{a['id']}/settlement", headers=seller.h(), json={"fee_minor": 10000}
    )
    assert r.status_code == 201, r.text
    st = r.json()["settlement"]
    assert st["status"] == "reconciled" and st["issue_count"] == 0 and st["source"] == "courier_api"
    assert st["collected_minor"] == total and st["fees_minor"] == 20000 and st["net_minor"] == total - 20000
    c = client.post(
        f"{API}/cod/settlements/{st['id']}/confirm", headers=seller.h(), json={"bank_reference": "NIC-778812"}
    )
    assert c.json()["status"] == "confirmed" and c.json()["bank_reference"] == "NIC-778812"
    for o, _ in rows:
        rec = cod_record(o["id"])
        assert rec.status == "settled" and rec.fee_minor == 10000 and str(rec.settlement_id) == st["id"]
    ov = client.get(f"{API}/cod/overview", headers=seller.h()).json()
    assert ov["settled"]["count"] == 2 and ov["received_last_30_days"]["amount_minor"] == total - 20000


def test_statement_mismatches_block_confirmation_until_accepted(client, seller):
    a = sandbox_courier(client, seller)
    rows = delivered(client, seller, a, n=2)
    r = client.post(
        f"{API}/_dev/couriers/sandbox/{a['id']}/settlement",
        headers=seller.h(),
        json={"fee_minor": 0, "short_minor": 50000, "extra_unknown": True},
    ).json()["settlement"]
    assert r["status"] == "needs_review" and r["issue_count"] == 2
    statuses = sorted(ln["match_status"] for ln in r["lines"])
    assert statuses == ["amount_mismatch", "matched", "unknown_shipment"]
    blocked = client.post(f"{API}/cod/settlements/{r['id']}/confirm", headers=seller.h(), json={})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "settlement_has_issues"
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    assert any(e["type"] == "cod_settlement_mismatch" for e in ex)
    for ln in r["lines"]:
        if ln["match_status"] != "matched":
            acc = client.post(
                f"{API}/cod/settlement-lines/{ln['id']}/accept",
                headers=seller.h(),
                json={"reason": "Courier will pay the rest next week"},
            )
            assert acc.status_code == 200
    ok = client.post(f"{API}/cod/settlements/{r['id']}/confirm", headers=seller.h(), json={}).json()
    assert ok["status"] == "confirmed"
    short_order = next(
        o
        for o, shp in rows
        if shp["tracking_number"]
        == next(ln for ln in r["lines"] if ln["match_status"] == "amount_mismatch")["tracking_number"]
    )
    assert (
        cod_record(short_order["id"]).collected_minor
        == short_order["totals"]["total"]["amount_minor"] - 50000
    )
    with session_scope() as db:
        from app.domains.audit.models import AuditLog

        acts = {x.action for x in db.scalars(select(AuditLog).execution_options(skip_tenant_filter=True))}
    assert {"fulfillment.settlement_line_accepted", "fulfillment.settlement_confirmed"} <= acts


def test_csv_statement_import_is_idempotent_and_reports_bad_rows(client, seller):
    a = sandbox_courier(client, seller)
    ((o, shp),) = delivered(client, seller, a, n=1)
    total_rs = o["totals"]["total"]["amount_minor"] / 100
    csv_ok = f'Tracking No,COD Amount,Delivery Charge,COD Fee\n{shp["tracking_number"]},"Rs {total_rs:,.2f}",100,25.50\n\n'.encode()
    up = lambda content, ref="STMT-1": client.post(  # noqa: E731
        f"{API}/cod/settlements/import",
        headers=seller.h(),
        data={"courier_account_id": a["id"], "reference": ref},
        files={"file": ("statement.csv", content, "text/csv")},
    )
    r = up(csv_ok)
    assert r.status_code == 201, r.text
    st = r.json()
    assert st["status"] == "reconciled" and st["fees_minor"] == 12550 and st["source"] == "file_import"
    again = up(csv_ok)
    assert again.status_code == 200 and again.json()["id"] == st["id"]
    bad = up(b"Tracking No,COD Amount\nSBX1,abc\n,100\n", ref="STMT-2")
    assert bad.status_code == 400
    assert bad.json()["error"]["details"]["rows"] == [
        {"row": 2, "field": "amount", "reason": "not_a_number"},
        {"row": 3, "field": "tracking_number", "reason": "missing"},
    ]
    missing = up(b"foo,bar\n1,2\n", ref="STMT-3")
    assert missing.json()["error"]["code"] == "settlement_file_invalid"


def test_settled_parcel_in_a_second_statement_is_flagged(client, seller):
    a = sandbox_courier(client, seller)
    ((o, shp),) = delivered(client, seller, a, n=1)
    st = client.post(f"{API}/_dev/couriers/sandbox/{a['id']}/settlement", headers=seller.h(), json={}).json()[
        "settlement"
    ]
    client.post(f"{API}/cod/settlements/{st['id']}/confirm", headers=seller.h(), json={})
    csv_dup = f"tracking_number,cod_collected\n{shp['tracking_number']},{o['totals']['total']['amount_minor'] / 100}\n".encode()
    r = client.post(
        f"{API}/cod/settlements/import",
        headers=seller.h(),
        data={"courier_account_id": a["id"], "reference": "DUP-1"},
        files={"file": ("s.csv", csv_dup, "text/csv")},
    ).json()
    assert r["lines"][0]["match_status"] == "already_settled" and r["status"] == "needs_review"


# ----------------------------------------------------------------------------- isolation + permissions
def test_shipments_and_settlements_are_tenant_isolated(client, seller):
    a = sandbox_courier(client, seller)
    _, _, s = shipped_cod_order(client, seller, a)
    other = onboard(client, shop="Other Shop")
    assert client.get(f"{API}/shipments/{s['id']}", headers=other.h()).status_code == 404
    assert client.get(f"{API}/shipments", headers=other.h()).json()["items"] == []
    assert client.get(f"{API}/couriers", headers=other.h()).json()["items"] == []
    r = client.post(
        f"{API}/_dev/couriers/sandbox/{a['id']}/simulate",
        headers=other.h(),
        json={"tracking_number": s["tracking_number"], "status": "delivered"},
    )
    assert r.status_code == 404
    listed = client.get(f"{API}/shipments", params={"bucket": "to_pickup"}, headers=seller.h()).json()
    assert [x["id"] for x in listed["items"]] == [s["id"]] and listed["counts"]["to_pickup"] == 1


def test_disconnect_is_refused_while_parcels_are_on_the_way(client, seller):
    a = sandbox_courier(client, seller)
    shipped_cod_order(client, seller, a)
    r = client.delete(f"{API}/couriers/{a['id']}", headers=seller.h())
    assert r.status_code == 409 and r.json()["error"]["code"] == "courier_has_live_shipments"
    m = manual_courier(client, seller)
    assert client.delete(f"{API}/couriers/{m['id']}", headers=seller.h()).status_code == 204
