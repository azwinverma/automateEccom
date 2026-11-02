from __future__ import annotations

import pyotp
from sqlalchemy import select

from app.core.db import session_scope
from app.domains.audit.models import AuditLog
from tests.conftest import PASSWORD, register_and_login

API = "/api/v1"


def test_register_rejects_weak_and_common_passwords(client):
    for pw, reason in [("short", "too_short"), ("password123", "too_common")]:
        r = client.post(
            f"{API}/auth/register", json={"email": "a@example.com", "password": pw, "full_name": "A"}
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "weak_password"
        assert reason in r.json()["error"]["details"]["reasons"]


def test_register_duplicate_email_case_insensitive(client):
    register_and_login(client, "Ram@Example.com")
    r = client.post(
        f"{API}/auth/register", json={"email": "ram@example.com", "password": PASSWORD, "full_name": "R"}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_taken"


def test_login_failure_is_generic_and_request_id_echoed(client):
    register_and_login(client, "hari@example.com")
    bad_user = client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    bad_pw = client.post(
        f"{API}/auth/login",
        json={"email": "hari@example.com", "password": "wrong-password-1"},
        headers={"X-Request-ID": "req-test-12345"},
    )
    assert bad_user.status_code == bad_pw.status_code == 401
    assert bad_user.json()["error"]["code"] == bad_pw.json()["error"]["code"] == "invalid_credentials"
    assert bad_pw.headers["X-Request-ID"] == "req-test-12345"
    assert bad_pw.json()["error"]["request_id"] == "req-test-12345"


def test_account_lockout_after_repeated_failures(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "login_max_failures", 3)
    register_and_login(client, "gita@example.com")
    for _ in range(3):
        assert (
            client.post(
                f"{API}/auth/login", json={"email": "gita@example.com", "password": "nope-nope-1"}
            ).status_code
            == 401
        )
    r = client.post(f"{API}/auth/login", json={"email": "gita@example.com", "password": PASSWORD})
    assert r.status_code == 429  # locked even with the correct password


def test_refresh_rotation_and_reuse_detection_revokes_family(client):
    s = register_and_login(client)
    r1 = client.post(f"{API}/auth/refresh", json={"refresh_token": s.refresh})
    assert r1.status_code == 200
    new = r1.json()
    assert new["refresh_token"] != s.refresh
    # Replay the old (rotated) token → whole session revoked.
    r2 = client.post(f"{API}/auth/refresh", json={"refresh_token": s.refresh})
    assert r2.status_code == 401 and r2.json()["error"]["code"] == "refresh_token_reused"
    r3 = client.post(f"{API}/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert r3.status_code == 401 and r3.json()["error"]["code"] == "session_revoked"
    # Access tokens of the revoked session stop working immediately.
    me = client.get(f"{API}/me", headers={"Authorization": f"Bearer {new['access_token']}"})
    assert me.status_code == 401 and me.json()["error"]["code"] == "session_revoked"
    with session_scope() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "accounts.refresh_token_reuse_detected"))


def test_logout_and_revoke_all_other_sessions(client):
    a = register_and_login(client, "multi@example.com")
    b = client.post(f"{API}/auth/login", json={"email": "multi@example.com", "password": PASSWORD}).json()
    sessions = client.get(f"{API}/auth/sessions", headers=a.h()).json()["items"]
    assert len(sessions) == 2 and sum(x["current"] for x in sessions) == 1
    assert client.post(f"{API}/auth/sessions/revoke-all", headers=a.h()).status_code == 204
    assert (
        client.get(f"{API}/me", headers={"Authorization": f"Bearer {b['access_token']}"}).status_code == 401
    )
    assert client.get(f"{API}/me", headers=a.h()).status_code == 200
    assert client.post(f"{API}/auth/logout", json={"refresh_token": a.refresh}).status_code == 204
    assert client.get(f"{API}/me", headers=a.h()).status_code == 401


def test_mfa_totp_flow_with_single_use_recovery_codes(client):
    s = register_and_login(client, "mfa@example.com")
    setup = client.post(f"{API}/auth/mfa/totp/setup", headers=s.h()).json()
    totp = pyotp.TOTP(setup["secret"])
    assert (
        client.post(f"{API}/auth/mfa/totp/enable", headers=s.h(), json={"code": "000000"}).status_code == 401
    )
    codes = client.post(f"{API}/auth/mfa/totp/enable", headers=s.h(), json={"code": totp.now()}).json()[
        "recovery_codes"
    ]
    assert len(codes) == 10

    r = client.post(f"{API}/auth/login", json={"email": "mfa@example.com", "password": PASSWORD})
    assert r.json()["mfa_required"] is True and "access_token" not in r.json()
    mfa_token = r.json()["mfa_token"]
    assert (
        client.post(f"{API}/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "123456"}).status_code
        == 401
    )
    ok = client.post(f"{API}/auth/mfa/verify", json={"mfa_token": mfa_token, "code": totp.now()})
    assert ok.status_code == 200 and "access_token" in ok.json()

    t2 = client.post(f"{API}/auth/login", json={"email": "mfa@example.com", "password": PASSWORD}).json()[
        "mfa_token"
    ]
    assert client.post(f"{API}/auth/mfa/verify", json={"mfa_token": t2, "code": codes[0]}).status_code == 200
    t3 = client.post(f"{API}/auth/login", json={"email": "mfa@example.com", "password": PASSWORD}).json()[
        "mfa_token"
    ]
    assert client.post(f"{API}/auth/mfa/verify", json={"mfa_token": t3, "code": codes[0]}).status_code == 401


def test_access_token_type_confusion_rejected(client):
    s = register_and_login(client, "conf@example.com")
    import uuid

    from app.core.security import issue_jwt

    mfa_token = issue_jwt(uuid.UUID(client.get(f"{API}/me", headers=s.h()).json()["user"]["id"]), "mfa", 60)
    assert client.get(f"{API}/me", headers={"Authorization": f"Bearer {mfa_token}"}).status_code == 401


def test_email_verification_via_outbox(client):
    import re

    import app.domains.handlers  # noqa: F401
    from app.core.config import REPO_ROOT
    from app.domains.platform.outbox import dispatch_batch

    mailbox = REPO_ROOT / ".data" / "mailbox"
    before = set(mailbox.glob("*.txt")) if mailbox.exists() else set()
    s = register_and_login(client, "verify@example.com")
    dispatch_batch()
    new = [p for p in mailbox.glob("*.txt") if p not in before and "verify@example.com" in p.read_text()]
    assert new, "verification email not written"
    token = re.search(r"token=([\w-]+)", new[0].read_text()).group(1)
    assert client.post(f"{API}/auth/verify-email/confirm", json={"token": token}).status_code == 204
    assert client.get(f"{API}/me", headers=s.h()).json()["user"]["email_verified"] is True
    assert client.post(f"{API}/auth/verify-email/confirm", json={"token": token}).status_code == 400
    for p in new:
        p.unlink()


def test_concurrent_duplicate_registration_returns_409_not_500(client):
    import threading

    from fastapi.testclient import TestClient

    from app.main import create_app

    results: list[int] = []
    body = {"email": "race@example.com", "password": PASSWORD, "full_name": "Race"}

    def go() -> None:
        with TestClient(create_app(), raise_server_exceptions=False) as c:
            results.append(c.post(f"{API}/auth/register", json=body).status_code)

    threads = [threading.Thread(target=go) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [201, 409, 409, 409]


def test_db_errors_do_not_leak_bound_parameters_or_row_values(capsys):
    import sqlalchemy as sa

    from app.core.db import session_scope

    try:
        with session_scope() as db:
            db.execute(sa.text("SELECT CAST(:v AS text), 1/0"), {"v": "secret-token-value"})
    except sa.exc.DBAPIError as e:
        assert "secret-token-value" not in str(e)  # hide_parameters
    else:
        raise AssertionError("expected a DB error")


def test_unhandled_db_error_log_omits_postgres_detail(client, capsys, monkeypatch):
    import sqlalchemy as sa

    from app.domains.accounts import service

    def boom(*a, **k):
        raise sa.exc.IntegrityError("INSERT", {}, Exception("Key (email)=(leak@example.com) already exists"))

    monkeypatch.setattr(service, "find_user_by_email", boom)
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app(), raise_server_exceptions=False) as c:
        r = c.post(
            f"{API}/auth/register", json={"email": "leak@example.com", "password": PASSWORD, "full_name": "L"}
        )
    assert r.status_code == 500 and "leak@example.com" not in r.text
    out = capsys.readouterr().out
    assert "unhandled_db_error" in out and "leak@example.com" not in out
