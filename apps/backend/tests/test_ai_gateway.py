from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.db import session_scope
from app.core.errors import FeatureNotInPlan
from app.domains.ai.circuit import BreakerConfig, CircuitBreaker
from app.domains.ai.gateway import AIGateway, AIUnavailable
from app.domains.ai.models import AIExecution, ProviderCredential
from app.domains.ai.policy import parse_policy
from app.domains.ai.providers.anthropic_adapter import AnthropicAdapter
from app.domains.ai.providers.sandbox import SandboxAdapter
from app.domains.ai.types import AIRequest, Message, ProviderError
from app.domains.billing.service import entitlements
from tests.conftest import set_plan

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"title": {"type": "string"}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
    "required": ["title", "confidence"],
}


def _gw(candidates=None, max_attempts=2, threshold=3, min_conf=0.7) -> AIGateway:
    doc = {
        "tasks": {
            "PRODUCT_DESCRIPTION": {
                "capability": "structured",
                "feature": "ai.text_generation",
                "usage_resource": "ai_text_generations",
                "timeout_s": 5,
                "max_attempts_per_candidate": max_attempts,
                "min_confidence": min_conf,
                "candidates": candidates
                or [
                    {"provider": "sandbox", "model": "primary"},
                    {"provider": "sandbox", "model": "secondary"},
                ],
            }
        },
        "pricing": {"sandbox:primary": {"input_usd_per_mtok": 4, "output_usd_per_mtok": 20}},
    }
    pol = parse_policy(doc)
    return AIGateway(pol, CircuitBreaker(BreakerConfig(threshold, 60, 30)), sleep=lambda s: None)


def _req() -> AIRequest:
    return AIRequest(
        messages=(Message("user", "Red cotton kurta, sizes S-XL"),),
        json_schema=SCHEMA,
        prompt_name="product_description",
        prompt_version=1,
        locale="ne",
    )


def _run(gw, seller, key="job-1"):
    return gw.run(
        task="PRODUCT_DESCRIPTION",
        request=_req(),
        merchant_id=uuid.UUID(seller.merchant_id),
        idempotency_key=key,
    )


def _usage(seller):
    with session_scope() as db:
        return next(
            x
            for x in entitlements.usage_summary(db, uuid.UUID(seller.merchant_id))
            if x["resource"] == "ai_text_generations"
        )


def test_structured_success_records_ledger_and_usage(client, seller):
    SandboxAdapter.override_data["primary"] = {"title": "Red cotton kurta", "confidence": 0.92}
    res = _run(_gw(), seller)
    assert (
        res.provider == "sandbox"
        and res.model == "primary"
        and not res.fallback_used
        and not res.needs_review
    )
    assert res.data["title"] == "Red cotton kurta" and res.cost_usd_micros == 1200  # 50 in + 50 out tokens
    assert _usage(seller)["used"] == 1
    with session_scope() as db:
        rows = db.scalars(select(AIExecution)).all()
        assert (
            len(rows) == 1 and rows[0].status == "succeeded" and rows[0].prompt_name == "product_description"
        )
        assert rows[0].plan_code == "starter"


def test_transient_errors_retry_then_fall_back(client, seller):
    SandboxAdapter.failures.push(ProviderError("provider_unavailable", retryable=True), times=2)
    SandboxAdapter.override_data["secondary"] = {"title": "ok", "confidence": 0.9}
    res = _run(_gw(), seller)
    assert res.model == "secondary" and res.fallback_used and res.attempts == 3
    with session_scope() as db:
        statuses = [
            (r.model, r.status) for r in db.scalars(select(AIExecution).order_by(AIExecution.created_at))
        ]
    assert statuses == [("primary", "failed"), ("primary", "failed"), ("secondary", "succeeded")]


def test_refusal_is_not_retried_and_does_not_trip_circuit(client, seller):
    SandboxAdapter.failures.push(ProviderError("refusal", counts_toward_circuit=False))
    gw = _gw(threshold=1)
    res = _run(gw, seller)
    assert res.model == "secondary" and res.attempts == 2
    assert gw.breaker.state("sandbox", "primary") == "closed"


def test_circuit_opens_and_skips_unhealthy_candidate(client, seller):
    gw = _gw(max_attempts=1, threshold=2)
    SandboxAdapter.override_data["secondary"] = {"title": "ok", "confidence": 0.9}
    for key in ("a", "b"):  # primary fails once per run; secondary serves the request
        SandboxAdapter.failures.push(ProviderError("timeout", retryable=True))
        assert _run(gw, seller, key).model == "secondary"
    assert gw.breaker.state("sandbox", "primary") == "open"
    res = _run(gw, seller, "c")
    assert res.model == "secondary"
    with session_scope() as db:
        skipped = db.scalars(select(AIExecution).where(AIExecution.status == "skipped")).all()
        assert skipped and skipped[0].error_code == "circuit_open"
        from app.domains.platform.models import OutboxEvent

        assert db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "ai.provider_circuit_opened"))


def test_all_providers_fail_releases_usage_and_raises(client, seller):
    SandboxAdapter.failures.push(ProviderError("provider_unavailable", retryable=True), times=10)
    with pytest.raises(AIUnavailable) as e:
        _run(_gw(), seller)
    assert e.value.details["last_error_code"] == "provider_unavailable"
    u = _usage(seller)
    assert u["used"] == 0 and u["reserved"] == 0  # merchant not charged for failure


def test_schema_violation_falls_back(client, seller):
    SandboxAdapter.override_data["primary"] = {"title": 123, "confidence": 0.9}
    SandboxAdapter.override_data["secondary"] = {"title": "valid", "confidence": 0.95}
    res = _run(_gw(), seller)
    assert res.model == "secondary"
    with session_scope() as db:
        assert (
            db.scalar(select(AIExecution.error_code).where(AIExecution.model == "primary"))
            == "schema_validation_failed"
        )


