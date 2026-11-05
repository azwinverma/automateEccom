"""Phase 6 part A: Autopilot Score (APS-001…005/007), Courier Brain (CRI-001…005, FUL-009),
COD Intelligence (CODI-001…005) and recommendations (REC-001…003/005…008)."""

from __future__ import annotations

import inspect
import uuid
from datetime import timedelta

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.automation.policy import log_action
from app.domains.fulfillment.models import Shipment
from app.domains.intelligence import aps, cod_risk, courier_brain
from app.domains.intelligence.models import AutopilotScoreSnapshot, CODRiskAssessment, Recommendation
from app.domains.orders.models import Order
from tests.conftest import onboard, register_and_login, set_plan
from tests.test_channels import _dispatch
from tests.test_fulfillment import PICKUP
from tests.test_orders import ADDR, item, order

API = "/api/v1"


def logs(
    merchant_id: str,
    capability: str,
    by: str,
    n: int,
    *,
    action: str = "act",
    outcome: str = "success",
    human: bool = False,
    eligible: bool = True,
    exclusion: str | None = None,
) -> None:
    with session_scope() as db:
        for i in range(n):
            log_action(
                db,
                uuid.UUID(merchant_id),
                capability,
                action,
                by,
                key=f"t:{capability}:{by}:{outcome}:{human}:{eligible}:{uuid.uuid4()}:{i}",
                outcome=outcome,
                human_intervened=human,
                eligible=eligible,
                exclusion_reason=exclusion,
            )


def seed_parcels(
    merchant_id: str,
    account_id: str,
    n: int,
    delivered: int,
    *,
    dest: str = "kaski",
    cod: bool = True,
    failed_first: int = 0,
) -> None:
    """Finished outbound parcels (orders + shipments) straight in the DB: Courier Brain's raw material."""
    mid = uuid.UUID(merchant_id)
    with session_scope(mid) as db:
        base = (db.query(Order).count() or 0) + 5000
        for i in range(n):
            o = Order(
                merchant_id=mid,
                number=base + i,
                status="delivered" if i < delivered else "returned",
                source="seller",
                currency="NPR",
                total_minor=200000,
                subtotal_minor=200000,
                payment_method="cod" if cod else "prepaid",
                payment_status="cod_collected" if cod else "paid",
                ship_district=dest,
            )
            db.add(o)
            db.flush()
            now = utcnow()
            db.add(
                Shipment(
                    merchant_id=mid,
                    order_id=o.id,
                    courier_account_id=uuid.UUID(account_id),
                    provider="sandbox_courier",
                    status="delivered" if i < delivered else "returned_to_origin",
                    weight_grams=500,
                    cod_amount_minor=200000 if cod else 0,
                    charge_minor=17500,
                    currency="NPR",
                    origin_district="kathmandu",
                    destination_district=dest,
                    attempt_count=1 if i < failed_first else 0,
                    idempotency_key=f"seed-{account_id}-{dest}-{base + i}",
                    picked_up_at=now - timedelta(days=3),
                    delivered_at=now - timedelta(days=1) if i < delivered else None,
                    returned_at=None if i < delivered else now,
                )
            )


