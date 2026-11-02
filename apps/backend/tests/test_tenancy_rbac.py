from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.db import TenantViolation, bind_tenant, session_factory, session_scope
from app.domains.merchants.models import Membership, Store
from tests.conftest import onboard, register_and_login, set_plan

API = "/api/v1"


def test_merchant_creation_sets_owner_store_subscription_and_audit(client, seller):
    me = client.get(f"{API}/me", headers=seller.h()).json()
    assert me["memberships"][0]["role"] == "owner"
    stores = client.get(f"{API}/stores", headers=seller.h()).json()["items"]
    assert len(stores) == 1 and stores[0]["is_default"]
    sub = client.get(f"{API}/billing/subscription", headers=seller.h()).json()
    assert sub["plan"]["code"] == "starter" and sub["status"] == "trialing"
    actions = {a["action"] for a in client.get(f"{API}/audit-logs", headers=seller.h()).json()["items"]}
    assert {"merchants.merchant_created", "billing.subscription_started"} <= actions


def test_cross_tenant_access_returns_404_not_403(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    for path in ("/merchant", "/stores", "/members", "/audit-logs", "/billing/entitlements"):
        r = client.get(f"{API}{path}", headers=a.h(merchant=b.merchant_id))
        assert r.status_code == 404, path
        assert r.json()["error"]["code"] == "merchant_not_found"
    assert client.get(f"{API}/stores", headers=a.h(merchant=str(uuid.uuid4()))).status_code == 404
    assert client.get(f"{API}/stores", headers=a.h(merchant="not-a-uuid")).status_code == 404


def test_cannot_patch_another_tenants_store_by_id(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    b_store = client.get(f"{API}/stores", headers=b.h()).json()["items"][0]["id"]
    r = client.patch(f"{API}/stores/{b_store}", headers=a.h(), json={"name": "Hijacked"})
    assert r.status_code == 404
    assert client.get(f"{API}/stores", headers=b.h()).json()["items"][0]["name"] == "Patan Crafts"


def test_orm_tenant_criteria_and_write_guard(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    with session_factory()() as db:
        bind_tenant(db, uuid.UUID(a.merchant_id))
        stores = db.scalars(select(Store)).all()  # no explicit filter on purpose
        assert {str(s.merchant_id) for s in stores} == {a.merchant_id}
        assert db.scalar(select(func.count()).select_from(Membership)) == 1
        db.add(Store(merchant_id=uuid.UUID(b.merchant_id), name="x", slug="x-store"))
        with pytest.raises(TenantViolation):
            db.flush()
        db.rollback()


def test_audit_log_is_append_only_at_db_level(client, seller):
    import sqlalchemy as sa

    with session_scope() as db:
        with pytest.raises(sa.exc.DBAPIError):
            db.execute(sa.text("UPDATE audit_logs SET action='tampered'"))
            db.flush()
        db.rollback()


def test_viewer_cannot_manage_team_and_manager_cannot_escalate(client):
    owner = onboard(client, shop="Boudha Beads")
    set_plan(owner.merchant_id, "growth")
    viewer = register_and_login(client, "viewer@example.com")
    manager = register_and_login(client, "manager@example.com")
    from app.domains.merchants.models import Membership as M

    with session_scope(uuid.UUID(owner.merchant_id)) as db:
        db.add(
            M(
                merchant_id=uuid.UUID(owner.merchant_id),
                user_id=uuid.UUID(_uid(client, viewer)),
                role="viewer",
            )
        )
        db.add(
            M(
                merchant_id=uuid.UUID(owner.merchant_id),
                user_id=uuid.UUID(_uid(client, manager)),
                role="manager",
            )
        )
    r = client.post(
        f"{API}/invitations",
        headers=viewer.h(merchant=owner.merchant_id),
        json={"email": "x@example.com", "role": "staff"},
    )
    assert r.status_code == 403 and r.json()["error"]["details"]["permission"] == "team.manage"
    r = client.post(
        f"{API}/invitations",
        headers=manager.h(merchant=owner.merchant_id),
        json={"email": "x@example.com", "role": "admin"},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "role_not_assignable"
    perms = client.get(f"{API}/permissions/me", headers=viewer.h(merchant=owner.merchant_id)).json()[
        "permissions"
    ]
    assert "orders.read" in perms and "orders.write" not in perms


def _uid(client, s) -> str:
    return client.get(f"{API}/me", headers=s.h()).json()["user"]["id"]


def test_last_owner_cannot_be_demoted_or_removed(client, seller):
    members = client.get(f"{API}/members", headers=seller.h()).json()["items"]
    mid = members[0]["id"]
    r = client.patch(f"{API}/members/{mid}", headers=seller.h(), json={"role": "admin"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "last_owner"
    r = client.delete(f"{API}/members/{mid}", headers=seller.h())
    assert r.status_code == 409


def test_invitation_flow_email_binding_and_team_limit(client):
    import app.domains.handlers  # noqa: F401

    owner = onboard(client, shop="Durbar Denim")  # starter: team_members limit 2
    r = client.post(
        f"{API}/invitations", headers=owner.h(), json={"email": "Staff@Example.com", "role": "staff"}
    )
    assert r.status_code == 201, r.text
    # Members(1) + pending(1) = 2 → next invite blocked by plan limit, with actionable options.
    r2 = client.post(
        f"{API}/invitations", headers=owner.h(), json={"email": "two@example.com", "role": "staff"}
    )
    assert r2.status_code == 402
    assert r2.json()["error"]["details"]["resource"] == "team_members"
    assert "upgrade" in r2.json()["error"]["details"]["options"]

    from sqlalchemy import select as sel

    from app.core.crypto import SealedSecret
    from app.domains.merchants.models import Invitation

    with session_scope() as db:
        inv = db.scalar(sel(Invitation))
        token = SealedSecret(inv.token_sealed).open(f"invitation:{inv.id}")
    intruder = register_and_login(client, "intruder@example.com")
    r = client.post(f"{API}/invitations/accept", headers=intruder.h(), json={"token": token})
    assert r.status_code == 403 and r.json()["error"]["code"] == "invitation_email_mismatch"
    staff = register_and_login(client, "staff@example.com")
    r = client.post(f"{API}/invitations/accept", headers=staff.h(), json={"token": token})
    assert r.status_code == 200
    assert client.get(f"{API}/stores", headers=staff.h(merchant=owner.merchant_id)).status_code == 200
    assert (
        client.post(f"{API}/invitations/accept", headers=staff.h(), json={"token": token}).status_code == 404
    )
    with session_scope() as db:
        assert db.scalar(sel(Invitation)).token_sealed is None  # secret purged after accept


def test_store_limit_enforced_by_entitlements_not_plan_name(client, seller):
    r = client.post(f"{API}/stores", headers=seller.h(), json={"name": "Second Brand"})
    assert r.status_code == 402 and r.json()["error"]["details"]["resource"] == "stores"
    set_plan(seller.merchant_id, "business")
    assert client.post(f"{API}/stores", headers=seller.h(), json={"name": "Second Brand"}).status_code == 201


def test_autopilot_mode_requires_entitlement(client, seller):
    r = client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "autopilot"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_not_in_plan"
    assert "pro" in r.json()["error"]["details"]["upgrade_options"]
    assert (
        client.patch(f"{API}/merchant", headers=seller.h(), json={"automation_mode": "smart"}).status_code
        == 200
    )
