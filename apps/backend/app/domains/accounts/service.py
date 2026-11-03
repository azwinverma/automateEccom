"""Identity: registration, login, MFA, sessions and refresh-token rotation (IAM-001..005, IAM-010)."""

from __future__ import annotations

import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pyotp
import structlog
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import Actor, RequestMeta
from app.core.crypto import SealedSecret
from app.core.db import utcnow
from app.core.errors import AppError, Conflict, NotAuthenticated, NotFound, RateLimited, ValidationFailed
from app.core.metrics import AUTH_EVENTS
from app.core.security import (
    decode_jwt,
    hash_password,
    hash_token,
    issue_jwt,
    new_opaque_token,
    password_needs_rehash,
    verify_password,
)
from app.domains.accounts.models import (
    AuthSession,
    EmailVerificationToken,
    MfaRecoveryCode,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.domains.audit import service as audit
from app.domains.platform import outbox

log = structlog.get_logger(__name__)

_COMMON_PASSWORDS: frozenset[str] = frozenset(
    (Path(__file__).parent / "common_passwords.txt").read_text().split()
)
RECOVERY_CODE_COUNT = 10
# Shown in authenticator apps for new enrolments. Existing enrolments keep the label they were created
# with (the secret is unaffected), see ADR-028.
TOTP_ISSUER = "Nivaro"


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    session_id: uuid.UUID
    expires_in: int
    token_type: str = "bearer"


@dataclass
class MfaChallenge:
    mfa_token: str
    mfa_required: bool = True


def validate_password(password: str, email: str) -> None:
    problems = []
    if len(password) < 10:
        problems.append("too_short")
    if len(password) > 256:
        problems.append("too_long")
    if password.lower() in _COMMON_PASSWORDS:
        problems.append("too_common")
    if password.lower() == email.lower() or password.lower() == email.split("@")[0].lower():
        problems.append("matches_email")
    if problems:
        raise ValidationFailed(
            "Password does not meet requirements", code="weak_password", details={"reasons": problems}
        )


def _user_actor(user: User) -> Actor:
    return Actor(type="user", id=user.id, display=user.email)


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def register(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    phone: str | None,
    locale: str,
    meta: RequestMeta,
) -> User:
    email = email.strip()
    validate_password(password, email)
    if find_user_by_email(db, email) is not None:
        raise Conflict("An account with this email already exists", code="email_taken")
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone=phone,
        locale=locale,
    )
    db.add(user)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as e:  # concurrent registration with the same email
        raise Conflict("An account with this email already exists", code="email_taken") from e
    audit.record(
        db,
        action="accounts.user_registered",
        resource_type="user",
        resource_id=user.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
    )
    outbox.publish(
        db,
        event_type="accounts.user_registered",
        aggregate_type="user",
        aggregate_id=user.id,
        merchant_id=None,
        payload={"user_id": str(user.id), "locale": locale},
    )
    outbox.publish(
        db,
        event_type="accounts.email_verification_requested",
        aggregate_type="user",
        aggregate_id=user.id,
        merchant_id=None,
        payload={"user_id": str(user.id)},
    )
    AUTH_EVENTS.labels("registered").inc()
    return user


# ----------------------------------------------------------------------------- sessions/tokens
def _issue_tokens(db: Session, user: User, session: AuthSession) -> TokenPair:
    s = get_settings()
    refresh = new_opaque_token()
    db.add(
        RefreshToken(
            session_id=session.id,
            token_hash=hash_token(refresh),
            expires_at=utcnow() + timedelta(seconds=s.refresh_token_ttl_seconds),
        )
    )
    access = issue_jwt(user.id, "access", s.access_token_ttl_seconds, sid=str(session.id), amr=session.amr)
    return TokenPair(access, refresh, session.id, s.access_token_ttl_seconds)


def _open_session(
    db: Session, user: User, meta: RequestMeta, device_name: str | None, amr: str
) -> AuthSession:
    s = get_settings()
    now = utcnow()
    session = AuthSession(
        user_id=user.id,
        device_name=(device_name or "")[:120] or None,
        user_agent=(meta.user_agent or "")[:512] or None,
        ip=meta.ip,
        amr=amr,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(seconds=s.refresh_token_ttl_seconds),
    )
    db.add(session)
    db.flush()
    user.last_login_at = now
    return session


