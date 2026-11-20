"""A seller's own payment gateways (Khalti, eSewa): connect, test, rotate, default, disconnect.

Secrets are sealed with envelope encryption (per-record data key, AAD = merchant + provider + row id),
opened only in memory when calling the provider, never returned by the API, never logged.
Disconnecting destroys the ciphertext.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.crypto import SealedSecret
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.integrations.base import IntegrationError
from app.domains.integrations.nepal_payments import EsewaAdapter, KhaltiAdapter, _RedirectGateway
from app.domains.payments.models import PaymentGateway

PROVIDERS: dict[str, type[_RedirectGateway]] = {"khalti": KhaltiAdapter, "esewa": EsewaAdapter}
_transport_override: Any = None  # tests: an httpx.MockTransport for every gateway call


def catalog() -> list[dict[str, Any]]:
    return [
        {
            "code": c.code,
            "name": c.display_name,
            "secret_fields": list(c.credential_fields),
            "public_fields": list(c.config_fields),
            "modes": ["test", "live"],
        }
        for c in PROVIDERS.values()
    ]


def _aad(g: PaymentGateway) -> str:
    return f"payment-gateway:{g.merchant_id}:{g.provider}:{g.id}"


def adapter_for(g: PaymentGateway) -> _RedirectGateway:
    if g.status == "disconnected" or not g.credentials_sealed:
        raise IntegrationError("gateway_disconnected", g.provider)
    creds = json.loads(SealedSecret(g.credentials_sealed).open(_aad(g)))
    config: dict[str, Any] = {"mode": g.mode}
    if g.public_id:
        config["product_code"] = g.public_id
    if _transport_override is not None:
        config["_transport"] = _transport_override
    return PROVIDERS[g.provider](creds, config)


def default_gateway(db: Session, merchant_id: uuid.UUID) -> PaymentGateway | None:
    rows = list(
        db.scalars(
            select(PaymentGateway)
            .where(PaymentGateway.merchant_id == merchant_id, PaymentGateway.status == "active")
            .order_by(PaymentGateway.is_default.desc(), PaymentGateway.created_at)
        )
    )
    return rows[0] if rows else None


def _get(db: Session, ctx: TenantContext, gid: uuid.UUID) -> PaymentGateway:
    g = db.get(PaymentGateway, gid)
    if g is None or g.merchant_id != ctx.merchant_id or g.status == "disconnected":
        raise NotFound(code="gateway_not_found")
    return g


def _validate(provider: str, secret_key: str, public_id: str | None) -> None:
    if provider not in PROVIDERS:
        raise ValidationFailed("Unsupported payment gateway", code="unsupported_gateway")
    if not (8 <= len(secret_key) <= 200) or any(c in secret_key for c in "\r\n\t"):
        raise ValidationFailed("That doesn't look like a secret key", code="invalid_secret_key")
    if PROVIDERS[provider].config_fields and not (public_id and 2 <= len(public_id) <= 80):
        raise ValidationFailed("Enter the merchant (product) code from eSewa", code="product_code_required")


def _check(g: PaymentGateway) -> None:
    try:
        ok = adapter_for(g).check_credentials()
    except IntegrationError as e:
        g.verified, g.last_error_code = None, e.code
        return
    g.verified = ok
    g.status = "error" if ok is False else "active"
    g.last_error_code = "invalid_credentials" if ok is False else None


def connect(
    db: Session,
    ctx: TenantContext,
    *,
    provider: str,
    mode: str,
    secret_key: str,
    public_id: str | None,
    make_default: bool,
) -> PaymentGateway:
    secret_key, public_id = secret_key.strip(), (public_id or "").strip() or None
    _validate(provider, secret_key, public_id)
    g = db.scalar(
        select(PaymentGateway).where(
            PaymentGateway.merchant_id == ctx.merchant_id,
            PaymentGateway.provider == provider,
            PaymentGateway.status != "disconnected",
        )
    )
    action = "payments.gateway_rotated" if g is not None else "payments.gateway_connected"
    if g is None:
        g = PaymentGateway(
            id=uuid.uuid4(), merchant_id=ctx.merchant_id, provider=provider, connected_by_user_id=ctx.actor.id
        )
        db.add(g)
    g.mode, g.public_id, g.secret_last4 = mode, public_id, secret_key[-4:]
    g.credentials_sealed = SealedSecret.seal(json.dumps({"secret_key": secret_key}), _aad(g)).blob
    g.status, g.last_error_code = "active", None
    db.flush()
    _check(g)
    if make_default or default_gateway(db, ctx.merchant_id) in (None, g):
        _make_default(db, ctx, g)
    audit.record(
        db,
        action=action,
        resource_type="payment_gateway",
        resource_id=g.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": provider, "mode": mode, "verified": g.verified},  # never the secret
    )
    return g


def _make_default(db: Session, ctx: TenantContext, g: PaymentGateway) -> None:
    for other in db.scalars(
        select(PaymentGateway).where(
            PaymentGateway.merchant_id == ctx.merchant_id, PaymentGateway.is_default.is_(True)
        )
    ):
        if other.id != g.id:
            other.is_default = False
    db.flush()
    g.is_default = True
    db.flush()


def set_default(db: Session, ctx: TenantContext, gid: uuid.UUID) -> PaymentGateway:
    g = _get(db, ctx, gid)
    if g.status != "active":
        raise Conflict("Fix this gateway's keys before using it for payments", code="gateway_not_active")
    _make_default(db, ctx, g)
    audit.record(
        db,
        action="payments.gateway_default_changed",
        resource_type="payment_gateway",
        resource_id=g.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": g.provider},
    )
    return g


def test(db: Session, ctx: TenantContext, gid: uuid.UUID) -> PaymentGateway:
    g = _get(db, ctx, gid)
    _check(g)
    return g


def disconnect(db: Session, ctx: TenantContext, gid: uuid.UUID) -> None:
    g = _get(db, ctx, gid)
    g.status, g.is_default, g.disconnected_at = "disconnected", False, utcnow()
    g.credentials_sealed = None  # crypto-shred: the ciphertext is gone, not just hidden
    audit.record(
        db,
        action="payments.gateway_disconnected",
        resource_type="payment_gateway",
        resource_id=g.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"provider": g.provider},
    )


def view(g: PaymentGateway) -> dict[str, Any]:
    return {
        "id": str(g.id),
        "provider": g.provider,
        "name": PROVIDERS[g.provider].display_name,
        "mode": g.mode,
        "status": g.status,
        "is_default": g.is_default,
        "public_id": g.public_id,
        "secret_hint": f"••••{g.secret_last4}" if g.secret_last4 else None,
        "verified": g.verified,
        "last_error_code": g.last_error_code,
        "last_payment_at": g.last_payment_at.isoformat() if g.last_payment_at else None,
        "connected_at": g.created_at.isoformat() if g.created_at else None,
    }
