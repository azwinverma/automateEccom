"""Operations: /metrics carries database-backed operational gauges (spec 16) and job health."""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core.db import session_scope, utcnow
from app.domains.platform import ops
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import publish


def _metric(text: str, name: str) -> float | None:
    for line in text.splitlines():
        if line.startswith(name + " ") or line.startswith(name + "{"):
            return float(line.rsplit(" ", 1)[1])
    return None


def test_metrics_report_outbox_backlog_and_dead_letters_from_the_database(client, seller):
    with session_scope() as db:
        ev = publish(
            db,
            event_type="platform.ping",
            aggregate_type="t",
            aggregate_id="x",
            payload={"note": "ops-test"},
            merchant_id=None,
        )
        dead = publish(
            db,
            event_type="platform.ping",
            aggregate_type="t",
            aggregate_id="y",
            payload={"note": "ops-test"},
            merchant_id=None,
        )
        db.flush()
        db.execute(update(OutboxEvent).where(OutboxEvent.id == dead.id).values(status="dead"))
        db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == ev.id)
            .values(created_at=utcnow() - timedelta(minutes=10))
        )
    ops.collect(force=True)
    text = client.get("/metrics").text
    assert _metric(text, "outbox_dead_events") >= 1
    assert _metric(text, "outbox_pending_events") >= 1
    assert _metric(text, "outbox_oldest_pending_seconds") >= 590  # alert: oldest pending > 5 min
    for name in (
        "webhook_events_unprocessed",
        "refunds_failed",
        "cod_settlement_overdue",
        "shipments_stuck",
        "product_brain_max_age_seconds",
        "data_quality_variants_without_cost_ratio",
        "recommendations_open",
        'celery_queue_backlog{queue="outbox"}',
    ):
        assert name.split("{")[0] in text, name


def test_one_failing_gauge_never_breaks_the_scrape(client, monkeypatch):
    real = ops._gauges

    def broken() -> list:
        items = real()

        def boom(db) -> None:
            raise RuntimeError("db hiccup")

        return [("money", boom), *[x for x in items if x[0] != "money"]]

    monkeypatch.setattr(ops, "_gauges", broken)
    ops.collect(force=True)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert 'ops_collect_errors_total{gauge="money"}' in r.text
    assert "outbox_pending_events" in r.text


def test_job_health_counts_outcomes_and_writes_a_heartbeat(client):
    from app.core.redis import get_redis

    name = f"test_job_{uuid.uuid4().hex[:6]}"

    @ops.tracked(name)
    def fine() -> int:
        return 1

    @ops.tracked(name)
    def bad() -> None:
        raise ValueError("nope")

    assert fine() == 1
    with pytest.raises(ValueError):
        bad()
    beat = float(get_redis().get(f"ops:job:{name}:last_success"))
    assert abs(beat - time.time()) < 30
    from prometheus_client import generate_latest

    text = generate_latest().decode()
    assert f'job_runs_total{{job="{name}",outcome="success"}} 1.0' in text
    assert f'job_runs_total{{job="{name}",outcome="failure"}} 1.0' in text


def test_ops_cli_replays_dead_events_with_dry_run_and_audit(client, seller, capsys):
    import argparse
    import json

    from sqlalchemy import select

    from app.cli_ops import run_ops
    from app.domains.audit.models import AuditLog

    with session_scope() as db:
        ev = publish(
            db,
            event_type="platform.ping",
            aggregate_type="t",
            aggregate_id="z",
            payload={"note": "x"},
            merchant_id=None,
        )
        db.flush()
        db.execute(update(OutboxEvent).where(OutboxEvent.id == ev.id).values(status="dead"))
        eid = ev.id
    ns = argparse.Namespace(
        cmd="outbox-replay", status="dead", event_type="platform.ping", since=None, limit=50, dry_run=True
    )
    run_ops(ns)
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["dry_run"] is True and out["count"] >= 1
    with session_scope() as db:
        assert db.get(OutboxEvent, eid).status == "dead"  # dry run changed nothing
    ns.dry_run = False
    run_ops(ns)
    capsys.readouterr()
    with session_scope() as db:
        assert db.get(OutboxEvent, eid).status in ("pending", "dispatched")
        acts = list(db.scalars(select(AuditLog.action).execution_options(skip_tenant_filter=True)))
    assert "ops.outbox_replayed" in acts
    run_ops(argparse.Namespace(cmd="ops-status"))
    status = json.loads(capsys.readouterr().out)
    assert "outbox_dead_events" in status and "outbox_pending_events" in status


def test_ops_cli_recomputes_one_merchant(client, seller, capsys):
    import argparse
    import json

    slug = client.get("/api/v1/merchant", headers=seller.h()).json()["slug"]
    from app.cli_ops import run_ops

    run_ops(argparse.Namespace(cmd="twin-reconcile", merchant=slug))
    out = json.loads(capsys.readouterr().out)
    assert out["part"] == "twin" and out["merchants"] == 1
    assert next(iter(out["results"].values()))["twin"] == 10
    with pytest.raises(SystemExit):
        run_ops(argparse.Namespace(cmd="recompute-intelligence", merchant="no-such-shop", part="all"))


def _kill(key: str, on: bool = True) -> None:
    from app.domains.platform.models import FeatureFlag

    with session_scope() as db:
        f = db.get(FeatureFlag, key)
        if f is None:
            f = FeatureFlag(key=key, description="ops test")
            db.add(f)
        f.kill_switch = on


