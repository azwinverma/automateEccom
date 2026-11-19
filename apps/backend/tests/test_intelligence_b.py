"""Phase 6 part B: true profit (ANA-007/008), Product Brain (PBR-001…005/008/009/010), Return
Intelligence (RTI-001…006), Commerce Memory (MEM-001…008) and profit-aware suggestions (ANA-010)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.catalog.models import Variant
from app.domains.customers.models import Customer
from app.domains.fulfillment.models import Shipment
from app.domains.intelligence import memory, product_brain, return_intel
from app.domains.intelligence.models import CommerceMemoryFact, ReturnInsight
from app.domains.inventory.models import InventoryLedgerEntry, InventoryLevel
from app.domains.orders.models import Order, OrderLine
from app.domains.returns.models import Refund, ReturnLine, ReturnRequest
from tests.conftest import onboard, set_plan
from tests.test_inbox import Chat, kurta
from tests.test_intelligence import courier
from tests.test_orders import item, order

API = "/api/v1"
_N = {"n": 7000}


def sale(
    merchant_id: str,
    product_id: str,
    variant_id: str,
    *,
    qty: int = 1,
    price: int = 245000,
    cost: int | None = 100000,
    status: str = "delivered",
    days_ago: float = 5,
    delivery_fee: int = 15000,
    discount: int = 0,
    courier_account: str | None = None,
    charge: int | None = 17500,
    return_reason: str | None = None,
    restocked: int = 0,
    refund: int | None = None,
    return_charge: int | None = None,
    customer_id: uuid.UUID | None = None,
    payment: str = "prepaid",
) -> str:
    """An order straight in the DB with its line, parcel, return and refund: the P&L's raw material."""
    mid = uuid.UUID(merchant_id)
    _N["n"] += 1
    at = utcnow() - timedelta(days=days_ago)
    with session_scope(mid) as db:
        o = Order(
            merchant_id=mid,
            number=_N["n"],
            status=status,
            source="seller",
            currency="NPR",
            subtotal_minor=price * qty,
            discount_minor=discount,
            delivery_fee_minor=delivery_fee,
            total_minor=price * qty - discount + delivery_fee,
            payment_method=payment,
            payment_status="paid" if payment == "prepaid" else "cod_pending",
            placed_at=at,
            customer_id=customer_id,
            ship_district="kaski",
        )
        db.add(o)
        db.flush()
        ln = OrderLine(
            merchant_id=mid,
            order_id=o.id,
            product_id=uuid.UUID(product_id),
            variant_id=uuid.UUID(variant_id),
            title="Item",
            unit_price_minor=price,
            quantity=qty,
            line_discount_minor=discount,
            unit_cost_minor=cost,
        )
        db.add(ln)
        db.flush()
        if courier_account:
            db.add(
                Shipment(
                    merchant_id=mid,
                    order_id=o.id,
                    courier_account_id=uuid.UUID(courier_account),
                    provider="sandbox_courier",
                    status="delivered" if status != "returned" or return_reason else "returned_to_origin",
                    weight_grams=500,
                    charge_minor=charge,
                    currency="NPR",
                    destination_district="kaski",
                    idempotency_key=f"s-{o.id}",
                )
            )
        if return_reason:
            r = ReturnRequest(
                merchant_id=mid,
                number=f"R-{_N['n']}",
                order_id=o.id,
                status="closed",
                resolution="refund",
                source="seller",
                idempotency_key=f"r-{o.id}",
                currency="NPR",
            )
            db.add(r)
            db.flush()
            db.add(
                ReturnLine(
                    merchant_id=mid,
                    return_id=r.id,
                    order_line_id=ln.id,
                    variant_id=uuid.UUID(variant_id),
                    quantity=qty,
                    unit_refund_minor=price,
                    reason=return_reason,
                    restocked_quantity=restocked,
                )
            )
            if return_charge is not None and courier_account:
                db.add(
                    Shipment(
                        merchant_id=mid,
                        order_id=o.id,
                        direction="return",
                        return_id=r.id,
                        courier_account_id=uuid.UUID(courier_account),
                        provider="sandbox_courier",
                        status="delivered",
                        weight_grams=500,
                        charge_minor=return_charge,
                        currency="NPR",
                        idempotency_key=f"rs-{o.id}",
                    )
                )
            if refund:
                db.add(
                    Refund(
                        merchant_id=mid,
                        order_id=o.id,
                        return_id=r.id,
                        amount_minor=refund,
                        currency="NPR",
                        method="cash",
                        status="succeeded",
                        idempotency_key=f"rf-{o.id}",
                    )
                )
        return str(o.id)


