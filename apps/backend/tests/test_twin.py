"""Phase 9: Digital Store Twin (TWIN-001…006) and simulation (SIM-001…006)."""

from __future__ import annotations

import math
import uuid
from datetime import timedelta

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.automation import policy
from app.domains.platform.models import OutboxEvent
from app.domains.twin import service as twin
from app.domains.twin import simulation
from app.domains.twin.models import SimulationRun, StoreTwinSection, StoreTwinSnapshot
from tests.conftest import set_plan
from tests.test_channels import _dispatch
from tests.test_intelligence_b import sale
from tests.test_orders import item, order

API = "/api/v1"


def _cost(vid: str, cost: int) -> None:
    from app.domains.catalog.models import Variant

    with session_scope() as db:
        db.execute(
            update(Variant)
            .where(Variant.id == uuid.UUID(vid))
            .values(cost_minor=cost)
            .execution_options(skip_tenant_filter=True)
        )


def _in_stock_since(merchant_id: str, vid: str, *, days: int, on_hand: int) -> None:
    """The ledger is append-only: add an older entry so the product counts as in stock since then."""
    from app.domains.inventory.models import InventoryLedgerEntry, InventoryLevel

    mid = uuid.UUID(merchant_id)
    with session_scope(mid) as db:
        lvl = db.scalar(select(InventoryLevel).where(InventoryLevel.variant_id == uuid.UUID(vid)))
        assert lvl is not None
        db.add(
            InventoryLedgerEntry(
                merchant_id=mid,
                variant_id=uuid.UUID(vid),
                location_id=lvl.location_id,
                kind="adjust",
                on_hand_delta=0,
                on_hand_after=on_hand,
                reserved_after=0,
                actor_type="system",
                created_at=utcnow() - timedelta(days=days),
            )
        )


def section(merchant_id: str, name: str) -> StoreTwinSection:
    with session_scope() as db:
        s = db.scalar(
            select(StoreTwinSection)
            .where(StoreTwinSection.merchant_id == uuid.UUID(merchant_id), StoreTwinSection.section == name)
            .execution_options(skip_tenant_filter=True)
        )
        assert s is not None
        db.expunge(s)
        return s


# ----------------------------------------------------------------------------- Twin
def test_twin_sections_follow_events_monotonically_and_flag_material_changes(client, seller):
    _p, vid = item(client, seller, stock=5)
    summary = client.get(f"{API}/twin/summary", headers=seller.h()).json()
    assert set(summary["sections"]) == set(twin.SECTIONS)
    inv = summary["sections"]["inventory"]
    assert inv["state"]["on_hand"] == 5 and inv["stale"] is False and inv["owner"] == "inventory"
    assert summary["currency"] == "NPR"
    assert summary["sections"]["orders"]["state"]["open"] == 0
    order(client, seller, vid, qty=2)
    _dispatch()
    o = section(seller.merchant_id, "orders")
    assert o.state["open"] == 1 and o.trigger in ("orders.created", "orders.status_changed")
    assert o.lag_ms is not None and o.lag_ms >= 0
    assert section(seller.merchant_id, "inventory").state["reserved"] == 2
    oid = client.get(f"{API}/orders", headers=seller.h()).json()["items"][0]["id"]
    for to in ("ready_to_ship", "shipped", "delivered"):
        client.post(f"{API}/orders/{oid}/transition", headers=seller.h(), json={"to": to})
    _dispatch()
    assert section(seller.merchant_id, "orders").state["open"] == 0  # delivered orders aren't open
    # Monotonic: an older version never overwrites newer state.
    mid = uuid.UUID(seller.merchant_id)
    with session_scope(mid) as db:
        kept = twin.refresh(db, mid, "orders", trigger="late_event", source_version=1)
        assert kept is not None and kept.trigger != "late_event"
    with session_scope() as db:
        evs = list(
            db.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.event_type == "twin.updated")
                .execution_options(skip_tenant_filter=True)
            )
        )
    assert any(e.payload["section"] == "orders" and e.payload["changes"].get("open") == 1 for e in evs)