def test_kill_switches_stop_agent_replies_and_publishing_until_cleared(client, seller):
    from tests.test_content import _post, _tick
    from tests.test_inbox import Chat, kurta

    kurta(client, seller)
    chat = Chat(client, seller)
    _kill("ops.sales_agent_replies")
    assert chat.say("Dhaka kurta XL cha?") is None  # stays in the inbox for the seller
    _kill("ops.sales_agent_replies", on=False)
    assert "Rs 2,450" in (chat.say("Dhaka kurta XL cha?") or "")
    p = _post(client, seller, chat.conn["id"])
    client.post(f"/api/v1/content/posts/{p['id']}/submit", headers=seller.h())
    client.post(f"/api/v1/content/posts/{p['id']}/schedule", headers=seller.h(), json={})
    _kill("ops.content_publishing")
    assert _tick()["published"] == 0
    assert client.get(f"/api/v1/content/posts/{p['id']}", headers=seller.h()).json()["status"] == "scheduled"
    _kill("ops.content_publishing", on=False)
    assert _tick()["published"] == 1


def test_merchant_override_kills_for_one_shop_only(client, seller):
    from app.domains.platform.flags import killed
    from app.domains.platform.models import FeatureFlag, FeatureFlagOverride

    mid = uuid.UUID(seller.merchant_id)
    with session_scope() as db:
        db.add(FeatureFlag(key="ops.automation", description="ops"))
        db.flush()
        db.add(FeatureFlagOverride(flag_key="ops.automation", merchant_id=mid, enabled=False))
    with session_scope() as db:
        assert killed(db, "ops.automation", mid) is True
        assert killed(db, "ops.automation", uuid.uuid4()) is False
        assert killed(db, "ops.not_a_flag") is False


def test_seed_demo_gives_a_working_sign_in_for_every_role(client, monkeypatch, tmp_path):
    import pyotp

    from app import cli_demo

    monkeypatch.setattr(cli_demo, "SHEET", tmp_path / "demo-users.txt")
    cli_demo.seed_demo()
    out = cli_demo.seed_demo()  # a re-run resets passwords and keeps one membership per person
    expected = {"owner": "billing.manage", "admin": "procurement.approve", "manager": "refunds.approve"}
    for u in out["users"]:
        r = client.post(
            "/api/v1/auth/login", json={"email": u["email"], "password": u["password"], "device_name": "t"}
        )
        assert r.status_code == 200, (u["role"], r.text)
        body = r.json()
        if u["role"] == "platform":
            assert "mfa_token" in body and "access_token" not in body  # two-step verification is on
            r = client.post(
                "/api/v1/auth/mfa/verify",
                json={"mfa_token": body["mfa_token"], "code": pyotp.TOTP(out["platform_totp_secret"]).now()},
            )
            assert r.status_code == 200, r.text
            continue
        h = {"Authorization": f"Bearer {body['access_token']}"}
        mems = client.get("/api/v1/me", headers=h).json()["memberships"]
        demo = [x for x in mems if x["merchant"]["slug"] == "nivaro-demo"]
        assert len(demo) == 1 and demo[0]["role"] == u["role"], (u["role"], mems)
        mid = demo[0]["merchant"]["id"]
        perms = client.get("/api/v1/permissions/me", headers={**h, "X-Merchant-Id": mid}).json()
        role, plist = perms.get("role"), set(perms.get("permissions", []))
        assert role == u["role"]
        if u["role"] in expected:
            assert expected[u["role"]] in plist
        if u["role"] in ("staff", "viewer"):
            assert "refunds.approve" not in plist and "billing.manage" not in plist
    assert cli_demo.demo_code().isdigit()


def test_new_plan_features_reach_existing_shops_only_when_the_price_is_unchanged(client, seller):
    import json as _json

    from sqlalchemy import select

    from app.domains.billing.models import Plan, PlanVersion
    from app.domains.billing.plans import DEFAULT_PATH, move_to_current_versions, seed_from_file
    from app.domains.billing.service import entitlements

    set_plan_mid = uuid.UUID(seller.merchant_id)
    doc = _json.loads(DEFAULT_PATH.read_text())
    starter = next(p for p in doc["plans"] if p["code"] == "starter")
    assert starter["version"]["features"]["marketing.campaigns"] is False
    starter["version"]["features"]["marketing.campaigns"] = True  # a feature added, same price
    path = DEFAULT_PATH.parent / "_test_plans.json"
    path.write_text(_json.dumps(doc))
    try:
        with session_scope() as db:
            seed_from_file(db, path)
        with session_scope() as db:
            assert not entitlements.resolve(db, set_plan_mid).has(
                "marketing.campaigns"
            )  # still on the old version
            dry = move_to_current_versions(db, dry_run=True)
        assert dry["moved"].get("starter", 0) >= 1
        with session_scope() as db:
            move_to_current_versions(db)
        with session_scope() as db:
            assert entitlements.resolve(db, set_plan_mid).has("marketing.campaigns")
            # A price change is never applied silently.
            plan = db.scalar(select(Plan).where(Plan.code == "starter"))
            active = db.scalar(
                select(PlanVersion).where(PlanVersion.plan_id == plan.id, PlanVersion.status == "active")
            )
            active.price_monthly_minor = 99900
    finally:
        path.unlink(missing_ok=True)
        with session_scope() as db:
            seed_from_file(db)  # restore the contract's plans for the other tests
            move_to_current_versions(db)
