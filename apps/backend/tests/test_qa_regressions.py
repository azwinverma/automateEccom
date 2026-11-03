"""Regression tests for issues found in the production-readiness QA cycle (docs/QA_TEST_REPORT.md).
Each test names its QA id; it reproduces the original failure and pins the fix."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import onboard

API = "/api/v1"


def _product(client, s, **variant) -> dict:
    r = client.post(
        f"{API}/catalog/products",
        headers=s.h(),
        json={"title": "Kurta", "variants": [{"price_minor": 125000, **variant}]},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_qa003_listings_of_foreign_or_unknown_product_is_404(client, seller):
    other = onboard(client, f"other-{uuid.uuid4().hex[:6]}@example.com", shop="Other Shop")
    foreign = _product(client, other)
    r = client.get(f"{API}/catalog/products/{foreign['id']}/listings", headers=seller.h())
    assert r.status_code == 404
    r = client.get(f"{API}/catalog/products/{uuid.uuid4()}/listings", headers=seller.h())
    assert r.status_code == 404
    own = _product(client, seller)
    r = client.get(f"{API}/catalog/products/{own['id']}/listings", headers=seller.h())
    assert r.status_code == 200 and r.json() == {"items": []}


@pytest.mark.parametrize("bad", ["100", 12.5, True, "1e3"])
def test_qa004_money_fields_are_strict_integers(client, seller, bad):
    for field in ("price_minor", "cost_minor", "compare_at_minor"):
        body = {"title": "Strict", "variants": [{"price_minor": 1000, field: bad}]}
        r = client.post(f"{API}/catalog/products", headers=seller.h(), json=body)
        assert r.status_code == 400, (field, bad, r.text)
        assert r.json()["error"]["code"] == "validation_error"
    p = _product(client, seller)
    v = p["variants"][0]["id"]
    r = client.patch(
        f"{API}/catalog/products/{p['id']}/variants/{v}", headers=seller.h(), json={"price_minor": "999"}
    )
    assert r.status_code == 400


# --------------------------------------------------------------------------- QA-001 password reset
def _mail_after(before: set, email: str, marker: str) -> list:
    from app.core.config import REPO_ROOT

    box = REPO_ROOT / ".data" / "mailbox"
    return [
        p
        for p in box.glob("*.txt")
        if p not in before and f"To: {email}" in p.read_text() and marker in p.read_text()
    ]


def _mailbox() -> set:
    from app.core.config import REPO_ROOT

    box = REPO_ROOT / ".data" / "mailbox"
    return set(box.glob("*.txt")) if box.exists() else set()


def test_qa001_password_reset_end_to_end(client):
    import re

    import app.domains.handlers  # noqa: F401
    from app.domains.platform.outbox import dispatch_batch
    from tests.conftest import PASSWORD, register_and_login

    email = f"reset-{uuid.uuid4().hex[:6]}@example.com"
    s = register_and_login(client, email)
    before = _mailbox()
    # Unknown email: same 202, and no email is sent (no account enumeration).
    assert (
        client.post(f"{API}/auth/password/forgot", json={"email": "nobody-x@example.com"}).status_code == 202
    )
    assert client.post(f"{API}/auth/password/forgot", json={"email": email.upper()}).status_code == 202
    dispatch_batch()
    mails = _mail_after(before, email, "/reset-password?token=")
    assert len(mails) == 1, "exactly one reset email"
    assert not _mail_after(before, "nobody-x@example.com", "token=")
    token = re.search(r"token=([\w-]+)", mails[0].read_text()).group(1)

    # Weak password is refused and the token stays usable.
    r = client.post(f"{API}/auth/password/reset", json={"token": token, "password": "password1"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "weak_password"
    new_pw = "Bhaktapur-Square-2027"
    assert (
        client.post(f"{API}/auth/password/reset", json={"token": token, "password": new_pw}).status_code
        == 204
    )
    # Single use.
    r = client.post(f"{API}/auth/password/reset", json={"token": token, "password": new_pw + "x"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "reset_invalid"
    # Every existing session is revoked; the old password no longer works; the new one does.
    assert client.get(f"{API}/me", headers=s.h()).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": s.refresh}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": email, "password": new_pw}).status_code == 200
    dispatch_batch()
    assert _mail_after(before, email, "/login"), "security notice sent (en or ne)"


def test_qa001_new_reset_link_invalidates_older_ones_and_links_expire(client):
    import re
    from datetime import timedelta

    from sqlalchemy import update

    import app.domains.handlers  # noqa: F401
    from app.core.db import session_scope, utcnow
    from app.domains.accounts.models import PasswordResetToken
    from app.domains.platform.outbox import dispatch_batch
    from tests.conftest import register_and_login

    email = f"reset2-{uuid.uuid4().hex[:6]}@example.com"
    register_and_login(client, email)
    before = _mailbox()
    client.post(f"{API}/auth/password/forgot", json={"email": email})
    dispatch_batch()
    first = re.search(r"token=([\w-]+)", _mail_after(before, email, "token=")[0].read_text()).group(1)
    before2 = _mailbox()
    client.post(f"{API}/auth/password/forgot", json={"email": email})
    dispatch_batch()
    second = re.search(r"token=([\w-]+)", _mail_after(before2, email, "token=")[0].read_text()).group(1)
    r = client.post(f"{API}/auth/password/reset", json={"token": first, "password": "Pokhara-Lakeside-77"})
    assert r.status_code == 400, "older link must stop working once a new one is issued"
    with session_scope() as db:
        db.execute(update(PasswordResetToken).values(expires_at=utcnow() - timedelta(minutes=1)))
    r = client.post(f"{API}/auth/password/reset", json={"token": second, "password": "Pokhara-Lakeside-77"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "reset_invalid"


def test_qa001_reset_requests_are_rate_limited_per_email(client):
    email = f"rl-{uuid.uuid4().hex[:6]}@example.com"
    codes = [client.post(f"{API}/auth/password/forgot", json={"email": email}).status_code for _ in range(5)]
    assert codes[:3] == [202, 202, 202] and codes[-1] == 429


def test_qa010_login_is_rate_limited_per_ip_and_per_email(client):
    """Brute-force protection: per-IP (30/min default) and per-email (10/5 min) limits answer 429."""
    email = f"rl-login-{uuid.uuid4().hex[:6]}@example.com"
    codes = [
        client.post(f"{API}/auth/login", json={"email": email, "password": "Wrong-Password-1"}).status_code
        for _ in range(11)
    ]
    assert codes[:10].count(401) == 10 and codes[-1] == 429
    ip_codes = [
        client.post(
            f"{API}/auth/login",
            json={"email": f"x{i}-{uuid.uuid4().hex[:4]}@example.com", "password": "Nope-nope-1"},
        ).status_code
        for i in range(31)
    ]
    assert 429 in ip_codes


def test_qa011_totp_code_is_accepted_only_once(client):
    """RFC 6238 §5.2: a captured/observed code (or a replayed mfa_token + code) must not open a second session."""
    import time

    import pyotp

    from tests.conftest import PASSWORD, register_and_login

    email = f"totp-{uuid.uuid4().hex[:6]}@example.com"
    s = register_and_login(client, email)
    totp = pyotp.TOTP(client.post(f"{API}/auth/mfa/totp/setup", headers=s.h()).json()["secret"])
    prev, now = totp.at(time.time() - 30), totp.now()
    assert client.post(f"{API}/auth/mfa/totp/enable", headers=s.h(), json={"code": prev}).status_code == 200
    tok = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}).json()["mfa_token"]
    # The step used to enable MFA can't be reused to sign in.
    assert client.post(f"{API}/auth/mfa/verify", json={"mfa_token": tok, "code": prev}).status_code == 401
    assert client.post(f"{API}/auth/mfa/verify", json={"mfa_token": tok, "code": now}).status_code == 200
    # Replaying the same token and code is refused…
    assert client.post(f"{API}/auth/mfa/verify", json={"mfa_token": tok, "code": now}).status_code == 401
    # …and so is the same code with a fresh login.
    tok2 = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}).json()["mfa_token"]
    assert client.post(f"{API}/auth/mfa/verify", json={"mfa_token": tok2, "code": now}).status_code == 401


# --------------------------------------------------------------------------- QA-012 cross-tenant references
def test_qa012_no_request_body_can_reference_another_merchants_records(client):
    """Every body-level id must belong to the caller's merchant. Found: post.product_id accepted B's product."""
    from tests.test_channels import connect
    from tests.test_media import phone_photo, upload

    a = onboard(client, f"xa-{uuid.uuid4().hex[:6]}@example.com", shop="Shop A")
    b = onboard(client, f"xb-{uuid.uuid4().hex[:6]}@example.com", shop="Shop B")
    b_product = _product(client, b)
    b_variant = b_product["variants"][0]["id"]
    b_media = upload(client, b, phone_photo())["id"]
    b_conn = connect(client, b)["id"]
    b_cat = client.post(f"{API}/catalog/categories", headers=b.h(), json={"name": "B cat"}).json()["id"]
    a_product = _product(client, a)
    a_conn = connect(client, a)["id"]
    a_media = upload(client, a, phone_photo())["id"]

    attempts = [
        ("POST", "/content/posts", {"connection_id": a_conn, "caption": "x", "product_id": b_product["id"]}),
        ("POST", "/content/posts", {"connection_id": b_conn, "caption": "x"}),
        ("POST", "/content/posts", {"connection_id": a_conn, "caption": "x", "asset_ids": [b_media]}),
        ("POST", "/catalog/products", {"title": "x", "category_id": b_cat, "variants": [{"price_minor": 1}]}),
        ("PATCH", f"/catalog/products/{a_product['id']}", {"category_id": b_cat}),
        ("POST", "/catalog/categories", {"name": "child", "parent_id": b_cat}),
        ("PUT", f"/catalog/products/{a_product['id']}/media", {"items": [{"asset_id": b_media}]}),
        (
            "PUT",
            f"/catalog/products/{a_product['id']}/media",
            {"items": [{"asset_id": a_media, "variant_id": b_variant}]},
        ),
        ("POST", f"/catalog/products/{a_product['id']}/publish", {"connection_ids": [b_conn]}),
        (
            "POST",
            "/channels/connect",
            {
                "provider": "sandbox_channel",
                "redirect_uri": "http://localhost:3010/channels/callback",
                "reconnect_connection_id": b_conn,
            },
        ),
        ("POST", "/media/videos/auto-reels", {"asset_ids": [b_media]}),
        ("POST", "/media/videos/auto-reels", {"asset_ids": [a_media], "product_id": b_product["id"]}),
        ("POST", "/studio/jobs", {"asset_ids": [b_media]}),
    ]
    leaks = []
    for method, path, body in attempts:
        r = client.request(method, f"{API}{path}", headers=a.h(), json=body)
        if r.status_code < 400:
            leaks.append((method, path, list(body), r.status_code))
    assert leaks == [], leaks


# --------------------------------------------------------------------------- QA-013 / QA-015 concurrency
def _set_product_limit(merchant_id: str, limit: int) -> None:
    from app.core.db import session_scope
    from app.domains.billing.models import EntitlementOverride

    with session_scope() as db:
        db.add(
            EntitlementOverride(
                merchant_id=uuid.UUID(merchant_id),
                resource_code="products",
                period="lifetime",
                limit_value=limit,
                reason="qa concurrency test",
            )
        )


def _mid(client, s) -> str:
    return client.get(f"{API}/me", headers=s.h()).json()["memberships"][0]["merchant"]["id"]


def test_qa013_concurrent_same_title_products_never_500(client, seller):
    import concurrent.futures as cf

    def make(_):
        return client.post(
            f"{API}/catalog/products",
            headers=seller.h(),
            json={"title": "Race Kurta", "variants": [{"price_minor": 100}]},
        )

    with cf.ThreadPoolExecutor(8) as ex:
        rs = list(ex.map(make, range(8)))
    assert [r.status_code for r in rs] == [201] * 8, [r.text[:120] for r in rs if r.status_code != 201]
    assert len({r.json()["handle"] for r in rs}) == 8


def test_qa013_explicit_handle_collision_is_409(client, seller):
    import concurrent.futures as cf

    def make(_):
        return client.post(
            f"{API}/catalog/products",
            headers=seller.h(),
            json={"title": "Fixed", "handle": "fixed-handle", "variants": [{"price_minor": 100}]},
        ).status_code

    with cf.ThreadPoolExecutor(6) as ex:
        codes = list(ex.map(make, range(6)))
    assert codes.count(201) == 1 and codes.count(409) == 5, codes


def test_qa015_gauge_limit_holds_under_concurrency(client, seller):
    import concurrent.futures as cf

    _set_product_limit(_mid(client, seller), 3)

    def make(i):
        return client.post(
            f"{API}/catalog/products",
            headers=seller.h(),
            json={"title": f"P{i}", "variants": [{"price_minor": 100}]},
        ).status_code

    with cf.ThreadPoolExecutor(10) as ex:
        codes = list(ex.map(make, range(10)))
    assert codes.count(201) == 3, codes
    ent = client.get(f"{API}/billing/entitlements", headers=seller.h()).json()
    used = next(x for x in ent["limits"] if x["resource"] == "products")["used"]
    assert used == 3


def test_qa014_upload_must_match_declared_size(client, seller):
    from tests.test_media import phone_photo

    data = phone_photo()
    r = client.post(
        f"{API}/media/uploads",
        headers=seller.h(),
        json={"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 1000},
    )
    aid, up = r.json()["asset_id"], r.json()["upload"]
    assert client.put(up["url"], content=data, headers=up["headers"]).status_code == 200
    done = client.post(f"{API}/media/{aid}/complete", headers=seller.h())
    assert done.status_code == 400 and done.json()["error"]["code"] == "upload_size_mismatch"
    # The oversized object was discarded: completing again reports it missing, nothing was stored.
    again = client.post(f"{API}/media/{aid}/complete", headers=seller.h())
    assert again.status_code == 409 and again.json()["error"]["code"] == "upload_missing"


def test_qa016_database_outage_is_503_not_500():
    import psycopg
    from sqlalchemy.exc import IntegrityError, OperationalError

    from app.core.errors import is_db_unavailable

    try:
        psycopg.connect("postgresql://localhost:5499/nope", connect_timeout=2)
    except psycopg.OperationalError as e:
        refused = OperationalError("connect", {}, e)
    assert is_db_unavailable(refused)
    assert not is_db_unavailable(IntegrityError("insert", {}, Exception("dup")))
    assert not is_db_unavailable(ValueError("x"))