def comp(result: dict[str, Any], code: str) -> dict[str, Any]:
    return next(c for c in result["components"] if c["code"] == code)


# ----------------------------------------------------------------------------- true profit
def test_true_profit_waterfall_counts_returns_failures_and_labels_missing_data(client, seller):
    set_plan(seller.merchant_id, "pro")
    p, vid = item(client, seller, stock=0)
    acc = courier(client, seller, "Courier A", default=True)["id"]
    m, pid = seller.merchant_id, p["id"]
    sale(m, pid, vid, courier_account=acc, discount=5000)
    sale(m, pid, vid, courier_account=acc)
    sale(m, pid, vid, courier_account=acc)
    # Sent back by the customer, back on the shelf, refunded, return parcel paid by the shop.
    sale(
        m,
        pid,
        vid,
        courier_account=acc,
        status="returned",
        return_reason="size_small",
        restocked=1,
        refund=245000,
        return_charge=17500,
    )
    # Never delivered (returned to origin): no revenue, only the cost of trying.
    sale(m, pid, vid, courier_account=acc, status="returned")
    # Still on its way: not counted yet.
    sale(m, pid, vid, courier_account=acc, status="shipped")
    r = client.get(f"{API}/intelligence/profit", headers=seller.h()).json()
    shop = r["shop"]
    assert r["currency"] == "NPR"
    assert r["counts"] == {"sold": 4, "failed": 1, "open": 1, "cost_from_current": 0}
    assert comp(shop, "goods")["amount_minor"] == 980000
    assert comp(shop, "delivery_fees")["amount_minor"] == 60000
    assert comp(shop, "discounts")["amount_minor"] == -5000
    assert comp(shop, "cogs")["amount_minor"] == -300000  # the restocked unit carries no cost
    assert comp(shop, "courier")["amount_minor"] == -70000
    assert comp(shop, "return_shipping")["amount_minor"] == -17500
    assert comp(shop, "refunds")["amount_minor"] == -245000
    assert comp(shop, "failed_delivery")["amount_minor"] == -(17500 + 17500 + 5000)
    assert comp(shop, "packaging") == {
        "code": "packaging",
        "amount_minor": None,
        "status": "not_included",
        "missing": 4,
        "reason": "packaging_not_set",
    }
    assert comp(shop, "ads")["status"] == "not_included" and comp(shop, "ads")["amount_minor"] is None
    assert shop["revenue_minor"] == 1040000 and shop["contribution_minor"] == 362500
    assert shop["complete"] is False
    # The seller sets a packaging cost: now every component has data.
    client.put(f"{API}/intelligence/profit/settings", headers=seller.h(), json={"packaging_cost_minor": 2000})
    shop = client.get(f"{API}/intelligence/profit", headers=seller.h()).json()["shop"]
    assert comp(shop, "packaging")["amount_minor"] == -8000 and shop["contribution_minor"] == 354500
    assert shop["complete"] is True and shop["margin_pct"] == round(100 * 354500 / 1040000, 1)
    # A product sold without a cost: its cost of goods is "not included", the shop's is "partial".
    p2, vid2 = item(client, seller, sku="SHAWL-1", stock=0)
    sale(m, p2["id"], vid2, cost=None, courier_account=acc)
    r = client.get(f"{API}/intelligence/profit", headers=seller.h()).json()
    assert comp(r["shop"], "cogs")["status"] == "partial" and comp(r["shop"], "cogs")["missing"] == 1
    shawl = next(x for x in r["products"] if x["product_id"] == p2["id"])
    assert comp(shawl, "cogs")["status"] == "not_included" and comp(shawl, "cogs")["amount_minor"] is None
    kurta_row = next(x for x in r["products"] if x["product_id"] == pid)
    assert kurta_row["units"] == 4 and kurta_row["contribution_per_unit_minor"] is not None


