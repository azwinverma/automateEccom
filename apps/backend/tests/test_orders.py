"""ORD-001…012: seller orders, state machine, stock, partial cancel, timeline, channel imports."""

from __future__ import annotations

import threading
import uuid

from sqlalchemy import select

from app.core.db import session_scope
from app.domains.channels.models import ChannelConnection
from app.domains.integrations.sandbox import SandboxChannelAdapter
from app.domains.integrations.woocommerce import WooCommerceAdapter
from app.domains.merchants.models import Membership
from tests.conftest import onboard, register_and_login, set_plan
from tests.test_channels import _dispatch, _webhook, connect

API = "/api/v1"
ADDR = {
    "recipient_name": "Sita Shrestha",
    "phone": "9841234567",
    "district": "Lalitpur",
    "municipality": "Lalitpur Metropolitan City",
    "ward": 3,
    "area": "Pulchowk",
    "landmark": "Opposite Labim Mall",
}


def item(client, s, sku="KURTA-M", price=245000, stock=5):
    p = client.post(
        f"{API}/catalog/products",
        headers=s.h(),
        json={"title": "Cotton Kurta", "variants": [{"price_minor": price, "sku": sku}]},
    ).json()
    vid = p["variants"][0]["id"]
    if stock:
        client.post(f"{API}/inventory/variants/{vid}/receive", headers=s.h(), json={"quantity": stock})
    return p, vid


def order(client, s, vid, qty=1, **extra):
    body = {
        "lines": [{"variant_id": vid, "quantity": qty}],
        "address": ADDR,
        "delivery_fee_minor": 15000,
        **extra,
    }
    return client.post(f"{API}/orders", headers=s.h(), json=body)


def available(client, s, pid):
    return client.get(f"{API}/catalog/products/{pid}/stock", headers=s.h()).json()["variants"][0]["available"]


def move(client, s, oid, to, **kw):
    return client.post(f"{API}/orders/{oid}/transition", headers=s.h(), json={"to": to, **kw})


def test_seller_cod_order_reserves_stock_and_follows_the_machine(client, seller):
    p, vid = item(client, seller)
    r = order(client, seller, vid, qty=2)
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["number"] == 1001 and o["status"] == "cod_pending" and o["payment_status"] == "cod_pending"
    assert (
        o["totals"]["subtotal"]["amount_minor"] == 490000 and o["totals"]["total"]["amount_minor"] == 505000
    )
    assert o["shipping"]["province"] == "bagmati" and o["shipping"]["district_name"] == "Lalitpur"
    assert o["customer"]["phone"] == "+9779841234567"
    assert available(client, seller, p["id"]) == 3
    # The address was saved on the new customer for next time.
    cust = client.get(f"{API}/customers/{o['customer']['id']}", headers=seller.h()).json()
    assert len(cust["addresses"]) == 1

    assert move(client, seller, o["id"], "delivered").json()["error"]["code"] == "invalid_transition"
    for to in ("ready_to_ship", "shipped"):
        assert move(client, seller, o["id"], to).status_code == 200
    stock = client.get(f"{API}/catalog/products/{p['id']}/stock", headers=seller.h()).json()["variants"][0]
    assert stock["on_hand"] == 3 and stock["reserved"] == 0  # shipped: off the shelf
    d = move(client, seller, o["id"], "delivered").json()
    assert d["payment_status"] == "cod_collected"
    assert move(client, seller, o["id"], "completed").json()["status"] == "completed"
    tl = client.get(f"{API}/orders/{o['id']}/timeline", headers=seller.h()).json()["items"]
    assert [e["to_status"] for e in tl if e["kind"] == "status_changed"] == [
        "confirmed",
        "cod_pending",
        "ready_to_ship",
        "shipped",
        "delivered",
        "completed",
    ]
    assert tl[0]["kind"] == "created" and tl[1]["actor"]["type"] == "user" and tl[2]["automated"] is True


def test_out_of_stock_refused_atomically_and_untracked_allowed(client, seller):
    _, vid = item(client, seller, stock=1)
    r = order(client, seller, vid, qty=2)
    assert r.status_code == 409 and r.json()["error"]["code"] == "out_of_stock"
    assert r.json()["error"]["details"] == {"variant_id": vid, "available": 1, "requested": 2}
    assert client.get(f"{API}/orders", headers=seller.h()).json()["items"] == []
    assert client.get(f"{API}/customers", headers=seller.h()).json()["items"] == []  # nothing half-created
    _, made_to_order = item(client, seller, sku="MTO-1", stock=0)
    assert order(client, seller, made_to_order, qty=9).status_code == 201


