"""Black-box adversarial API probe (QA). Runs against a live stack; never against production data.

    QA_API=http://localhost:8190 uv run python qa/probe.py [--only auth,tenancy,...]

Creates throwaway merchants/users with unique emails, then attacks the implemented surface:
auth/session/MFA, tenant isolation (guessed IDs, header spoofing, filters), RBAC per role, input
validation boundaries, idempotency, concurrency near quotas, media upload abuse, webhook auth,
admin gating, secret leakage. Prints PASS/FAIL per check and writes qa/last_probe.json.
Findings are triaged into docs/QA_TEST_REPORT.md; real bugs get pytest regression tests.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pyotp

API = os.environ.get("QA_API", "http://localhost:8190").rstrip("/")
V1 = f"{API}/api/v1"
MAILBOX = Path(__file__).resolve().parents[3] / ".data" / "mailbox"
PW = "Patan-Durbar-Qa-2026"
RUN = uuid.uuid4().hex[:8]
SECRET_PATTERNS = [
    re.compile(r"\$argon2|\$2[aby]\$"),  # password hashes
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}"),  # provider keys
    re.compile(r"refresh_token_hash|password_hash|secret_ciphertext|wrapped_dek", re.I),
    re.compile(r"Traceback \(most recent call last\)"),
]

results: list[dict[str, Any]] = []


class _Client(httpx.Client):
    """Waits out 429 rate limits (asserted separately in probe_platform) so other checks stay meaningful."""

    def request(self, *a: Any, **kw: Any) -> httpx.Response:  # type: ignore[override]
        for _ in range(8):
            r = super().request(*a, **kw)
            if r.status_code != 429 or kw.pop("_no_retry", False):
                return r
            wait = float(r.json().get("error", {}).get("details", {}).get("retry_after", 2))
            if wait > 10:
                return r  # a lockout, not a throttle: let the check see it
            time.sleep(wait + 0.2)
        return r


http = _Client(timeout=30)
raw = httpx.Client(timeout=30)  # no retry: used for the rate-limit assertion itself
VALIDATION = (400, 422)


def check(area: str, name: str, ok: bool, detail: Any = "") -> bool:
    results.append({"area": area, "check": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(f"{'PASS' if ok else 'FAIL'}  [{area}] {name}{'' if ok else '  → ' + str(detail)[:300]}")
    return bool(ok)


def no_secrets(area: str, where: str, text: str) -> None:
    hits = [p.pattern for p in SECRET_PATTERNS if p.search(text)]
    check(area, f"no secrets in {where}", not hits, hits)


@dataclass
class User:
    email: str
    token: str = ""
    refresh: str = ""
    session_id: str = ""
    merchant: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def h(self, merchant: str | None = "self", **kw: str) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}", **kw}
        mid = self.merchant if merchant == "self" else merchant
        if mid:
            h["X-Merchant-Id"] = mid
        return h


def register(prefix: str, name: str = "QA Seller") -> User:
    email = f"qa-{prefix}-{RUN}@example.com"
    r = http.post(f"{V1}/auth/register", json={"email": email, "password": PW, "full_name": name})
    assert r.status_code == 201, r.text
    return login(User(email))


def login(u: User) -> User:
    r = http.post(f"{V1}/auth/login", json={"email": u.email, "password": PW, "device_name": "qa"})
    assert r.status_code == 200, r.text
    b = r.json()
    u.token, u.refresh, u.session_id = (
        b.get("access_token", ""),
        b.get("refresh_token", ""),
        b.get("session_id", ""),
    )
    u.extra["login"] = b
    return u


def onboard(u: User, shop: str) -> User:
    r = http.post(
        f"{V1}/merchants",
        headers=u.h(None),
        json={
            "name": f"{shop} {RUN}",
            "currency": "NPR",
            "timezone": "Asia/Kathmandu",
            "default_locale": "en",
        },
    )
    assert r.status_code == 201, r.text
    u.merchant = r.json()["id"]
    return u


def product_body(title: str, price: int = 125000, **kw: Any) -> dict[str, Any]:
    return {"title": title, "variants": [{"price_minor": price, **kw}]}


def mail_token(email: str, kind: str = "token=") -> str | None:
    for _ in range(40):
        for f in sorted(MAILBOX.glob("*.txt"), reverse=True)[:400]:
            t = f.read_text()
            if f"To: {email}" in t and kind in t:
                m = re.search(r"token=([A-Za-z0-9_\-\.]+)", t)
                if m:
                    return m.group(1)
        time.sleep(0.5)
    return None


# ------------------------------------------------------------------------------------------ auth
def probe_auth() -> None:
    a = "auth"
    # validation
    for body, why in [
        ({}, "empty body"),
        ({"email": "not-an-email", "password": PW, "full_name": "x"}, "bad email"),
        ({"email": f"weak-{RUN}@example.com", "password": "password1", "full_name": "x"}, "common password"),
        ({"email": f"short-{RUN}@example.com", "password": "Ab1!", "full_name": "x"}, "short password"),
        ({"email": f"name-{RUN}@example.com", "password": PW, "full_name": "x" * 201}, "201-char name"),
        (
            {"email": f"phone-{RUN}@example.com", "password": PW, "full_name": "x", "phone": "abc"},
            "bad phone",
        ),
    ]:
        r = http.post(f"{V1}/auth/register", json=body)
        check(a, f"register rejects {why}", r.status_code in VALIDATION, (r.status_code, r.text[:200]))
        no_secrets(a, f"register error ({why})", r.text)
    u = register("auth")
    r = http.post(f"{V1}/auth/register", json={"email": u.email.upper(), "password": PW, "full_name": "Dup"})
    check(a, "duplicate email (case-insensitive) rejected", r.status_code == 409, r.status_code)
    no_secrets(a, "login response", json.dumps(u.extra["login"]))
    # wrong password vs unknown email: same status + code (no account enumeration)
    r1 = http.post(f"{V1}/auth/login", json={"email": u.email, "password": "Wrong-Password-123"})
    r2 = http.post(
        f"{V1}/auth/login", json={"email": f"nobody-{RUN}@example.com", "password": "Wrong-Password-123"}
    )
    check(
        a,
        "wrong password and unknown email are indistinguishable",
        r1.status_code == r2.status_code == 401 and r1.json()["error"]["code"] == r2.json()["error"]["code"],
        (r1.status_code, r1.text[:120], r2.status_code, r2.text[:120]),
    )
    # tampered / garbage tokens
    me = http.get(f"{V1}/me", headers={"Authorization": f"Bearer {u.token[:-4]}abcd"})
    check(a, "tampered access token rejected", me.status_code == 401, me.status_code)
    me = http.get(f"{V1}/me", headers={"Authorization": "Bearer x"})
    check(a, "garbage token rejected", me.status_code == 401, me.status_code)
    me = http.get(f"{V1}/me")
    check(a, "missing token rejected", me.status_code == 401, me.status_code)
    # refresh rotation + reuse detection
    r = http.post(f"{V1}/auth/refresh", json={"refresh_token": u.refresh})
    check(
        a, "refresh rotates", r.status_code == 200 and r.json()["refresh_token"] != u.refresh, r.status_code
    )
    new_access, new_refresh = r.json().get("access_token"), r.json().get("refresh_token")
    r = http.post(f"{V1}/auth/refresh", json={"refresh_token": u.refresh})
    check(a, "reused refresh token rejected", r.status_code == 401, (r.status_code, r.text[:120]))
    r = http.post(f"{V1}/auth/refresh", json={"refresh_token": new_refresh})
    check(a, "reuse revokes the whole token family", r.status_code == 401, (r.status_code, r.text[:120]))
    me = http.get(f"{V1}/me", headers={"Authorization": f"Bearer {new_access}"})
    check(a, "access token of a revoked family stops working", me.status_code == 401, me.status_code)
    # multi-session: revoke one session from another
    s1 = login(User(u.email))
    s2 = login(User(u.email))
    sess = http.get(f"{V1}/auth/sessions", headers=s1.h(None)).json()
    check(a, "sessions list shows current sessions", isinstance(sess, (list, dict)), sess)
    no_secrets(a, "sessions list", json.dumps(sess))
    r = http.delete(f"{V1}/auth/sessions/{s2.session_id}", headers=s1.h(None))
    check(a, "revoke another session", r.status_code in (200, 204), (r.status_code, r.text[:120]))
    me = http.get(f"{V1}/me", headers=s2.h(None))
    check(a, "revoked session's access token rejected immediately", me.status_code == 401, me.status_code)
    r = http.post(f"{V1}/auth/refresh", json={"refresh_token": s2.refresh})
    check(a, "revoked session cannot refresh", r.status_code == 401, r.status_code)
    # logout
    r = http.post(f"{V1}/auth/logout", headers=s1.h(None), json={"refresh_token": s1.refresh})
    check(a, "logout ok", r.status_code in (200, 204), (r.status_code, r.text[:120]))
    me = http.get(f"{V1}/me", headers=s1.h(None))
    check(a, "access token unusable after logout", me.status_code == 401, me.status_code)
    # cross-user session revoke
    other = register("auth2")
    r = http.delete(f"{V1}/auth/sessions/{other.session_id}", headers=login(User(u.email)).h(None))
    check(a, "cannot revoke another user's session", r.status_code == 404, r.status_code)
    me = http.get(f"{V1}/me", headers=other.h(None))
    check(a, "other user's session unaffected", me.status_code == 200, me.status_code)
    # MFA
    m = login(User(u.email))
    setup = http.post(f"{V1}/auth/mfa/totp/setup", headers=m.h(None))
    check(a, "MFA setup", setup.status_code == 200, setup.text[:160])
    secret = re.search(r"secret=([A-Z2-7]+)", setup.json().get("otpauth_uri", "")).group(1)  # type: ignore[union-attr]
    r = http.post(f"{V1}/auth/mfa/totp/enable", headers=m.h(None), json={"code": "000000"})
    check(a, "MFA enable rejects wrong code", r.status_code in (*VALIDATION, 401), r.status_code)
    # Enable with the previous step: each TOTP step is accepted once (QA-011), so login uses the current one.
    r = http.post(
        f"{V1}/auth/mfa/totp/enable",
        headers=m.h(None),
        json={"code": pyotp.TOTP(secret).at(time.time() - 30)},
    )
    check(a, "MFA enable with valid code", r.status_code == 200, r.text[:160])
    recovery = r.json().get("recovery_codes", [])
    no_secrets(a, "MFA enable response", r.text)
    r = http.post(f"{V1}/auth/login", json={"email": u.email, "password": PW})
    check(
        a,
        "login now requires MFA",
        r.json().get("mfa_required") is True and "access_token" not in r.json(),
        r.text[:160],
    )
    tok = r.json().get("mfa_token")
    r = http.post(f"{V1}/auth/mfa/verify", json={"mfa_token": tok, "code": "123456"})
    check(a, "MFA verify rejects wrong code", r.status_code == 401, r.status_code)
    r = http.post(f"{V1}/auth/mfa/verify", json={"mfa_token": tok, "code": pyotp.TOTP(secret).now()})
    check(
        a, "MFA verify accepts valid code", r.status_code == 200 and "access_token" in r.json(), r.text[:160]
    )
    r = http.post(f"{V1}/auth/mfa/verify", json={"mfa_token": tok, "code": pyotp.TOTP(secret).now()})
    check(a, "MFA token is single-use", r.status_code == 401, r.status_code)
    if recovery:
        t2 = http.post(f"{V1}/auth/login", json={"email": u.email, "password": PW}).json()["mfa_token"]
        r = http.post(f"{V1}/auth/mfa/verify", json={"mfa_token": t2, "code": recovery[0]})
        check(a, "recovery code works once", r.status_code == 200, r.status_code)
        t3 = http.post(f"{V1}/auth/login", json={"email": u.email, "password": PW}).json()["mfa_token"]
        r = http.post(f"{V1}/auth/mfa/verify", json={"mfa_token": t3, "code": recovery[0]})
        check(a, "used recovery code rejected", r.status_code == 401, r.status_code)
    # email verification
    r = http.post(f"{V1}/auth/verify-email/confirm", json={"token": "x" * 40})
    check(a, "invalid verification token rejected", r.status_code in (400, 401, 404, 422), r.status_code)
    # brute force: lockout after repeated failures (login_max_failures)
    victim = register("lock")
    codes = [
        raw.post(f"{V1}/auth/login", json={"email": victim.email, "password": "Nope-Nope-123"}).status_code
        for _ in range(12)
    ]
    r = raw.post(f"{V1}/auth/login", json={"email": victim.email, "password": PW})
    check(
        a,
        "account locks after repeated failures (even with right password)",
        r.status_code in (401, 423, 429),
        (codes[-3:], r.status_code),
    )


# ------------------------------------------------------------------------------------------ tenancy
CALLBACK = os.environ.get("QA_WEB", "http://localhost:3110") + "/channels/callback"


def connect_sandbox(u: User) -> str:
    from urllib.parse import parse_qs, urlparse

    r = http.post(
        f"{V1}/channels/connect",
        headers=u.h(),
        json={"provider": "sandbox_channel", "redirect_uri": CALLBACK},
    )
    assert r.status_code == 200, r.text
    consent = http.get(r.json()["authorize_url"], follow_redirects=False)
    q = parse_qs(urlparse(consent.headers["location"]).query)
    cb = http.post(
        f"{V1}/channels/oauth/callback",
        headers=u.h(),
        json={"provider": "sandbox_channel", "state": q["state"][0], "code": q["code"][0]},
    )
    assert cb.status_code == 201, cb.text
    return cb.json()["id"]


def seed_merchant(u: User) -> dict[str, str]:
    ids: dict[str, str] = {}
    ids["connection"] = connect_sandbox(u)
    r = http.post(
        f"{V1}/catalog/products",
        headers=u.h(),
        json=product_body(f"Kurta {RUN}", sku=f"K-{uuid.uuid4().hex[:6]}"),
    )
    ids["product"] = r.json()["id"]
    ids["variant"] = r.json()["variants"][0]["id"]
    ids["category"] = http.post(
        f"{V1}/catalog/categories", headers=u.h(), json={"name": f"Cat {RUN}"}
    ).json()["id"]
    ids["collection"] = (
        http.post(f"{V1}/catalog/collections", headers=u.h(), json={"title": f"Col {RUN}"})
        .json()
        .get("id", "")
    )
    up = http.post(
        f"{V1}/media/uploads",
        headers=u.h(),
        json={"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 1000},
    )
    ids["media"] = up.json().get("asset_id") or up.json().get("id", "")
    ids["post"] = (
        http.post(
            f"{V1}/content/posts",
            headers=u.h(),
            json={"connection_id": ids["connection"], "caption": "hello", "product_id": ids["product"]},
        )
        .json()
        .get("id", "")
    )
    inv = http.post(
        f"{V1}/invitations",
        headers=u.h(),
        json={"email": f"inv-{uuid.uuid4().hex[:6]}@example.com", "role": "staff"},
    )
    ids["invitation"] = inv.json().get("id", "")
    ids["store"] = http.get(f"{V1}/stores", headers=u.h()).json()["items"][0]["id"]
    mem = http.get(f"{V1}/members", headers=u.h()).json()
    items = mem.get("items", mem) if isinstance(mem, dict) else mem
    ids["membership"] = items[0]["id"] if items else ""
    return ids


def probe_tenancy() -> None:
    a = "tenancy"
    ma, mb = onboard(register("ta"), "Shop A"), onboard(register("tb"), "Shop B")
    bid = seed_merchant(mb)
    seed_merchant(ma)
    check(a, "seeded merchant mb resources", all(bid.values()), bid)
    attempts = [
        ("GET", f"/catalog/products/{bid['product']}", None),
        ("PATCH", f"/catalog/products/{bid['product']}", {"title": "pwned"}),
        ("POST", f"/catalog/products/{bid['product']}/status", {"status": "archived"}),
        ("PATCH", f"/catalog/products/{bid['product']}/variants/{bid['variant']}", {"price_minor": 1}),
        ("DELETE", f"/catalog/products/{bid['product']}/variants/{bid['variant']}", None),
        ("POST", f"/catalog/products/{bid['product']}/variants", {"price_minor": 1, "options": {}}),
        ("PUT", f"/catalog/products/{bid['product']}/media", {"items": []}),
        ("DELETE", f"/catalog/products/{bid['product']}/listings/{bid['connection']}", None),
        ("POST", f"/channels/{bid['connection']}/health", None),
        ("DELETE", f"/channels/{bid['connection']}", None),
        ("POST", f"/content/posts/{bid['post']}/schedule", {"scheduled_at": "2030-01-01T10:00:00Z"}),
        ("GET", f"/catalog/products/{bid['product']}/listings", None),
        ("POST", f"/catalog/products/{bid['product']}/publish", {"connection_ids": [str(uuid.uuid4())]}),
        ("PATCH", f"/catalog/categories/{bid['category']}", {"name": "pwned"}),
        ("DELETE", f"/catalog/categories/{bid['category']}", None),
        ("GET", f"/catalog/collections/{bid['collection']}/products", None),
        ("PUT", f"/catalog/collections/{bid['collection']}/products/{bid['product']}", None),
        ("GET", f"/media/{bid['media']}", None),
        ("DELETE", f"/media/{bid['media']}", None),
        ("POST", f"/media/{bid['media']}/complete", None),
        ("GET", f"/content/posts/{bid['post']}", None),
        ("PATCH", f"/content/posts/{bid['post']}", {"caption": "pwned"}),
        ("POST", f"/content/posts/{bid['post']}/approve", None),
        ("POST", f"/content/posts/{bid['post']}/cancel", None),
        ("DELETE", f"/invitations/{bid['invitation']}", None),
        ("PATCH", f"/members/{bid['membership']}", {"role": "viewer"}),
        ("DELETE", f"/members/{bid['membership']}", None),
        ("PATCH", f"/stores/{bid['store']}", {"name": "pwned"}),
    ]
    for method, path, body in attempts:
        r = http.request(method, f"{V1}{path}", headers=ma.h(), json=body)
        check(
            a,
            f"ma cannot {method} mb's {path.split('/')[1]}{'/' + path.split('/')[3] if path.count('/') > 2 else ''}",
            r.status_code in (404,),
            (method, path, r.status_code, r.text[:120]),
        )
    # header spoofing: ma's token with mb's merchant id
    for path in [
        "/catalog/products",
        "/merchant",
        "/members",
        "/billing/subscription",
        "/audit-logs",
        "/media",
        "/content/posts",
        "/channels",
        "/ai/credentials",
        "/exceptions",
    ]:
        r = http.get(f"{V1}{path}", headers=ma.h(mb.merchant))
        check(
            a,
            f"ma's token + mb's X-Merchant-Id denied on {path}",
            r.status_code in (403, 404),
            (r.status_code, r.text[:100]),
        )
    # lists never include mb's records; filters can't reach them
    lst = http.get(f"{V1}/catalog/products", headers=ma.h()).text
    check(a, "ma's product list excludes mb", bid["product"] not in lst)
    r = http.get(f"{V1}/content/posts", headers=ma.h(), params={"product_id": bid["product"]})
    check(
        a,
        "filter by mb's product id returns nothing",
        r.status_code in (200, 404, *VALIDATION) and bid["post"] not in r.text,
        (r.status_code, r.text[:120]),
    )
    # cross-tenant references inside ma's own requests
    a_conn = connect_sandbox(ma)
    r = http.post(
        f"{V1}/content/posts",
        headers=ma.h(),
        json={"connection_id": a_conn, "caption": "x", "product_id": bid["product"]},
    )
    check(
        a,
        "ma cannot attach mb's product to its post",
        r.status_code in (404, *VALIDATION),
        (r.status_code, r.text[:120]),
    )
    r = http.post(
        f"{V1}/content/posts", headers=ma.h(), json={"connection_id": bid["connection"], "caption": "x"}
    )
    check(
        a,
        "ma cannot post through mb's channel connection",
        r.status_code in (404, *VALIDATION),
        (r.status_code, r.text[:120]),
    )
    r = http.post(
        f"{V1}/content/posts",
        headers=ma.h(),
        json={"connection_id": a_conn, "caption": "x", "asset_ids": [bid["media"]]},
    )
    check(
        a,
        "ma cannot attach mb's media to its post (same answer as a missing photo)",
        r.status_code in (404, 409, *VALIDATION),
        (r.status_code, r.text[:120]),
    )
    r = http.post(f"{V1}/studio/jobs", headers=ma.h(), json={"asset_ids": [bid["media"]], "locale": "en"})
    check(
        a,
        "ma cannot start a Studio job on mb's media",
        r.status_code in (404, *VALIDATION),
        (r.status_code, r.text[:120]),
    )
    r = http.post(f"{V1}/media/videos/auto-reels", headers=ma.h(), json={"asset_ids": [bid["media"]]})
    check(
        a,
        "ma cannot make a reel from mb's media",
        r.status_code in (404, 409, *VALIDATION),
        (r.status_code, r.text[:120]),
    )
    r = http.post(
        f"{V1}/catalog/products", headers=ma.h(), json={**product_body("x"), "category_id": bid["category"]}
    )
    check(
        a, "ma cannot use mb's category", r.status_code in (404, *VALIDATION), (r.status_code, r.text[:120])
    )
    r = http.put(
        f"{V1}/catalog/collections/{bid['collection']}/products",
        headers=ma.h(),
        json={"product_ids": [bid["product"]]},
    )
    check(a, "ma cannot bulk-set mb's collection", r.status_code == 404, r.status_code)
    # mb's data is intact
    p = http.get(f"{V1}/catalog/products/{bid['product']}", headers=mb.h()).json()
    check(
        a,
        "mb's product unchanged after attacks",
        p.get("title", "").startswith("Kurta") and p.get("status") != "archived",
        p.get("title"),
    )


# ------------------------------------------------------------------------------------------ rbac
def accept_invite(owner: User, role: str) -> User:
    email = f"qa-{role}-{uuid.uuid4().hex[:6]}@example.com"
    r = http.post(f"{V1}/invitations", headers=owner.h(), json={"email": email, "role": role})
    assert r.status_code == 201, r.text
    member = register_email(email)
    token = mail_token(email, "/invite?token=")
    assert token, f"no invite email for {email}"
    r = http.post(f"{V1}/invitations/accept", headers=member.h(None), json={"token": token})
    assert r.status_code in (200, 201), r.text
    member.merchant = owner.merchant
    return member


def register_email(email: str) -> User:
    r = http.post(f"{V1}/auth/register", json={"email": email, "password": PW, "full_name": "QA Member"})
    assert r.status_code == 201, r.text
    return login(User(email))


def probe_rbac() -> None:
    a = "rbac"
    # The trial plan has 2 seats (owner + 1), so each role gets its own merchant.
    roles: dict[str, User] = {}
    owners: dict[str, User] = {}
    for role in ["admin", "manager", "staff", "viewer"]:
        owners[role] = onboard(register(f"rbac-owner-{role}"), f"RBAC {role}")
        try:
            roles[role] = accept_invite(owners[role], role)
        except AssertionError as e:
            check(a, f"invite+accept {role}", False, e)
    if not roles:
        return
    pids = {
        role: http.post(f"{V1}/catalog/products", headers=o.h(), json=product_body(f"R {RUN}")).json()["id"]
        for role, o in owners.items()
    }
    # (method, path, body, permission) — expectation derived from /permissions/me for each role
    ops = [
        ("POST", "/catalog/products", product_body("rbac"), "catalog.write"),
        ("POST", "/catalog/products/{pid}/status", {"status": "active"}, "catalog.publish"),
        ("POST", "/catalog/categories", {"name": f"c{uuid.uuid4().hex[:4]}"}, "catalog.write"),
        (
            "POST",
            "/invitations",
            {"email": f"x{uuid.uuid4().hex[:6]}@example.com", "role": "viewer"},
            "team.manage",
        ),
        ("PATCH", "/merchant", {"automation_mode": "assisted"}, "merchant.update"),
        ("GET", "/audit-logs", None, "audit.read"),
        ("GET", "/billing/subscription", None, "billing.read"),
        ("GET", "/ai/credentials", None, "ai.credentials.manage"),
        (
            "POST",
            "/channels/connect",
            {"provider": "sandbox_channel", "redirect_uri": "http://localhost:3110/channels/callback"},
            "channels.manage",
        ),
        (
            "POST",
            "/media/uploads",
            {"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 1000},
            "media.write",
        ),
        ("POST", "/content/posts", {"caption": "rbac"}, "content.write"),
        ("POST", "/catalog/imports", None, "catalog.write"),
    ]
    for role, u in roles.items():
        perms = set(http.get(f"{V1}/permissions/me", headers=u.h()).json().get("permissions", []))
        for method, path, body, perm in ops:
            path = path.replace("{pid}", pids[role])
            r = http.request(method, f"{V1}{path}", headers=u.h(), json=body)
            allowed = perm in perms
            denied = r.status_code == 403
            # Allowed ops may still fail validation (e.g. imports without a file), but never with 403.
            ok = (not denied) if allowed else denied
            check(
                a,
                f"{role} {'can' if allowed else 'cannot'} {method} {path.split('?')[0][:40]} ({perm})",
                ok,
                (r.status_code, r.text[:100]),
            )
    # privilege escalation: manager cannot grant admin; staff cannot invite; nobody can make an owner except owner
    if "manager" in roles:
        r = http.post(
            f"{V1}/invitations",
            headers=roles["manager"].h(),
            json={"email": f"esc{uuid.uuid4().hex[:6]}@example.com", "role": "admin"},
        )
        check(a, "manager cannot invite an admin", r.status_code == 403, r.status_code)
        mem = http.get(f"{V1}/members", headers=owners["manager"].h()).json()
        items = mem.get("items", mem) if isinstance(mem, dict) else mem
        self_m = next(
            (
                m
                for m in items
                if m.get("user", {}).get("email") == roles["manager"].email
                or m.get("email") == roles["manager"].email
            ),
            None,
        )
        if self_m:
            r = http.patch(
                f"{V1}/members/{self_m['id']}", headers=roles["manager"].h(), json={"role": "owner"}
            )
            check(a, "manager cannot promote self to owner", r.status_code in (403, 422), r.status_code)
    if "admin" in roles:
        mem = http.get(f"{V1}/members", headers=owners["admin"].h()).json()
        items = mem.get("items", mem) if isinstance(mem, dict) else mem
        own = next((m for m in items if m.get("role") == "owner"), None)
        if own:
            r = http.delete(f"{V1}/members/{own['id']}", headers=roles["admin"].h())
            check(a, "admin cannot remove the owner", r.status_code in (403, 409, 422), r.status_code)
    # removed member loses access immediately
    if "staff" in roles:
        mem = http.get(f"{V1}/members", headers=owners["staff"].h()).json()
        items = mem.get("items", mem) if isinstance(mem, dict) else mem
        st = next((m for m in items if m.get("role") == "staff"), None)
        if st:
            http.delete(f"{V1}/members/{st['id']}", headers=owners["staff"].h())
            r = http.get(f"{V1}/catalog/products", headers=roles["staff"].h())
            check(a, "removed member loses access at once", r.status_code in (403, 404), r.status_code)


# ------------------------------------------------------------------------------------------ catalog
def probe_catalog() -> None:
    a = "catalog"
    u = onboard(register("cat"), "Catalog Shop")
    bad = [
        (product_body("neg", price=-1), "negative price"),
        (product_body("huge", price=10_000_000_001), "price above limit"),
        ({"title": "", "variants": [{"price_minor": 100}]}, "empty title"),
        ({"title": "x" * 256, "variants": [{"price_minor": 100}]}, "256-char title"),
        ({"title": "no variants", "variants": []}, "no variants"),
        ({"title": "float", "variants": [{"price_minor": 12.5}]}, "fractional minor units"),
        ({"title": "str", "variants": [{"price_minor": "100"}]}, "price as string"),
        (product_body("cost", cost_minor=-5), "negative cost"),
        (
            {
                "title": "opts",
                "options": [{"name": "Size", "values": ["M"]}] * 4,
                "variants": [{"price_minor": 1}],
            },
            "4 options",
        ),
        (
            {
                "title": "many",
                "variants": [{"price_minor": 1, "options": {"Size": str(i)}} for i in range(101)],
            },
            "101 variants",
        ),
    ]
    for body, why in bad:
        r = http.post(f"{V1}/catalog/products", headers=u.h(), json=body)
        check(a, f"rejects {why}", r.status_code in VALIDATION, (r.status_code, r.text[:150]))
        no_secrets(a, f"error body ({why})", r.text)
    sku = f"SKU-{RUN}"
    r1 = http.post(f"{V1}/catalog/products", headers=u.h(), json=product_body("a", sku=sku))
    r2 = http.post(f"{V1}/catalog/products", headers=u.h(), json=product_body("b", sku=sku.lower()))
    check(
        a,
        "duplicate SKU rejected (case-insensitive)",
        r1.status_code == 201 and r2.status_code == 409,
        (r1.status_code, r2.status_code, r2.text[:120]),
    )
    # concurrent duplicate SKU creation: exactly one wins
    sku2 = f"RACE-{RUN}"
    with cf.ThreadPoolExecutor(8) as ex:
        codes = list(
            ex.map(
                lambda _: (
                    http.post(
                        f"{V1}/catalog/products", headers=u.h(), json=product_body("race", sku=sku2)
                    ).status_code
                ),
                range(8),
            )
        )
    check(
        a,
        "concurrent duplicate SKU: exactly one created",
        codes.count(201) == 1 and all(c in (201, 409) for c in codes),
        codes,
    )
    # realistic: 2 options x 3 values (shirt), shoes 7 sizes x 2 colours, single SKU
    shirt = {
        "title": f"Shirt {RUN}",
        "options": [
            {"name": "Size", "values": ["S", "M", "L"]},
            {"name": "Colour", "values": ["Black", "Maroon"]},
        ],
        "variants": [
            {"price_minor": 150000, "options": {"Size": s, "Colour": c}}
            for s in ["S", "M", "L"]
            for c in ["Black", "Maroon"]
        ],
    }
    r = http.post(f"{V1}/catalog/products", headers=u.h(), json=shirt)
    check(
        a,
        "shirt 3x2 variants created with unique auto SKUs",
        r.status_code == 201 and len({v["sku"] for v in r.json()["variants"]}) == 6,
        (r.status_code, r.text[:150]),
    )
    dup_combo = {**shirt, "title": "dup combo", "variants": shirt["variants"] + [shirt["variants"][0]]}
    r = http.post(f"{V1}/catalog/products", headers=u.h(), json=dup_combo)
    check(
        a, "duplicate option combination rejected", r.status_code in VALIDATION, (r.status_code, r.text[:150])
    )
    shoes = {
        "title": f"Shoes {RUN}",
        "options": [
            {"name": "Size", "values": [str(s) for s in range(38, 45)]},
            {"name": "Colour", "values": ["White", "Black"]},
        ],
        "variants": [
            {"price_minor": 450000, "options": {"Size": str(s), "Colour": c}}
            for s in range(38, 45)
            for c in ["White", "Black"]
        ],
    }
    r = http.post(f"{V1}/catalog/products", headers=u.h(), json=shoes)
    check(
        a,
        "shoes 7x2 variants created",
        r.status_code == 201 and len(r.json()["variants"]) == 14,
        (r.status_code, r.text[:120]),
    )
    single = http.post(f"{V1}/catalog/products", headers=u.h(), json=product_body(f"Single {RUN}"))
    pid = single.json()["id"]
    # status transitions
    r = http.post(f"{V1}/catalog/products/{pid}/status", headers=u.h(), json={"status": "nonsense"})
    check(a, "invalid status rejected", r.status_code in VALIDATION, r.status_code)
    http.post(f"{V1}/catalog/products/{pid}/status", headers=u.h(), json={"status": "archived"})
    r = http.patch(f"{V1}/catalog/products/{pid}", headers=u.h(), json={"title": "edit archived"})
    check(
        a,
        "archived product edit is blocked or explicit",
        r.status_code in (200, 409, 422),
        (r.status_code, r.text[:120]),
    )
    # optimistic locking
    p = http.get(f"{V1}/catalog/products/{single.json()['id']}", headers=u.h()).json()
    ver = p.get("version")
    if ver is not None:
        r1 = http.patch(f"{V1}/catalog/products/{pid}", headers=u.h(), json={"title": "v1", "version": ver})
        r2 = http.patch(f"{V1}/catalog/products/{pid}", headers=u.h(), json={"title": "v2", "version": ver})
        check(
            a, "stale version write rejected (409)", r2.status_code == 409, (r1.status_code, r2.status_code)
        )
    # malformed CSV import
    files = {"file": ("bad.csv", b"\xff\xfe\x00garbage,,,\n\n", "text/csv")}
    r = http.post(f"{V1}/catalog/imports", headers=u.h(), files=files)
    check(a, "malformed CSV import handled without 500", r.status_code < 500, (r.status_code, r.text[:150]))
    files = {"file": ("big.csv", b"title,price\n" + b"x,1\n" * 200_000, "text/csv")}
    r = http.post(f"{V1}/catalog/imports", headers=u.h(), files=files)
    check(a, "oversized CSV import handled without 500", r.status_code < 500, (r.status_code, r.text[:150]))
    # pagination bounds
    for q in ["limit=0", "limit=100000", "limit=-1", "cursor=garbage"]:
        r = http.get(f"{V1}/catalog/products?{q}", headers=u.h())
        check(a, f"list with {q} handled", r.status_code in (200, *VALIDATION), (r.status_code, r.text[:100]))


# ------------------------------------------------------------------------------------------ media
def probe_media() -> None:
    a = "media"
    u = onboard(register("media"), "Media Shop")
    for body, why in [
        ({"file_name": "a.exe", "content_type": "application/x-msdownload", "size_bytes": 100}, "executable"),
        ({"file_name": "a.svg", "content_type": "image/svg+xml", "size_bytes": 100}, "svg (script risk)"),
        ({"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 200 * 1024 * 1024}, "200 MB"),
        ({"file_name": "a.jpg", "content_type": "image/jpeg", "size_bytes": 0}, "0 bytes"),
        (
            {"file_name": "../../etc/passwd", "content_type": "image/jpeg", "size_bytes": 100},
            "path traversal name",
        ),
    ]:
        r = http.post(f"{V1}/media/uploads", headers=u.h(), json=body)
        ok = r.status_code in (*VALIDATION, 413) or (
            why == "path traversal name" and r.status_code == 201 and "../" not in r.text
        )
        check(a, f"upload slot rejects/neutralises {why}", ok, (r.status_code, r.text[:150]))
    # declared size mismatch + corrupted bytes
    r = http.post(
        f"{V1}/media/uploads",
        headers=u.h(),
        json={"file_name": "x.jpg", "content_type": "image/jpeg", "size_bytes": 1000},
    )
    up = r.json()
    url = up.get("upload_url") or up.get("upload", {}).get("url")
    aid = up.get("asset_id") or up.get("id")
    if url:
        hdrs = up.get("headers") or up.get("upload", {}).get("headers") or {"Content-Type": "image/jpeg"}
        rr = http.put(url, content=b"not really a jpeg" * 200, headers=hdrs)
        rc0 = http.post(f"{V1}/media/{aid}/complete", headers=u.h())
        check(
            a,
            "upload larger than declared is refused at PUT or complete",
            rr.status_code in (400, 403, 413)
            or rc0.json().get("error", {}).get("code") == "upload_size_mismatch",
            (rr.status_code, rc0.status_code, rc0.text[:120]),
        )
        rr = http.put(url, content=b"\x00" * 1000, headers=hdrs)
        rc = http.post(f"{V1}/media/{aid}/complete", headers=u.h())
        st = None
        for _ in range(30):
            st = http.get(f"{V1}/media/{aid}", headers=u.h()).json().get("status")
            if st in ("rejected", "ready"):
                break
            time.sleep(0.5)
        check(
            a,
            "corrupted image ends rejected, not ready",
            st == "rejected",
            (rr.status_code, rc.status_code, st),
        )
        tampered = re.sub(r"(sig(nature)?=)[^&]+", r"\1AAAA", url)
        if tampered != url:
            rr = http.put(tampered, content=b"\x00" * 1000, headers=hdrs)
            check(a, "tampered signed URL rejected", rr.status_code in (401, 403), rr.status_code)
    r = http.post(f"{V1}/media/{uuid.uuid4()}/complete", headers=u.h())
    check(a, "complete on unknown asset → 404", r.status_code == 404, r.status_code)
    r = http.get(f"{V1}/media/{aid}", headers=u.h())
    no_secrets(a, "media detail", r.text)


# ------------------------------------------------------------------------------------------ quotas
def probe_quota() -> None:
    a = "quota"
    u = onboard(register("quota"), "Quota Shop")
    ent = http.get(f"{V1}/billing/entitlements", headers=u.h()).json()
    lim = next(
        (x for x in ent.get("limits", []) if x.get("resource") in ("products", "catalog.products")), None
    )
    check(
        a,
        "product limit present in entitlements",
        lim is not None,
        [x.get("resource") for x in ent.get("limits", [])],
    )
    if not lim or not lim.get("limit"):
        return
    limit = int(lim["limit"])
    used = int(lim.get("used") or 0)
    # fill to limit-3, then fire 10 concurrently: exactly 3 may succeed
    for i in range(limit - used - 3):
        http.post(f"{V1}/catalog/products", headers=u.h(), json=product_body(f"fill {i}"))
    with cf.ThreadPoolExecutor(10) as ex:
        codes = list(
            ex.map(
                lambda i: (
                    http.post(
                        f"{V1}/catalog/products", headers=u.h(), json=product_body(f"race {i}")
                    ).status_code
                ),
                range(10),
            )
        )
    ok = codes.count(201) == 3 and all(c in (201, 402, 403, 409, 429) for c in codes)
    check(a, f"concurrent creates at the product limit ({limit}): exactly 3 succeed", ok, codes)
    after = next(
        x
        for x in http.get(f"{V1}/billing/entitlements", headers=u.h()).json()["limits"]
        if x["resource"] == lim["resource"]
    )
    check(a, "usage never exceeds the limit", int(after.get("used") or 0) <= limit, after)
    r = http.post(f"{V1}/catalog/products", headers=u.h(), json=product_body("over"))
    check(
        a,
        "over-limit error is the structured limit code",
        r.status_code in (402, 403, 409, 429) and "limit" in r.text.lower(),
        (r.status_code, r.text[:160]),
    )


# ------------------------------------------------------------------------------------------ idempotency
def probe_idempotency() -> None:
    a = "idempotency"
    u = register("idem")
    key = f"idem-{RUN}"
    body = {
        "name": f"Idem Shop {RUN}",
        "currency": "NPR",
        "timezone": "Asia/Kathmandu",
        "default_locale": "en",
    }
    with cf.ThreadPoolExecutor(6) as ex:
        rs = list(
            ex.map(
                lambda _: http.post(
                    f"{V1}/merchants", headers=u.h(None, **{"Idempotency-Key": key}), json=body
                ),
                range(6),
            )
        )
    codes = [r.status_code for r in rs]
    ids = {r.json().get("id") for r in rs if r.status_code == 201}
    check(
        a,
        "concurrent identical merchant creates → one merchant",
        len(ids) == 1 and all(c in (201, 409) for c in codes),
        (codes, ids),
    )
    r = http.post(
        f"{V1}/merchants", headers=u.h(None, **{"Idempotency-Key": key}), json={**body, "name": "different"}
    )
    check(a, "same key, different body → conflict", r.status_code in (409, 422), r.status_code)


# ------------------------------------------------------------------------------------------ admin / platform
def probe_platform() -> None:
    a = "platform"
    u = onboard(register("plat"), "Plat Shop")
    for path in [
        "/admin/merchants",
        "/admin/outbox",
        "/admin/feature-flags",
        "/admin/ai/providers",
        "/admin/webhooks",
    ]:
        r = http.get(f"{V1}{path}", headers=u.h(None))
        check(a, f"non-staff gets 404 on {path}", r.status_code == 404, r.status_code)
    r = http.post(
        f"{API}/webhooks/sandbox_channel", content=b'{"x":1}', headers={"Content-Type": "application/json"}
    )
    check(
        a, "unsigned webhook rejected", r.status_code in (400, 401, 403, 404), (r.status_code, r.text[:120])
    )
    r = http.post(
        f"{API}/webhooks/sandbox_channel",
        content=b"x" * (2 * 1024 * 1024),
        headers={"Content-Type": "application/json"},
    )
    check(a, "oversized webhook rejected", r.status_code in (400, 401, 403, 404, 413), r.status_code)
    r = http.post(
        f"{V1}/catalog/products", headers={**u.h(), "Content-Type": "application/json"}, content=b"{bad json"
    )
    check(
        a,
        "malformed JSON → validation envelope, no stack trace",
        r.status_code in VALIDATION and "Traceback" not in r.text and "error" in r.json(),
        (r.status_code, r.text[:160]),
    )
    r = http.get(f"{API}/metrics")
    no_secrets(a, "/metrics", r.text)
    r = http.options(
        f"{V1}/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    check(
        a,
        "CORS refuses unknown origin",
        r.headers.get("access-control-allow-origin") not in ("*", "https://evil.example"),
        dict(r.headers),
    )
    r = http.get(f"{V1}/me", headers=u.h(None))
    for h in ["x-content-type-options", "x-request-id"]:
        check(a, f"response header {h}", h in {k.lower() for k in r.headers}, dict(r.headers))
    # login rate limit
    if os.environ.get("QA_LOGIN_LIMIT_RAISED"):
        check(a, "login rate limit (skipped: limit raised for this QA stack; covered by backend tests)", True)
    else:
        codes = [
            raw.post(
                f"{V1}/auth/login", json={"email": f"rl-{i}-{RUN}@example.com", "password": "x" * 12}
            ).status_code
            for i in range(40)
        ]
        check(a, "login is rate limited per client", 429 in codes, codes[-5:])


AREAS = {
    "auth": probe_auth,
    "tenancy": probe_tenancy,
    "rbac": probe_rbac,
    "catalog": probe_catalog,
    "media": probe_media,
    "quota": probe_quota,
    "idempotency": probe_idempotency,
    "platform": probe_platform,
}

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=",".join(AREAS))
    args = ap.parse_args()
    assert http.get(f"{API}/readyz").status_code == 200, f"API not ready at {API}"
    for name in args.only.split(","):
        try:
            AREAS[name]()
        except Exception as e:  # a crash in one area is itself a finding; keep going
            check(name, "probe area completed without crashing", False, repr(e))
    fails = [r for r in results if not r["ok"]]
    out = Path(__file__).with_name("last_probe.json")
    out.write_text(
        json.dumps(
            {"run": RUN, "api": API, "total": len(results), "failed": len(fails), "results": results},
            indent=1,
        )
    )
    print(f"\n{len(results) - len(fails)}/{len(results)} passed · {len(fails)} failed · {out}")
