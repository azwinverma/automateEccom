from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.db import session_scope
from app.domains.audit.models import AuditLog
from app.domains.billing.models import EntitlementOverride
from app.domains.catalog import rules
from app.domains.catalog.imports import rupees_to_minor
from app.domains.platform.models import OutboxEvent
from tests.conftest import onboard, register_and_login

API = "/api/v1/catalog"

KURTA = {
    "title": "Cotton Kurta — Dhaka Border",
    "title_ne": "सुती कुर्ता — ढाका बोर्डर",
    "description": "Hand-finished cotton kurta with Palpali dhaka border.",
    "brand": "Thamel Threads",
    "tags": ["Kurta", "dhaka", "kurta"],
    "options": [{"name": "Color", "values": ["Maroon", "Navy"]}, {"name": "Size", "values": ["M", "L"]}],
    "variants": [
        {
            "options": {"Color": "Maroon", "Size": "M"},
            "price_minor": 245000,
            "cost_minor": 120000,
            "weight_grams": 350,
        },
        {"options": {"Color": "Maroon", "Size": "L"}, "price_minor": 245000, "compare_at_minor": 290000},
        {"options": {"Color": "Navy", "Size": "M"}, "price_minor": 245000, "barcode": "4006381333931"},
        {"options": {"Color": "navy", "Size": "l"}, "price_minor": 255000, "sku": "kurta-navy-xl special"},
    ],
}


def _create(client, s, body=None, **headers):
    return client.post(f"{API}/products", headers=s.h(**headers), json=body or KURTA)


def test_create_product_with_variants_auto_skus_audit_and_events(client, seller):
    r = _create(client, seller)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["status"] == "draft" and p["handle"] == "cotton-kurta-dhaka-border" and p["version"] == 1
    assert p["tags"] == ["kurta", "dhaka"]  # normalized + de-duplicated
    assert [o["name"] for o in p["options"]] == ["Color", "Size"]
    skus = [v["sku"] for v in p["variants"]]
    assert skus[:3] == [
        "COTTON-KURTA-DHAKA-BORDE-MAROON-M",
        "COTTON-KURTA-DHAKA-BORDE-MAROON-L",
        "COTTON-KURTA-DHAKA-BORDE-NAVY-M",
    ]
    assert skus[3] == "KURTA-NAVY-XL-SPECIAL"
    assert p["variants"][3]["options"] == {
        "Color": "Navy",
        "Size": "L",
    }  # case-insensitive match to declared values
    assert p["variants"][0]["price"] == {"amount_minor": 245000, "currency": "NPR"}
    with session_scope() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "catalog.product_created"))
        assert db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "catalog.product_created"))


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        (
            {
                "variants": [
                    {"options": {"Color": "Red", "Size": "M"}, "price_minor": 1000, "compare_at_minor": 900}
                ],
                "options": [{"name": "Color", "values": []}, {"name": "Size", "values": []}],
            },
            "invalid_compare_at",
        ),
        ({"variants": [{"options": {"Color": "Red"}, "price_minor": 1000}]}, "variant_options_mismatch"),
        (
            {
                "variants": [
                    {"options": {"Color": "Red", "Size": "M"}, "price_minor": 1000},
                    {"options": {"Color": "red", "Size": "m"}, "price_minor": 1000},
                ]
            },
            "duplicate_variant",
        ),
        (
            {
                "variants": [
                    {
                        "options": {"Color": "Red", "Size": "M"},
                        "price_minor": 1000,
                        "barcode": "4006381333932",
                    }
                ]
            },
            "invalid_barcode",
        ),
        ({"options": [], "variants": [{"price_minor": 1}, {"price_minor": 2}]}, "options_required"),
    ],
)
def test_create_product_validation(client, seller, patch, code):
    body = {**KURTA, **patch}
    r = _create(client, seller, body)
    assert r.status_code == 400 and r.json()["error"]["code"] == code, r.text