def test_order_lines_keep_the_cost_at_the_time_of_sale(client, seller):
    _p, vid = item(client, seller, stock=5)
    with session_scope() as db:
        db.execute(
            update(Variant)
            .where(Variant.id == uuid.UUID(vid))
            .values(cost_minor=120000)
            .execution_options(skip_tenant_filter=True)
        )
    oid = order(client, seller, vid).json()["id"]
    with session_scope() as db:
        db.execute(
            update(Variant)
            .where(Variant.id == uuid.UUID(vid))
            .values(cost_minor=150000)
            .execution_options(skip_tenant_filter=True)
        )
        line = db.scalar(
            select(OrderLine)
            .where(OrderLine.order_id == uuid.UUID(oid))
            .execution_options(skip_tenant_filter=True)
        )
    assert line is not None and line.unit_cost_minor == 120000  # a later cost change doesn't rewrite history


def test_profit_settings_are_validated_and_audited(client, seller):
    set_plan(seller.merchant_id, "pro")
    bad = client.put(
        f"{API}/intelligence/profit/settings", headers=seller.h(), json={"max_return_rate_pct": 140}
    )
    assert bad.status_code in (400, 422)
    ok = client.put(
        f"{API}/intelligence/profit/settings",
        headers=seller.h(),
        json={"packaging_cost_minor": 3000, "min_margin_pct": 25, "max_return_rate_pct": 12},
    ).json()
    assert ok == {
        "packaging_cost_minor": 3000,
        "min_margin_pct": 25.0,
        "min_contribution_minor": 0,
        "max_return_rate_pct": 12.0,
    }
    cleared = client.put(
        f"{API}/intelligence/profit/settings", headers=seller.h(), json={"clear_packaging": True}
    ).json()
    assert cleared["packaging_cost_minor"] is None
    from app.domains.audit.models import AuditLog

    with session_scope() as db:
        n = len(
            list(
                db.scalars(
                    select(AuditLog)
                    .where(AuditLog.action == "intelligence.profit_settings_updated")
                    .execution_options(skip_tenant_filter=True)
                )
            )
        )
    assert n == 2


# ----------------------------------------------------------------------------- Product Brain
def test_ewma_golden_values_and_backtest():
    assert product_brain.ewma([]) is None
    assert product_brain.ewma([4, 4, 4]) == 4
    assert product_brain.ewma([0, 0, 10]) == 2.0
    # PBR-010 backtest: steady demand of 3/day with a 20-day stockout. Counting only in-stock days
    # recovers ~3/day; averaging over all days would say 2.3/day and under-order.
    days = [3.0] * 70  # in-stock days only (the 20 sold-out days are excluded by construction)
    est = product_brain.ewma(days)
    assert est is not None and abs(est - 3.0) < 0.01
    naive = sum(days) / 90
    assert abs(naive - 3.0) > 0.6


