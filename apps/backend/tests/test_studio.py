from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.db import session_scope
from app.domains.ai.models import AIExecution
from app.domains.ai.providers.sandbox import SandboxAdapter
from app.domains.ai.types import ProviderError
from app.domains.billing.models import EntitlementOverride
from app.domains.studio import grounding
from tests.conftest import onboard
from tests.test_media import phone_photo, upload

API = "/api/v1"

DRAFT = {
    "is_product_photo": True,
    "category": {"path": ["Clothing", "Women", "Kurta"], "confidence": 0.86},
    "title_en": "Maroon Cotton Kurta with Dhaka Border",
    "title_ne": "ढाका बोर्डर भएको मरुन सुती कुर्ता",
    "description_en": "Soft cotton kurta in deep maroon with a woven dhaka border on the neckline and cuffs.",
    "description_ne": "नरम सुती कपडामा बनेको मरुन कुर्ता, घाँटी र बाहुलामा ढाका बोर्डर।",
    "bullets_en": ["Cotton fabric", "Dhaka border detail", "Straight fit"],
    "attributes": [
        {"key": "material", "value": "cotton", "confidence": 0.82},
        {"key": "pattern", "value": "solid with dhaka border", "confidence": 0.9},
        {"key": "fit", "value": "straight", "confidence": 0.55},
    ],
    "colors": ["maroon"],
    "suggested_options": [],
    "seo": {"title": "Maroon Cotton Kurta – Dhaka Border", "description": "Cotton kurta with dhaka border."},
    "hashtags": ["#Kurta", "dhaka", "nepalifashion"],
    "captions": {
        "instagram": "Maroon + dhaka = festive ready ✨\nDM to order.",
        "facebook": "New maroon cotton kurta with dhaka border. Message us for sizes.",
        "tiktok": "Dhaka border kurta 🔥 DM us",
    },
    "needs_seller_input": ["price", "sizes"],
    "confidence": 0.84,
}


def _photos(client, s, n=2):
    return [upload(client, s, phone_photo())["id"] for _ in range(n)]


def _run(client, s, asset_ids, notes=None):
    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch

    r = client.post(f"{API}/studio/jobs", headers=s.h(), json={"asset_ids": asset_ids, "seller_notes": notes})
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "queued"
    dispatch_batch()  # outbox → celery (eager) → gateway → sandbox provider
    return client.get(f"{API}/studio/jobs/{r.json()['id']}", headers=s.h()).json()


def _apply_body(**over):
    body = {
        "product": {
            "title": DRAFT["title_en"],
            "title_ne": DRAFT["title_ne"],
            "description": DRAFT["description_en"],
            "description_ne": DRAFT["description_ne"],
            "options": [{"name": "Size", "values": ["M", "L"]}],
            "variants": [
                {"options": {"Size": "M"}, "price_minor": 245000},
                {"options": {"Size": "L"}, "price_minor": 245000},
            ],
        },
        "category_path": DRAFT["category"]["path"],
        "accepted_attribute_keys": [],
    }
    body.update(over)
    return body