def test_cancel_releases_stock_and_needs_permission(client, seller):
    p, vid = item(client, seller)
    o = order(client, seller, vid, qty=2).json()
    staff = register_and_login(client, "packer@example.com")
    uid = client.get(f"{API}/me", headers=staff.h()).json()["user"]["id"]
    set_plan(seller.merchant_id, "growth")
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        db.add(Membership(merchant_id=uuid.UUID(seller.merchant_id), user_id=uuid.UUID(uid), role="staff"))
    denied = client.post(
        f"{API}/orders/{o['id']}/transition",
        headers=staff.h(merchant=seller.merchant_id),
        json={"to": "cancelled"},
    )
    assert denied.status_code == 403 and denied.json()["error"]["details"]["permission"] == "orders.cancel"
    # Staff can still move the order forward (pack and hand over).
    assert (
        client.post(
            f"{API}/orders/{o['id']}/transition",
            headers=staff.h(merchant=seller.merchant_id),
            json={"to": "ready_to_ship"},
        ).status_code
        == 200
    )
    c = move(client, seller, o["id"], "cancelled", reason="customer changed mind").json()
    assert c["status"] == "cancelled" and c["cancel_reason"] == "customer changed mind"
    assert available(client, seller, p["id"]) == 5
    assert move(client, seller, o["id"], "confirmed").json()["error"]["code"] == "invalid_transition"


def test_prepaid_waits_for_payment_and_version_conflict(client, seller):
    _, vid = item(client, seller)
    o = order(client, seller, vid, payment_method="prepaid").json()
    assert o["status"] == "payment_pending" and o["payment_status"] == "pending"
    r = move(client, seller, o["id"], "ready_to_ship")
    assert r.status_code == 409 and r.json()["error"]["code"] == "payment_not_confirmed"
    stale = move(client, seller, o["id"], "cancelled", expected_version=o["version"] - 1)
    assert stale.json()["error"]["code"] == "version_conflict"


def test_partial_cancel_releases_part_and_recomputes(client, seller):
    p, vid = item(client, seller)
    p2, vid2 = item(client, seller, sku="SHAWL-1", price=100000)
    body = {
        "lines": [{"variant_id": vid, "quantity": 3}, {"variant_id": vid2, "quantity": 1}],
        "address": ADDR,
    }
    o = client.post(f"{API}/orders", headers=seller.h(), json=body).json()
    line = next(ln for ln in o["lines"] if ln["sku"] == "KURTA-M")
    r = client.post(
        f"{API}/orders/{o['id']}/cancel-lines",
        headers=seller.h(),
        json={"items": [{"line_id": line["id"], "quantity": 2}], "reason": "only one in stock colour"},
    ).json()
    assert r["status"] == "cod_pending"
    assert r["totals"]["subtotal"]["amount_minor"] == 245000 + 100000
    assert available(client, seller, p["id"]) == 4  # 5 - 1 still reserved
    other = next(ln for ln in r["lines"] if ln["sku"] == "SHAWL-1")
    rest = client.post(
        f"{API}/orders/{o['id']}/cancel-lines",
        headers=seller.h(),
        json={
            "items": [{"line_id": line["id"], "quantity": 1}, {"line_id": other["id"], "quantity": 1}],
            "reason": "customer cancelled",
        },
    ).json()
    assert (
        rest["status"] == "cancelled"
        and available(client, seller, p["id"]) == 5
        and available(client, seller, p2["id"]) == 5
    )
    too_many = client.post(
        f"{API}/orders/{o['id']}/cancel-lines",
        headers=seller.h(),
        json={"items": [{"line_id": line["id"], "quantity": 1}], "reason": "xx"},
    )
    assert too_many.json()["error"]["code"] == "order_not_editable"