def test_product_brain_uses_in_stock_days_and_lists_what_it_cant_know(client, seller):
    set_plan(seller.merchant_id, "growth")
    p, vid = item(client, seller, stock=5)
    m, pid = seller.merchant_id, p["id"]
    mid = uuid.UUID(m)
    with session_scope(mid) as db:
        lvl = db.scalar(select(InventoryLevel).where(InventoryLevel.variant_id == uuid.UUID(vid)))
        assert lvl is not None
        now = utcnow()
        for days, after in ((60, 10), (30, 0), (20, 15)):
            db.add(
                InventoryLedgerEntry(
                    merchant_id=mid,
                    variant_id=uuid.UUID(vid),
                    location_id=lvl.location_id,
                    kind="adjust",
                    on_hand_delta=0,
                    on_hand_after=after,
                    reserved_after=0,
                    actor_type="system",
                    created_at=now - timedelta(days=days, hours=1),
                )
            )
    for d in range(1, 20, 2):
        sale(m, pid, vid, qty=2, days_ago=d, cost=None)
    r = client.get(f"{API}/intelligence/products/{pid}/brain", headers=seller.h())
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["in_stock_days_90d"] == 52 and b["stockouts_90d"] == 1
    assert b["units_30d"] == 20 and b["units_7d"] == 6
    assert b["demand_per_day"] is not None and b["demand_per_day"] > 0
    assert b["available"] == 5 and b["cover_days"] == round(5 / b["demand_per_day"], 1)
    assert b["margin_pct"] is None and b["not_included"]["margin"] == "cost_not_set"
    assert b["not_included"]["channel_conversion"] == "needs_content_metrics"
    assert b["not_included"]["seasonality"] == "needs_12_months"
    assert b["completeness"] < 1 and b["method_version"] == "pbr-1.0"
    assert b["stock_risk"] in ("high", "medium", "low")
    # Cost set → margin appears on refresh.
    with session_scope() as db:
        db.execute(
            update(Variant)
            .where(Variant.id == uuid.UUID(vid))
            .values(cost_minor=98000)
            .execution_options(skip_tenant_filter=True)
        )
    b = client.get(
        f"{API}/intelligence/products/{pid}/brain", params={"refresh": True}, headers=seller.h()
    ).json()
    assert b["margin_pct"] == 60.0
    # Stock risk list (UX-012) includes it when cover is short.
    risk = client.get(f"{API}/intelligence/stock-risk", headers=seller.h()).json()["items"]
    assert any(x["product_id"] == pid for x in risk) == (b["stock_risk"] in ("out", "high", "medium"))


def test_product_brain_refreshes_when_an_order_is_delivered(client, seller):
    set_plan(seller.merchant_id, "growth")
    p, vid = item(client, seller, stock=5)
    oid = order(client, seller, vid).json()["id"]
    from tests.test_channels import _dispatch

    for to in ("ready_to_ship", "shipped", "delivered"):
        client.post(f"{API}/orders/{oid}/transition", headers=seller.h(), json={"to": to})
    _dispatch()
    from app.domains.intelligence.models import ProductIntelligenceProfile

    with session_scope() as db:
        prof = db.scalar(
            select(ProductIntelligenceProfile)
            .where(ProductIntelligenceProfile.product_id == uuid.UUID(p["id"]))
            .execution_options(skip_tenant_filter=True)
        )
    assert prof is not None and prof.units_7d == 1


# ----------------------------------------------------------------------------- Return Intelligence
def _return_pattern(client, seller) -> tuple[dict[str, Any], str]:
    p = kurta(client, seller)
    vid = p["variants"][0]["id"]
    acc = courier(client, seller, "Courier A", default=True)["id"]
    m = seller.merchant_id
    for i in range(12):
        reason = "size_small" if i < 5 else ("changed_mind" if i == 5 else None)
        sale(
            m,
            p["id"],
            vid,
            courier_account=acc,
            days_ago=40,
            status="returned" if reason else "delivered",
            return_reason=reason,
            restocked=1 if reason else 0,
            refund=245000 if reason else None,
        )
    # The rest of the shop: 40 sales, 1 return → a 7/52 baseline.
    other, ovid = item(client, seller, sku="SHAWL-9", stock=0)
    for i in range(40):
        sale(
            m,
            other["id"],
            ovid,
            courier_account=acc,
            days_ago=40,
            status="returned" if i == 0 else "delivered",
            return_reason="changed_mind" if i == 0 else None,
        )
    return p, vid