def test_photos_to_draft_to_product_with_grounded_attributes(client, seller):
    SandboxAdapter.override_data["sandbox-text"] = DRAFT
    assets = _photos(client, seller)
    job = _run(client, seller, assets)
    assert job["status"] == "ready" and job["draft"]["title_en"].startswith("Maroon")
    assert job["draft"]["hashtags"] == ["kurta", "dhaka", "nepalifashion"]  # normalised
    assert job["needs_review"] is True  # model asked the seller for price + sizes
    assert job["issues"] == []
    assert job["ai"]["provider"] == "sandbox" and job["ai"]["prompt_version"] == 1
    with session_scope() as db:
        ex = db.scalar(select(AIExecution).where(AIExecution.status == "succeeded"))
        assert ex.task == "PRODUCT_EXTRACTION" and ex.prompt_name == "studio.product_extraction"

    r = client.post(f"{API}/studio/jobs/{job['id']}/apply", headers=seller.h(), json=_apply_body())
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["status"] == "draft" and len(p["media"]) == 2 and len(p["variants"]) == 2
    attrs = {a["key"]: a for a in p["attributes"]}
    assert attrs["material"]["confirmed"] and attrs["pattern"]["confirmed"]  # >= policy threshold 0.75
    assert (
        attrs["fit"]["confirmed"] is False and attrs["fit"]["source"] == "ai"
    )  # low confidence → seller confirms
    cat_paths = [
        c["path"] for c in client.get(f"{API}/catalog/categories", headers=seller.h()).json()["items"]
    ]
    assert "clothing/women/kurta" in cat_paths
    # Cannot go live until the seller confirms the low-confidence attribute.
    r = client.post(f"{API}/catalog/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    assert "unconfirmed_ai_attributes" in r.json()["error"]["details"]["problems"]
    # Applying again is idempotent (no duplicate product).
    again = client.post(f"{API}/studio/jobs/{job['id']}/apply", headers=seller.h(), json=_apply_body())
    assert again.json()["id"] == p["id"]
    assert client.get(f"{API}/studio/jobs/{job['id']}", headers=seller.h()).json()["status"] == "applied"


def test_unsupported_commercial_claims_are_flagged(client, seller):
    SandboxAdapter.override_data["sandbox-text"] = {
        **DRAFT,
        "captions": {
            "instagram": "Only Rs 999! Free delivery inside Kathmandu valley. 100% original.",
            "facebook": "In stock now — 20% off this week.",
            "tiktok": "Warranty included",
        },
    }
    job = _run(client, seller, _photos(client, seller, 1), notes="free delivery inside Kathmandu valley")
    kinds = sorted({i["kind"] for i in job["issues"]})
    assert kinds == [
        "unsupported_claim:authenticity",
        "unsupported_claim:discount",
        "unsupported_claim:price",
        "unsupported_claim:stock",
        "unsupported_claim:warranty",
    ]  # delivery was in the seller notes
    assert job["needs_review"] is True


def test_provider_outage_requeues_then_fails_without_charging(client, seller):
    SandboxAdapter.failures.push(ProviderError("provider_unavailable", retryable=True), times=50)
    job = _run(client, seller, _photos(client, seller, 1))
    assert job["status"] == "queued" and job["error_code"] == "ai_unavailable" and job["attempts"] == 1
    from app.domains.studio.service import run_job

    run_job(uuid.UUID(job["id"]))
    run_job(uuid.UUID(job["id"]))
    final = client.get(f"{API}/studio/jobs/{job['id']}", headers=seller.h()).json()
    assert final["status"] == "failed" and final["attempts"] == 3
    usage = client.get(f"{API}/billing/entitlements", headers=seller.h()).json()["limits"]
    text_usage = next(x for x in usage if x["resource"] == "ai_text_generations")
    assert text_usage["used"] == 0 and text_usage["reserved"] == 0
    SandboxAdapter.failures.clear()
    SandboxAdapter.override_data["sandbox-text"] = DRAFT
    from app.domains.ai.gateway import gateway

    # The outage tripped the shared circuit breaker, so new jobs skip the failing provider for open_s.
    assert gateway.breaker.state("sandbox", "sandbox-text") == "open"
    gateway.breaker.reset("sandbox", "sandbox-text")  # what the breaker timeout does in production
    retry = client.post(f"{API}/studio/jobs/{job['id']}/retry", headers=seller.h())
    assert retry.status_code == 202
    from app.domains.platform.outbox import dispatch_batch

    dispatch_batch()
    assert client.get(f"{API}/studio/jobs/{job['id']}", headers=seller.h()).json()["status"] == "ready"


def test_not_a_product_photo_is_reported(client, seller):
    SandboxAdapter.override_data["sandbox-text"] = {**DRAFT, "is_product_photo": False}
    job = _run(client, seller, _photos(client, seller, 1))
    assert {"field": "photos", "kind": "not_a_product_photo"} in job["issues"]


def test_feature_gate_and_tenant_isolation(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    assets = _photos(client, a, 1)
    r = client.post(f"{API}/studio/jobs", headers=b.h(), json={"asset_ids": assets})
    assert r.status_code == 404 and r.json()["error"]["code"] == "media_not_found"
    with session_scope() as db:
        db.add(
            EntitlementOverride(
                merchant_id=uuid.UUID(a.merchant_id),
                feature_code="ai.product_studio",
                enabled=False,
                reason="test",
            )
        )
    r = client.post(f"{API}/studio/jobs", headers=a.h(), json={"asset_ids": assets})
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_not_in_plan"


def test_apply_requires_ready_draft_and_seller_prices(client, seller):
    SandboxAdapter.failures.push(ProviderError("bad_request", counts_toward_circuit=False), times=50)
    job = _run(client, seller, _photos(client, seller, 1))
    r = client.post(f"{API}/studio/jobs/{job['id']}/apply", headers=seller.h(), json=_apply_body())
    assert r.status_code == 409 and r.json()["error"]["code"] == "draft_not_ready"
    SandboxAdapter.failures.clear()
    SandboxAdapter.override_data["sandbox-text"] = DRAFT
    job = _run(client, seller, _photos(client, seller, 1))
    body = _apply_body()
    body["product"]["variants"] = []
    r = client.post(f"{API}/studio/jobs/{job['id']}/apply", headers=seller.h(), json=body)
    assert r.status_code == 400  # AI never sets prices: seller must provide variants


def test_grounding_unit():
    v = grounding.check({"c": "रू 1,500 मा पाउनुहोस्! निःशुल्क डेलिभरी"})
    assert {x.kind for x in v} == {"price", "delivery"}
    assert grounding.check({"c": "Soft cotton, straight fit, message us for sizes"}) == []