def courier(client, s, name, default=False):
    r = client.post(
        f"{API}/couriers",
        headers=s.h(),
        json={"provider": "sandbox_courier", "display_name": name, "pickup": PICKUP, "is_default": default},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ----------------------------------------------------------------------------- Autopilot Score
def test_score_counts_automated_failed_manual_and_excluded_with_thin_data(client, seller):
    mid = seller.merchant_id
    logs(mid, "customer_messaging", "ai", 30)
    logs(mid, "customer_messaging", "ai", 5, human=True)  # suggestions a person approved → manual
    logs(mid, "customer_messaging", "user", 5)
    logs(mid, "fulfillment", "automation", 8, action="book_courier")
    logs(mid, "fulfillment", "user", 2, action="book_courier")
    logs(mid, "workflow:book_courier", "automation", 1, action="book_courier", outcome="failed")
    logs(
        mid,
        "workflow:approve_return",
        "automation",
        4,
        action="approve_return",
        eligible=False,
        exclusion="above_threshold",
    )
    logs(mid, "returns", "user", 3, action="approve_return")
    with session_scope() as db:
        sc = aps.compute(db, uuid.UUID(mid))
    cr = sc["capabilities"]["customer_replies"]
    assert (cr["A"], cr["F"], cr["M"], cr["score"]) == (30, 0, 10, 0.75)
    sh = sc["capabilities"]["shipment_creation"]
    assert (sh["A"], sh["F"], sh["M"], sh["eligible"], sh["score"]) == (8, 1, 2, 11, round(8 / 11, 3))
    rt = sc["capabilities"]["returns"]
    assert (
        rt["X"] == 4
        and rt["excluded"] == {"above_threshold": 4}
        and rt["score"] is None
        and rt["status"] == "not_enough_activity"
    )
    assert sc["overall"] == round(
        (40 * 0.75 + 11 * (8 / 11)) / 51, 3
    )  # volume-weighted, thin capabilities left out
    assert sc["hours_saved_estimate"] > 0


def test_score_api_levers_need_the_plan_and_snapshots_flag_jumps(client, seller):
    logs(seller.merchant_id, "customer_messaging", "user", 12)
    r = client.get(f"{API}/intelligence/autopilot-score", headers=seller.h()).json()
    assert (
        r["capabilities"]["customer_replies"]["score"] == 0 and r["levers"] == []
    )  # starter: score yes, levers no
    set_plan(seller.merchant_id, "growth")
    r = client.get(f"{API}/intelligence/autopilot-score", headers=seller.h()).json()
    lv = r["levers"][0]
    assert (
        lv["capability"] == "customer_replies"
        and lv["lever"] == {"type": "set_mode", "params": {"mode": "smart"}}
        and lv["potential_score"] == 1.0
    )
    mid = uuid.UUID(seller.merchant_id)
    with session_scope(mid) as db:
        db.add(
            AutopilotScoreSnapshot(
                merchant_id=mid,
                computed_on=utcnow().date() - timedelta(days=1),
                window_days=30,
                overall=0.9,
                eligible=12,
                capabilities={},
                method_version="aps-1.0",
            )
        )
    with session_scope(mid) as db:
        snap = aps.snapshot(db, mid)
        assert snap.overall == 0 and snap.anomaly == "jump_-90pts"
    assert [
        h["overall"]
        for h in client.get(f"{API}/intelligence/autopilot-score", headers=seller.h()).json()["history"]
    ] == [0.9, 0.0]


# ----------------------------------------------------------------------------- Courier Brain
def test_courier_brain_picks_the_courier_that_delivers_on_this_route(client, seller):
    set_plan(seller.merchant_id, "pro")
    a = courier(client, seller, "Courier A", default=True)
    b = courier(client, seller, "Courier B")
    seed_parcels(seller.merchant_id, a["id"], 25, 17)  # 68% to Kaski
    seed_parcels(seller.merchant_id, b["id"], 25, 24)  # 96%
    perf = client.get(
        f"{API}/intelligence/couriers/performance", params={"refresh": True}, headers=seller.h()
    ).json()
    rows = {(r["courier_name"], r["destination"]): r for r in perf["items"]}
    assert (
        rows[("Courier B", "kaski")]["delivery_success"] == 0.96
        and rows[("Courier B", "kaski")]["enough_data"] is True
    )
    assert rows[("Courier A", "kaski")]["eta_p50_days"] == 2.0
    _, vid = item(client, seller)
    o = order(
        client,
        seller,
        vid,
        address={**ADDR, "district": "Kaski", "municipality": "Pokhara Metropolitan City"},
    ).json()
    rec = client.get(f"{API}/couriers/rates", params={"order_id": o["id"]}, headers=seller.h()).json()[
        "recommendation"
    ]
    assert (
        rec["courier_account_id"] == b["id"]
        and rec["method"] == "courier_brain"
        and rec["reason"] == "route_history"
    )
    assert (
        rec["evidence"]["success_pct"] == 96
        and rec["evidence"]["n"] == 25
        and rec["alternatives"][0]["success_pct"] == 68
    )
    client.patch(f"{API}/fulfillment/settings", headers=seller.h(), json={"courier_selection": "preferred"})
    rec = client.get(f"{API}/couriers/rates", params={"order_id": o["id"]}, headers=seller.h()).json()[
        "recommendation"
    ]
    assert rec["courier_account_id"] == a["id"] and rec["reason"] == "preferred_only"
    # Lalitpur has no history: rules, and the response says why (cold start).
    client.patch(f"{API}/fulfillment/settings", headers=seller.h(), json={"courier_selection": "smart"})
    o2 = order(client, seller, vid).json()
    rec2 = client.get(f"{API}/couriers/rates", params={"order_id": o2["id"]}, headers=seller.h()).json()[
        "recommendation"
    ]
    assert rec2["method"] == "rules" and rec2["note"] == "not_enough_route_data"
    # Without the plan feature: plain rules, and the performance view is gated.
    set_plan(seller.merchant_id, "growth")
    rec3 = client.get(f"{API}/couriers/rates", params={"order_id": o["id"]}, headers=seller.h()).json()[
        "recommendation"
    ]
    assert rec3["method"] == "rules" and rec3["courier_account_id"] == a["id"]
    assert client.get(f"{API}/intelligence/couriers/performance", headers=seller.h()).status_code == 403


# ----------------------------------------------------------------------------- COD Intelligence
def test_cod_risk_uses_allowed_inputs_only_and_never_rejects(client, seller):
    set_plan(seller.merchant_id, "pro")
    _, vid = item(client, seller, stock=20)
    first = order(client, seller, vid).json()
    _dispatch()
    a = client.get(f"{API}/intelligence/cod/assessments/{first['id']}", headers=seller.h()).json()
    assert a["level"] == "LOW" and a["recommended_action"] == "cod_ok"
    assert [f["code"] for f in a["factors"]] == ["new_customer"] and a["model_version"] == "codi-1.0"
    # The same customer fails delivery twice: the next order is held for a person, with reasons.
    with session_scope() as db:
        db.execute(
            update(Order)
            .where(Order.id == uuid.UUID(first["id"]))
            .values(status="returned")
            .execution_options(skip_tenant_filter=True)
        )
    second = order(client, seller, vid).json()
    with session_scope() as db:
        db.execute(
            update(Order)
            .where(Order.id == uuid.UUID(second["id"]))
            .values(status="delivery_failed")
            .execution_options(skip_tenant_filter=True)
        )
    third = order(client, seller, vid).json()
    _dispatch()
    a3 = client.get(f"{API}/intelligence/cod/assessments/{third['id']}", headers=seller.h()).json()
    assert a3["level"] == "HIGHER" and a3["recommended_action"] == "manual_review"
    hist = next(f for f in a3["factors"] if f["code"] == "delivery_history")
    assert hist["evidence"] == {"delivered": 0, "failed": 2}
    d = client.get(f"{API}/orders/{third['id']}", headers=seller.h()).json()
    assert d["needs_review"] == "cod_risk" and d["status"] == "cod_pending"  # held, not cancelled
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    assert any(e["type"] == "high_risk_cod" and e["resource"]["id"] == third["id"] for e in ex)
    ov = client.post(
        f"{API}/intelligence/cod/assessments/{third['id']}/override",
        headers=seller.h(),
        json={"level": "LOW", "reason": "Called the customer, confirmed"},
    ).json()
    assert ov["level"] == "LOW" and ov["model_level"] == "HIGHER" and ov["overridden"] is True
    assert client.get(f"{API}/orders/{third['id']}", headers=seller.h()).json()["needs_review"] is None
    dp = client.post(
        f"{API}/intelligence/cod/assessments/{third['id']}/dispute",
        headers=seller.h(),
        json={"note": "Customer says the earlier parcel never arrived"},
    ).json()
    assert dp["disputed"] is True
    for to in ("ready_to_ship", "shipped", "delivered"):
        client.post(f"{API}/orders/{third['id']}/transition", headers=seller.h(), json={"to": to})
    _dispatch()
    with session_scope() as db:
        assert (
            db.scalar(
                select(CODRiskAssessment.outcome)
                .where(CODRiskAssessment.order_id == uuid.UUID(third["id"]))
                .execution_options(skip_tenant_filter=True)
            )
            == "delivered"
        )
    cal = client.get(f"{API}/intelligence/cod/calibration", headers=seller.h()).json()
    assert cal["by_level"]["LOW"]["delivered"] == 1 and cal["override_rate"] == round(1 / 3, 3)
    assert cal["by_province"][0]["province"] == "bagmati"
    from app.domains.audit.models import AuditLog

    with session_scope() as db:
        acts = {x.action for x in db.scalars(select(AuditLog).execution_options(skip_tenant_filter=True))}
    assert {"intelligence.cod_override", "intelligence.cod_dispute"} <= acts


def test_cod_model_reads_no_personal_attributes():
    src = inspect.getsource(cod_risk)
    for field in (
        "ship_name",
        "display_name",
        "full_name",
        "recipient_name",
        "gender",
        "religion",
        "caste",
        "ethnicity",
    ):
        assert f".{field}" not in src and f'"{field}"' not in src, field
    assert {
        "delivery_history",
        "new_customer",
        "return_history",
        "address_completeness",
        "order_value",
        "route_failures",
    } == cod_risk.ALLOWED_FACTORS


def test_cod_risk_needs_the_plan(client, seller):
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    _dispatch()
    with session_scope() as db:
        assert db.scalar(select(CODRiskAssessment).execution_options(skip_tenant_filter=True)) is None
    assert client.get(f"{API}/intelligence/cod/assessments/{o['id']}", headers=seller.h()).status_code == 403


# ----------------------------------------------------------------------------- Recommendations
def test_autopilot_recommendation_is_r3_accepted_by_a_manager_and_measured(client, seller):
    set_plan(seller.merchant_id, "growth")
    logs(seller.merchant_id, "customer_messaging", "user", 15)
    r = client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h()).json()
    assert r["created"] == 1
    assert (
        client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h()).json()["created"] == 0
    )  # deduped
    rec = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"][0]
    assert rec["type"] == "autopilot_improvement" and rec["action"] == {
        "type": "set_mode",
        "params": {"mode": "smart"},
    }
    assert rec["evidence"][0]["manual_or_failed"] == 15 and rec["estimated_impact"] == {
        "capability": "customer_replies",
        "score_from": 0.0,
        "score_to": 1.0,
    }
    staff = register_and_login(client, "staff-rec@example.com")
    from app.domains.merchants.models import Membership

    me = client.get(f"{API}/me", headers=staff.h()).json()
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        db.add(
            Membership(
                merchant_id=uuid.UUID(seller.merchant_id), user_id=uuid.UUID(me["user"]["id"]), role="staff"
            )
        )
    assert (
        client.post(
            f"{API}/intelligence/recommendations/{rec['id']}/accept",
            headers=staff.h(merchant=seller.merchant_id),
        ).status_code
        == 403
    )
    done = client.post(f"{API}/intelligence/recommendations/{rec['id']}/accept", headers=seller.h()).json()
    assert done["status"] == "executed"
    assert client.get(f"{API}/merchant", headers=seller.h()).json()["automation_mode"] == "smart"
    again = client.post(f"{API}/intelligence/recommendations/{rec['id']}/accept", headers=seller.h()).json()
    assert again["status"] == "executed"  # idempotent
    with session_scope() as db:
        from app.domains.automation.models import DecisionRecord

        d = db.scalar(
            select(DecisionRecord)
            .where(DecisionRecord.source == "recommendation")
            .execution_options(skip_tenant_filter=True)
        )
        assert d is not None and d.risk_class == "R3" and d.outcome == "approved"
        db.execute(
            update(Recommendation)
            .values(resolved_at=utcnow() - timedelta(days=15))
            .execution_options(skip_tenant_filter=True)
        )
    from app.domains.intelligence.recommendations import measure

    with session_scope() as db:
        assert measure(db)["measured"] == 1
    out = client.get(
        f"{API}/intelligence/recommendations", params={"status": "executed"}, headers=seller.h()
    ).json()["items"][0]["outcome"]
    assert out["method"] == "pre_post" and out["before"] == 0.0