def test_return_pattern_becomes_a_fit_fact_used_in_chat_only_after_the_seller_confirms(client, seller):
    p, _vid = _return_pattern(client, seller)
    chat = Chat(client, seller, plan="pro")
    d = client.post(f"{API}/intelligence/return-insights/refresh", headers=seller.h()).json()
    assert d["raised"] == 1
    ins = client.get(f"{API}/intelligence/return-insights", headers=seller.h()).json()["items"][0]
    assert ins["pattern"] == "reason:size_small" and ins["reason_share"] == round(5 / 6, 2)
    assert ins["sold"] == 12 and ins["returned"] == 6 and ins["baseline_rate"] == round(7 / 52, 4)
    assert ins["p_value"] < 0.05 and any(c["type"] == "content_version" for c in ins["causes"])
    facts = client.get(f"{API}/intelligence/memory/facts", headers=seller.h()).json()["items"]
    fit = next(f for f in facts if f["fact_type"] == "fit_runs_small")
    assert fit["subject_id"] == p["id"] and fit["confirmed"] is False and fit["value"]["returns"] == 5
    # Not confirmed yet: the Sales Agent says nothing about fit.
    assert "runs small" not in (chat.say("Dhaka kurta M cha?") or "")
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    rec = next(
        r
        for r in client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
        if r["type"] == "return_prevention"
    )
    assert rec["action"]["type"] == "confirm_fact" and rec["explanation"]["vars"]["share_pct"] == 83
    done = client.post(f"{API}/intelligence/recommendations/{rec['id']}/accept", headers=seller.h()).json()
    assert done["status"] == "executed"
    assert (
        client.get(f"{API}/intelligence/return-insights", headers=seller.h()).json()["items"][0]["status"]
        == "acted"
    )
    reply = chat.say("Dhaka kurta M cha?")
    assert reply is not None and "runs small" in reply and "one size up" in reply
    brain = client.get(f"{API}/intelligence/products/{p['id']}/brain", headers=seller.h()).json()
    assert brain["fit"] == "small" and brain["return_insights"][0]["status"] == "acted"
    # RTI-005: 30 days later, 10 new sales with 1 return → measured.
    with session_scope() as db:
        db.execute(
            update(ReturnInsight)
            .values(acted_at=utcnow() - timedelta(days=31))
            .execution_options(skip_tenant_filter=True)
        )
    acc = client.get(f"{API}/couriers", headers=seller.h()).json()["items"][0]["id"]
    for i in range(10):
        sale(
            seller.merchant_id,
            p["id"],
            p["variants"][0]["id"],
            days_ago=2,
            courier_account=acc,
            status="returned" if i == 0 else "delivered",
            return_reason="size_small" if i == 0 else None,
        )
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        assert return_intel.measure(db, uuid.UUID(seller.merchant_id)) == 1
    ins = client.get(f"{API}/intelligence/return-insights", headers=seller.h()).json()["items"][0]
    assert ins["post_change_rate"] == 0.1 and ins["post_change_sold"] == 10


def test_dismissed_insight_is_not_raised_again_and_needs_the_plan(client, seller):
    _return_pattern(client, seller)
    set_plan(seller.merchant_id, "growth")
    assert client.get(f"{API}/intelligence/return-insights", headers=seller.h()).status_code == 403
    assert client.get(f"{API}/intelligence/profit", headers=seller.h()).status_code == 403
    set_plan(seller.merchant_id, "pro")
    client.post(f"{API}/intelligence/return-insights/refresh", headers=seller.h())
    ins = client.get(f"{API}/intelligence/return-insights", headers=seller.h()).json()["items"][0]
    r = client.post(
        f"{API}/intelligence/return-insights/{ins['id']}/dismiss",
        headers=seller.h(),
        json={"reason": "Sizes changed with the new batch"},
    )
    assert r.json()["status"] == "dismissed"
    assert (
        client.post(f"{API}/intelligence/return-insights/refresh", headers=seller.h()).json()["raised"] == 0
    )
    assert client.get(f"{API}/intelligence/return-insights", headers=seller.h()).json()["items"] == []


