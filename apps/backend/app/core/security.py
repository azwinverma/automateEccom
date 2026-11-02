"""Password hashing (Argon2id), JWT access tokens, opaque token hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import NotAuthenticated

_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)
# A pre-computed hash used to equalise timing when the account does not exist.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_opaque_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Deterministic hash for lookup of high-entropy opaque tokens (refresh, verification, invites)."""
    return hashlib.sha256(token.encode()).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def issue_jwt(subject: uuid.UUID, typ: str, ttl_seconds: int, **claims: Any) -> str:
    s = get_settings()
    now = utcnow()
    payload = {
        "sub": str(subject),
        "typ": typ,
        "iss": s.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "jti": secrets.token_hex(8),
        **claims,
    }
    return jwt.encode(payload, s.jwt_secret.get_secret_value(), algorithm=s.jwt_algorithm)


def decode_jwt(token: str, expected_typ: str) -> dict[str, Any]:
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.jwt_secret.get_secret_value(),
            algorithms=[s.jwt_algorithm],
            issuer=s.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "typ"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise NotAuthenticated("Token expired", code="token_expired") from e
    except jwt.PyJWTError as e:
        raise NotAuthenticated("Invalid token", code="invalid_token") from e
    if payload.get("typ") != expected_typ:
        raise NotAuthenticated("Invalid token type", code="invalid_token")
    return payload
