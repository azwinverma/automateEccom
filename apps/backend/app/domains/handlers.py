"""Outbox event handlers. Imported by the worker so registrations happen at startup."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

import app.domains.catalog.imports
import app.domains.channels.service
import app.domains.media.service
import app.domains.media.video
import app.domains.studio.service
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
    app.domains.catalog.imports,
    app.domains.channels.service,
    app.domains.media.service,
    app.domains.media.video,
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


@handler("platform.ping")
def ping(db: Session, ev: OutboxEvent) -> None:
    return None
