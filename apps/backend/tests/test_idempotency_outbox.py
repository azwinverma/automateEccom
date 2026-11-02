from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.core.db import session_scope, utcnow
from app.domains.merchants.models import Merchant
from app.domains.platform import idempotency, outbox
from app.domains.platform.models import OutboxConsumption, OutboxEvent
from tests.conftest import register_and_login

API = "/api/v1"


def test_idempotent_merchant_create_replays_and_detects_body_change(client):
    s = register_and_login(client)
    body = {"name": "Kathmandu Kicks"}
    h = s.h(**{"Idempotency-Key": "onboard-key-0001"})
    r1 = client.post(f"{API}/merchants", headers=h, json=body)
    r2 = client.post(f"{API}/merchants", headers=h, json=body)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"] and r2.headers.get("Idempotent-Replayed") == "true"
    with session_scope() as db:
        assert db.scalar(select(func.count()).select_from(Merchant)) == 1
    r3 = client.post(f"{API}/merchants", headers=h, json={"name": "Different"})
    assert r3.status_code == 422 and r3.json()["error"]["code"] == "idempotency_key_reused"


def test_in_progress_duplicate_conflicts_and_failed_attempt_is_retryable(client):
    claim = idempotency.begin("user:x", "scope.a", "key-in-flight-1", "hash")
    with pytest.raises(Exception) as e:
        idempotency.begin("user:x", "scope.a", "key-in-flight-1", "hash")
    assert getattr(e.value, "code", None) == "idempotency_in_progress"
    idempotency.abandon(claim)
    assert isinstance(idempotency.begin("user:x", "scope.a", "key-in-flight-1", "hash"), idempotency.Claim)


def test_invalid_idempotency_key_rejected(client):
    s = register_and_login(client)
    r = client.post(
        f"{API}/merchants", headers=s.h(**{"Idempotency-Key": "short"}), json={"name": "Shop Name"}
    )
    assert r.status_code == 400


def test_run_once_executes_side_effect_once():
    calls = []
    with session_scope() as db:
        assert idempotency.run_once(db, "provider:x", "webhook", "evt-1", lambda: calls.append(1))[0]
    with session_scope() as db:
        assert not idempotency.run_once(db, "provider:x", "webhook", "evt-1", lambda: calls.append(1))[0]
    assert calls == [1]


def test_outbox_rejects_unknown_events_and_invalid_payloads():
    import jsonschema

    with session_scope() as db:
        with pytest.raises(outbox.UnknownEventType):
            outbox.publish(
                db,
                event_type="orders.nope",
                aggregate_type="x",
                aggregate_id="1",
                payload={},
                merchant_id=None,
            )
        with pytest.raises(jsonschema.ValidationError):
            outbox.publish(
                db,
                event_type="platform.ping",
                aggregate_type="x",
                aggregate_id="1",
                payload={"note": 1},
                merchant_id=None,
            )
        db.rollback()


def test_outbox_dispatch_exactly_once_per_handler_with_retry_and_dlq(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "outbox_max_attempts", 2)
    calls = {"ok": 0, "flaky": 0}

    @outbox.handler("platform.ping", name="test.ok")
    def ok(db, ev):
        calls["ok"] += 1

    @outbox.handler("platform.ping", name="test.flaky")
    def flaky(db, ev):
        calls["flaky"] += 1
        raise RuntimeError("courier API down")

    try:
        with session_scope() as db:
            ev = outbox.publish(
                db,
                event_type="platform.ping",
                aggregate_type="t",
                aggregate_id="1",
                payload={"note": "hi"},
                merchant_id=None,
            )
            ev_id = ev.id
        assert outbox.dispatch_batch()["retried"] == 1
        with session_scope() as db:
            e = db.get(OutboxEvent, ev_id)
            assert e.status == "pending" and e.attempts == 1 and "courier API down" in e.last_error
            db.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id == ev_id)
                .values(available_at=utcnow() - timedelta(seconds=1))
            )
        assert outbox.dispatch_batch()["dead"] == 1
        assert calls["ok"] == 1, "successful handler must not re-run on retry"
        assert calls["flaky"] == 2
        with session_scope() as db:
            assert db.get(OutboxEvent, ev_id).status == "dead"
            assert db.get(OutboxConsumption, (ev_id, "test.ok")) is not None
            outbox.requeue(db, ev_id)
        with session_scope() as db:
            assert db.get(OutboxEvent, ev_id).status == "pending"
    finally:
        outbox._HANDLERS["platform.ping"] = [
            r for r in outbox._HANDLERS["platform.ping"] if not r.name.startswith("test.")
        ]


def test_outbox_event_rolls_back_with_business_transaction():
    with pytest.raises(RuntimeError), session_scope() as db:
        outbox.publish(
            db,
            event_type="platform.ping",
            aggregate_type="t",
            aggregate_id="1",
            payload={"note": "x"},
            merchant_id=None,
        )
        raise RuntimeError("business failure")
    with session_scope() as db:
        assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 0


def test_every_event_in_catalog_has_valid_schema():
    import jsonschema

    for spec in outbox.catalog().values():
        jsonschema.Draft202012Validator.check_schema(spec["payload_schema"])
        assert spec["type"].count(".") == 1
    assert uuid  # keep import