def test_low_confidence_flags_human_review(client, seller):
    SandboxAdapter.override_data["primary"] = {"title": "maybe a kurta?", "confidence": 0.4}
    assert _run(_gw(), seller).needs_review is True


def test_feature_not_in_plan_blocks_before_any_provider_call(client, seller):
    doc = {
        "tasks": {
            "VIDEO_GENERATION": {
                "capability": "video_generation",
                "feature": "video.premium",
                "usage_resource": "premium_video_clips",
                "timeout_s": 5,
                "candidates": [{"provider": "sandbox_media", "model": "v"}],
            }
        }
    }
    gw = AIGateway(parse_policy(doc), sleep=lambda s: None)
    with pytest.raises(FeatureNotInPlan):
        gw.run(
            task="VIDEO_GENERATION",
            request=AIRequest(messages=(), video_spec={"duration_s": 8}),
            merchant_id=uuid.UUID(seller.merchant_id),
            idempotency_key="vid-1",
        )
    with session_scope() as db:
        assert db.scalars(select(AIExecution)).all() == []
    set_plan(seller.merchant_id, "growth")
    res = gw.run(
        task="VIDEO_GENERATION",
        request=AIRequest(messages=(), video_spec={"duration_s": 8}),
        merchant_id=uuid.UUID(seller.merchant_id),
        idempotency_key="vid-2",
    )
    assert res.job_id.startswith("sbx-vid-")


def test_unconfigured_real_providers_are_skipped(client, seller):
    gw = _gw(
        candidates=[
            {"provider": "anthropic", "model": "claude-opus-5-5"},
            {"provider": "sandbox", "model": "secondary"},
        ]
    )
    SandboxAdapter.override_data["secondary"] = {"title": "ok", "confidence": 0.9}
    res = _run(gw, seller)  # no COS_ANTHROPIC_API_KEY in tests
    assert res.model == "secondary"


def test_byok_requires_entitlement_and_never_exposes_key(client, seller):
    key = "sk-ant-api03-" + "x" * 40 + "WXYZ"
    h = seller.h()
    r = client.post("/api/v1/ai/credentials", headers=h, json={"provider": "anthropic", "api_key": key})
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_not_in_plan"
    set_plan(seller.merchant_id, "business")
    r = client.post("/api/v1/ai/credentials", headers=h, json={"provider": "anthropic", "api_key": key})
    assert r.status_code == 201 and key not in r.text and r.json()["key_last4"] == "WXYZ"
    listing = client.get("/api/v1/ai/credentials", headers=h)
    assert key not in listing.text
    audit = client.get("/api/v1/audit-logs?action=ai.byok", headers=h)
    assert key not in audit.text and audit.json()["items"]
    with session_scope() as db:
        cred = db.scalar(select(ProviderCredential))
        assert key not in cred.key_sealed
        from app.domains.ai.credentials import active_keys

        assert active_keys(db, uuid.UUID(seller.merchant_id))["anthropic"][0] == key
    cid = r.json()["id"]
    assert client.delete(f"/api/v1/ai/credentials/{cid}", headers=h).status_code == 204
    with session_scope() as db:
        assert db.scalar(select(ProviderCredential)).key_sealed is None


# ---------------------------------------------------------------- Claude adapter mapping (no network)
class _FakeMessages:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.kwargs = resp, exc, None

    def create(self, **kw):
        self.kwargs = kw
        if self.exc:
            raise self.exc
        return self.resp


def _adapter_with(monkeypatch, fake) -> AnthropicAdapter:
    a = AnthropicAdapter("sk-test", options={})
    monkeypatch.setattr(
        a, "_client", lambda t: SimpleNamespace(messages=fake, beta=SimpleNamespace(messages=fake))
    )
    return a


def _resp(text, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        model="claude-opus-5-5",
        usage=SimpleNamespace(
            input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0
        ),
        stop_details=None,
    )


def test_anthropic_structured_uses_output_config_and_parses(monkeypatch):
    fake = _FakeMessages(_resp('{"title": "Kurta", "confidence": 0.9}'))
    out = _adapter_with(monkeypatch, fake).generate_structured(
        "claude-opus-5-5", _req(), timeout_s=5, effort="medium"
    )
    assert out.data == {"title": "Kurta", "confidence": 0.9}
    assert fake.kwargs["output_config"] == {
        "format": {"type": "json_schema", "schema": SCHEMA},
        "effort": "medium",
    }
    assert "thinking" not in fake.kwargs and "temperature" not in fake.kwargs


def test_anthropic_refusal_and_errors_are_normalized(monkeypatch):
    with pytest.raises(ProviderError) as e:
        _adapter_with(monkeypatch, _FakeMessages(_resp("", stop="refusal"))).generate_text(
            "claude-opus-5-5", _req(), timeout_s=5, effort=None
        )
    assert e.value.code == "refusal" and not e.value.retryable and not e.value.counts_toward_circuit

    import anthropic
    import httpx2 as httpx_mod

    req = httpx_mod.Request("POST", "https://api.anthropic.com/v1/messages")
    exc = anthropic.InternalServerError("boom", response=httpx_mod.Response(500, request=req), body=None)
    with pytest.raises(ProviderError) as e2:
        _adapter_with(monkeypatch, _FakeMessages(exc=exc)).generate_text(
            "claude-opus-5-5", _req(), timeout_s=5, effort=None
        )
    assert e2.value.retryable and e2.value.code == "provider_unavailable"
