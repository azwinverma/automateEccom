"""Outbox event handlers. Imported by the worker so registrations happen at startup."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

import app.domains.automation.engine
import app.domains.catalog.imports
import app.domains.channels.service
import app.domains.content.autopost
import app.domains.fulfillment.service
import app.domains.inbox.agent
import app.domains.inbox.service
import app.domains.intelligence.cod_risk
import app.domains.intelligence.product_brain
import app.domains.media.service
import app.domains.media.video
import app.domains.orders.service
import app.domains.payments.service
import app.domains.retention.service
import app.domains.returns.service
import app.domains.studio.service
import app.domains.twin.service
import app.domains.twin.simulation
from app.core.config import get_settings
from app.core.crypto import SealedSecret
from app.domains.accounts.models import User
from app.domains.accounts.service import issue_email_verification
from app.domains.merchants.models import Invitation, Merchant
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler
from app.integrations_i18n import email_copy

# Modules whose import registers outbox handlers (referenced so the import is explicit, not accidental).
HANDLER_MODULES = (
    app.domains.automation.engine,
    app.domains.catalog.imports,
    app.domains.channels.service,
    app.domains.content.autopost,
    app.domains.fulfillment.service,
    app.domains.inbox.agent,
    app.domains.inbox.service,
    app.domains.intelligence.cod_risk,
    app.domains.intelligence.product_brain,
    app.domains.twin.service,
    app.domains.twin.simulation,
    app.domains.media.service,
    app.domains.media.video,
    app.domains.orders.service,
    app.domains.payments.service,
    app.domains.retention.service,
    app.domains.returns.service,
    app.domains.studio.service,
)

WEB_BASE_URL_DEFAULT = "http://localhost:3010"


def _web_base() -> str:
    origins = get_settings().cors_origins
    return origins[0] if origins else WEB_BASE_URL_DEFAULT


@handler("accounts.email_verification_requested")
def send_email_verification(db: Session, ev: OutboxEvent) -> None:
    from app.domains.integrations.registry import mailer

    user = db.get(User, uuid.UUID(ev.payload["user_id"]))
    if user is None or user.email_verified_at is not None:
        return
    token = issue_email_verification(db, user)
    subject, body = email_copy(
        "verify_email", user.locale, link=f"{_web_base()}/verify-email?token={token}", name=user.full_name
    )
    mailer().send_email(user.email, subject, body, idempotency_key=f"verify:{ev.id}", locale=user.locale)


@handler("accounts.password_reset_requested")
def send_password_reset(db: Session, ev: OutboxEvent) -> None:
    from app.domains.accounts.service import issue_password_reset
    from app.domains.integrations.registry import mailer

    user = db.get(User, uuid.UUID(ev.payload["user_id"]))
    if user is None or user.status != "active":
        return
    token = issue_password_reset(db, user)
    subject, body = email_copy(
        "password_reset", user.locale, link=f"{_web_base()}/reset-password?token={token}", name=user.full_name
    )
    mailer().send_email(user.email, subject, body, idempotency_key=f"pwreset:{ev.id}", locale=user.locale)


@handler("accounts.password_changed")
def send_password_changed(db: Session, ev: OutboxEvent) -> None:
    from app.domains.integrations.registry import mailer

    user = db.get(User, uuid.UUID(ev.payload["user_id"]))
    if user is None:
        return
    subject, body = email_copy(
        "password_changed", user.locale, name=user.full_name, link=f"{_web_base()}/login"
    )
    mailer().send_email(user.email, subject, body, idempotency_key=f"pwchanged:{ev.id}", locale=user.locale)


@handler("merchants.invitation_created")
def send_invitation(db: Session, ev: OutboxEvent) -> None:
    from app.domains.integrations.registry import mailer

    inv = db.get(Invitation, uuid.UUID(ev.payload["invitation_id"]))
    if inv is None or inv.status != "pending" or not inv.token_sealed:
        return
    merchant = db.get(Merchant, inv.merchant_id)
    token = SealedSecret(inv.token_sealed).open(f"invitation:{inv.id}")
    locale = merchant.default_locale if merchant else "en"
    subject, body = email_copy(
        "team_invite",
        locale,
        link=f"{_web_base()}/invite?token={token}",
        shop=merchant.name if merchant else "",
        role=inv.role,
    )
    mailer().send_email(inv.email, subject, body, idempotency_key=f"invite:{ev.id}", locale=locale)


@handler("billing.usage_threshold_reached")
def send_usage_alert(db: Session, ev: OutboxEvent) -> None:
    """BIL-009: tell the people who decide on money (owner, admins) once per threshold per period."""
    from sqlalchemy import select

    from app.domains.integrations.registry import mailer
    from app.domains.merchants.models import Membership
    from app.integrations_i18n import resource_name

    merchant = db.get(Merchant, ev.merchant_id) if ev.merchant_id else None
    if merchant is None:
        return
    p = ev.payload
    threshold = int(p["threshold"])
    key = "usage_limit_reached" if threshold >= 100 else "usage_warning"
    recipients = db.execute(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.merchant_id == merchant.id,
            Membership.status == "active",
            Membership.role.in_(("owner", "admin")),
            User.status == "active",
        )
        .execution_options(skip_tenant_filter=True)
    ).scalars()
    for user in recipients:
        locale = user.locale or merchant.default_locale or "en"
        subject, body = email_copy(
            key,
            locale,
            name=user.full_name,
            shop=merchant.name,
            resource=resource_name(p["resource"], locale),
            threshold=str(threshold),
            used=str(p["used"]),
            limit=str(p["limit"]),
            link=f"{_web_base()}/settings/plan",
        )
        mailer().send_email(
            user.email, subject, body, idempotency_key=f"usage:{ev.id}:{user.id}", locale=locale
        )


@handler("platform.ping")
def ping(db: Session, ev: OutboxEvent) -> None:
    return None
