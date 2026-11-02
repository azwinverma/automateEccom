from __future__ import annotations

import json
import shutil
import subprocess
import uuid

import pytest

from app.core.db import session_scope
from app.domains.billing.models import EntitlementOverride
from app.domains.media import reels
from tests.conftest import onboard
from tests.test_media import phone_photo, upload

API = "/api/v1"
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _dispatch():
    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch

    dispatch_batch()


def _usage(client, s):
    limits = client.get(f"{API}/billing/entitlements", headers=s.h()).json()["limits"]
    return next(x for x in limits if x["resource"] == "auto_reels")


def _reel(client, s, **body):
    r = client.post(f"{API}/media/videos/auto-reels", headers=s.h(), json=body)
    return r


def test_auto_reel_from_seller_photos_with_catalog_price(client, seller, tmp_path):
    photos = [upload(client, seller, phone_photo())["id"] for _ in range(3)]
    prod = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={
            "title": "Maroon Kurta",
            "options": [{"name": "Size", "values": ["M", "L"]}],
            "variants": [
                {"options": {"Size": "M"}, "price_minor": 245000},
                {"options": {"Size": "L"}, "price_minor": 255000},
            ],
        },
    ).json()
    r = _reel(
        client,
        seller,
        asset_ids=photos,
        aspect="9:16",
        locale="en",
        headline="Maroon Cotton Kurta",
        cta="DM to order",
        product_id=prod["id"],
        show_price=True,
    )
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "queued" and _usage(client, seller)["reserved"] == 1
    _dispatch()
    job = client.get(f"{API}/media/videos/{r.json()['id']}", headers=seller.h()).json()
    assert job["status"] == "ready" and job["duration_s"] == 6.5
    out = job["output"]
    assert (
        out["kind"] == "video"
        and out["source"] == "auto_reel"
        and (out["width"], out["height"]) == (1080, 1920)
    )
    mp4 = client.get(out["derivatives"]["video"]["url"])
    assert mp4.status_code == 200 and mp4.headers["content-type"] == "video/mp4"
    path = tmp_path / "r.mp4"
    path.write_bytes(mp4.content)
    probe = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height,pix_fmt",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            check=True,
        ).stdout
    )["streams"][0]
    assert probe == {"codec_name": "h264", "width": 1080, "height": 1920, "pix_fmt": "yuv420p"}
    assert client.get(out["derivatives"]["poster"]["url"]).status_code == 200
    u = _usage(client, seller)
    assert u["used"] == 1 and u["reserved"] == 0


def test_render_failure_and_cancel_do_not_charge(client, seller, monkeypatch):
    photos = [upload(client, seller, phone_photo())["id"]]

    def boom(*a, **k):
        raise reels.ReelError("render_failed", "simulated")

    monkeypatch.setattr(reels, "render", boom)
    job = _reel(client, seller, asset_ids=photos, aspect="1:1").json()
    _dispatch()
    failed = client.get(f"{API}/media/videos/{job['id']}", headers=seller.h()).json()
    assert failed["status"] == "failed" and failed["error_code"] == "render_failed"
    monkeypatch.setattr(
        "app.worker.tasks.run_video_job.delay", lambda *a, **k: None
    )  # keep the next one queued
    queued = _reel(client, seller, asset_ids=photos, aspect="4:5").json()
    _dispatch()
    assert (
        client.post(f"{API}/media/videos/{queued['id']}/cancel", headers=seller.h()).json()["status"]
        == "cancelled"
    )
    u = _usage(client, seller)
    assert u["used"] == 0 and u["reserved"] == 0


def test_nepali_text_is_never_rendered_broken(client, seller):
    photos = [upload(client, seller, phone_photo())["id"]]
    r = _reel(client, seller, asset_ids=photos, headline="ढाका बोर्डर भएको कुर्ता")
    if reels.shaping_available():
        assert r.status_code == 202
    else:
        assert r.status_code == 409 and r.json()["error"]["code"] == "text_shaping_unavailable"
        assert _usage(client, seller)["reserved"] == 0  # refused before charging


def test_validation_gating_and_tenancy(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    photos = [upload(client, a, phone_photo())["id"]]
    assert _reel(client, b, asset_ids=photos).json()["error"]["code"] == "media_not_ready"  # not b's photos
    r = _reel(client, a, asset_ids=photos, show_price=True)
    assert r.json()["error"]["code"] == "product_required_for_price"
    r = _reel(client, a, asset_ids=photos, seconds_per_slide=0.5)
    assert r.status_code == 400
    with session_scope() as db:
        db.add(
            EntitlementOverride(
                merchant_id=uuid.UUID(a.merchant_id),
                feature_code="video.auto_reels",
                enabled=False,
                reason="test",
            )
        )
    r = _reel(client, a, asset_ids=photos)
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_not_in_plan"


def test_npr_formatting():
    assert reels.format_npr(12345678900, "en") == "Rs 12,34,56,789"
    assert reels.format_npr(99, "en") == "Rs 0.99"
    assert reels.format_npr(245000, "ne", from_prefix=True) == "देखि रू २,४५०"


def test_overlay_never_covers_the_product():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (900, 1600), (30, 90, 160)).save(buf, "PNG")  # tall portrait product photo
    size = reels.ASPECTS["9:16"]
    _, reserved = reels.card(size, reels.Overlay("Tall product", "Rs 1,000", "DM to order"))
    s = reels.slide(buf.getvalue(), size, reserved)
    under_card = s.crop((0, size[1] - reserved, size[0], size[1])).getcolors(10_000_000)
    assert reserved > 0 and not any(rgb == (30, 90, 160) for _, rgb in under_card)