def test_idempotent_creation_and_order_limit(client, seller):
    _, vid = item(client, seller)
    h = seller.h(**{"Idempotency-Key": "order-form-0001"})
    body = {"lines": [{"variant_id": vid, "quantity": 1}], "address": ADDR}
    a = client.post(f"{API}/orders", headers=h, json=body)
    b = client.post(f"{API}/orders", headers=h, json=body)
    assert a.json()["id"] == b.json()["id"] and b.headers["Idempotent-Replayed"] == "true"
    assert (
        available(
            client,
            seller,
            client.get(f"{API}/orders/{a.json()['id']}", headers=seller.h()).json()["lines"][0]["product_id"],
        )
        == 4
    )
    from app.domains.billing.models import EntitlementOverride

    with session_scope() as db:
        db.add(
            EntitlementOverride(
                merchant_id=uuid.UUID(seller.merchant_id),
                resource_code="orders",
                period="month",
                limit_value=1,
                reason="test",
            )
        )
    # Plans bill orders past the allowance as overage: a sale is never refused for a plan limit.
    r = order(client, seller, vid)
    assert r.status_code == 201
    from app.domains.billing.models import UsageEvent

    with session_scope() as db:
        funding = [
            e.funding
            for e in db.scalars(
                select(UsageEvent).where(UsageEvent.resource_code == "orders").order_by(UsageEvent.id)
            )
        ]
    assert funding == ["quota", "overage"]


def test_last_unit_race_sells_once(client, seller):
    _, vid = item(client, seller, stock=1)
    results = []

    def buy(i):
        results.append(order(client, seller, vid, customer_phone=f"98000000{i:02d}").status_code)

    threads = [threading.Thread(target=buy, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [201, 409, 409, 409, 409, 409]


def test_orders_are_tenant_isolated(client, seller):
    other = onboard(client, shop="Patan Crafts")
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    assert client.get(f"{API}/orders/{o['id']}", headers=other.h()).status_code == 404
    assert move(client, other, o["id"], "cancelled").status_code == 404
    assert client.get(f"{API}/orders/{o['id']}/timeline", headers=other.h()).status_code == 404
    assert (
        order(client, other, vid).json()["error"]["code"] == "variant_not_found"
    )  # can't sell someone else's item
    assert client.get(f"{API}/orders", headers=other.h()).json()["items"] == []


def test_merging_customers_moves_their_orders(client, seller):
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    other = client.post(
        f"{API}/customers", headers=seller.h(), json={"display_name": "Sita (Instagram)"}
    ).json()
    client.post(
        f"{API}/customers/{other['id']}/merge", headers=seller.h(), json={"source_id": o["customer"]["id"]}
    )
    assert (
        client.get(f"{API}/orders", params={"customer_id": other["id"]}, headers=seller.h()).json()["items"][
            0
        ]["id"]
        == o["id"]
    )


# ----------------------------------------------------------------------------- channel imports
def _acct(cid):
    with session_scope() as db:
        return db.get(ChannelConnection, uuid.UUID(cid)).external_account_id


def channel_order(ext_id="WO-1", sku="KURTA-M", qty=1, status="confirmed", **kw):
    return {
        "id": ext_id,
        "status": status,
        "customer": {"id": "c-77", "name": "Bikash Rai", "phone": "9807654321"},
        "district": "Kaski",
        "address": "Lakeside, Pokhara",
        "lines": [{"sku": sku, "title": "Cotton Kurta M", "quantity": qty, "price_minor": 245000}],
        "delivery_fee_minor": 10000,
        **kw,
    }


def test_channel_order_webhook_imports_once_and_follows_cancellation(client, seller):
    p, vid = item(client, seller)
    c = connect(client, seller)
    acct = _acct(c["id"])
    _webhook(client, {"id": "evt-o1", "type": "order.created", "account_id": acct, "data": channel_order()})
    _webhook(
        client, {"id": "evt-o2", "type": "order.updated", "account_id": acct, "data": channel_order()}
    )  # same order again
    _dispatch()
    orders = client.get(f"{API}/orders", headers=seller.h()).json()["items"]
    assert len(orders) == 1
    o = client.get(f"{API}/orders/{orders[0]['id']}", headers=seller.h()).json()
    assert o["source"] == "channel" and o["external_number"] == "WO-1" and o["status"] == "cod_pending"
    assert o["shipping"]["district"] == "kaski" and o["shipping"]["text"] == "Lakeside, Pokhara"
    assert o["lines"][0]["variant_id"] == vid and available(client, seller, p["id"]) == 4
    _webhook(
        client,
        {
            "id": "evt-o3",
            "type": "order.updated",
            "account_id": acct,
            "data": channel_order(status="cancelled"),
        },
    )
    _dispatch()
    assert client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()["status"] == "cancelled"
    assert available(client, seller, p["id"]) == 5
    tl = client.get(f"{API}/orders/{o['id']}/timeline", headers=seller.h()).json()["items"]
    assert (
        tl[0]["kind"] == "imported"
        and tl[-1]["provider"] == "sandbox_channel"
        and tl[-1]["data"]["reason"] == "cancelled_on_channel"
    )


def test_import_flags_unknown_items_and_stock_gaps_instead_of_dropping(client, seller):
    _, vid = item(client, seller, stock=0)
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 1})
    c = connect(client, seller)
    acct = _acct(c["id"])
    _webhook(
        client,
        {
            "id": "e1",
            "type": "order.created",
            "account_id": acct,
            "data": channel_order("WO-2", sku="NOT-IN-CATALOG"),
        },
    )
    _webhook(
        client,
        {"id": "e2", "type": "order.created", "account_id": acct, "data": channel_order("WO-3", qty=4)},
    )
    _dispatch()
    by_ext = {
        o["external_number"]: o for o in client.get(f"{API}/orders", headers=seller.h()).json()["items"]
    }
    assert by_ext["WO-2"]["needs_review"] == "unmatched_items"
    assert by_ext["WO-3"]["needs_review"] == "stock_short" and by_ext["WO-3"]["status"] == "cod_pending"
    assert (
        client.get(f"{API}/orders", params={"needs_review": True}, headers=seller.h())
        .json()["items"]
        .__len__()
        == 2
    )


