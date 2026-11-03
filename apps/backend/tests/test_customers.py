"""CRM-001…004 + ORD-012: customers, identity resolution, Nepal addresses, merge."""

from __future__ import annotations

import uuid

from app.core.context import Actor, TenantContext
from app.core.db import session_scope
from app.domains.customers import nepal, service
from tests.conftest import onboard

API = "/api/v1"
ADDR = {
    "recipient_name": "Sita Shrestha",
    "phone": "9841234567",
    "district": "Kathmandu",
    "municipality": "Kathmandu Metropolitan City",
    "ward": 26,
    "area": "Thamel",
    "landmark": "Near Kathmandu Guest House",
}


def test_phone_normalisation_and_lookup():
    assert nepal.normalize_phone("984-123-4567") == "+9779841234567"
    assert nepal.normalize_phone("+977 9801234567") == "+9779801234567"
    assert nepal.normalize_phone("01-4412345") is None  # landline: not usable for delivery calls/SMS
    assert nepal.find_phone("dai mero number 9812345678 ho, XL chahiyo") == "+9779812345678"
    assert nepal.district_code("rukum west") == "rukum_west"
    assert len(nepal.DISTRICTS) == 77 and len(nepal.PROVINCES) == 7


def test_create_customer_address_and_province_derived(client, seller):
    r = client.post(
        f"{API}/customers", headers=seller.h(), json={"display_name": "Sita", "phone": "9841234567"}
    )
    assert r.status_code == 201 and r.json()["phone"] == "+9779841234567"
    cid = r.json()["id"]
    dup = client.post(
        f"{API}/customers", headers=seller.h(), json={"display_name": "S", "phone": "+977-9841234567"}
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "customer_phone_exists"
    a = client.post(f"{API}/customers/{cid}/addresses", headers=seller.h(), json=ADDR)
    assert a.status_code == 201, a.text
    body = a.json()
    assert body["province"] == "bagmati" and body["district"] == "kathmandu" and body["is_default"] is True
    assert body["completeness"] == 1.0
    found = client.get(f"{API}/customers", params={"q": "41234"}, headers=seller.h()).json()["items"]
    assert [c["id"] for c in found] == [cid]


def test_address_validation_errors_are_field_level(client, seller):
    cid = client.post(f"{API}/customers", headers=seller.h(), json={"display_name": "Ram"}).json()["id"]
    bad = {**ADDR, "province": "gandaki", "phone": "014412345"}
    r = client.post(f"{API}/customers/{cid}/addresses", headers=seller.h(), json=bad)
    assert r.status_code == 400
    fields = {f["loc"][-1]: f["type"] for f in r.json()["error"]["details"]["fields"]}
    assert fields == {"district": "district_not_in_province", "phone": "invalid_phone"}
    r = client.post(
        f"{API}/customers/{cid}/addresses", headers=seller.h(), json={**ADDR, "district": "Atlantis"}
    )
    assert {f["loc"][-1] for f in r.json()["error"]["details"]["fields"]} >= {"district"}
    assert (
        client.post(
            f"{API}/customers/{cid}/addresses", headers=seller.h(), json={**ADDR, "ward": 99}
        ).status_code
        == 400
    )


def test_identity_resolution_joins_by_phone_and_merge_moves_everything(client, seller):
    mid = uuid.UUID(seller.merchant_id)
    ctx = TenantContext(
        merchant_id=mid, actor=Actor.system("test"), permissions=frozenset({"customers.merge"})
    )
    with session_scope(mid) as db:
        a = service.resolve_identity(
            db, mid, provider="sandbox_channel", external_id="psid-1", display_name="Sita FB"
        )
        again = service.resolve_identity(db, mid, provider="sandbox_channel", external_id="psid-1")
        assert again.id == a.id
        b = service.resolve_identity(
            db, mid, provider="woocommerce", external_id="17", display_name="Sita S", phone="9841234567"
        )
        assert b.id != a.id
        # The Messenger chat later shares the same phone: the two become one customer.
        merged = service.attach_phone(db, ctx, a, "9841234567")
        assert merged.id == b.id
        aid, bid = a.id, b.id
    d = client.get(f"{API}/customers/{aid}", headers=seller.h()).json()  # old id resolves to the survivor
    assert d["id"] == str(bid)
    assert {i["provider"] for i in d["identities"]} == {"sandbox_channel", "woocommerce"}


def test_manual_merge_requires_permission_and_tenant(client, seller):
    other = onboard(client, shop="Patan Crafts")
    c1 = client.post(f"{API}/customers", headers=seller.h(), json={"display_name": "A"}).json()["id"]
    c2 = client.post(
        f"{API}/customers", headers=seller.h(), json={"display_name": "B", "phone": "9801111111"}
    ).json()["id"]
    foreign = client.post(f"{API}/customers", headers=other.h(), json={"display_name": "X"}).json()["id"]
    assert (
        client.post(
            f"{API}/customers/{c2}/merge", headers=seller.h(), json={"source_id": foreign}
        ).status_code
        == 404
    )
    assert client.get(f"{API}/customers/{c1}", headers=other.h()).status_code == 404
    r = client.post(f"{API}/customers/{c2}/merge", headers=seller.h(), json={"source_id": c1})
    assert r.status_code == 200 and r.json()["id"] == c2
    assert (
        client.post(f"{API}/customers/{c2}/merge", headers=seller.h(), json={"source_id": c2}).status_code
        == 400
    )


def test_nepal_reference_is_public():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get(f"{API}/reference/nepal")
    assert r.status_code == 200 and len(r.json()["districts"]) == 77