def test_sku_unique_per_merchant_but_not_across_merchants(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    body = {"title": "Singing Bowl", "variants": [{"price_minor": 350000, "sku": "BOWL-01"}]}
    assert _create(client, a, body).status_code == 201
    r = _create(client, a, {**body, "title": "Another Bowl"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "sku_taken"
    assert _create(client, b, body).status_code == 201


def test_optimistic_locking_on_concurrent_edits(client, seller):
    p = _create(client, seller).json()
    ok = client.patch(f"{API}/products/{p['id']}", headers=seller.h(), json={"version": 1, "brand": "TT"})
    assert ok.status_code == 200 and ok.json()["version"] == 2
    stale = client.patch(
        f"{API}/products/{p['id']}", headers=seller.h(), json={"version": 1, "brand": "Other"}
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "version_conflict"
    assert stale.json()["error"]["details"]["current_version"] == 2


def test_lifecycle_state_machine_and_publish_guards(client, seller):
    body = {"title": "Pashmina Shawl", "variants": [{"price_minor": 0}]}
    p = _create(client, seller, body).json()
    r = client.post(f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    assert r.status_code == 400 and "price_required" in r.json()["error"]["details"]["problems"]
    vid = p["variants"][0]["id"]
    client.patch(f"{API}/products/{p['id']}/variants/{vid}", headers=seller.h(), json={"price_minor": 650000})
    assert (
        client.post(f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "active"}).json()[
            "status"
        ]
        == "active"
    )
    # last variant of a live product cannot be removed
    r = client.delete(f"{API}/products/{p['id']}/variants/{vid}", headers=seller.h())
    assert r.status_code == 409 and r.json()["error"]["code"] == "last_variant"
    assert (
        client.post(
            f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "archived"}
        ).status_code
        == 200
    )
    r = client.post(f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_state_transition"
    assert r.json()["error"]["details"]["allowed"] == ["draft"]


def test_unconfirmed_ai_attributes_block_publishing_until_seller_confirms(client, seller):
    from app.domains.catalog.service import suggest_attributes

    p = _create(client, seller).json()
    with session_scope() as db:
        suggest_attributes(
            db,
            uuid.UUID(seller.merchant_id),
            uuid.UUID(p["id"]),
            [("material", "cotton", 0.62), ("neckline", "mandarin", 0.91)],
        )
    detail = client.get(f"{API}/products/{p['id']}", headers=seller.h()).json()
    assert detail["needs_review"] is True
    r = client.post(f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    assert "unconfirmed_ai_attributes" in r.json()["error"]["details"]["problems"]
    # Seller corrects one value (becomes seller-sourced) and confirms the other.
    client.put(
        f"{API}/products/{p['id']}/attributes",
        headers=seller.h(),
        json={"items": [{"key": "material", "value": "cotton-silk blend"}]},
    )
    client.post(
        f"{API}/products/{p['id']}/attributes/confirm", headers=seller.h(), json={"keys": ["neckline"]}
    )
    with session_scope() as db:  # AI must never overwrite the seller's value
        suggest_attributes(
            db, uuid.UUID(seller.merchant_id), uuid.UUID(p["id"]), [("material", "polyester", 0.99)]
        )
    detail = client.get(f"{API}/products/{p['id']}", headers=seller.h()).json()
    material = next(a for a in detail["attributes"] if a["key"] == "material")
    assert material == {
        "key": "material",
        "value": "cotton-silk blend",
        "locale": "en",
        "source": "seller",
        "confidence": None,
        "confirmed": True,
    }
    assert (
        client.post(
            f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "active"}
        ).status_code
        == 200
    )


def test_product_limit_counts_non_archived_products(client, seller):
    with session_scope() as db:
        db.add(
            EntitlementOverride(
                merchant_id=uuid.UUID(seller.merchant_id),
                resource_code="products",
                period="lifetime",
                limit_value=1,
                reason="test",
            )
        )
    p = _create(client, seller).json()
    r = _create(client, seller, {"title": "Second", "variants": [{"price_minor": 100}]})
    assert r.status_code == 402 and r.json()["error"]["details"]["resource"] == "products"
    client.post(f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "archived"})
    second = _create(client, seller, {"title": "Second", "variants": [{"price_minor": 100}]})
    assert second.status_code == 201
    r = client.post(f"{API}/products/{p['id']}/status", headers=seller.h(), json={"status": "draft"})
    assert r.status_code == 402  # un-archiving re-checks the limit


def test_tenant_isolation_and_permissions(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    p = _create(client, a).json()
    assert client.get(f"{API}/products/{p['id']}", headers=b.h()).status_code == 404
    assert client.patch(f"{API}/products/{p['id']}", headers=b.h(), json={"title": "x"}).status_code == 404
    assert client.get(f"{API}/products", headers=b.h()).json()["items"] == []

    from app.domains.merchants.models import Membership

    staff = register_and_login(client, "packer@example.com")
    uid = client.get("/api/v1/me", headers=staff.h()).json()["user"]["id"]
    with session_scope(uuid.UUID(a.merchant_id)) as db:
        db.add(Membership(merchant_id=uuid.UUID(a.merchant_id), user_id=uuid.UUID(uid), role="staff"))
    sh = staff.h(merchant=a.merchant_id)
    assert client.patch(f"{API}/products/{p['id']}", headers=sh, json={"brand": "x"}).status_code == 200
    r = client.post(f"{API}/products/{p['id']}/status", headers=sh, json={"status": "active"})
    assert r.status_code == 403 and r.json()["error"]["details"]["permission"] == "catalog.publish"


def test_idempotent_create_and_search_by_sku(client, seller):
    h = {"Idempotency-Key": "create-kurta-0001"}
    r1, r2 = _create(client, seller, **h), _create(client, seller, **h)
    assert r1.json()["id"] == r2.json()["id"] and r2.headers["Idempotent-Replayed"] == "true"
    found = client.get(f"{API}/products?q=navy-xl", headers=seller.h()).json()["items"]
    assert [x["id"] for x in found] == [r1.json()["id"]]
    assert found[0]["price_range"] == {"min_minor": 245000, "max_minor": 255000, "currency": "NPR"}


def test_categories_and_collections(client, seller):
    women = client.post(f"{API}/categories", headers=seller.h(), json={"name": "Women"}).json()
    kurta = client.post(
        f"{API}/categories",
        headers=seller.h(),
        json={"name": "Kurta", "name_ne": "कुर्ता", "parent_id": women["id"]},
    ).json()
    assert kurta["path"] == "women/kurta" and kurta["depth"] == 1
    dup = client.post(
        f"{API}/categories", headers=seller.h(), json={"name": "Kurta", "parent_id": women["id"]}
    )
    assert dup.status_code == 409
    p = _create(client, seller, {**KURTA, "category_id": kurta["id"]}).json()
    col = client.post(f"{API}/collections", headers=seller.h(), json={"title": "Dashain Edit"}).json()
    r = client.put(
        f"{API}/collections/{col['id']}/products",
        headers=seller.h(),
        json={"product_ids": [p["id"], str(uuid.uuid4())]},
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "product_not_found"
    assert client.put(
        f"{API}/collections/{col['id']}/products", headers=seller.h(), json={"product_ids": [p["id"]]}
    ).json() == {"count": 1}
    assert client.get(f"{API}/products/{p['id']}", headers=seller.h()).json()["collection_ids"] == [col["id"]]


# ----------------------------------------------------------------------------- CSV import
CSV = """handle,title,category,tags,option1_name,option1_value,option2_name,option2_value,sku,barcode,price,compare_at_price,cost
dhaka-topi,ढाका टोपी (Dhaka Topi),Accessories > Hats,"topi, dhaka",Size,57cm,,,TOPI-57,,"1,250",,600
dhaka-topi,ढाका टोपी (Dhaka Topi),Accessories > Hats,,Size,58cm,,,TOPI-58,,1250,1500,600
felt-ball-garland,Felt Ball Garland,Home > Decor,,Color,Rainbow,,,,,950.5,,
singing-bowl,Singing Bowl,Home > Decor,,,,,,BOWL-7,,abc,,
"""


def _run_import(client, seller, data: bytes, name="products.csv"):
    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch

    r = client.post(f"{API}/imports", headers=seller.h(), files={"file": (name, data, "text/csv")})
    if r.status_code != 202:
        return r, None
    dispatch_batch()
    return r, client.get(f"{API}/imports/{r.json()['id']}", headers=seller.h()).json()


def test_csv_import_partial_success_with_row_errors(client, seller):
    r, job = _run_import(client, seller, CSV.encode())
    assert r.status_code == 202 and r.json()["status"] == "queued"
    assert job["status"] == "completed_with_errors"
    assert job["products_created"] == 2 and job["rows_failed"] == 1
    assert job["errors"][0]["row"] == 5 and "not a number" in job["errors"][0]["message"]
    items = client.get(f"{API}/products", headers=seller.h()).json()["items"]
    topi = next(i for i in items if i["handle"] == "dhaka-topi")
    assert topi["variant_count"] == 2 and topi["price_range"]["min_minor"] == 125000
    detail = client.get(f"{API}/products/{topi['id']}", headers=seller.h()).json()
    assert (
        detail["title"] == "ढाका टोपी (Dhaka Topi)"
        and detail["variants"][1]["compare_at"]["amount_minor"] == 150000
    )
    cats = [c["path"] for c in client.get(f"{API}/categories", headers=seller.h()).json()["items"]]
    assert {"accessories/hats", "home/decor"} <= set(cats)
    garland = next(i for i in items if i["handle"] == "felt-ball-garland")
    assert garland["price_range"]["min_minor"] == 95050

    dup, _ = _run_import(client, seller, CSV.encode())
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "duplicate_import"


def test_csv_import_updates_existing_by_sku_and_rejects_unknown_skus(client, seller):
    _run_import(client, seller, CSV.encode())
    update = (
        "handle,title,sku,price,cost\n"
        "dhaka-topi,Dhaka Topi,TOPI-57,1350,650\n"
        "dhaka-topi,Dhaka Topi,TOPI-60,1350,650\n"
    )
    _, job = _run_import(client, seller, update.encode(), "update.csv")
    # Group fails atomically: the unknown SKU row rolls back the whole product's update.
    assert job["status"] == "completed_with_errors" and job["products_updated"] == 0
    assert any("TOPI-60" in e["message"] for e in job["errors"])
    ok = "handle,title,sku,price,cost\ndhaka-topi,Dhaka Topi,TOPI-57,1350,650\n"
    _, job = _run_import(client, seller, ok.encode(), "update2.csv")
    assert job["status"] == "completed" and job["products_updated"] == 1


def test_csv_import_rejects_structural_problems_upfront(client, seller):
    r, _ = _run_import(client, seller, b"name,cost\nx,1\n")
    assert r.status_code == 400 and r.json()["error"]["details"]["missing_columns"] == ["title", "price"]
    r, _ = _run_import(client, seller, b"title,price\n")
    assert r.status_code == 400 and r.json()["error"]["code"] == "empty_csv"


# ----------------------------------------------------------------------------- rules
def test_rules_units():
    assert rules.gtin_valid("4006381333931") and not rules.gtin_valid("4006381333932")
    assert rules.gtin_valid("036000291452")  # UPC-A
    assert rules.normalize_barcode("SHOP-0042") == "SHOP-0042"
    assert rupees_to_minor("1,250", "price") == 125000
    assert rupees_to_minor("रू 99.5", "price") == 9950
    assert rupees_to_minor("", "price") is None
    for bad in ("12.345", "-1", "abc"):
        with pytest.raises(ValueError):
            rupees_to_minor(bad, "price")
    assert (
        rules.generate_sku("Cotton Kurta", ["Maroon", "M"], {"COTTON-KURTA-MAROON-M"})
        == "COTTON-KURTA-MAROON-M-2"
    )
    assert rules.generate_sku("ढाका टोपी", [], set()) == "ITEM"  # Devanagari-only handle → safe fallback
    with session_scope() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0