def test_missed_webhooks_caught_up_by_reconciliation(client, seller):
    from app.domains.channels.service import reconcile_all

    item(client, seller)
    connect(client, seller)
    SandboxChannelAdapter.orders.extend(
        [channel_order("WO-9"), channel_order("WO-9"), channel_order("draft-1", status="draft")]
    )
    with session_scope() as db:
        stats = reconcile_all(db)
    assert stats["orders_imported"] == 1
    with session_scope() as db:
        assert reconcile_all(db)["orders_imported"] == 0  # idempotent
    assert [
        o["external_number"] for o in client.get(f"{API}/orders", headers=seller.h()).json()["items"]
    ] == ["WO-9"]


def test_woocommerce_order_mapping():
    a = WooCommerceAdapter()
    raw = {
        "id": 512,
        "number": "512",
        "status": "processing",
        "currency": "NPR",
        "customer_id": 9,
        "payment_method": "cod",
        "date_created_gmt": "2026-11-03T08:15:00",
        "billing": {
            "first_name": "Sita",
            "last_name": "Shrestha",
            "phone": "9841234567",
            "email": "sita@example.com",
            "address_1": "Thamel",
            "city": "Kathmandu",
        },
        "shipping": {},
        "shipping_total": "150.00",
        "discount_total": "0.00",
        "line_items": [{"sku": "KURTA-M", "name": "Cotton Kurta - M", "quantity": 2, "price": 2450}],
    }
    ext = a.normalize_order(raw)
    assert ext.status == "confirmed" and ext.payment_method == "cod" and not ext.paid
    assert (
        ext.customer_name == "Sita Shrestha"
        and ext.customer_external_id == "9"
        and ext.district_hint == "Kathmandu"
    )
    assert ext.lines[0].unit_price_minor == 245000 and ext.delivery_fee_minor == 15000
    assert a.normalize_order({**raw, "status": "checkout-draft"}) is None
    paid = a.normalize_order({**raw, "payment_method": "esewa", "date_paid_gmt": "2026-11-03T08:16:00"})
    assert paid.payment_method == "prepaid" and paid.paid
    assert a.normalize_order({**raw, "status": "refunded"}).status == "cancelled"


def test_customer_segments_come_from_real_orders(client, seller):
    from sqlalchemy import update as sql_update

    from app.core.db import utcnow
    from app.domains.orders.models import Order

    _, vid = item(client, seller, stock=10)
    a = order(client, seller, vid, customer_phone="9800000011").json()["customer"]["id"]
    order(client, seller, vid, customer_phone="9800000011")
    b = order(client, seller, vid, customer_phone="9800000012").json()["customer"]["id"]
    c = order(client, seller, vid, customer_phone="9800000013").json()
    with session_scope() as db:
        from datetime import timedelta

        db.execute(
            sql_update(Order)
            .where(Order.id == uuid.UUID(c["id"]))
            .values(placed_at=utcnow() - timedelta(days=120))
        )

    def seg(name):
        return {
            x["id"]
            for x in client.get(f"{API}/customers", params={"segment": name}, headers=seller.h()).json()[
                "items"
            ]
        }

    assert seg("repeat") == {a}
    assert seg("new") == {b, c["customer"]["id"]}
    assert seg("inactive") == {c["customer"]["id"]}
    assert client.get(f"{API}/customers", params={"segment": "vip"}, headers=seller.h()).status_code == 400