def test_rejected_recommendations_dont_come_back_and_restock_uses_real_sales(client, seller):
    _p, vid = item(client, seller, stock=3)
    client.put(f"{API}/inventory/variants/{vid}/threshold", headers=seller.h(), json={"threshold": 5})
    order(client, seller, vid, qty=2)
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    rec = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    restock = next(r for r in rec if r["type"] == "restock")
    assert (
        restock["explanation"]["vars"]["sold_30d"] == 2 and restock["explanation"]["vars"]["available"] == 1
    )
    assert restock["explanation"]["vars"]["cover_days"] == 15.0
    client.post(
        f"{API}/intelligence/recommendations/{restock['id']}/reject",
        headers=seller.h(),
        json={"reason": "Supplier closed for Tihar"},
    )
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    assert not any(
        r["type"] == "restock"
        for r in client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
    )


def test_courier_selection_recommendation_switches_to_smart(client, seller):
    set_plan(seller.merchant_id, "pro")
    a = courier(client, seller, "Courier A", default=True)
    b = courier(client, seller, "Courier B")
    client.patch(f"{API}/fulfillment/settings", headers=seller.h(), json={"courier_selection": "rules"})
    seed_parcels(seller.merchant_id, a["id"], 22, 15)
    seed_parcels(seller.merchant_id, b["id"], 22, 21)
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        courier_brain.recompute(db, uuid.UUID(seller.merchant_id))
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    rec = next(
        r
        for r in client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
        if r["type"] == "courier_selection"
    )
    assert (
        rec["explanation"]["vars"]["destination"] == "kaski"
        and rec["estimated_impact"]["success_gain_points"] == 27
    )
    client.post(f"{API}/intelligence/recommendations/{rec['id']}/accept", headers=seller.h())
    assert (
        client.get(f"{API}/fulfillment/settings", headers=seller.h()).json()["courier_selection"] == "smart"
    )


def test_recommendations_are_tenant_isolated(client, seller):
    set_plan(seller.merchant_id, "growth")
    logs(seller.merchant_id, "customer_messaging", "user", 15)
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    rec = client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"][0]
    other = onboard(client, shop="Other Intel")
    assert client.get(f"{API}/intelligence/recommendations", headers=other.h()).json()["items"] == []
    assert (
        client.post(f"{API}/intelligence/recommendations/{rec['id']}/accept", headers=other.h()).status_code
        == 404
    )
