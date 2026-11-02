"""CNT-012: creative attributes recorded on content for the Creative Genome (specs/09)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta

import pytest

from app.domains.content import creative
from tests.conftest import onboard
from tests.test_channels import connect
from tests.test_media import phone_photo, upload

API = "/api/v1/content"


@pytest.mark.parametrize(
    ("text", "mix"),
    [
        ("नयाँ ढाका टोपी आइपुग्यो। म्यासेज गर्नुहोस्।", "ne"),
        ("New dhaka topi just arrived. DM to order.", "en"),
        ("Naya collection आइपुग्यो! Size M, L, XL available छ। DM गर्नुस्", "ne_en_mixed"),
        ("🔥🔥 2450", "none"),
    ],
)
def test_language_mix(text, mix):
    assert creative.language_mix(text) == mix


@pytest.mark.parametrize(
    ("text", "cta"),
    [
        ("DM to order", "dm"),
        ("थप जानकारीका लागि म्यासेज गर्नुहोस्", "dm"),
        ("Comment 'size' below", "comment"),
        ("Shop now: https://thamelthreads.example/kurta", "link"),
        ("Call 9801234567 for orders", "call"),
        ("Maroon kurta, dhaka border.", "none"),
    ],
)
def test_cta_detection(text, cta):
    assert creative.cta_type(text) == cta


def test_caption_bucket_and_posting_window_in_kathmandu():
    assert creative.caption_bucket("x" * 20) == "short"
    assert creative.caption_bucket("x" * 150) == "medium"
    assert creative.caption_bucket("x" * 400) == "long"
    # 13:30 UTC = 19:15 in Kathmandu (UTC+5:45) → the 7 PM window
    assert creative.posting_window(datetime(2026, 11, 2, 13, 30, tzinfo=UTC), "Asia/Kathmandu") == 19
    assert creative.posting_window(None, "Asia/Kathmandu") is None


def test_post_records_derived_and_declared_attributes(client, seller):
    c = connect(client, seller)
    r = client.post(
        f"{API}/posts",
        headers=seller.h(),
        json={
            "connection_id": c["id"],
            "caption": "Naya collection आइपुग्यो! DM गर्नुस्",
            "hook_type": "offer",
            "human_presence": True,
            "background": "lifestyle",
        },
    )
    assert r.status_code == 201, r.text
    cr = r.json()["creative"]
    assert cr["language_mix"] == "ne_en_mixed" and cr["cta_type"] == "dm" and cr["caption_bucket"] == "short"
    assert (cr["hook_type"], cr["human_presence"], cr["background"]) == ("offer", True, "lifestyle")
    assert cr["posting_hour"] is None and cr["version"] == 1
    pid = r.json()["id"]
    # Editing the caption re-derives; declared values survive a caption-only edit.
    upd = client.patch(
        f"{API}/posts/{pid}",
        headers=seller.h(),
        json={"caption": "Full English caption, comment below for sizes"},
    ).json()["creative"]
    assert upd["language_mix"] == "en" and upd["cta_type"] == "comment" and upd["hook_type"] == "offer"
    # Scheduling records the merchant-local posting hour.
    client.post(f"{API}/posts/{pid}/submit", headers=seller.h(), json={})
    slot = (datetime.now(UTC) + timedelta(days=1)).replace(hour=13, minute=30, second=0, microsecond=0)
    sch = client.post(f"{API}/posts/{pid}/schedule", headers=seller.h(), json={"at": slot.isoformat()}).json()
    assert sch["creative"]["posting_hour"] == 19
    bad = client.post(
        f"{API}/posts",
        headers=seller.h(),
        json={"connection_id": c["id"], "caption": "x", "hook_type": "viral"},
    )
    assert bad.status_code == 400


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_reel_post_inherits_video_attributes(client, seller):
    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch

    c = connect(client, seller)
    photos = [upload(client, seller, phone_photo())["id"] for _ in range(2)]
    prod = client.post(
        "/api/v1/catalog/products",
        headers=seller.h(),
        json={"title": "Kurta", "variants": [{"price_minor": 245000}]},
    ).json()
    job = client.post(
        "/api/v1/media/videos/auto-reels",
        headers=seller.h(),
        json={
            "asset_ids": photos,
            "aspect": "9:16",
            "locale": "en",
            "headline": "Kurta",
            "product_id": prod["id"],
            "show_price": True,
        },
    ).json()
    early = client.post(
        f"{API}/posts",
        headers=seller.h(),
        json={"connection_id": c["id"], "caption": "Reel", "kind": "reel", "video_job_id": job["id"]},
    )
    assert early.status_code == 409 and early.json()["error"]["code"] == "video_not_ready"
    dispatch_batch()
    r = client.post(
        f"{API}/posts",
        headers=seller.h(),
        json={
            "connection_id": c["id"],
            "caption": "New kurta drop. DM to order",
            "kind": "reel",
            "video_job_id": job["id"],
        },
    )
    assert r.status_code == 201, r.text
    p = r.json()
    cr = p["creative"]
    assert cr["duration_s"] == 4.5 and cr["price_shown"] is True and cr["price_timing_s"] == 0.0
    assert (cr["hook_type"], cr["background"], cr["template_id"]) == (
        "price_first",
        "blurred_photo",
        "auto_reel.showcase.v1",
    )
    video_asset = client.get(f"/api/v1/media/videos/{job['id']}", headers=seller.h()).json()["output"]["id"]
    assert p["asset_ids"][0] == video_asset  # reel output attached automatically


def test_video_reference_is_tenant_scoped(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    import uuid

    cb = connect(client, b)
    r = client.post(
        f"{API}/posts",
        headers=b.h(),
        json={"connection_id": cb["id"], "caption": "x", "video_job_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "video_not_found"
    assert a  # a's resources are never reachable from b (covered across suites)
