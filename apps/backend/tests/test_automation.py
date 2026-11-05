"""Phase 5 (AUT-001…019, UX-016): Decision Policy matrix, workflows (versions, triggers, conditions,
waits, branches, approvals, retries, circuit breaker, dry-run), decision records, action log and the
Control Center."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.core.context import Actor, TenantContext
from app.core.db import session_scope, utcnow
from app.domains.automation import engine, policy
from app.domains.automation.models import AutomationActionLog, DecisionRecord, WorkflowRun
from app.domains.integrations.base import IntegrationError
from app.domains.integrations.sandbox import SandboxChannelAdapter, SandboxCourierAdapter
from app.domains.platform.models import OutboxEvent
from tests.conftest import onboard, set_plan
from tests.test_channels import _dispatch
from tests.test_fulfillment import book, courier_event, sandbox_courier
from tests.test_inbox import Chat, kurta
from tests.test_orders import item, move, order

API = "/api/v1"


def mode(client, s, m):
    r = client.patch(f"{API}/merchant", headers=s.h(), json={"automation_mode": m})
    assert r.status_code == 200, r.text


def from_template(client, s, code, name="Flow", activate=True):
    r = client.post(f"{API}/automation/workflows", headers=s.h(), json={"name": name, "template_code": code})
    assert r.status_code == 201, r.text
    w = r.json()
    if activate:
        w = client.post(
            f"{API}/automation/workflows/{w['id']}/status", headers=s.h(), json={"status": "active"}
        ).json()
    return w


def runs(client, s, wid):
    return client.get(f"{API}/automation/workflows/{wid}/runs", headers=s.h()).json()["items"]


def flush():
    _dispatch()
    _dispatch()


# ----------------------------------------------------------------------------- Decision Policy (AUT-016/017)
@pytest.mark.parametrize(
    ("m", "risk", "conf", "action", "expected", "rule"),
    [
        ("assisted", "R0", 1.0, "notify_seller", "AUTO_EXECUTE", "informational"),
        ("assisted", "R1", 1.0, "send_customer_message", "REQUIRE_APPROVAL", "assisted_mode"),
        ("smart", "R1", 0.9, "send_customer_message", "AUTO_EXECUTE", "smart_r1"),
        ("smart", "R1", 0.7, "send_customer_message", "REQUIRE_APPROVAL", "below_confidence_threshold"),
        ("smart", "R2", 1.0, "send_review_request", "REQUIRE_APPROVAL", "r2_not_enabled"),
        ("smart", "R2", 1.0, "request_reattempt", "AUTO_EXECUTE", "smart_r2_enabled"),
        ("smart", "R1", 0.4, "send_customer_message", "REQUIRE_APPROVAL", "low_confidence"),
        ("smart", "R3", 1.0, "issue_refund", "REQUIRE_APPROVAL", "high_risk"),
        ("smart", "R4", 1.0, "anything", "BLOCK", "prohibited"),
    ],
)
def test_decision_matrix(client, seller, m, risk, conf, action, expected, rule):
    set_plan(seller.merchant_id, "pro")  # autopilot needs it; harmless for the others
    mode(client, seller, m)
    with session_scope() as db:
        rec = policy.decide(
            db,
            uuid.UUID(seller.merchant_id),
            policy.Proposal(action=action, risk_class=risk, source="test", confidence=conf),
        )
        assert (rec.decision, rec.rule) == (expected, rule)


def test_thresholds_entitlement_and_capability_gate_automation(client, seller):
    mode(client, seller, "smart")
    mid = uuid.UUID(seller.merchant_id)
    with session_scope() as db:
        p = policy.Proposal(
            action="approve_return",
            risk_class="R2",
            source="test",
            enabled=True,
            threshold_key="return_approve_minor",
            impact_minor=200000,
        )
        rec = policy.decide(db, mid, p)
        assert (rec.decision, rec.rule, rec.risk_class) == ("REQUIRE_APPROVAL", "above_threshold", "R3")
        p.impact_minor = 100000
        assert policy.decide(db, mid, p).decision == "AUTO_EXECUTE"
        p.entitled = False
        assert policy.decide(db, mid, p).rule == "missing_entitlement"
        p.entitled, p.capable = True, False
        assert policy.decide(db, mid, p).rule == "missing_capability"
    # Autopilot: R1 auto even at moderate confidence, R2 still needs the opt-in.
    set_plan(seller.merchant_id, "pro")
    mode(client, seller, "autopilot")
    with session_scope() as db:
        assert (
            policy.decide(
                db, mid, policy.Proposal(action="x", risk_class="R1", source="t", confidence=0.6)
            ).decision
            == "AUTO_EXECUTE"
        )
        assert (
            policy.decide(
                db, mid, policy.Proposal(action="send_review_request", risk_class="R2", source="t")
            ).rule
            == "r2_not_enabled"
        )


def test_loosening_limits_needs_automation_approve_and_is_audited(client, seller):
    pol = client.get(f"{API}/automation/policy", headers=seller.h()).json()
    assert pol["thresholds"]["refund_minor"] == 0 and pol["enabled_r2"] == ["request_reattempt"]
    r = client.patch(
        f"{API}/automation/policy",
        headers=seller.h(),
        json={
            "thresholds": {"return_approve_minor": 300000},
            "enabled_r2": ["request_reattempt", "send_review_request"],
        },
    )
    assert r.status_code == 200 and r.json()["thresholds"]["return_approve_minor"] == 300000
    bad = client.patch(f"{API}/automation/policy", headers=seller.h(), json={"thresholds": {"made_up": 1}})
    assert bad.json()["error"]["code"] == "threshold_invalid"
    with session_scope() as db:
        ctx = TenantContext(
            merchant_id=uuid.UUID(seller.merchant_id),
            actor=Actor(type="user"),
            permissions=frozenset({"automation.write"}),
        )
        policy.update_settings(
            db, ctx, thresholds={"discount_pct": 5}, enabled_r2=None, confidence_threshold=None
        )  # tighter: fine
        with pytest.raises(Exception) as e:
            policy.update_settings(
                db, ctx, thresholds={"discount_pct": 50}, enabled_r2=None, confidence_threshold=None
            )
        assert getattr(e.value, "code", "") == "permission_denied"
    from app.domains.audit.models import AuditLog

    with session_scope() as db:
        acts = [a.action for a in db.scalars(select(AuditLog).execution_options(skip_tenant_filter=True))]
    assert "automation.policy_loosened" in acts


# ----------------------------------------------------------------------------- workflows
def test_workflows_need_the_plan_and_valid_definitions(client, seller):
    r = client.post(
        f"{API}/automation/workflows",
        headers=seller.h(),
        json={"name": "Flow", "template_code": "low_stock_alert"},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_not_in_plan"
    set_plan(seller.merchant_id, "growth")
    cat = client.get(f"{API}/automation/catalog", headers=seller.h()).json()
    assert {t["code"] for t in cat["triggers"]} >= {
        "order.created",
        "shipment.status_changed",
        "return.status_changed",
    }
    assert len(cat["templates"]) == 6
    bad = [
        (
            {
                "trigger": {"event": "nope"},
                "steps": [{"id": "a", "type": "action", "action": "notify_seller"}],
            },
            "unknown_trigger",
        ),
        (
            {
                "trigger": {"event": "order.created"},
                "steps": [
                    {
                        "id": "a",
                        "type": "condition",
                        "when": {"field": "order.secret", "op": "eq", "value": 1},
                    }
                ],
            },
            "unknown_field",
        ),
        (
            {
                "trigger": {"event": "order.created"},
                "steps": [{"id": "a", "type": "action", "action": "request_reattempt"}],
            },
            "action_subject",
        ),
        (
            {
                "trigger": {"event": "order.created"},
                "steps": [
                    {"id": "a", "type": "action", "action": "notify_seller"},
                    {
                        "id": "b",
                        "type": "branch",
                        "when": {"field": "order.total_minor", "op": "gt", "value": 1},
                        "then": "a",
                    },
                ],
            },
            "target",
        ),
        (
            {
                "trigger": {"event": "order.created"},
                "steps": [
                    {
                        "id": "a",
                        "type": "condition",
                        "when": {"field": "order.total_minor", "op": "gt", "value": "big"},
                    }
                ],
            },
            "value_type",
        ),
    ]
    for definition, reason in bad:
        r = client.post(
            f"{API}/automation/workflows", headers=seller.h(), json={"name": "Bad", "definition": definition}
        )
        assert r.status_code == 400, (reason, r.text)
        assert r.json()["error"]["details"]["reason"] in (reason, "backward_jump"), (reason, r.json())


def test_book_courier_when_packed_runs_automatically_in_smart_mode(client, seller):
    set_plan(seller.merchant_id, "growth")
    mode(client, seller, "smart")
    sandbox_courier(client, seller)
    w = from_template(client, seller, "book_courier_when_packed")
    assert w["status"] == "active" and w["version"] == 1
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    assert move(client, seller, o["id"], "ready_to_ship").status_code == 200
    flush()
    s = client.get(f"{API}/orders/{o['id']}/shipments", headers=seller.h()).json()["items"]
    assert len(s) == 1 and s[0]["status"] == "pickup_requested"
    run = runs(client, seller, w["id"])[0]
    assert run["status"] == "completed"
    steps = {x["step_id"]: x for x in run["steps"]}
    assert steps["complete"]["output"] == {"result": True}
    assert (
        steps["book"]["decision"]["decision"] == "AUTO_EXECUTE"
        and steps["book"]["decision"]["rule"] == "smart_r1"
    )
    assert steps["book"]["decision"]["impact"]["amount_minor"] == 10000  # courier charge recorded
    with session_scope() as db:
        logs = {
            (x.action, x.performed_by)
            for x in db.scalars(select(AutomationActionLog).execution_options(skip_tenant_filter=True))
        }
    assert ("book_courier", "automation") in logs and ("create_order", "user") in logs
    # Redelivered event: no second run.
    with session_scope() as db:
        ev = db.scalar(
            select(OutboxEvent)
            .where(OutboxEvent.event_type == "orders.status_changed")
            .order_by(OutboxEvent.id.desc())
        )
        assert ev is not None
        engine.start_runs(db, ev)
    assert len(runs(client, seller, w["id"])) == 1


def test_assisted_mode_waits_for_approval_and_rereads_facts(client, seller):
    set_plan(seller.merchant_id, "growth")
    sandbox_courier(client, seller)
    from_template(client, seller, "book_courier_when_packed")
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    move(client, seller, o["id"], "ready_to_ship")
    flush()
    ap = client.get(f"{API}/automation/approvals", headers=seller.h()).json()["items"]
    assert len(ap) == 1 and ap[0]["action"] == "book_courier" and ap[0]["order_number"] == o["number"]
    assert ap[0]["decision"]["rule"] == "assisted_mode"
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    assert any(e["type"] == "automation_approval" for e in ex)
    run = client.post(f"{API}/automation/approvals/{ap[0]['id']}/approve", headers=seller.h(), json={}).json()
    # Pickup is another R1 step: it asks again (assisted), the booking itself happened.
    assert {x["step_id"]: x["status"] for x in run["steps"]}["book"] == "done"
    assert (
        client.get(f"{API}/orders/{o['id']}/shipments", headers=seller.h()).json()["items"][0]["status"]
        == "booked"
    )
    ap2 = client.get(f"{API}/automation/approvals", headers=seller.h()).json()["items"]
    rej = client.post(
        f"{API}/automation/approvals/{ap2[0]['id']}/reject",
        headers=seller.h(),
        json={"note": "I'll call them first"},
    ).json()
    assert rej["status"] == "completed" and rej["error"] == "rejected"
    again = client.post(f"{API}/automation/approvals/{ap2[0]['id']}/approve", headers=seller.h(), json={})
    assert again.status_code == 409
    # A second order that the seller books by hand before approving: the approval no longer applies.
    o2 = order(client, seller, vid).json()
    move(client, seller, o2["id"], "ready_to_ship")
    flush()
    ap3 = client.get(f"{API}/automation/approvals", headers=seller.h()).json()["items"][0]
    book(client, seller, o2["id"], client.get(f"{API}/couriers", headers=seller.h()).json()["items"][0]["id"])
    r = client.post(f"{API}/automation/approvals/{ap3['id']}/approve", headers=seller.h(), json={}).json()
    assert r["status"] == "failed" and r["error"] == "automation_no_longer_applicable"
    assert len(client.get(f"{API}/orders/{o2['id']}/shipments", headers=seller.h()).json()["items"]) == 1


def test_failed_delivery_followup_waits_then_branches(client, seller):
    set_plan(seller.merchant_id, "growth")
    mode(client, seller, "smart")
    a = sandbox_courier(client, seller)
    w = from_template(client, seller, "failed_delivery_followup")
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    s = book(client, seller, o["id"], a["id"]).json()
    courier_event(client, seller, a["id"], s["tracking_number"], "picked_up")
    courier_event(
        client,
        seller,
        a["id"],
        s["tracking_number"],
        "delivery_failed",
        failure_reason="customer_unavailable",
    )
    flush()
    run = runs(client, seller, w["id"])[0]
    assert run["status"] == "waiting" and run["current_step"] == "wait"
    with session_scope() as db:
        db.execute(
            update(WorkflowRun)
            .values(next_run_at=utcnow() - timedelta(minutes=1))
            .execution_options(skip_tenant_filter=True)
        )
    with session_scope() as db:
        assert engine.resume_due(db) == 1
    run = runs(client, seller, w["id"])[0]
    assert run["status"] == "completed"
    status = {x["step_id"]: x["status"] for x in run["steps"]}
    assert status == {
        "wait": "done",
        "still_failed": "done",
        "few": "done",
        "retry": "done",
    }  # "tell" skipped via next=stop
    assert SandboxCourierAdapter.requests[-1][0] == "reattempt"
    assert (
        client.get(f"{API}/shipments/{s['id']}", headers=seller.h()).json()["status"] == "reattempt_requested"
    )


def test_review_request_is_r2_and_needs_the_opt_in(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, mode="smart")  # growth plan
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
    definition = {
        "trigger": {"event": "order.status_changed", "filter": ["delivered"]},
        "steps": [{"id": "ask", "type": "action", "action": "send_review_request"}],
    }
    w = client.post(
        f"{API}/automation/workflows", headers=seller.h(), json={"name": "Reviews", "definition": definition}
    ).json()
    client.post(f"{API}/automation/workflows/{w['id']}/status", headers=seller.h(), json={"status": "active"})
    for to in ("ready_to_ship", "shipped", "delivered"):
        move(client, seller, oid, to)
    flush()
    assert runs(client, seller, w["id"])[0]["status"] == "awaiting_approval"  # R2 not enabled
    client.patch(
        f"{API}/automation/policy",
        headers=seller.h(),
        json={"enabled_r2": ["request_reattempt", "send_review_request"]},
    )
    ap = client.get(f"{API}/automation/approvals", headers=seller.h()).json()["items"][0]
    client.post(f"{API}/automation/approvals/{ap['id']}/approve", headers=seller.h(), json={})
    flush()
    last = [m["text"] for m in SandboxChannelAdapter.sent if m["thread"] == chat.thread][-1]
    assert "We hope you love your order #1001" in last
    # Next delivered order: now automatic.
    w2 = client.post(
        f"{API}/automation/workflows",
        headers=seller.h(),
        json={"name": "Reviews 2", "definition": definition},
    ).json()
    with session_scope() as db:
        mid = uuid.UUID(seller.merchant_id)
        rec = policy.decide(
            db, mid, policy.Proposal(action="send_review_request", risk_class="R2", source="t")
        )
        assert rec.decision == "AUTO_EXECUTE"
    assert w2["status"] == "draft"  # created workflows start off; turning on needs automation.approve


def test_retries_then_circuit_breaker_pauses_and_raises_an_exception(client, seller, monkeypatch):
    monkeypatch.setattr(engine, "MAX_ATTEMPTS", 2)
    monkeypatch.setattr(engine, "BREAKER_FAILURES", 2)
    set_plan(seller.merchant_id, "growth")
    mode(client, seller, "smart")
    a = sandbox_courier(client, seller)
    definition = {
        "trigger": {"event": "order.status_changed", "filter": ["ready_to_ship"]},
        "steps": [{"id": "pickup", "type": "action", "action": "request_pickup"}],
    }
    w = client.post(
        f"{API}/automation/workflows", headers=seller.h(), json={"name": "Pickups", "definition": definition}
    ).json()
    client.post(f"{API}/automation/workflows/{w['id']}/status", headers=seller.h(), json={"status": "active"})
    _, vid = item(client, seller, stock=10)
    for _ in range(2):
        o = order(client, seller, vid).json()
        book(client, seller, o["id"], a["id"])  # booking moves it to ready_to_ship → trigger
        SandboxCourierAdapter.failures.push(IntegrationError("timeout", "slow", retryable=True), times=5)
        flush()
        with session_scope() as db:
            db.execute(
                update(WorkflowRun)
                .where(WorkflowRun.status == "waiting")
                .values(next_run_at=utcnow())
                .execution_options(skip_tenant_filter=True)
            )
        with session_scope() as db:
            engine.resume_due(db)
        SandboxCourierAdapter.failures.clear()
    rs = runs(client, seller, w["id"])
    assert [r["status"] for r in rs] == ["failed", "failed"]
    assert rs[0]["steps"][0]["attempts"] == 2 and rs[0]["error"] == "courier_unavailable"
    wf = client.get(f"{API}/automation/workflows/{w['id']}", headers=seller.h()).json()
    assert wf["status"] == "paused" and wf["paused_reason"] == "circuit_breaker:request_pickup"
    ex = client.get(f"{API}/exceptions", headers=seller.h()).json()["items"]
    assert any(e["type"] == "automation_paused" and e["severity"] == "urgent" for e in ex)


def test_dry_run_explains_without_doing_anything(client, seller):
    set_plan(seller.merchant_id, "growth")
    sandbox_courier(client, seller)
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    from app.domains.automation.templates import BY_CODE

    with session_scope() as db:
        before = db.scalar(
            select(func.count()).select_from(DecisionRecord).execution_options(skip_tenant_filter=True)
        )
    r = client.post(
        f"{API}/automation/dry-run",
        headers=seller.h(),
        json={"definition": BY_CODE["book_courier_when_packed"]["definition"], "subject_id": o["id"]},
    ).json()
    assert r["trace"][0] == {
        "step": "trigger",
        "result": False,
        "note": "trigger_filter_not_met",
    }  # it's cod_pending, not packed
    by = {t["step"]: t for t in r["trace"][1:]}
    assert (
        by["complete"]["result"] is True
        and by["book"]["decision"] == "REQUIRE_APPROVAL"
        and by["book"]["rule"] == "assisted_mode"
    )
    assert (
        r["facts"]["order.total_minor"] == o["totals"]["total"]["amount_minor"] and "_order" not in r["facts"]
    )
    with session_scope() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(DecisionRecord).execution_options(skip_tenant_filter=True)
            )
            == before
        )
    assert client.get(f"{API}/orders/{o['id']}/shipments", headers=seller.h()).json()["items"] == []


def test_editing_creates_a_version_and_runs_keep_theirs(client, seller):
    set_plan(seller.merchant_id, "growth")
    mode(client, seller, "smart")
    a = sandbox_courier(client, seller)
    w = from_template(client, seller, "failed_delivery_followup")
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    s = book(client, seller, o["id"], a["id"]).json()
    courier_event(client, seller, a["id"], s["tracking_number"], "picked_up")
    courier_event(client, seller, a["id"], s["tracking_number"], "delivery_failed", failure_reason="other")
    flush()
    new_def = {
        "trigger": {"event": "shipment.status_changed", "filter": ["delivery_failed"]},
        "steps": [{"id": "tell", "type": "action", "action": "notify_seller"}],
    }
    w2 = client.patch(
        f"{API}/automation/workflows/{w['id']}", headers=seller.h(), json={"definition": new_def}
    ).json()
    assert w2["version"] == 2 and w2["definition"]["steps"][0]["id"] == "tell"
    with session_scope() as db:
        db.execute(
            update(WorkflowRun).values(next_run_at=utcnow()).execution_options(skip_tenant_filter=True)
        )
    with session_scope() as db:
        engine.resume_due(db)
    run = runs(client, seller, w["id"])[0]
    assert run["status"] == "completed" and "retry" in {
        x["step_id"] for x in run["steps"]
    }  # still v1's steps


# ----------------------------------------------------------------------------- existing automation through the policy
def test_sales_agent_auto_send_is_a_recorded_decision(client, seller):
    kurta(client, seller)
    chat = Chat(client, seller, mode="smart")
    chat.say("Dhaka kurta XL cha? kati ho?")
    ai = next(m for m in chat.messages() if m["author_type"] == "ai")
    assert ai["status"] == "sent" and ai["grounding"]["decision_rule"] == "smart_r1"
    with session_scope() as db:
        rec = db.get(DecisionRecord, uuid.UUID(ai["grounding"]["decision_id"]))
        assert rec is not None and rec.source == "inbox" and rec.outcome == "executed"
        logs = db.scalars(
            select(AutomationActionLog)
            .where(AutomationActionLog.capability == "customer_messaging")
            .execution_options(skip_tenant_filter=True)
        ).all()
        assert [x.performed_by for x in logs] == ["ai"]


# ----------------------------------------------------------------------------- Control Center (UX-016)
def test_control_center_shows_real_numbers_and_the_autopilot_feed(client, seller):
    set_plan(seller.merchant_id, "growth")
    mode(client, seller, "smart")
    a = sandbox_courier(client, seller)
    from_template(client, seller, "book_courier_when_packed")
    _, vid = item(client, seller, stock=5)
    o1 = order(client, seller, vid).json()
    move(client, seller, o1["id"], "ready_to_ship")
    flush()
    s = client.get(f"{API}/orders/{o1['id']}/shipments", headers=seller.h()).json()["items"][0]
    courier_event(client, seller, a["id"], s["tracking_number"], "picked_up")
    courier_event(client, seller, a["id"], s["tracking_number"], "delivered")
    order(client, seller, vid)
    cc = client.get(f"{API}/control-center", headers=seller.h()).json()
    assert cc["metrics"]["orders"] == 2 and cc["metrics"]["delivered"] == 1
    assert cc["metrics"]["revenue_minor"] == 2 * o1["totals"]["total"]["amount_minor"]
    assert cc["automation"]["done_automatically"] >= 2 and cc["automation"]["done_by_team"] >= 3
    assert 0 < cc["automation"]["share_automatic"] < 1
    assert any(f["action"] == "book_courier" and f["rule"] == "smart_r1" for f in cc["feed"])
    assert cc["state"] in ("running", "waiting", "attention") and cc["mode"] == "smart"


def test_workflows_are_tenant_isolated(client, seller):
    set_plan(seller.merchant_id, "growth")
    w = from_template(client, seller, "low_stock_alert", activate=False)
    other = onboard(client, shop="Other Flows")
    assert client.get(f"{API}/automation/workflows/{w['id']}", headers=other.h()).status_code == 404
    assert client.get(f"{API}/automation/workflows", headers=other.h()).json()["items"] == []
    assert (
        client.post(
            f"{API}/automation/workflows/{w['id']}/status", headers=other.h(), json={"status": "active"}
        ).status_code
        == 404
    )