def test_small_samples_raise_nothing(client, seller):
    set_plan(seller.merchant_id, "pro")
    p, vid = item(client, seller, stock=0)
    for i in range(4):  # 2 of 4 returned: 50%, but far too few to call a pattern
        sale(
            seller.merchant_id,
            p["id"],
            vid,
            status="returned" if i < 2 else "delivered",
            return_reason="size_small" if i < 2 else None,
        )
    assert (
        client.post(f"{API}/intelligence/return-insights/refresh", headers=seller.h()).json()["raised"] == 0
    )
    assert return_intel.binomial_p(5, 10, 0.1) < 0.01 and return_intel.binomial_p(1, 10, 0.1) > 0.6


# ----------------------------------------------------------------------------- Commerce Memory
def test_memory_facts_are_versioned_and_the_seller_has_the_last_word(client, seller):
    set_plan(seller.merchant_id, "growth")
    p, vid = item(client, seller, stock=0)
    mid = uuid.UUID(seller.merchant_id)
    custs = []
    with session_scope(mid) as db:
        for i in range(6):
            c = Customer(merchant_id=mid, display_name=f"Customer {i}", phone=f"+97798000000{i:02d}")
            db.add(c)
            db.flush()
            custs.append(c.id)
    # Six customers reorder every 20 days (3 orders each → 12 intervals).
    for c in custs:
        for k in range(3):
            sale(seller.merchant_id, p["id"], vid, days_ago=60 - 20 * k, customer_id=c)
    out = client.post(f"{API}/intelligence/memory/refresh", headers=seller.h()).json()
    assert out["metrics"] > 0
    facts = client.get(f"{API}/intelligence/memory/facts", headers=seller.h()).json()["items"]
    cyc = next(f for f in facts if f["fact_type"] == "repeat_cycle_days")
    assert cyc["value"] == {"days": 20, "customers": 6} and cyc["version"] == 1 and cyc["source"] == "derived"
    assert cyc["evidence"][0]["intervals"] == 12
    # The seller knows better: festival buyers come back monthly.
    fixed = client.post(
        f"{API}/intelligence/memory/facts/{cyc['id']}/correct",
        headers=seller.h(),
        json={"value": {"days": 30}, "note": "Most reorder for the next festival"},
    ).json()
    assert fixed["version"] == 2 and fixed["source"] == "merchant" and fixed["confirmed"] is True
    assert fixed["value"] == {"days": 30, "customers": 6}
    client.post(f"{API}/intelligence/memory/refresh", headers=seller.h())
    now = client.get(f"{API}/intelligence/memory/facts", headers=seller.h()).json()["items"]
    assert (
        next(f for f in now if f["fact_type"] == "repeat_cycle_days")["id"] == fixed["id"]
    )  # not overwritten
    hist = client.get(
        f"{API}/intelligence/memory/facts", params={"include_history": True}, headers=seller.h()
    ).json()["items"]
    assert [f["status"] for f in hist if f["fact_type"] == "repeat_cycle_days"] == ["active", "superseded"]
    bad = client.post(
        f"{API}/intelligence/memory/facts/{fixed['id']}/correct",
        headers=seller.h(),
        json={"value": {"days": "soon"}, "note": "typo"},
    )
    assert bad.status_code in (400, 422)
    # Metrics are registered, defined and idempotent.
    pts = client.get(
        f"{API}/intelligence/memory/metrics",
        params={"metric": "units_sold", "subject_type": "product", "subject_id": p["id"]},
        headers=seller.h(),
    ).json()
    assert pts["definition"].startswith("Units on orders") and sum(x["value"] for x in pts["points"]) == 18
    client.post(f"{API}/intelligence/memory/refresh", headers=seller.h())
    pts2 = client.get(
        f"{API}/intelligence/memory/metrics",
        params={"metric": "units_sold", "subject_type": "product", "subject_id": p["id"]},
        headers=seller.h(),
    ).json()
    assert pts2["points"] == pts["points"]


