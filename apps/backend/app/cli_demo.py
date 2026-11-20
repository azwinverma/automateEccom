"""`seed-demo`: sample sign-ins for every role, for local development and testing only.

Creates (or, on a re-run, resets) one demo shop on the Business plan with an owner, admin, manager,
staff member and viewer, plus a platform-staff (Nivaro admin) account with two-step verification
already on. Passwords are random per run (never stored in the repo); the sign-in sheet is printed
and written to .data/demo-users.txt (git-ignored). Refuses to run in staging or production.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any

import pyotp
from sqlalchemy import select

from app.core.config import REPO_ROOT, Environment, get_settings
from app.core.context import Actor, RequestMeta
from app.core.crypto import SealedSecret
from app.core.db import bind_tenant, session_scope, utcnow
from app.core.security import hash_password

DEMO_SLUG = "nivaro-demo"
DEMO_DOMAIN = "nivaro-demo.example.com"
SHOP_ROLES = ("owner", "admin", "manager", "staff", "viewer")
NAMES = {
    "owner": "Sita Shrestha",
    "admin": "Ramesh Karki",
    "manager": "Gita Thapa",
    "staff": "Bikash Gurung",
    "viewer": "Asha Rai",
    "platform": "Nivaro Support",
}
SHEET = REPO_ROOT / ".data" / "demo-users.txt"


def _email(role: str) -> str:
    return f"{role}@{DEMO_DOMAIN}"


def _password() -> str:
    # Satisfies the password policy (length, mixed classes) and is easy to type.
    return f"Demo-{secrets.token_hex(4)}-{secrets.randbelow(90) + 10}!"


def _upsert_user(db: Any, role: str, password: str) -> Any:
    from app.domains.accounts.models import AuthSession
    from app.domains.accounts.service import find_user_by_email, register

    email = _email(role)
    u = find_user_by_email(db, email)
    if u is None:
        u = register(
            db,
            email=email,
            password=password,
            full_name=NAMES[role],
            phone=None,
            locale="en",
            meta=RequestMeta(source="cli"),
        )
    else:
        u.password_hash = hash_password(password)
        u.status, u.failed_login_count, u.locked_until = "active", 0, None
        for s in db.scalars(select(AuthSession).where(AuthSession.user_id == u.id)):
            s.revoked_at = s.revoked_at or utcnow()  # old demo sign-ins end with the old password
    u.email_verified_at = u.email_verified_at or utcnow()
    db.flush()
    return u


def seed_demo() -> dict[str, Any]:
    settings = get_settings()
    if settings.environment not in (Environment.DEVELOPMENT, Environment.TEST):
        raise SystemExit(f"seed-demo is for local development only (COS_ENVIRONMENT={settings.environment})")

    from app.domains.accounts.models import MfaRecoveryCode
    from app.domains.audit import service as audit
    from app.domains.billing.models import Plan, PlanVersion, Subscription
    from app.domains.merchants.models import Membership, Merchant
    from app.domains.merchants.service import create_merchant

    passwords = {r: _password() for r in (*SHOP_ROLES, "platform")}
    with session_scope() as db:
        users = {r: _upsert_user(db, r, passwords[r]) for r in (*SHOP_ROLES, "platform")}

        m = db.scalar(select(Merchant).where(Merchant.slug == DEMO_SLUG))
        if m is None:
            m = create_merchant(
                db,
                owner=users["owner"],
                name="Nivaro Demo Shop",
                slug=DEMO_SLUG,
                country="NP",
                currency="NPR",
                timezone="Asia/Kathmandu",
                default_locale="en",
                meta=RequestMeta(source="cli"),
            )
            db.flush()
        mid: uuid.UUID = m.id
        bind_tenant(db, mid)
        for role in SHOP_ROLES:
            mem = db.scalar(
                select(Membership).where(Membership.merchant_id == mid, Membership.user_id == users[role].id)
            )
            if mem is None:
                db.add(Membership(merchant_id=mid, user_id=users[role].id, role=role))
            else:
                mem.role, mem.status = role, "active"

        # Business plan, so every screen is visible to try.
        pv = db.scalar(
            select(PlanVersion)
            .join(Plan, Plan.id == PlanVersion.plan_id)
            .where(Plan.code == "business", PlanVersion.status == "active")
        )
        sub = db.scalar(
            select(Subscription)
            .where(Subscription.merchant_id == mid)
            .execution_options(skip_tenant_filter=True)
        )
        if pv is not None and sub is not None:
            sub.plan_version_id, sub.status = pv.id, "active"

        # Platform staff must sign in with two-step verification: switch it on with a fresh secret.
        staff = users["platform"]
        staff.is_platform_staff = True
        secret = pyotp.random_base32()
        staff.mfa_totp_secret_sealed = SealedSecret.seal(secret, f"user:{staff.id}:totp").blob
        staff.mfa_totp_last_step = None
        staff.mfa_enabled_at = utcnow()
        for rc in db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == staff.id)):
            db.delete(rc)
        recovery = [secrets.token_hex(5) for _ in range(4)]
        for c in recovery:
            db.add(MfaRecoveryCode(user_id=staff.id, code_hash=hash_password(c)))

        audit.record(
            db,
            action="ops.demo_seeded",
            resource_type="merchant",
            resource_id=mid,
            actor=Actor.system("cli"),
            merchant_id=mid,
            metadata={"roles": [*SHOP_ROLES, "platform"]},
        )

    out = {
        "shop": DEMO_SLUG,
        "plan": "business" if pv is not None else "default (run seed-plans first for Business)",
        "users": [
            {"role": r, "email": _email(r), "password": passwords[r]} for r in (*SHOP_ROLES, "platform")
        ],
        "platform_totp_secret": secret,
        "platform_totp_uri": pyotp.TOTP(secret).provisioning_uri(
            name=_email("platform"), issuer_name="Nivaro"
        ),
        "platform_recovery_codes": [f"{c[:5]}-{c[5:]}" for c in recovery],
    }
    _write_sheet(out)
    return out


def _write_sheet(out: dict[str, Any]) -> None:
    lines = [
        "Nivaro demo sign-ins (local only; regenerated by `python -m app.cli seed-demo`)",
        f"Shop: {out['shop']}   Plan: {out['plan']}",
        "",
        *(f"{u['role']:<9} {u['email']:<36} {u['password']}" for u in out["users"]),
        "",
        "Platform staff two-step verification:",
        f"  secret         {out['platform_totp_secret']}  (add to an authenticator app)",
        f"  otpauth URI    {out['platform_totp_uri']}",
        "  current code   uv run python -m app.cli demo-code",
        f"  recovery codes {', '.join(out['platform_recovery_codes'])}",
    ]
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text("\n".join(lines) + "\n")
    SHEET.chmod(0o600)


def demo_code() -> str:
    """Current 6-digit code for the demo platform-staff account (read from the local sign-in sheet)."""
    if not SHEET.exists():
        raise SystemExit("run seed-demo first")
    for line in SHEET.read_text().splitlines():
        if line.strip().startswith("secret"):
            return pyotp.TOTP(line.split()[1]).now()
    raise SystemExit("no secret in the sign-in sheet; run seed-demo again")