def test_old_sections_are_recomputed_on_read_and_snapshots_are_daily(client, seller):
    item(client, seller, stock=3)
    client.get(f"{API}/twin/summary", headers=seller.h())
    with session_scope() as db:
        db.execute(
            update(StoreTwinSection)
            .where(StoreTwinSection.section == "catalog")
            .values(as_of=utcnow() - timedelta(hours=5), state={"active": 99})
            .execution_options(skip_tenant_filter=True)
        )
    got = client.get(f"{API}/twin/sections/catalog", headers=seller.h()).json()
    assert got["state"]["draft"] == 1 and got["stale"] is False  # recomputed because it was past its TTL
    assert section(seller.merchant_id, "catalog").trigger == "read"
    mid = uuid.UUID(seller.merchant_id)
    with session_scope(mid) as db:
        twin.snapshot(db, mid)
        twin.snapshot(db, mid)  # idempotent per day
    with session_scope() as db:
        snaps = list(db.scalars(select(StoreTwinSnapshot).execution_options(skip_tenant_filter=True)))
    assert len(snaps) == 1 and snaps[0].sections["inventory"]["on_hand"] == 3
    f = client.get(f"{API}/twin/freshness", headers=seller.h()).json()
    assert f["target_p95_s"] == 60 and {s["section"] for s in f["sections"]} >= {"catalog", "inventory"}
    assert (
        client.get(f"{API}/twin/summary", params={"sections": "nope"}, headers=seller.h()).status_code == 400
    )
    from tests.test_procurement import staff_of

    staff = staff_of(client, seller, "staff-twin@example.com")
    staff_h = staff.h(merchant=seller.merchant_id)
    assert client.get(f"{API}/twin/summary", headers=staff_h).status_code == 403  # shop totals: managers+


def test_decision_policy_refuses_to_auto_run_on_stale_twin_data(client, seller):
    set_plan(seller.merchant_id, "business")
    r = client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "autopilot"})
    assert r.status_code == 200, r.text
    client.get(f"{API}/twin/summary", headers=seller.h())
    mid = uuid.UUID(seller.merchant_id)
    prop = policy.Proposal(
        action="send_message", risk_class="R1", source="workflow", confidence=0.99, twin_sections=("orders",)
    )
    with session_scope(mid) as db:
        first = policy.decide(db, mid, prop)
        assert first.decision == "AUTO_EXECUTE", first.rule
    with session_scope() as db:
        db.execute(
            update(StoreTwinSection)
            .values(as_of=utcnow() - timedelta(hours=1))
            .execution_options(skip_tenant_filter=True)
        )
    with session_scope(mid) as db:
        rec = policy.decide(db, mid, prop)
        assert rec.decision == "REQUIRE_APPROVAL" and rec.rule == "stale_data"
        assert rec.explanation["vars"]["stale_sections"] == ["orders"]


# ----------------------------------------------------------------------------- simulation maths
def test_poisson_helpers_golden_values():
    assert simulation.poisson_sf(-1, 3) == 1.0 and simulation.poisson_sf(5, 0) == 0.0
    assert abs(simulation.poisson_sf(2, 2) - (1 - math.exp(-2) * (1 + 2 + 2))) < 1e-9
    assert abs(simulation.poisson_sf(1000, 1000) - 0.4874) < 0.01  # normal approximation
    assert simulation.expected_sold(5, 100) > 4.99 and simulation.expected_sold(50, 10) < 10
    assert simulation.expected_sold(3, 0) == 0


# ----------------------------------------------------------------------------- simulations
def _run(client, s, body) -> dict:
    r = client.post(f"{API}/simulations", headers=s.h(), json=body)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "queued" and r.json()["executes_nothing"] is True
    _dispatch()
    return client.get(f"{API}/simulations/{r.json()['id']}", headers=s.h()).json()


def test_discount_uses_own_promotion_history_and_shows_the_trade_off(client, seller):
    set_plan(seller.merchant_id, "business")
    p, vid = item(client, seller, stock=0)  # untracked stock: no cap
    m = seller.merchant_id
    _cost(vid, 120000)
    for d in range(1, 61):
        if d % 6 == 0:  # 10 promotion days at 20% off: 3 units instead of 1
            sale(m, p["id"], vid, qty=3, days_ago=d, discount=3 * 49000, cost=120000)
        else:
            sale(m, p["id"], vid, qty=1, days_ago=d, cost=120000)
    run = _run(
        client,
        seller,
        {"kind": "discount", "discount": {"product_id": p["id"], "discount_pct": 20, "days": 14}},
    )
    assert run["status"] == "completed" and run["label"] == "estimate", run
    o = run["outputs"]
    el = next(a for a in run["assumptions"] if a["code"].startswith("elasticity_"))
    assert el["code"] == "elasticity_history" and el["vars"]["discount_days"] == 10
    assert el["vars"]["value"] < -1  # history says customers respond strongly
    assert o["units"]["low"] <= o["units"]["expected"] <= o["units"]["high"]
    assert o["demand_per_day"]["expected"] > o["demand_per_day"]["baseline"]
    assert o["margin_pct"]["after"] < o["margin_pct"]["before"]
    assert o["contribution_per_unit_minor"]["after"] == o["contribution_per_unit_minor"]["before"] - round(
        245000 * 0.2
    )
    assert o["stock"] is None and any(a["code"] == "stock_not_tracked" for a in run["assumptions"])
    assert run["confidence"] == "medium"
    # A deeper discount below the margin floor is flagged.
    deep = _run(
        client,
        seller,
        {"kind": "discount", "discount": {"product_id": p["id"], "discount_pct": 45, "days": 14}},
    )
    assert any(w["code"] == "below_min_margin" for w in deep["outputs"]["warnings"])


