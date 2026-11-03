"""Nivaro Console API (ADM-*): staff + MFA only, every write audited, nothing secret returned."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import update

from app.core.db import session_scope, utcnow
from app.domains.accounts.models import AuthSession
from app.domains.accounts.service import find_user_by_email
from tests.conftest import onboard, register_and_login
from tests.test_channels import connect

API = "/api/v1"


def make_staff(s, mfa: bool = True):
    with session_scope() as db:
        u = find_user_by_email(db, s.email)
        u.is_platform_staff = True
        if mfa:
            db.execute(update(AuthSession).where(AuthSession.user_id == u.id).values(amr="pwd+mfa"))
    return s


def test_me_reports_staff_and_session_mfa(client):
    s = register_and_login(client, "ops@nivaro.example")
    me = client.get(f"{API}/me", headers=s.h()).json()
    assert me["user"]["is_platform_staff"] is False and me["session"] == {"mfa": False}
    make_staff(s)
    me = client.get(f"{API}/me", headers=s.h()).json()
    assert me["user"]["is_platform_staff"] is True and me["session"] == {"mfa": True}


def test_merchant_detail_has_team_channels_usage_and_no_secrets(client, seller):
    connect(client, seller)
    staff = make_staff(register_and_login(client, "ops@nivaro.example"))
    found = client.get(f"{API}/admin/merchants", params={"q": "thamel"}, headers=staff.h()).json()["items"]
    assert [m["id"] for m in found] == [seller.merchant_id]
    d = client.get(f"{API}/admin/merchants/{seller.merchant_id}", headers=staff.h()).json()
    assert d["merchant"]["status"] == "active" and d["plan"]
    assert d["team"][0]["email"] == seller.email and d["team"][0]["role"] == "owner"
    assert (
        d["connections"][0]["provider"] == "sandbox_channel" and d["connections"][0]["status"] == "connected"
    )
    body = str(d)
    assert "sealed" not in body and "access_token" not in body and "password" not in body
    assert client.get(f"{API}/admin/merchants/{uuid.uuid4()}", headers=staff.h()).status_code == 404


def test_suspend_blocks_seller_and_reactivate_restores(client, seller):
    staff = make_staff(register_and_login(client, "ops@nivaro.example"))
    url = f"{API}/admin/merchants/{seller.merchant_id}/status"
    assert client.post(url, headers=staff.h(), json={"status": "suspended", "reason": "x"}).status_code == 400
    r = client.post(url, headers=staff.h(), json={"status": "suspended", "reason": "Chargeback fraud review"})
    assert r.status_code == 200 and r.json()["status"] == "suspended"
    blocked = client.get(f"{API}/catalog/products", headers=seller.h())
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "merchant_suspended"
    client.post(url, headers=staff.h(), json={"status": "active", "reason": "Review cleared"})
    assert client.get(f"{API}/catalog/products", headers=seller.h()).status_code == 200
    logs = client.get(
        f"{API}/admin/audit-logs",
        params={"merchant_id": seller.merchant_id, "actor_type": "staff"},
        headers=staff.h(),
    ).json()["items"]
    assert [a["action"] for a in logs] == ["admin.merchant_status_changed"] * 2
    assert logs[1]["metadata"]["reason"] == "Chargeback fraud review"
    assert logs[0]["actor"]["display"] == "ops@nivaro.example"


def test_override_raises_limit_then_ending_it_restores_plan(client, seller):
    staff = make_staff(register_and_login(client, "ops@nivaro.example"))
    base = f"{API}/admin/merchants/{seller.merchant_id}/overrides"

    def ai_limit() -> int:
        limits = client.get(f"{API}/billing/entitlements", headers=seller.h()).json()["limits"]
        return next(u["limit"] for u in limits if u["resource"] == "ai_text_generations")

    plan_limit = ai_limit()
    bad = client.post(
        base,
        headers=staff.h(),
        json={"resource_code": "nope", "period": "month", "limit_value": 5, "reason": "pilot shop"},
    )
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "unknown_resource"
    gauge = client.post(
        base,
        headers=staff.h(),
        json={"resource_code": "products", "period": "month", "limit_value": 5, "reason": "pilot shop"},
    )
    assert gauge.json()["error"]["code"] == "gauge_period_lifetime"
    past = (utcnow() - timedelta(days=1)).isoformat()
    assert (
        client.post(
            base,
            headers=staff.h(),
            json={
                "resource_code": "ai_text_generations",
                "period": "month",
                "limit_value": 5,
                "reason": "pilot shop",
                "expires_at": past,
            },
        ).json()["error"]["code"]
        == "expires_in_past"
    )
    o = client.post(
        base,
        headers=staff.h(),
        json={
            "resource_code": "ai_text_generations",
            "period": "month",
            "limit_value": plan_limit + 500,
            "reason": "Pilot shop goodwill",
        },
    )
    assert o.status_code == 201 and o.json()["active"] is True
    assert ai_limit() == plan_limit + 500
    assert client.delete(f"{base}/{o.json()['id']}", headers=staff.h()).status_code == 204
    assert ai_limit() == plan_limit
    d = client.get(f"{API}/admin/merchants/{seller.merchant_id}", headers=staff.h()).json()
    assert d["overrides"][0]["active"] is False  # kept for the record
    other = onboard(client, shop="Patan Crafts")
    wrong = f"{API}/admin/merchants/{other.merchant_id}/overrides/{o.json()['id']}"
    assert client.delete(wrong, headers=staff.h()).status_code == 404


def test_credit_grant_is_idempotent_and_audited(client, seller):
    staff = make_staff(register_and_login(client, "ops@nivaro.example"))
    url = f"{API}/admin/merchants/{seller.merchant_id}/credits"
    body = {"amount": 50, "reason": "Outage goodwill", "idempotency_key": "goodwill-2026-11-03"}
    r1 = client.post(url, headers=staff.h(), json=body)
    r2 = client.post(url, headers=staff.h(), json=body)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]
    assert client.get(f"{API}/billing/credits", headers=seller.h()).json()["balance"] == r1.json()["balance"]
    assert client.post(url, headers=staff.h(), json={**body, "amount": 0}).status_code == 400
    assert client.post(url, headers=staff.h(), json={**body, "amount": "50"}).status_code == 400


def test_console_writes_need_staff_and_mfa(client, seller):
    no_mfa = make_staff(register_and_login(client, "ops@nivaro.example"), mfa=False)
    paths = [
        (
            "post",
            f"/admin/merchants/{seller.merchant_id}/status",
            {"status": "suspended", "reason": "testing"},
        ),
        (
            "post",
            f"/admin/merchants/{seller.merchant_id}/credits",
            {"amount": 5, "reason": "testing", "idempotency_key": "k-12345678"},
        ),
        (
            "post",
            f"/admin/merchants/{seller.merchant_id}/overrides",
            {"resource_code": "auto_reels", "period": "month", "limit_value": 1, "reason": "testing"},
        ),
        ("get", "/admin/audit-logs", None),
    ]
    for method, path, body in paths:
        kw = {"json": body} if body else {}
        assert (
            getattr(client, method)(f"{API}{path}", headers=seller.h(), **kw).status_code == 404
        )  # not staff
        r = getattr(client, method)(f"{API}{path}", headers=no_mfa.h(), **kw)
        assert r.status_code == 403 and r.json()["error"]["code"] == "mfa_required"