def login(
    db: Session, *, email: str, password: str, device_name: str | None, meta: RequestMeta
) -> TokenPair | MfaChallenge:
    s = get_settings()
    user = find_user_by_email(db, email)
    now = utcnow()
    if user is not None and user.locked_until is not None and user.locked_until > now:
        AUTH_EVENTS.labels("locked").inc()
        raise RateLimited(
            "Too many attempts. Try again later.",
            details={"retry_after": int((user.locked_until - now).total_seconds())},
        )
    ok = verify_password(password, user.password_hash if user else None)
    if not ok or user is None or user.status != "active":
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= s.login_max_failures:
                user.locked_until = now + timedelta(seconds=s.login_lockout_seconds)
                user.failed_login_count = 0
                audit.record(
                    db,
                    action="accounts.locked_out",
                    resource_type="user",
                    resource_id=user.id,
                    actor=Actor.system("auth"),
                    merchant_id=None,
                    meta=meta,
                )
            db.commit()  # persist failure counters even though we raise
        AUTH_EVENTS.labels("login_failed").inc()
        raise NotAuthenticated("Email or password is incorrect", code="invalid_credentials")
    user.failed_login_count = 0
    user.locked_until = None
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    if user.mfa_enabled:
        token = issue_jwt(user.id, "mfa", s.mfa_token_ttl_seconds, dev=(device_name or "")[:120])
        AUTH_EVENTS.labels("mfa_challenge").inc()
        return MfaChallenge(token)
    session = _open_session(db, user, meta, device_name, "pwd")
    audit.record(
        db,
        action="accounts.login",
        resource_type="session",
        resource_id=session.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
        metadata={"amr": "pwd"},
    )
    AUTH_EVENTS.labels("login").inc()
    return _issue_tokens(db, user, session)


def verify_mfa(db: Session, *, mfa_token: str, code: str, meta: RequestMeta) -> TokenPair:
    payload = decode_jwt(mfa_token, "mfa")
    # Row lock: makes TOTP replay protection and failure counting atomic under concurrent requests.
    user = db.get(User, uuid.UUID(payload["sub"]), with_for_update=True)
    if user is None or not user.mfa_enabled or user.status != "active":
        raise NotAuthenticated(code="invalid_token")
    if not (_check_totp(user, code) or _consume_recovery_code(db, user, code)):
        user.failed_login_count += 1
        if user.failed_login_count >= get_settings().login_max_failures:
            user.locked_until = utcnow() + timedelta(seconds=get_settings().login_lockout_seconds)
            user.failed_login_count = 0
        db.commit()
        AUTH_EVENTS.labels("mfa_failed").inc()
        raise NotAuthenticated("Invalid verification code", code="mfa_invalid_code")
    user.failed_login_count = 0
    session = _open_session(db, user, meta, payload.get("dev") or None, "pwd+mfa")
    audit.record(
        db,
        action="accounts.login",
        resource_type="session",
        resource_id=session.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
        metadata={"amr": "pwd+mfa"},
    )
    AUTH_EVENTS.labels("login").inc()
    return _issue_tokens(db, user, session)


def refresh(db: Session, *, refresh_token: str, meta: RequestMeta) -> TokenPair:
    now = utcnow()
    rt = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)).with_for_update()
    )
    if rt is None:
        raise NotAuthenticated("Invalid refresh token", code="invalid_token")
    session = db.scalar(select(AuthSession).where(AuthSession.id == rt.session_id).with_for_update())
    assert session is not None
    if session.revoked_at is not None:
        raise NotAuthenticated("Session revoked", code="session_revoked")
    if rt.rotated_at is not None:
        # Replay of a rotated token: assume theft, kill the whole family.
        _revoke(db, session, "refresh_reuse")
        audit.record(
            db,
            action="accounts.refresh_token_reuse_detected",
            resource_type="session",
            resource_id=session.id,
            actor=Actor.system("auth"),
            merchant_id=None,
            meta=meta,
            metadata={"user_id": str(session.user_id)},
        )
        outbox.publish(
            db,
            event_type="accounts.refresh_token_reuse_detected",
            aggregate_type="user",
            aggregate_id=session.user_id,
            merchant_id=None,
            payload={"user_id": str(session.user_id), "session_id": str(session.id)},
        )
        db.commit()
        AUTH_EVENTS.labels("refresh_reuse").inc()
        raise NotAuthenticated("Refresh token already used", code="refresh_token_reused")
    if rt.expires_at < now or session.expires_at < now:
        raise NotAuthenticated("Session expired", code="session_expired")
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise NotAuthenticated(code="invalid_token")
    rt.rotated_at = now
    session.last_used_at = now
    session.ip = meta.ip or session.ip
    AUTH_EVENTS.labels("refresh").inc()
    return _issue_tokens(db, user, session)