def test_discount_without_history_uses_a_typical_range_and_caps_by_stock(client, seller):
    set_plan(seller.merchant_id, "business")
    p, vid = item(client, seller, stock=0)
    m = seller.merchant_id
    for d in range(1, 31):
        sale(m, p["id"], vid, qty=2, days_ago=d, cost=100000)
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 10})
    _in_stock_since(seller.merchant_id, vid, days=40, on_hand=10)
    run = _run(
        client,
        seller,
        {"kind": "discount", "discount": {"product_id": p["id"], "discount_pct": 15, "days": 14}},
    )
    assert run["status"] == "completed", run
    o = run["outputs"]
    assert (
        any(a["code"] == "elasticity_typical_range" for a in run["assumptions"])
        and run["confidence"] == "low"
    )
    assert o["stock"] == 10 and o["units"]["expected"] <= 10  # can't sell what isn't there
    assert o["stockout_probability"] > 0.9 and any(w["code"] == "stockout_likely" for w in o["warnings"])


def test_purchase_quantity_estimates_risk_cover_and_cash(client, seller):
    set_plan(seller.merchant_id, "business")
    sup = client.post(
        f"{API}/procurement/suppliers",
        headers=seller.h(),
        json={"name": "Thimi Pottery", "default_lead_time_days": 12},
    ).json()
    p, vid = item(client, seller, stock=6)
    client.put(
        f"{API}/procurement/suppliers/{sup['id']}/products/{vid}",
        headers=seller.h(),
        json={"cost_minor": 80000, "moq": 30},
    )
    for d in range(1, 91, 3):
        sale(seller.merchant_id, p["id"], vid, qty=1, days_ago=d)
    run = _run(client, seller, {"kind": "purchase_quantity", "purchase": {"variant_id": vid, "quantity": 20}})
    assert run["status"] == "completed", run
    o = run["outputs"]
    assert o["lead_days"] == 12 and o["supplier"] == "Thimi Pottery" and o["available"] == 6
    assert o["cash_tied_up_minor"] == 20 * 80000
    assert 0 <= o["stockout_before_arrival_probability"] <= 1
    assert any(w["code"] == "below_moq" for w in o["warnings"])
    assert any(a["code"] == "lead_time_supplier_terms" for a in run["assumptions"])


def test_simulation_rules_plan_and_ad_budget(client, seller):
    set_plan(seller.merchant_id, "pro")
    p, _vid = item(client, seller, stock=0)
    body = {"kind": "discount", "discount": {"product_id": p["id"], "discount_pct": 10, "days": 7}}
    assert client.post(f"{API}/simulations", headers=seller.h(), json=body).status_code == 403
    set_plan(seller.merchant_id, "business")
    ad = client.post(f"{API}/simulations", headers=seller.h(), json={"kind": "ad_budget"})
    assert ad.status_code == 409 and ad.json()["error"]["code"] == "simulation_needs_ad_account"
    none = _run(client, seller, body)
    assert none["status"] == "failed" and none["error_code"] == "simulation_not_enough_sales"
    assert client.post(f"{API}/simulations", headers=seller.h(), json={"kind": "discount"}).status_code == 400


def test_calibration_backtests_demand_and_compares_realized_discounts(client, seller):
    set_plan(seller.merchant_id, "business")
    p, vid = item(client, seller, stock=0)
    for d in range(9, 109):  # full-price history ends before the discount window
        sale(seller.merchant_id, p["id"], vid, qty=2, days_ago=d - 0.5, cost=100000)
    run = _run(
        client,
        seller,
        {"kind": "discount", "discount": {"product_id": p["id"], "discount_pct": 20, "days": 7}},
    )
    assert run["status"] == "completed"
    # The seller then ran a 20% discount for those 7 days.
    with session_scope() as db:
        db.execute(
            update(SimulationRun)
            .values(created_at=utcnow() - timedelta(days=8))
            .execution_options(skip_tenant_filter=True)
        )
    for d in range(2, 8):
        sale(seller.merchant_id, p["id"], vid, qty=3, days_ago=d, discount=3 * 49000, cost=100000)
    cal = client.get(f"{API}/simulations/calibration", headers=seller.h()).json()
    bt = cal["demand_backtest"]
    assert bt["products"] == 1 and bt["holdout_days"] == 14 and bt["mape"] is not None
    assert cal["discount_runs_compared"] == 1 and cal["discount_runs_mape"] is not None
    got = client.get(f"{API}/simulations/{run['id']}", headers=seller.h()).json()
    assert got["actual"]["comparable"] is True and got["abs_pct_error"] is not None
