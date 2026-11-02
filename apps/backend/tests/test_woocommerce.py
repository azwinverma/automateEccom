"""WooCommerce adapter contract tests (mocked HTTP following WooCommerce REST API v3 shapes)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import httpx
import respx

from app.domains.integrations.woocommerce import WooCommerceAdapter
from tests.test_channels import _dispatch, listing
from tests.test_media import phone_photo, upload

API = "/api/v1"
STORE = "https://shop.thamelthreads.example"
WC = f"{STORE}/wp-json/wc/v3"
KEYS = {
    "provider": "woocommerce",
    "store_url": STORE,
    "consumer_key": "ck_" + "a" * 37,
    "consumer_secret": "cs_" + "b" * 37,
}


def _mock_store(currency: str = "NPR") -> None:
    respx.get(f"{WC}/products").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{WC}/settings/general/woocommerce_currency").mock(
        return_value=httpx.Response(200, json={"id": "woocommerce_currency", "value": currency})
    )


def _connect(client, s) -> dict:
    r = client.post(f"{API}/channels/connect-with-keys", headers=s.h(), json=KEYS)
    assert r.status_code == 201, r.text
    return r.json()


@respx.mock
def test_connect_with_keys_validates_url_keys_and_currency(client, seller):
    r = client.post(
        f"{API}/channels/connect-with-keys",
        headers=seller.h(),
        json={**KEYS, "store_url": "http://x.example"},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_store_url"
    respx.get(f"{WC}/products").mock(
        return_value=httpx.Response(401, json={"code": "woocommerce_rest_cannot_view"})
    )
    r = client.post(f"{API}/channels/connect-with-keys", headers=seller.h(), json=KEYS)
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_api_keys"
    respx.reset()
    _mock_store("USD")
    r = client.post(f"{API}/channels/connect-with-keys", headers=seller.h(), json=KEYS)
    assert r.status_code == 409 and r.json()["error"]["code"] == "currency_mismatch"
    respx.reset()
    _mock_store()
    c = _connect(client, seller)
    assert c["provider"] == "woocommerce" and c["external_account_id"] == STORE and c["status"] == "connected"
    assert "product_listing" in c["capabilities"] and "content_publish" not in c["capabilities"]
    assert KEYS["consumer_secret"] not in json.dumps(c)
    audit = client.get(f"{API}/audit-logs?action=channels.connected", headers=seller.h()).text
    assert KEYS["consumer_secret"] not in audit and KEYS["consumer_key"] not in audit


@respx.mock
def test_publish_variable_product_then_update_by_sku(client, seller):
    _mock_store()
    c = _connect(client, seller)
    photo = upload(client, seller, phone_photo())["id"]
    p = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={
            "title": "Cotton Kurta",
            "description": "Hand-finished cotton kurta.",
            "options": [{"name": "Size", "values": ["M", "L"]}],
            "variants": [
                {"options": {"Size": "M"}, "price_minor": 245000, "compare_at_minor": 290000, "sku": "KUR-M"},
                {"options": {"Size": "L"}, "price_minor": 245000, "sku": "KUR-L"},
            ],
        },
    ).json()
    client.put(
        f"{API}/catalog/products/{p['id']}/media", headers=seller.h(), json={"items": [{"asset_id": photo}]}
    )
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    _dispatch()

    create = respx.post(f"{WC}/products").mock(return_value=httpx.Response(201, json={"id": 501}))
    respx.get(f"{WC}/products/501/variations").mock(return_value=httpx.Response(200, json=[]))
    batch = respx.post(f"{WC}/products/501/variations/batch").mock(
        return_value=httpx.Response(
            200, json={"create": [{"id": 9001}, {"id": 9002}], "update": [], "delete": []}
        )
    )
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    lst = listing(client, seller, p["id"])
    assert lst["status"] == "published" and lst["external_id"] == "501"
    body = json.loads(create.calls.last.request.content)
    assert body["type"] == "variable" and body["status"] == "publish"
    assert body["attributes"] == [{"name": "Size", "options": ["M", "L"], "variation": True, "visible": True}]
    assert len(body["images"]) == 1 and "/square_white.jpg" in body["images"][0]["src"]
    variations = json.loads(batch.calls.last.request.content)["create"]
    assert variations[0] == {
        "sku": "KUR-M",
        "regular_price": "2900.00",
        "sale_price": "2450.00",
        "attributes": [{"name": "Size", "option": "M"}],
        "weight": "",
    }
    assert variations[1]["regular_price"] == "2450.00" and variations[1]["sale_price"] == ""

    # Price change → product PUT + variation update by SKU (no duplicate product, no duplicate variations).
    update = respx.put(f"{WC}/products/501").mock(return_value=httpx.Response(200, json={"id": 501}))
    respx.get(f"{WC}/products/501/variations").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 9001, "sku": "KUR-M"}, {"id": 9002, "sku": "KUR-L"}, {"id": 9003, "sku": "OLD-XL"}],
        )
    )
    batch2 = respx.post(f"{WC}/products/501/variations/batch").mock(
        return_value=httpx.Response(
            200, json={"create": [], "update": [{"id": 9002}], "delete": [{"id": 9003}]}
        )
    )
    client.patch(
        f"{API}/catalog/products/{p['id']}/variants/{p['variants'][1]['id']}",
        headers=seller.h(),
        json={"price_minor": 255000},
    )
    _dispatch()
    assert update.called and create.call_count == 1
    sent = json.loads(batch2.calls.last.request.content)
    assert (
        [u["id"] for u in sent["update"]] == [9001, 9002]
        and sent["create"] == []
        and sent["delete"] == [9003]
    )
    assert next(u for u in sent["update"] if u["id"] == 9002)["regular_price"] == "2550.00"
    assert listing(client, seller, p["id"])["status"] == "published"


@respx.mock
def test_revoked_keys_expire_the_connection(client, seller):
    _mock_store()
    c = _connect(client, seller)
    p = client.post(
        f"{API}/catalog/products",
        headers=seller.h(),
        json={"title": "Singing Bowl", "variants": [{"price_minor": 350000, "sku": "BOWL-7"}]},
    ).json()
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    _dispatch()
    respx.post(f"{WC}/products").mock(
        return_value=httpx.Response(401, json={"code": "woocommerce_rest_cannot_create"})
    )
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    conns = client.get(f"{API}/channels", headers=seller.h()).json()["items"]
    assert conns[0]["status"] == "expired" and listing(client, seller, p["id"])["status"] == "failed"


def test_webhook_signature_and_parsing():
    body = json.dumps({"id": 812, "status": "processing"}).encode()
    secret = "wc-webhook-secret"
    sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    a = WooCommerceAdapter({"webhook_secret": secret})
    headers = {
        "X-WC-Webhook-Signature": sig,
        "X-WC-Webhook-Topic": "order.created",
        "X-WC-Webhook-ID": "4",
        "X-WC-Webhook-Delivery-ID": "77",
        "X-WC-Webhook-Source": STORE + "/",
    }
    assert a.verify_webhook(headers, body)
    assert not a.verify_webhook({**headers, "X-WC-Webhook-Signature": "AAAA"}, body)
    ev = a.parse_webhook(headers, body)[0]
    assert (ev.event_type, ev.external_event_id, ev.external_account_id) == ("order.created", "4:77", STORE)
