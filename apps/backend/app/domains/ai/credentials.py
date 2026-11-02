"""BYOK provider credentials (AIG-011). Keys: envelope-encrypted, server-side only, never returned,
never logged. AAD binds ciphertext to merchant+provider+credential id."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.crypto import SealedSecret
from app.core.db import utcnow
from app.core.errors import NotFound, ValidationFailed
from app.domains.ai.models import ProviderCredential
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements

BYOK_PROVIDERS = frozenset({"anthropic", "openai", "gemini"})


def _aad(merchant_id: uuid.UUID, provider: str, cred_id: uuid.UUID) -> str:
    return f"byok:{merchant_id}:{provider}:{cred_id}"


def _validate(provider: str, api_key: str) -> None:
    if provider not in BYOK_PROVIDERS:
        raise ValidationFailed("Unsupported provider", details={"fields": [{"loc": ["body", "provider"]}]})
    if not (20 <= len(api_key) <= 400) or any(c.isspace() for c in api_key):
        raise ValidationFailed("That does not look like a valid API key", code="invalid_api_key")


def _get(db: Session, merchant_id: uuid.UUID, cred_id: uuid.UUID) -> ProviderCredential:
    c = db.get(ProviderCredential, cred_id)
    if c is None or c.merchant_id != merchant_id:
        raise NotFound()
    return c


def create(
    db: Session, ctx: TenantContext, provider: str, api_key: str, fallback_to_platform: bool
) -> ProviderCredential:
    entitlements.require_feature(db, ctx.merchant_id, "ai.byok")
    _validate(provider, api_key)
    existing = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.merchant_id == ctx.merchant_id,
            ProviderCredential.provider == provider,
            ProviderCredential.status == "active",
        )
    )
    if existing is not None:
        return rotate(db, ctx, existing.id, api_key, fallback_to_platform)
    cred = ProviderCredential(
        id=uuid.uuid4(),
        merchant_id=ctx.merchant_id,
        provider=provider,
        key_last4=api_key[-4:],
        fallback_to_platform=fallback_to_platform,
        created_by_user_id=ctx.actor.id,
    )
    cred.key_sealed = SealedSecret.seal(api_key, _aad(ctx.merchant_id, provider, cred.id)).blob
    db.add(cred)
    db.flush()
    audit.record(
        db,
        action="ai.byok_credential_created",
        resource_type="ai_credential",
        resource_id=cred.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={
            "provider": provider,
            "key_last4": cred.key_last4,
            "fallback_to_platform": fallback_to_platform,
        },
    )
    return cred


def rotate(
    db: Session,
    ctx: TenantContext,
    cred_id: uuid.UUID,
    api_key: str,
    fallback_to_platform: bool | None = None,
) -> ProviderCredential:
    entitlements.require_feature(db, ctx.merchant_id, "ai.byok")
    cred = _get(db, ctx.merchant_id, cred_id)
    if cred.status != "active":
        raise NotFound()
    _validate(cred.provider, api_key)
    cred.key_sealed = SealedSecret.seal(api_key, _aad(ctx.merchant_id, cred.provider, cred.id)).blob
    old_last4, cred.key_last4 = cred.key_last4, api_key[-4:]
    cred.rotated_at = utcnow()
    cred.last_test_ok = None
    if fallback_to_platform is not None:
        cred.fallback_to_platform = fallback_to_platform
    audit.record(
        db,
        action="ai.byok_credential_rotated",
        resource_type="ai_credential",
        resource_id=cred.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"key_last4": [old_last4, cred.key_last4]},
    )
    return cred


def revoke(db: Session, ctx: TenantContext, cred_id: uuid.UUID) -> None:
    cred = _get(db, ctx.merchant_id, cred_id)
    if cred.status == "revoked":
        return
    cred.status = "revoked"
    cred.revoked_at = utcnow()
    cred.key_sealed = None  # crypto-shred: ciphertext removed on revoke
    audit.record(
        db,
        action="ai.byok_credential_revoked",
        resource_type="ai_credential",
        resource_id=cred.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": cred.provider},
    )


def test(db: Session, ctx: TenantContext, cred_id: uuid.UUID) -> bool:
    from app.domains.ai.gateway import ADAPTERS

    cred = _get(db, ctx.merchant_id, cred_id)
    if cred.status != "active" or not cred.key_sealed:
        raise NotFound()
    key = SealedSecret(cred.key_sealed).open(_aad(cred.merchant_id, cred.provider, cred.id))
    ok = ADAPTERS[cred.provider](key).health_check(timeout_s=10)
    cred.last_tested_at = utcnow()
    cred.last_test_ok = ok
    audit.record(
        db,
        action="ai.byok_credential_tested",
        resource_type="ai_credential",
        resource_id=cred.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"ok": ok},
    )
    return ok


def active_keys(db: Session, merchant_id: uuid.UUID) -> dict[str, tuple[str, bool]]:
    """provider -> (plaintext key, fallback_to_platform). Plaintext lives only in worker memory."""
    out: dict[str, tuple[str, bool]] = {}
    for c in db.scalars(
        select(ProviderCredential).where(
            ProviderCredential.merchant_id == merchant_id, ProviderCredential.status == "active"
        )
    ):
        if c.key_sealed:
            out[c.provider] = (
                SealedSecret(c.key_sealed).open(_aad(merchant_id, c.provider, c.id)),
                c.fallback_to_platform,
            )
    return out