def _revoke(db: Session, session: AuthSession, reason: str) -> None:
    if session.revoked_at is None:
        session.revoked_at = utcnow()
        session.revoked_reason = reason


def logout(db: Session, *, refresh_token: str, meta: RequestMeta) -> None:
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
    if rt is None:
        return  # idempotent
    session = db.get(AuthSession, rt.session_id)
    if session is not None and session.revoked_at is None:
        _revoke(db, session, "logout")
        audit.record(
            db,
            action="accounts.logout",
            resource_type="session",
            resource_id=session.id,
            actor=Actor(type="user", id=session.user_id),
            merchant_id=None,
            meta=meta,
        )


def list_sessions(db: Session, user_id: uuid.UUID) -> list[AuthSession]:
    return list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > utcnow(),
            )
            .order_by(AuthSession.last_used_at.desc())
        )
    )


def revoke_session(db: Session, user: User, session_id: uuid.UUID, meta: RequestMeta) -> None:
    session = db.get(AuthSession, session_id)
    if session is None or session.user_id != user.id:
        raise NotFound()
    _revoke(db, session, "user_revoked")
    audit.record(
        db,
        action="accounts.session_revoked",
        resource_type="session",
        resource_id=session.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
    )


def revoke_all_other_sessions(
    db: Session, user: User, current_session_id: uuid.UUID, meta: RequestMeta
) -> int:
    res = db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.id != current_session_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=utcnow(), revoked_reason="user_revoked_all")
    )
    count = int(getattr(res, "rowcount", 0) or 0)
    audit.record(
        db,
        action="accounts.sessions_revoked_all",
        resource_type="user",
        resource_id=user.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
        metadata={"count": count},
    )
    return count


def authenticate_access_token(db: Session, token: str) -> tuple[User, AuthSession]:
    payload = decode_jwt(token, "access")
    session = db.get(AuthSession, uuid.UUID(payload["sid"])) if payload.get("sid") else None
    if session is None or session.revoked_at is not None:
        raise NotAuthenticated("Session revoked", code="session_revoked")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or user.status != "active" or session.user_id != user.id:
        raise NotAuthenticated(code="invalid_token")
    return user, session


# ----------------------------------------------------------------------------- MFA
def _totp_aad(user: User) -> str:
    return f"user:{user.id}:totp"


def _check_totp(user: User, code: str) -> bool:
    """Accept a TOTP code once: only a time-step newer than the last accepted one (QA-011).
    Callers must hold the user row lock so two concurrent requests can't both accept the same step."""
    if not user.mfa_totp_secret_sealed or not code.isdigit() or len(code) != 6:
        return False
    secret = SealedSecret(user.mfa_totp_secret_sealed).open(_totp_aad(user))
    totp = pyotp.TOTP(secret)
    now = utcnow()
    current = totp.timecode(now)
    for step in (current - 1, current, current + 1):  # ±1 step of clock skew, as before
        if step <= (user.mfa_totp_last_step or -1):
            continue
        if hmac.compare_digest(totp.generate_otp(step), code):
            user.mfa_totp_last_step = step
            return True
    return False


def _consume_recovery_code(db: Session, user: User, code: str) -> bool:
    normalized = code.replace("-", "").strip().lower()
    if len(normalized) != 10:
        return False
    for rc in db.scalars(
        select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None))
    ):
        if verify_password(normalized, rc.code_hash):
            rc.used_at = utcnow()
            return True
    return False


def totp_setup(db: Session, user: User) -> tuple[str, str]:
    if user.mfa_enabled:
        raise Conflict("MFA is already enabled", code="mfa_already_enabled")
    secret = pyotp.random_base32()
    user.mfa_totp_secret_sealed = SealedSecret.seal(secret, _totp_aad(user)).blob
    user.mfa_totp_last_step = None  # new secret, new step history
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=TOTP_ISSUER)
    return secret, uri


