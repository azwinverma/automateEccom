from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest
import respx

from app.core.crypto import SealedSecret
from app.core.logging import _redact
from app.domains.ai.providers.gemini_adapter import GeminiAdapter
from app.domains.ai.providers.openai_adapter import OpenAIAdapter
from app.domains.ai.types import AIRequest, Message, ProviderError
from app.domains.integrations import registry
from app.domains.integrations.base import CapabilityNotSupported, ChannelCapability, Money
from app.domains.integrations.http import ResilientClient
from app.domains.integrations.storage import LocalStorage, tenant_key


def test_health_readiness_metrics(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["checks"] == {"database": "ok", "redis": "ok"}
    client.get("/api/v1/me")
    m = client.get("/metrics").text
    assert "http_requests_total" in m and 'route="/api/v1/me"' in m
    assert client.get("/healthz").headers["X-Content-Type-Options"] == "nosniff"


def test_error_envelope_for_validation_and_404(client):
    r = client.post("/api/v1/auth/register", json={"email": "not-an-email"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["details"]["fields"]
    assert client.get("/api/v1/nope").json()["error"]["code"] == "not_found"


def test_admin_requires_staff_with_mfa(client, seller):
    assert client.get("/api/v1/admin/merchants", headers=seller.h()).status_code == 404
    from app.core.db import session_scope
    from app.domains.accounts.service import find_user_by_email

    with session_scope() as db:
        find_user_by_email(db, seller.email).is_platform_staff = True
    r = client.get("/api/v1/admin/merchants", headers=seller.h())
    assert r.status_code == 403 and r.json()["error"]["code"] == "mfa_required"


def test_feature_flags_override_and_rollout(client, seller):
    import uuid

    from app.core.db import session_scope
    from app.domains.platform.models import FeatureFlag, FeatureFlagOverride

    with session_scope() as db:
        db.add(FeatureFlag(key="inbox.beta", default_enabled=False))
        db.add(FeatureFlag(key="killed", default_enabled=True, kill_switch=True))
        db.flush()
        db.add(
            FeatureFlagOverride(
                flag_key="inbox.beta", merchant_id=uuid.UUID(seller.merchant_id), enabled=True
            )
        )
    flags = client.get("/api/v1/feature-flags", headers=seller.h()).json()["flags"]
    assert flags == {"inbox.beta": True, "killed": False}


def test_sealed_secret_is_bound_to_aad():
    blob = SealedSecret.seal("sk-live-secret", "merchant:a")
    assert "sk-live-secret" not in blob.blob
    assert blob.open("merchant:a") == "sk-live-secret"
    with pytest.raises(Exception):
        blob.open("merchant:b")


def test_log_redaction():
    out = _redact({"password": "x", "nested": {"api_key": "y", "ok": 1}, "headers": [{"Authorization": "z"}]})
    assert out == {
        "password": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "ok": 1},
        "headers": [{"Authorization": "[REDACTED]"}],
    }


def test_registry_capabilities_and_production_guard(monkeypatch):
    ch = registry.channel("sandbox_channel")
    assert ch.supports(ChannelCapability.MESSAGES) and not ch.supports(ChannelCapability.REFUNDS)
    cod = registry.payment("cod")
    with pytest.raises(CapabilityNotSupported):
        cod.refund("x", Money(100, "NPR"), "k")
    from app.core.config import Environment, get_settings

    monkeypatch.setattr(get_settings(), "environment", Environment.PRODUCTION)
    with pytest.raises(registry.AdapterNotAvailable):
        registry.channel("sandbox_channel")
    assert all(not a["sandbox"] for a in registry.available("payment"))


def test_sandbox_webhook_signature_verification():
    a = registry.channel("sandbox_channel", credentials={"webhook_secret": "whsec"})
    body = json.dumps({"id": "evt_1", "type": "order.created", "data": {}}).encode()
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert a.verify_webhook({"X-Sandbox-Signature": sig}, body)
    assert not a.verify_webhook({"X-Sandbox-Signature": "0" * 64}, body)
    assert a.parse_webhook({}, body)[0].external_event_id == "evt_1"


def test_resilient_client_retries_get_but_not_unsafe_post():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503 if calls["n"] < 3 else 200, headers={"retry-after": "0"})

    c = ResilientClient("courier_x", transport=httpx.MockTransport(handler), sleep=lambda s: None)
    assert (
        c.request("GET", "https://x.invalid/track", operation="track").status_code == 200 and calls["n"] == 3
    )
    calls["n"] = 0
    assert (
        c.request("POST", "https://x.invalid/shipments", operation="create").status_code == 503
        and calls["n"] == 1
    )


def test_local_storage_blocks_traversal_and_signs_urls(tmp_path):
    s = LocalStorage(tmp_path, "secret")
    key = tenant_key("m1", "media", "original.jpg")
    s.put(key, b"img", "image/jpeg")
    assert s.get(key) == b"img"
    with pytest.raises(ValueError):
        s.put("../../etc/passwd", b"", "text/plain")
    url = s.signed_get_url(key, ttl_s=99999)
    import urllib.parse as up

    q = dict(up.parse_qsl(up.urlparse(url).query))
    assert s.verify("GET", key, int(q["exp"]), q["sig"]) and not s.verify("PUT", key, int(q["exp"]), q["sig"])


@respx.mock
def test_openai_adapter_contract():
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "gpt-x",
                "choices": [{"message": {"content": '{"a": 1}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            },
        )
    )
    out = OpenAIAdapter("sk-test").generate_structured(
        "gpt-x",
        AIRequest(messages=(Message("user", "hi"),), json_schema={"type": "object"}),
        timeout_s=5,
        effort=None,
    )
    assert out.data == {"a": 1} and out.usage.input_tokens == 7
    sent = json.loads(respx.calls.last.request.content)
    assert sent["response_format"]["json_schema"]["strict"] is True
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(429, headers={"retry-after": "2"})
    )
    with pytest.raises(ProviderError) as e:
        OpenAIAdapter("sk-test").generate_text(
            "gpt-x", AIRequest(messages=(Message("user", "hi"),)), timeout_s=5, effort=None
        )
    assert e.value.retryable and e.value.retry_after_s == 2


@respx.mock
def test_gemini_adapter_contract_key_in_header_not_url():
    route = respx.post("https://generativelanguage.googleapis.com/v1beta/models/g:generateContent").mock(
        return_value=httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "नमस्ते"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
            },
        )
    )
    out = GeminiAdapter("g-key").generate_text(
        "g", AIRequest(messages=(Message("user", "hi"),)), timeout_s=5, effort=None
    )
    assert out.text == "नमस्ते"
    req = route.calls.last.request
    assert "g-key" not in str(req.url) and req.headers["x-goog-api-key"] == "g-key"


def test_route_template_recovers_mount_prefix():
    from app.core.middleware import route_template

    class R:
        path = "/stores/{store_id}"

    scope = {"route": R(), "path": "/api/v1/stores/abc-123", "path_params": {"store_id": "abc-123"}}
    assert route_template(scope) == "/api/v1/stores/{store_id}"
    assert route_template({"path": "/nope"}) == "unmatched"
