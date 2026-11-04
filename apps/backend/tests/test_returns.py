"""Phase 4 (RET-001…011, PAY-007): policy, eligibility with overrides, return pickups, inspection
and restock, exchanges with reserved stock, idempotent threshold-controlled refunds, abuse signals."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.integrations.sandbox import SandboxChannelAdapter
from app.domains.merchants.models import Membership
from app.domains.orders.models import OrderEvent
from app.domains.payments.models import CODRecord
from tests.conftest import onboard, register_and_login
from tests.test_channels import _dispatch
from tests.test_fulfillment import book, courier_event, sandbox_courier
from tests.test_inbox import Chat, kurta
from tests.test_orders import available, item, move, order

API = "/api/v1"


def deliver(client, s, oid):
    for to in ("ready_to_ship", "shipped", "delivered"):
        r = move(client, s, oid, to)
        assert r.status_code == 200, r.text
    return client.get(f"{API}/orders/{oid}", headers=s.h()).json()


def delivered_order(client, s, *, qty=1, price=245000, sku="RET-1", stock=5, **extra):
    p, vid = item(client, s, sku=sku, price=price, stock=stock)
    o = order(client, s, vid, qty=qty, **extra).json()
    return p, vid, deliver(client, s, o["id"])


def ret(client, s, oid, lines, resolution="refund", key=None, **extra):
    return client.post(
        f"{API}/orders/{oid}/returns",
        headers=s.h(**{"Idempotency-Key": key or uuid.uuid4().hex}),
        json={"resolution": resolution, "lines": lines, **extra},
    )


def refund(client, s, oid, amount, method="esewa", key=None, **extra):
    return client.post(
        f"{API}/orders/{oid}/refunds",
        headers=s.h(**{"Idempotency-Key": key or uuid.uuid4().hex}),
        json={"amount_minor": amount, "method": method, **extra},
    )


def line_of(o, i=0, **kw):
    return {"order_line_id": o["lines"][i]["id"], "quantity": 1, "reason": "size_small", **kw}


def member(client, owner, role, email):
    u = register_and_login(client, email)
    me = client.get(f"{API}/me", headers=u.h()).json()
    with session_scope(uuid.UUID(owner.merchant_id)) as db:
        db.add(
            Membership(
                merchant_id=uuid.UUID(owner.merchant_id), user_id=uuid.UUID(me["user"]["id"]), role=role
            )
        )
    u.merchant_id = owner.merchant_id
    return u


# ----------------------------------------------------------------------------- the main path
def test_delivered_cod_order_return_pickup_inspection_restock_and_refund(client, seller):
    a = sandbox_courier(client, seller)
    p, _vid, o = delivered_order(client, seller, stock=3)
    assert available(client, seller, p["id"]) == 2
    info = client.get(f"{API}/orders/{o['id']}/returnable", headers=seller.h()).json()
    assert info["lines"][0]["returnable_quantity"] == 1 and info["lines"][0]["unit_refund_minor"] == 245000
    assert info["deadline"] and info["refundable_minor"] == o["totals"]["total"]["amount_minor"]
    r = ret(client, seller, o["id"], [line_of(o)], key="ret-key-0001")
    assert r.status_code == 201, r.text
    rr = r.json()
    assert rr["number"] == f"R-{o['number']}-1" and rr["status"] == "requested" and rr["eligible"] is True
    assert {c["code"] for c in rr["eligibility"]["checks"]} >= {
        "order_delivered",
        "within_window",
        "quantity_available",
    }
    assert rr["refund_due"]["amount_minor"] == 245000 and rr["customer_pays_shipping"] is True
    assert ret(client, seller, o["id"], [line_of(o)], key="ret-key-0001").json()["id"] == rr["id"]  # replay
    again = ret(client, seller, o["id"], [line_of(o)])
    assert again.status_code == 409 and again.json()["error"]["code"] == "return_not_eligible"  # nothing left
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    assert any(e["type"] == "return_requested" and e["action"] == "review_return" for e in ex)

    rr = client.post(f"{API}/returns/{rr['id']}/approve", headers=seller.h(), json={}).json()
    assert rr["status"] == "approved" and "book_pickup" in rr["actions"]
    r = client.post(
        f"{API}/returns/{rr['id']}/pickup",
        headers=seller.h(**{"Idempotency-Key": "pickup-key-0001"}),
        json={"courier_account_id": a["id"]},
    )
    assert r.status_code == 201, r.text
    pickup = r.json()["pickup"]
    assert pickup["direction"] == "return" and pickup["cod_amount"]["amount_minor"] == 0
    t = pickup["tracking_number"]
    courier_event(client, seller, a["id"], t, "picked_up")
    assert client.get(f"{API}/returns/{rr['id']}", headers=seller.h()).json()["status"] == "in_transit"
    courier_event(client, seller, a["id"], t, "delivered")
    rr = client.get(f"{API}/returns/{rr['id']}", headers=seller.h()).json()
    assert rr["status"] == "received" and rr["actions"] == ["inspect"]
    # The return pickup never touched the order or its COD record.
    assert client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()["status"] == "delivered"
    with session_scope() as db:
        assert (
            db.scalar(select(CODRecord.status).execution_options(skip_tenant_filter=True))
            == "settlement_pending"
        )

    early = refund(client, seller, o["id"], 245000, return_id=rr["id"])
    assert early.json()["error"]["code"] == "return_not_inspected"
    rr = client.post(
        f"{API}/returns/{rr['id']}/inspect",
        headers=seller.h(),
        json={"items": [{"line_id": rr["lines"][0]["id"], "condition": "resellable", "restock": 1}]},
    ).json()
    assert rr["status"] == "inspected" and rr["lines"][0]["restocked_quantity"] == 1
    assert available(client, seller, p["id"]) == 3  # back on the shelf
    assert any(
        e["type"] == "refund_due" for e in client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    )

    over = refund(client, seller, o["id"], o["totals"]["total"]["amount_minor"] + 1, return_id=rr["id"])
    assert over.json()["error"]["code"] == "refund_exceeds_paid"
    online = refund(client, seller, o["id"], 245000, method="original_payment", return_id=rr["id"])
    assert online.json()["error"]["code"] == "refund_method_unavailable"  # COD wasn't paid online
    r1 = refund(
        client, seller, o["id"], 245000, return_id=rr["id"], reference="eSewa 98000", key="refund-key-0001"
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["status"] == "succeeded" and r1.json()["reference"] == "eSewa 98000"
    replay = refund(
        client, seller, o["id"], 245000, return_id=rr["id"], reference="eSewa 98000", key="refund-key-0001"
    )
    assert replay.json()["id"] == r1.json()["id"]  # double tap: one refund
    clash = refund(client, seller, o["id"], 245000, return_id=rr["id"], key="refund-key-0001")
    assert clash.status_code == 422 or clash.status_code == 409  # same key, different request: refused
    rr = client.get(f"{API}/returns/{rr['id']}", headers=seller.h()).json()
    assert (
        rr["status"] == "refunded" and rr["refundable_minor"] == o["totals"]["total"]["amount_minor"] - 245000
    )
    d = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert d["status"] == "returned"  # everything sold came back
    tl = {
        e["kind"] for e in client.get(f"{API}/orders/{o['id']}/timeline", headers=seller.h()).json()["items"]
    }
    assert {
        "return_requested",
        "return_approved",
        "return_received",
        "return_inspected",
        "refund_succeeded",
    } <= tl


def test_prepaid_auto_refund_within_threshold_goes_to_the_original_payment(client, seller):
    client.patch(
        f"{API}/returns/policy",
        headers=seller.h(),
        json={"auto_approve": True, "auto_refund_max_minor": 300000},
    )
    _, vid = item(client, seller, sku="PRE-R")
    o = order(client, seller, vid, payment_method="prepaid").json()
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert client.post(f"{API}/payments/{p['id']}/verify", headers=seller.h()).json()["status"] == "paid"
    for to in ("shipped", "delivered"):
        assert move(client, seller, o["id"], to).status_code == 200
    o = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    rr = ret(client, seller, o["id"], [line_of(o, reason="changed_mind")]).json()
    assert rr["status"] == "approved"  # policy auto-approve: eligible, no signals
    rr = client.post(f"{API}/returns/{rr['id']}/received", headers=seller.h()).json()
    rr = client.post(
        f"{API}/returns/{rr['id']}/inspect",
        headers=seller.h(),
        json={"items": [{"line_id": rr["lines"][0]["id"], "condition": "resellable", "restock": 1}]},
    ).json()
    assert rr["status"] == "refunded"
    ref = rr["refunds"][0]
    assert ref["method"] == "original_payment" and ref["provider"] == "sandbox_wallet"
    assert ref["provider_refund_id"].startswith("sbx-ref-") and ref["amount"]["amount_minor"] == 245000


def test_refund_above_threshold_waits_for_a_manager(client, seller):
    staff = member(client, seller, "staff", "staff-r@example.com")
    manager = member(client, seller, "manager", "manager-r@example.com")
    _, _, o = delivered_order(client, seller)
    rr = ret(client, staff, o["id"], [line_of(o)]).json()
    assert client.post(f"{API}/returns/{rr['id']}/approve", headers=staff.h(), json={}).status_code == 403
    client.post(f"{API}/returns/{rr['id']}/approve", headers=manager.h(), json={})
    client.post(f"{API}/returns/{rr['id']}/received", headers=staff.h())
    rr = client.post(
        f"{API}/returns/{rr['id']}/inspect",
        headers=staff.h(),
        json={"items": [{"line_id": rr["lines"][0]["id"], "condition": "damaged"}]},
    ).json()
    pending = refund(client, staff, o["id"], 245000, return_id=rr["id"], reference="bank 1").json()
    assert pending["status"] == "pending_approval"
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    assert any(e["type"] == "refund_above_threshold" and e["action"] == "approve_refund" for e in ex)
    assert client.post(f"{API}/refunds/{pending['id']}/approve", headers=staff.h()).status_code == 403
    done = client.post(f"{API}/refunds/{pending['id']}/approve", headers=manager.h()).json()
    assert done["status"] == "succeeded"
    assert client.get(f"{API}/returns/{rr['id']}", headers=seller.h()).json()["status"] == "refunded"


# ----------------------------------------------------------------------------- policy + eligibility
def test_outside_window_needs_an_override_reason_and_not_delivered_is_refused(client, seller):
    _, vid, o = delivered_order(client, seller)
    with session_scope() as db:
        db.execute(
            update(OrderEvent)
            .where(OrderEvent.to_status == "delivered")
            .values(created_at=utcnow() - timedelta(days=30))
            .execution_options(skip_tenant_filter=True)
        )
    rr = ret(client, seller, o["id"], [line_of(o)]).json()
    assert rr["eligible"] is False
    failed = [c["code"] for c in rr["eligibility"]["checks"] if not c["ok"]]
    assert failed == ["within_window"]
    r = client.post(f"{API}/returns/{rr['id']}/approve", headers=seller.h(), json={})
    assert r.status_code == 400 and r.json()["error"]["code"] == "override_reason_required"
    ok = client.post(
        f"{API}/returns/{rr['id']}/approve",
        headers=seller.h(),
        json={"override_reason": "Loyal customer, stitching fault"},
    ).json()
    assert ok["status"] == "approved" and ok["override_reason"] == "Loyal customer, stitching fault"
    # An order that hasn't been delivered can't be returned at all.
    fresh = order(client, seller, vid).json()
    r = ret(client, seller, fresh["id"], [line_of(fresh)])
    assert r.status_code == 409 and r.json()["error"]["details"]["checks"][0]["code"] == "order_delivered"


def test_final_sale_and_missing_evidence_are_flagged(client, seller):
    p, _, o = delivered_order(client, seller)
    client.patch(f"{API}/catalog/products/{p['id']}", headers=seller.h(), json={"final_sale": True})
    chk = client.post(
        f"{API}/orders/{o['id']}/returns/check",
        headers=seller.h(),
        json={"lines": [line_of(o, reason="quality_defect")]},
    ).json()
    assert chk["can_request"] is True and chk["eligible"] is False
    assert {c["code"] for c in chk["checks"] if not c["ok"]} == {"not_final_sale", "evidence"}
    client.patch(
        f"{API}/returns/policy", headers=seller.h(), json={"evidence_reasons": [], "window_days": 14}
    )
    pol = client.get(f"{API}/returns/policy", headers=seller.h()).json()
    assert pol["evidence_reasons"] == [] and pol["window_days"] == 14
    bad = client.patch(f"{API}/returns/policy", headers=seller.h(), json={"evidence_reasons": ["bored"]})
    assert bad.json()["error"]["code"] == "return_reason_invalid"


def test_missing_items_are_not_refunded_and_a_zero_refund_closes(client, seller):
    _, _, o = delivered_order(client, seller)
    rr = ret(client, seller, o["id"], [line_of(o)]).json()
    client.post(f"{API}/returns/{rr['id']}/approve", headers=seller.h(), json={})
    client.post(f"{API}/returns/{rr['id']}/received", headers=seller.h())
    bad = client.post(
        f"{API}/returns/{rr['id']}/inspect",
        headers=seller.h(),
        json={"items": [{"line_id": rr["lines"][0]["id"], "condition": "damaged", "restock": 1}]},
    )
    assert bad.json()["error"]["code"] == "restock_invalid"  # damaged goods don't go back on sale
    rr = client.post(
        f"{API}/returns/{rr['id']}/inspect",
        headers=seller.h(),
        json={"items": [{"line_id": rr["lines"][0]["id"], "condition": "missing", "note": "Empty bag"}]},
    ).json()
    assert rr["status"] == "closed" and rr["refund_due"]["amount_minor"] == 0


def test_shop_fault_on_the_whole_order_refunds_delivery_and_customer_fault_pays_return_shipping(
    client, seller
):
    client.patch(
        f"{API}/returns/policy",
        headers=seller.h(),
        json={"return_shipping_fee_minor": 10000, "evidence_reasons": []},
    )
    _, _, o = delivered_order(client, seller)
    rr = ret(client, seller, o["id"], [line_of(o, reason="wrong_item")]).json()
    assert rr["customer_pays_shipping"] is False
    assert rr["refund_due"]["amount_minor"] == 245000 + 15000  # item + original delivery charge
    _, _, o2 = delivered_order(client, seller, sku="RET-2")
    rr2 = ret(client, seller, o2["id"], [line_of(o2, reason="changed_mind")]).json()
    assert rr2["return_shipping_fee_minor"] == 10000 and rr2["refund_due"]["amount_minor"] == 245000 - 10000


# ----------------------------------------------------------------------------- exchange
def test_exchange_reserves_the_replacement_and_ships_it_free_after_inspection(client, seller):
    p = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={
            "title": "Dhaka Topi",
            "options": [{"name": "Size", "values": ["M", "L", "XL"]}],
            "variants": [
                {"options": {"Size": "M"}, "price_minor": 80000, "sku": "TOPI-M"},
                {"options": {"Size": "L"}, "price_minor": 80000, "sku": "TOPI-L"},
                {"options": {"Size": "XL"}, "price_minor": 95000, "sku": "TOPI-XL"},
            ],
        },
    ).json()
    vm, vl, vxl = (v["id"] for v in p["variants"])
    for v in (vm, vl, vxl):
        client.post(f"{API}/inventory/variants/{v}/receive", headers=seller.h(), json={"quantity": 2})
    o = order(client, seller, vm).json()
    o = deliver(client, seller, o["id"])
    opts = client.get(f"{API}/orders/{o['id']}/returnable", headers=seller.h()).json()["lines"][0][
        "exchange_options"
    ]
    assert [x["title"] for x in opts] == ["L"]  # same price only
    pricey = ret(client, seller, o["id"], [line_of(o, exchange_variant_id=vxl)], resolution="exchange")
    assert pricey.status_code == 409
    rr = ret(client, seller, o["id"], [line_of(o, exchange_variant_id=vl)], resolution="exchange").json()
    rr = client.post(f"{API}/returns/{rr['id']}/approve", headers=seller.h(), json={}).json()
    stock = {
        v["sku"]: v
        for v in client.get(f"{API}/catalog/products/{p['id']}/stock", headers=seller.h()).json()["variants"]
    }
    assert stock["TOPI-L"]["available"] == 1 and stock["TOPI-L"]["reserved"] == 1  # held for this customer
    client.post(f"{API}/returns/{rr['id']}/received", headers=seller.h())
    rr = client.post(
        f"{API}/returns/{rr['id']}/inspect",
        headers=seller.h(),
        json={"items": [{"line_id": rr["lines"][0]["id"], "condition": "resellable", "restock": 1}]},
    ).json()
    assert rr["status"] == "exchanged" and rr["exchange_order_id"]
    ex = client.get(f"{API}/orders/{rr['exchange_order_id']}", headers=seller.h()).json()
    assert (
        ex["totals"]["total"]["amount_minor"] == 0
        and ex["lines"][0]["sku"] == "TOPI-L"
        and ex["status"] == "cod_pending"
    )
    stock = {
        v["sku"]: v
        for v in client.get(f"{API}/catalog/products/{p['id']}/stock", headers=seller.h()).json()["variants"]
    }
    assert (
        stock["TOPI-L"]["reserved"] == 1 and stock["TOPI-L"]["available"] == 1
    )  # moved to the order, not doubled
    assert stock["TOPI-M"]["available"] == 2  # the returned M is back


def test_cancelling_an_approved_exchange_releases_the_held_stock(client, seller):
    p = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={
            "title": "Cotton Kurta",
            "options": [{"name": "Size", "values": ["M", "L"]}],
            "variants": [
                {"options": {"Size": z}, "price_minor": 245000, "sku": f"CX-{z}"} for z in ("M", "L")
            ],
        },
    ).json()
    vm, vl = (v["id"] for v in p["variants"])
    client.post(f"{API}/inventory/variants/{vm}/receive", headers=seller.h(), json={"quantity": 3})
    client.post(f"{API}/inventory/variants/{vl}/receive", headers=seller.h(), json={"quantity": 1})
    o = deliver(client, seller, order(client, seller, vm).json()["id"])
    rr = ret(client, seller, o["id"], [line_of(o, exchange_variant_id=vl)], resolution="exchange").json()
    client.post(f"{API}/returns/{rr['id']}/approve", headers=seller.h(), json={})

    def large():
        stock = client.get(f"{API}/catalog/products/{p['id']}/stock", headers=seller.h()).json()["variants"]
        return next(v for v in stock if v["sku"] == "CX-L")

    assert large()["available"] == 0
    assert (
        client.post(f"{API}/returns/{rr['id']}/cancel", headers=seller.h(), json={}).json()["status"]
        == "cancelled"
    )
    assert large()["available"] == 1


# ----------------------------------------------------------------------------- abuse signals + chat
def test_frequent_returner_is_flagged_and_never_auto_approved(client, seller):
    client.patch(f"{API}/returns/policy", headers=seller.h(), json={"auto_approve": True})
    statuses = []
    for i in range(3):
        _, _, o = delivered_order(client, seller, sku=f"AB-{i}")
        statuses.append(ret(client, seller, o["id"], [line_of(o)]).json())
    assert [r["status"] for r in statuses[:2]] == ["approved", "approved"]
    third = statuses[2]
    assert third["status"] == "requested"
    codes = {s["code"] for s in third["signals"]}
    assert "frequent_returns" in codes and "high_return_rate" in codes
    ex = next(
        e
        for e in client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
        if e["resource"]["id"] == third["id"]
    )
    assert ex["severity"] == "high" and "frequent_returns" in ex["details"]["signals"]


def test_sales_agent_answers_return_questions_from_the_policy_and_hands_over(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, mode="smart")
    for text in (
        "Dhaka kurta XL cha?",
        "XL 1 wota chahiyo",
        "9807654321",
        "Kaski",
        "Pokhara Metropolitan City ward 6",
        "Lakeside",
        "COD",
        "YES",
    ):
        chat.say(text)
    oid = client.get(f"{API}/orders", headers=seller.h()).json()["items"][0]["id"]
    deliver(client, seller, oid)
    reply = chat.say("I want to return it, size is small")
    assert "can be returned or exchanged until" in reply and "#1001" in reply
    conv = chat.conversation()
    assert conv["escalated"] is True and conv["escalation_reason"] == "return"
    assert any("return" in (m["text"] or "") for m in SandboxChannelAdapter.sent)


def test_returns_are_tenant_isolated(client, seller):
    _, _, o = delivered_order(client, seller)
    rr = ret(client, seller, o["id"], [line_of(o)]).json()
    other = onboard(client, shop="Other Returns")
    assert client.get(f"{API}/returns/{rr['id']}", headers=other.h()).status_code == 404
    assert client.post(f"{API}/returns/{rr['id']}/approve", headers=other.h(), json={}).status_code == 404
    assert client.get(f"{API}/returns", headers=other.h()).json()["items"] == []
    listed = client.get(f"{API}/returns", params={"bucket": "to_decide"}, headers=seller.h()).json()
    assert [x["id"] for x in listed["items"]] == [rr["id"]] and listed["counts"]["to_decide"] == 1


def test_customer_hears_about_the_return_in_their_chat(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, mode="smart")
    for text in (
        "Dhaka kurta XL cha?",
        "XL 1 wota chahiyo",
        "9807654321",
        "Kaski",
        "Pokhara Metropolitan City ward 6",
        "Lakeside",
        "COD",
        "YES",
    ):
        chat.say(text)
    o = client.get(f"{API}/orders", headers=seller.h()).json()["items"][0]
    o = deliver(client, seller, o["id"])
    rr = ret(client, seller, o["id"], [line_of(o)]).json()
    client.post(f"{API}/returns/{rr['id']}/approve", headers=seller.h(), json={})
    _dispatch()
    _dispatch()
    last = [m["text"] for m in SandboxChannelAdapter.sent if m["thread"] == chat.thread][-1]
    assert f"Your return {rr['number']} for order #{o['number']} is approved" in last
    _ = book  # (pickup booking is covered in the main path)