def totp_enable(db: Session, user: User, code: str, meta: RequestMeta) -> list[str]:
    if user.mfa_enabled:
        raise Conflict("MFA is already enabled", code="mfa_already_enabled")
    if not user.mfa_totp_secret_sealed:
        raise AppError("Start MFA setup first", code="mfa_setup_required")
    if not _check_totp(user, code):
        raise NotAuthenticated("Invalid verification code", code="mfa_invalid_code")
    user.mfa_enabled_at = utcnow()
    codes = [secrets.token_hex(5) for _ in range(RECOVERY_CODE_COUNT)]
    for c in codes:
        db.add(MfaRecoveryCode(user_id=user.id, code_hash=hash_password(c)))
    audit.record(
        db,
        action="accounts.mfa_enabled",
        resource_type="user",
        resource_id=user.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
    )
    outbox.publish(
        db,
        event_type="accounts.mfa_enabled",
        aggregate_type="user",
        aggregate_id=user.id,
        merchant_id=None,
        payload={"user_id": str(user.id)},
    )
    return [f"{c[:5]}-{c[5:]}" for c in codes]


def totp_disable(db: Session, user: User, code: str, password: str, meta: RequestMeta) -> None:
    if not user.mfa_enabled:
        return
    if not verify_password(password, user.password_hash) or not _check_totp(user, code):
        raise NotAuthenticated("Invalid verification", code="mfa_invalid_code")
    user.mfa_enabled_at = None
    user.mfa_totp_secret_sealed = None
    for rc in db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id)):
        db.delete(rc)
    audit.record(
        db,
        action="accounts.mfa_disabled",
        resource_type="user",
        resource_id=user.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
    )


# ----------------------------------------------------------------------------- email verification
EMAIL_TOKEN_TTL = timedelta(hours=24)


def issue_email_verification(db: Session, user: User) -> str:
    token = new_opaque_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id, token_hash=hash_token(token), expires_at=utcnow() + EMAIL_TOKEN_TTL
        )
    )
    return token


def confirm_email(db: Session, token: str, meta: RequestMeta) -> User:
    row = db.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == hash_token(token))
        .with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise ValidationFailed("Verification link is invalid or expired", code="verification_invalid")
    row.used_at = utcnow()
    user = db.get(User, row.user_id)
    assert user is not None
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
        audit.record(
            db,
            action="accounts.email_verified",
            resource_type="user",
            resource_id=user.id,
            actor=_user_actor(user),
            merchant_id=None,
            meta=meta,
        )
    return user


# ----------------------------------------------------------------------------- password reset (QA-001)
PASSWORD_RESET_TTL = timedelta(minutes=30)


def request_password_reset(db: Session, email: str, meta: RequestMeta) -> None:
    """Always succeeds from the caller's view (no account enumeration). Only active accounts get an
    email; the token itself is issued when the email is sent (outbox handler)."""
    user = find_user_by_email(db, email)
    if user is None or user.status != "active":
        return
    outbox.publish(
        db,
        event_type="accounts.password_reset_requested",
        aggregate_type="user",
        aggregate_id=user.id,
        merchant_id=None,
        payload={"user_id": str(user.id)},
    )
    audit.record(
        db,
        action="accounts.password_reset_requested",
        resource_type="user",
        resource_id=user.id,
        actor=Actor.system("auth"),
        merchant_id=None,
        meta=meta,
    )


def issue_password_reset(db: Session, user: User) -> str:
    """New token; any earlier unused tokens for this user stop working."""
    now = utcnow()
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = new_opaque_token()
    db.add(
        PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=now + PASSWORD_RESET_TTL)
    )
    return token


def reset_password(db: Session, token: str, new_password: str, meta: RequestMeta) -> User:
    row = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)).with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise ValidationFailed("Reset link is invalid or expired", code="reset_invalid")
    user = db.get(User, row.user_id)
    if user is None or user.status != "active":
        raise ValidationFailed("Reset link is invalid or expired", code="reset_invalid")
    validate_password(new_password, user.email)
    now = utcnow()
    row.used_at = now
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    # Whoever knew the old password must not stay signed in anywhere.
    revoked = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revoked_reason="password_reset")
    )
    audit.record(
        db,
        action="accounts.password_reset",
        resource_type="user",
        resource_id=user.id,
        actor=_user_actor(user),
        merchant_id=None,
        meta=meta,
        metadata={"sessions_revoked": int(getattr(revoked, "rowcount", 0) or 0)},
    )
    outbox.publish(
        db,
        event_type="accounts.password_changed",
        aggregate_type="user",
        aggregate_id=user.id,
        merchant_id=None,
        payload={"user_id": str(user.id)},
    )
    return user