def test_rejected_fact_is_not_derived_again_until_the_method_changes(client, seller):
    set_plan(seller.merchant_id, "growth")
    mid = uuid.UUID(seller.merchant_id)
    with session_scope(mid) as db:
        f = memory.put_fact(
            db,
            mid,
            "shop",
            str(mid),
            "peak_order_hours",
            {"start_hour": 19, "end_hour": 22, "share": 0.4},
            0.7,
            [],
        )
        assert f is not None
        fid = f.id
    r = client.post(
        f"{API}/intelligence/memory/facts/{fid}/reject", headers=seller.h(), json={"note": "We close at 6pm"}
    )
    assert r.json()["status"] == "rejected_by_merchant"
    with session_scope(mid) as db:
        assert (
            memory.put_fact(
                db,
                mid,
                "shop",
                str(mid),
                "peak_order_hours",
                {"start_hour": 19, "end_hour": 22, "share": 0.5},
                0.7,
                [],
            )
            is None
        )
        db.execute(
            update(CommerceMemoryFact)
            .values(method_version="mem-0.9")
            .execution_options(skip_tenant_filter=True)
        )
    with session_scope(mid) as db:
        again = memory.put_fact(
            db,
            mid,
            "shop",
            str(mid),
            "peak_order_hours",
            {"start_hour": 18, "end_hour": 21, "share": 0.5},
            0.7,
            [],
        )
        assert again is not None and again.version == 2  # MEM-008: a new method may suggest it again


def test_memory_holds_no_personal_facts_and_is_tenant_isolated(client, seller):
    assert all(spec["subject"] != "customer" for spec in memory.FACT_TYPES.values())
    assert all(spec["subject"] != "customer" for spec in memory.METRICS.values())
    set_plan(seller.merchant_id, "growth")
    mid = uuid.UUID(seller.merchant_id)
    with session_scope(mid) as db:
        f = memory.put_fact(
            db, mid, "shop", str(mid), "repeat_cycle_days", {"days": 20, "customers": 6}, 0.6, []
        )
        assert f is not None
        fid = f.id
    o = onboard(client, shop="Other Shop")
    set_plan(o.merchant_id, "growth")
    assert client.post(f"{API}/intelligence/memory/facts/{fid}/confirm", headers=o.h()).status_code == 404
    assert client.get(f"{API}/intelligence/memory/facts", headers=o.h()).json()["items"] == []


# ----------------------------------------------------------------------------- profit-aware suggestions
def test_suggestions_rank_by_profit_and_never_push_loss_makers(client, seller):
    set_plan(seller.merchant_id, "pro")
    acc = courier(client, seller, "Courier A", default=True)["id"]
    good, gvid = item(client, seller, sku="GOOD-1", stock=3)
    bad, bvid = item(client, seller, sku="BAD-1", price=100000, stock=3)
    for vid in (gvid, bvid):
        client.put(f"{API}/inventory/variants/{vid}/threshold", headers=seller.h(), json={"threshold": 5})
    for _ in range(6):
        sale(seller.merchant_id, good["id"], gvid, courier_account=acc)
        sale(
            seller.merchant_id, bad["id"], bvid, price=100000, cost=95000, courier_account=acc, delivery_fee=0
        )
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        product_brain.recompute_merchant(db, uuid.UUID(seller.merchant_id))
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    recs = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    restock = [r for r in recs if r["type"] == "restock"]
    assert [r["explanation"]["vars"]["title"] for r in restock] == ["Cotton Kurta"]
    assert restock[0]["estimated_impact"]["contribution_30d_minor"] > 0
    assert restock[0]["subject_id"] == gvid
    loss = next(r for r in recs if r["type"] == "profit_loss")
    assert loss["subject_id"] == bad["id"] and loss["explanation"]["vars"]["contribution"] < 0
    assert loss["action"]["type"] == "none"  # Nivaro never changes prices on its own


def test_profit_suggestion_asks_for_cost_when_missing(client, seller):
    set_plan(seller.merchant_id, "pro")
    p, vid = item(client, seller, stock=0)
    for _ in range(3):
        sale(seller.merchant_id, p["id"], vid, cost=None)
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    recs = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    r = next(x for x in recs if x["type"] == "profit_data")
    assert r["explanation"]["what"] == "add_cost" and r["subject_id"] == p["id"]
