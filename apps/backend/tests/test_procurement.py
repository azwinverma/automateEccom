"""Phase 8: suppliers + supplier products (PRO-001/002), purchase orders + approval (PRO-003/004), receiving
with lots (PRO-005, SPI-002), landed cost (PRO-006), supplier performance (SPI-001), supplier switch
(SPI-003) and reorder suggestions on true economics (PRO-007, SPI-004)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.catalog.models import Variant
from app.domains.orders.models import OrderLine
from app.domains.procurement.models import PurchaseOrder, PurchaseReceipt, PurchaseReceiptLine
from tests.conftest import onboard, register_and_login, set_plan
from tests.test_intelligence_b import sale
from tests.test_orders import item, order

API = "/api/v1"
P = f"{API}/procurement"


def supplier(client, s, name="Bhaktapur Weavers", **kw: Any) -> dict[str, Any]:
    r = client.post(f"{P}/suppliers", headers=s.h(), json={"name": name, "phone": "9801111111", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def po(client, s, sup_id: str, lines: list[dict[str, Any]], key: str | None = None, **kw: Any):
    return client.post(
        f"{P}/purchase-orders",
        headers={**s.h(), "Idempotency-Key": key or f"po-{uuid.uuid4().hex}"},
        json={"supplier_id": sup_id, "lines": lines, **kw},
    )


def receive(client, s, po_id: str, lines: list[dict[str, Any]], key: str | None = None, **kw: Any):
    return client.post(
        f"{P}/purchase-orders/{po_id}/receipts",
        headers={**s.h(), "Idempotency-Key": key or f"rc-{uuid.uuid4().hex}"},
        json={"lines": lines, **kw},
    )


def stock(client, s, pid: str) -> int:
    return client.get(f"{API}/catalog/products/{pid}/stock", headers=s.h()).json()["variants"][0]["on_hand"]


def cost_of(vid: str) -> int | None:
    with session_scope() as db:
        return db.scalar(
            select(Variant.cost_minor)
            .where(Variant.id == uuid.UUID(vid))
            .execution_options(skip_tenant_filter=True)
        )


def staff_of(client, seller, email: str):
    from app.domains.merchants.models import Membership

    staff = register_and_login(client, email)
    me = client.get(f"{API}/me", headers=staff.h()).json()
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        db.add(
            Membership(
                merchant_id=uuid.UUID(seller.merchant_id), user_id=uuid.UUID(me["user"]["id"]), role="staff"
            )
        )
    return staff


# ----------------------------------------------------------------------------- suppliers
def test_suppliers_and_their_products(client, seller):
    set_plan(seller.merchant_id, "growth")
    assert client.get(f"{P}/suppliers", headers=seller.h()).status_code == 403
    set_plan(seller.merchant_id, "pro")
    a = supplier(client, seller, default_lead_time_days=10, payment_terms="50% advance")
    assert (
        client.post(f"{P}/suppliers", headers=seller.h(), json={"name": "bhaktapur weavers"}).status_code
        == 409
    )
    b = supplier(client, seller, "Kathmandu Textiles")
    _p, vid = item(client, seller, stock=0)
    r = client.put(
        f"{P}/suppliers/{a['id']}/products/{vid}",
        headers=seller.h(),
        json={"cost_minor": 90000, "moq": 20, "lead_time_days": 8, "supplier_sku": "BW-K1"},
    )
    assert r.status_code == 200 and r.json()["items"][0]["is_preferred"] is True  # first supplier = preferred
    client.put(
        f"{P}/suppliers/{b['id']}/products/{vid}",
        headers=seller.h(),
        json={"cost_minor": 110000, "is_preferred": True},
    )
    got = client.get(f"{P}/suppliers/{a['id']}", headers=seller.h()).json()
    assert got["products"][0]["is_preferred"] is False and got["payment_terms"] == "50% advance"
    assert (
        client.patch(f"{P}/suppliers/{b['id']}", headers=seller.h(), json={"status": "archived"}).json()[
            "status"
        ]
        == "archived"
    )
    assert [x["name"] for x in client.get(f"{P}/suppliers", headers=seller.h()).json()["items"]] == [
        "Bhaktapur Weavers"
    ]
    other = onboard(client, shop="Other Procurement")
    set_plan(other.merchant_id, "pro")
    assert client.get(f"{P}/suppliers/{a['id']}", headers=other.h()).status_code == 404
    assert (
        client.put(
            f"{P}/suppliers/{a['id']}/products/{vid}", headers=other.h(), json={"cost_minor": 1}
        ).status_code
        == 404
    )


# ----------------------------------------------------------------------------- purchase orders
def test_po_approval_receiving_lots_and_landed_cost(client, seller):
    set_plan(seller.merchant_id, "pro")
    s = supplier(client, seller)
    p, vid = item(client, seller, stock=0)
    client.put(
        f"{P}/suppliers/{s['id']}/products/{vid}", headers=seller.h(), json={"cost_minor": 100000, "moq": 50}
    )
    r = po(
        client,
        seller,
        s["id"],
        [{"variant_id": vid, "quantity": 40}],
        key="po-key-0001",
        freight_minor=200000,
        duty_minor=100000,
    )
    assert r.status_code == 201, r.text
    x = r.json()
    assert x["number"] == "PO-1001" and x["status"] == "draft" and x["lines"][0]["unit_cost_minor"] == 100000
    assert x["subtotal_minor"] == 4000000 and x["total_minor"] == 4300000
    assert x["lines"][0]["landed_unit_cost_minor"] == 107500  # 1,000 + (2,000 + 1,000) / 40
    assert x["warnings"] == [{"code": "below_moq", "variant_id": vid, "moq": 50}]
    assert "Purchase order PO-1001" in x["share_text"] and ": 40" in x["share_text"]
    assert (
        po(
            client,
            seller,
            s["id"],
            [{"variant_id": vid, "quantity": 40}],
            key="po-key-0001",
            freight_minor=200000,
            duty_minor=100000,
        ).json()["id"]
        == x["id"]
    )  # replay with the same key and body
    changed = po(client, seller, s["id"], [{"variant_id": vid, "quantity": 41}], key="po-key-0001")
    assert changed.status_code in (409, 422)  # same key, different body: refused
    # Default threshold is 0: every PO waits for an explicit approval, even the owner's.
    sub = client.post(f"{P}/purchase-orders/{x['id']}/submit", headers=seller.h()).json()
    assert sub["status"] == "pending_approval" and sub["approval_reason"] == "above_threshold"
    assert (
        receive(client, seller, x["id"], [{"po_line_id": x["lines"][0]["id"], "quantity": 1}]).status_code
        == 409
    )
    assert (
        client.post(f"{P}/purchase-orders/{x['id']}/approve", headers=seller.h()).json()["status"]
        == "approved"
    )
    assert client.post(f"{P}/purchase-orders/{x['id']}/send", headers=seller.h()).json()["status"] == "sent"
    line = x["lines"][0]["id"]
    # First delivery: 25 arrive, 2 of them damaged → 23 into stock.
    r1 = receive(
        client,
        seller,
        x["id"],
        [{"po_line_id": line, "quantity": 23, "defective_quantity": 2}],
        key="rcv-key-0001",
        lot_code="LOT-A",
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["status"] == "partially_received" and r1.json()["lines"][0]["remaining"] == 15
    assert r1.json()["receipts"][0]["lot_code"] == "LOT-A"
    assert stock(client, seller, p["id"]) == 23
    assert cost_of(vid) == 107500  # no stock before: the landed cost
    assert (
        receive(
            client,
            seller,
            x["id"],
            [{"po_line_id": line, "quantity": 23, "defective_quantity": 2}],
            key="rcv-key-0001",
            lot_code="LOT-A",
        ).json()["status"]
        == "partially_received"
    )
    assert stock(client, seller, p["id"]) == 23  # the replay didn't stock twice
    over = receive(client, seller, x["id"], [{"po_line_id": line, "quantity": 16}])
    assert over.status_code == 400 and over.json()["error"]["code"] == "receipt_over_order"
    r2 = receive(client, seller, x["id"], [{"po_line_id": line, "quantity": 15}])
    assert r2.json()["status"] == "received" and r2.json()["receipts"][1]["lot_code"] == "PO-1001-2"
    assert stock(client, seller, p["id"]) == 38
    # A second order at a different landed cost moves the average.
    y = po(client, seller, s["id"], [{"variant_id": vid, "quantity": 10, "unit_cost_minor": 120000}]).json()
    client.post(f"{P}/purchase-orders/{y['id']}/submit", headers=seller.h())
    client.post(f"{P}/purchase-orders/{y['id']}/approve", headers=seller.h())
    receive(client, seller, y["id"], [{"po_line_id": y["lines"][0]["id"], "quantity": 10}])
    assert cost_of(vid) == round((38 * 107500 + 10 * 120000) / 48)
    # New orders keep the landed cost at the time of sale (true economics in profit).
    oid = order(client, seller, vid).json()["id"]
    with session_scope() as db:
        line_cost = db.scalar(
            select(OrderLine.unit_cost_minor)
            .where(OrderLine.order_id == uuid.UUID(oid))
            .execution_options(skip_tenant_filter=True)
        )
    assert line_cost == cost_of(vid)
    from app.domains.audit.models import AuditLog

    with session_scope() as db:
        acts = {a.action for a in db.scalars(select(AuditLog).execution_options(skip_tenant_filter=True))}
    assert {
        "procurement.po_submitted",
        "procurement.po_approved",
        "procurement.po_received",
        "procurement.variant_cost_updated",
    } <= acts


def test_staff_create_but_only_approvers_approve(client, seller):
    set_plan(seller.merchant_id, "pro")
    client.patch(f"{API}/automation/policy", headers=seller.h(), json={"thresholds": {"po_minor": 5_000_000}})
    s = supplier(client, seller)
    _p, vid = item(client, seller, stock=0)
    staff = staff_of(client, seller, "staff-po@example.com")
    sh = staff.h(merchant=seller.merchant_id)
    body = {"supplier_id": s["id"], "lines": [{"variant_id": vid, "quantity": 5, "unit_cost_minor": 50000}]}
    # Staff can't buy on the shop's behalf (system roles: procurement is for owners/managers).
    assert (
        client.post(
            f"{P}/purchase-orders", headers={**sh, "Idempotency-Key": "staff-po-0001"}, json=body
        ).status_code
        == 403
    )
    # Someone with procurement.write but not .approve (a custom role) waits for an approver.
    from app.core.context import Actor, TenantContext
    from app.domains.procurement import service as procurement

    x = po(client, seller, s["id"], body["lines"]).json()
    me = client.get(f"{API}/me", headers=seller.h()).json()
    writer = TenantContext(
        merchant_id=uuid.UUID(seller.merchant_id),
        actor=Actor(type="user", id=uuid.UUID(me["user"]["id"])),
        permissions=frozenset({"procurement.read", "procurement.write"}),
    )
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        got = procurement.submit(db, writer, uuid.UUID(x["id"]))
        assert got.status == "pending_approval" and got.approval_reason == "needs_approver"
    assert client.post(f"{P}/purchase-orders/{x['id']}/approve", headers=sh).status_code == 403
    back = client.post(
        f"{P}/purchase-orders/{x['id']}/reject",
        headers=seller.h(),
        json={"reason": "Wait for Tihar prices"},
    ).json()
    assert back["status"] == "draft" and "Wait for Tihar prices" in back["notes"]
    # Below the threshold, an owner's PO is approved on submit.
    own = po(client, seller, s["id"], [{"variant_id": vid, "quantity": 5, "unit_cost_minor": 50000}]).json()
    assert (
        client.post(f"{P}/purchase-orders/{own['id']}/submit", headers=seller.h()).json()["status"]
        == "approved"
    )
    # Edits only on drafts; cancel vs close.
    assert (
        client.patch(f"{P}/purchase-orders/{own['id']}", headers=seller.h(), json={"notes": "x"}).status_code
        == 409
    )
    assert (
        client.post(
            f"{P}/purchase-orders/{own['id']}/cancel", headers=seller.h(), json={"reason": "Ordered by phone"}
        ).json()["status"]
        == "cancelled"
    )
    part = po(client, seller, s["id"], [{"variant_id": vid, "quantity": 5, "unit_cost_minor": 50000}]).json()
    client.post(f"{P}/purchase-orders/{part['id']}/submit", headers=seller.h())
    receive(client, seller, part["id"], [{"po_line_id": part["lines"][0]["id"], "quantity": 2}])
    closed = client.post(
        f"{P}/purchase-orders/{part['id']}/cancel", headers=seller.h(), json={"reason": "Supplier ran out"}
    ).json()
    assert closed["status"] == "received" and closed["cancel_reason"] == "Supplier ran out"
    assert client.get(f"{P}/incoming", headers=seller.h()).json()["items"] == []


# ----------------------------------------------------------------------------- supplier intelligence
def _supplied(
    client,
    seller,
    sup: dict[str, Any],
    vid: str,
    qty: int,
    defective: int,
    unit: int,
    *,
    days_ago: int,
    lead_days: float = 5,
    on_time: bool = True,
) -> None:
    x = po(
        client, seller, sup["id"], [{"variant_id": vid, "quantity": qty + defective, "unit_cost_minor": unit}]
    ).json()
    client.post(f"{P}/purchase-orders/{x['id']}/submit", headers=seller.h())
    client.post(f"{P}/purchase-orders/{x['id']}/approve", headers=seller.h())
    client.post(f"{P}/purchase-orders/{x['id']}/send", headers=seller.h())
    receive(
        client,
        seller,
        x["id"],
        [{"po_line_id": x["lines"][0]["id"], "quantity": qty, "defective_quantity": defective}],
    )
    at = utcnow() - timedelta(days=days_ago)
    with session_scope() as db:
        db.execute(
            update(PurchaseOrder)
            .where(PurchaseOrder.id == uuid.UUID(x["id"]))
            .values(
                created_at=at - timedelta(days=lead_days),
                sent_at=at - timedelta(days=lead_days),
                expected_at=at + timedelta(days=1) if on_time else at - timedelta(days=1),
            )
            .execution_options(skip_tenant_filter=True)
        )
        db.execute(
            update(PurchaseReceipt)
            .where(PurchaseReceipt.po_id == uuid.UUID(x["id"]))
            .values(received_at=at)
            .execution_options(skip_tenant_filter=True)
        )
        rid = db.scalar(
            select(PurchaseReceipt.id)
            .where(PurchaseReceipt.po_id == uuid.UUID(x["id"]))
            .execution_options(skip_tenant_filter=True)
        )
        db.execute(
            update(PurchaseReceiptLine)
            .where(PurchaseReceiptLine.receipt_id == rid)
            .values(created_at=at)
            .execution_options(skip_tenant_filter=True)
        )


def test_true_economics_prefer_the_supplier_with_fewer_defects_and_returns(client, seller):
    set_plan(seller.merchant_id, "business")
    cheap = supplier(client, seller, "Cheap Fabrics")
    good = supplier(client, seller, "Good Fabrics")
    p, vid = item(client, seller, stock=0, price=245000)
    client.put(f"{P}/suppliers/{cheap['id']}/products/{vid}", headers=seller.h(), json={"cost_minor": 80000})
    client.put(f"{P}/suppliers/{good['id']}/products/{vid}", headers=seller.h(), json={"cost_minor": 95000})
    # Cheap lot arrived 60 days ago: 40 good + 10 defective, 5 days late; Good lot 30 days ago: 50 good, on time.
    _supplied(client, seller, cheap, vid, 40, 10, 80000, days_ago=60, lead_days=12, on_time=False)
    _supplied(client, seller, good, vid, 50, 0, 95000, days_ago=30, lead_days=4)
    m = seller.merchant_id
    for i in range(20):  # sold from the cheap lot (between its arrival and the good lot's)
        reason = "quality_defect" if i < 6 else None
        sale(
            m,
            p["id"],
            vid,
            days_ago=45,
            status="returned" if reason else "delivered",
            return_reason=reason,
            restocked=0,
            cost=None,
        )
    for i in range(20):  # sold from the good lot
        reason = "changed_mind" if i < 1 else None
        sale(
            m,
            p["id"],
            vid,
            days_ago=10,
            status="returned" if reason else "delivered",
            return_reason=reason,
            restocked=1 if reason else 0,
            cost=None,
        )
    perf = client.post(f"{P}/suppliers/performance/refresh", headers=seller.h()).json()
    assert perf["suppliers"] == 2
    items = {
        x["name"]: x["performance"] for x in client.get(f"{P}/suppliers", headers=seller.h()).json()["items"]
    }
    c, g = items["Cheap Fabrics"], items["Good Fabrics"]
    assert c["defect_rate"] == 0.2 and g["defect_rate"] == 0.0
    assert c["sold_units"] == 20 and g["sold_units"] == 20  # lot linkage
    assert c["quality_return_rate"] == 0.3 and g["quality_return_rate"] == 0.0
    assert c["lead_time_days_avg"] == 12 and c["on_time_rate"] == 0.0 and g["on_time_rate"] == 1.0
    assert c["components"]["defect_cost"] == round(0.2 / 0.8 * 80000)
    assert c["components"]["return_cost"] == round(6 * 80000 / 20)  # 6 unrestockable units at landed cost
    assert g["contribution_per_unit_minor"] > c["contribution_per_unit_minor"]  # costs more, earns more
    assert "packaging" in c["not_included"]
    # Cheap is still preferred (first linked) → switch suggestion with the reason.
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    rec = next(
        r
        for r in client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
        if r["type"] == "supplier_switch"
    )
    assert (
        rec["explanation"]["vars"]["from"] == "Cheap Fabrics"
        and rec["explanation"]["vars"]["to"] == "Good Fabrics"
    )
    assert (
        rec["explanation"]["vars"]["gain_per_unit"] > 0 and rec["action"]["type"] == "set_preferred_supplier"
    )
    assert (
        client.post(f"{API}/intelligence/recommendations/{rec['id']}/accept", headers=seller.h()).json()[
            "status"
        ]
        == "executed"
    )
    prods = client.get(f"{P}/suppliers/{good['id']}", headers=seller.h()).json()["products"]
    assert prods[0]["is_preferred"] is True


def test_reorder_suggestion_uses_lead_time_moq_and_creates_a_draft_for_approval(client, seller):
    set_plan(seller.merchant_id, "pro")
    s = supplier(client, seller, default_lead_time_days=10)
    p, vid = item(client, seller, stock=8)
    p2, vid2 = item(client, seller, sku="SHAWL-77", stock=4)
    client.put(f"{API}/inventory/variants/{vid}/threshold", headers=seller.h(), json={"threshold": 10})
    client.put(
        f"{P}/suppliers/{s['id']}/products/{vid}", headers=seller.h(), json={"cost_minor": 90000, "moq": 50}
    )
    client.put(f"{P}/suppliers/{s['id']}/products/{vid2}", headers=seller.h(), json={"cost_minor": 50000})
    for d in range(0, 90, 3):  # 60 units in 90 days = 0.67/day: 8 left last 12 days < 10 lead + 3 safety
        sale(seller.merchant_id, p["id"], vid, qty=2, days_ago=d + 0.5)
        sale(seller.merchant_id, p2["id"], vid2, qty=1, days_ago=d + 0.5, cost=30000)
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    recs = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    assert not any(r["type"] == "restock" for r in recs)  # replaced by reorder when a supplier exists
    ro = {r["subject_id"]: r for r in recs if r["type"] == "reorder"}
    r1 = ro[vid]
    v = r1["explanation"]["vars"]
    assert v["lead_days"] == 10 and v["safety_days"] == 3 and v["supplier"] == "Bhaktapur Weavers"
    assert v["quantity"] == 50  # below the MOQ → rounded up
    assert abs(v["days_left"] - 8 / v["per_day"]) < 0.2
    done = client.post(f"{API}/intelligence/recommendations/{r1['id']}/accept", headers=seller.h()).json()
    assert done["status"] == "executed"
    drafts = client.get(f"{P}/purchase-orders", params={"status": "draft"}, headers=seller.h()).json()[
        "items"
    ]
    assert (
        len(drafts) == 1
        and drafts[0]["source"] == "recommendation"
        and drafts[0]["lines"][0]["quantity"] == 50
    )
    # A second suggestion for the same supplier joins the same draft (still needs submit + approval).
    client.post(f"{API}/intelligence/recommendations/{ro[vid2]['id']}/accept", headers=seller.h())
    drafts = client.get(f"{P}/purchase-orders", params={"status": "draft"}, headers=seller.h()).json()[
        "items"
    ]
    assert len(drafts) == 1 and len(drafts[0]["lines"]) == 2
    # Ordered stock counts as incoming: no new suggestion once the PO is approved.
    client.post(f"{P}/purchase-orders/{drafts[0]['id']}/submit", headers=seller.h())
    client.post(f"{P}/purchase-orders/{drafts[0]['id']}/approve", headers=seller.h())
    inc = {
        x["variant_id"]: x["quantity"]
        for x in client.get(f"{P}/incoming", headers=seller.h()).json()["items"]
    }
    assert inc[vid] == 50
    from app.domains.intelligence.recommendations import generate

    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        generate(db, uuid.UUID(seller.merchant_id))
    recs = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    assert not any(r["type"] == "reorder" and r["subject_id"] == vid for r in recs)


def test_loss_makers_are_not_reordered(client, seller):
    set_plan(seller.merchant_id, "pro")
    s = supplier(client, seller)
    p, vid = item(client, seller, stock=2, price=100000)
    client.put(f"{P}/suppliers/{s['id']}/products/{vid}", headers=seller.h(), json={"cost_minor": 99000})
    for d in range(10):
        sale(seller.merchant_id, p["id"], vid, price=100000, cost=99000, days_ago=d + 1, delivery_fee=0)
    from app.domains.intelligence import product_brain

    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        product_brain.recompute_merchant(db, uuid.UUID(seller.merchant_id))
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    recs = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    assert not any(r["type"] == "reorder" for r in recs)
