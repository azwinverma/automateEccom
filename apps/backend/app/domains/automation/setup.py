"""Autopilot setup: one place that says what's connected and turns the recommended automations on.

``readiness`` is the end-to-end selling checklist (where customers chat, how they pay, how orders
ship, what gets posted, what runs by itself), each step with its state and the next action.
``apply`` switches on the recommended set in one go: the shop's automation mode, the workflow
templates (book the courier when packed, follow up failed deliveries, ask for a review, thank first
orders, low-stock alerts), automatic posting to the accounts that can post, and a win-back campaign.
Everything stays within the Decision Policy and plan limits; each change is audited.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.errors import PermissionDenied
from app.domains.audit import service as audit
from app.domains.automation.models import Workflow
from app.domains.billing.service import entitlements
from app.domains.channels.models import ChannelConnection

RECOMMENDED_WORKFLOWS: dict[str, str] = {
    "book_courier_when_packed": "Book the courier when an order is packed",
    "failed_delivery_followup": "Follow up failed deliveries",
    "review_request_after_delivery": "Ask for a review after delivery",
    "thank_first_order": "Thank customers for their first order",
    "low_stock_alert": "Tell me when stock runs low",
}


def _connections(db: Session, merchant_id: Any) -> list[ChannelConnection]:
    return list(
        db.scalars(
            select(ChannelConnection).where(
                ChannelConnection.merchant_id == merchant_id, ChannelConnection.status != "disconnected"
            )
        )
    )


def readiness(db: Session, merchant_id: Any) -> dict[str, Any]:
    from app.domains.content.autopost import get_settings_row
    from app.domains.fulfillment.models import CourierAccount
    from app.domains.merchants.models import Merchant
    from app.domains.payments.models import PaymentGateway
    from app.domains.retention.models import Campaign

    m = db.get(Merchant, merchant_id)
    ent = entitlements.resolve(db, merchant_id)
    conns = _connections(db, merchant_id)
    live = [c for c in conns if c.status == "connected"]
    needs_reconnect = [c.display_name for c in conns if c.status == "expired"]
    chat = [c for c in live if "messages" in c.capabilities and c.provider != "sandbox_channel"]
    post = [c for c in live if "content_publish" in c.capabilities and c.provider != "sandbox_channel"]
    gateways = list(
        db.scalars(
            select(PaymentGateway).where(
                PaymentGateway.merchant_id == merchant_id, PaymentGateway.status == "active"
            )
        )
    )
    couriers = list(
        db.scalars(
            select(CourierAccount).where(
                CourierAccount.merchant_id == merchant_id, CourierAccount.status == "connected"
            )
        )
    )
    api_couriers = [a for a in couriers if a.provider != "manual"]
    auto = get_settings_row(db, merchant_id)
    installed = {
        w.template_code: w.status
        for w in db.scalars(
            select(Workflow).where(Workflow.merchant_id == merchant_id, Workflow.template_code.is_not(None))
        )
    }
    winback = db.scalar(
        select(func.count())
        .select_from(Campaign)
        .where(Campaign.merchant_id == merchant_id, Campaign.kind == "win_back", Campaign.status == "active")
    )

    def step(key: str, state: str, detail: str, action: str | None = None, **extra: Any) -> dict[str, Any]:
        return {"key": key, "state": state, "detail": detail, "action": action, **extra}

    steps = [
        step(
            "chat",
            "done" if chat else "todo",
            ", ".join(c.display_name for c in chat)
            if chat
            else "Connect Telegram, WhatsApp or Facebook/Instagram so customers can message you",
            None if chat else "/settings/channels",
        ),
        step(
            "sales_agent",
            "done"
            if ent.has("ai.sales_agent") and m is not None and m.automation_mode != "assisted"
            else ("blocked" if not ent.has("ai.sales_agent") else "todo"),
            "The AI Sales Agent answers price, stock and delivery questions and takes orders"
            if ent.has("ai.sales_agent")
            else "The AI Sales Agent is on the Growth plan and above",
            None if ent.has("ai.sales_agent") else "/settings/plan",
            mode=m.automation_mode if m else None,
        ),
        step(
            "payments",
            "done" if gateways else "partial",
            ", ".join(f"{g.provider} ({g.mode})" for g in gateways) if gateways else "Cash on delivery only",
            None if gateways else "/settings/payments",
        ),
        step(
            "delivery",
            "done" if api_couriers else ("partial" if couriers else "todo"),
            ", ".join(a.display_name for a in couriers)
            if couriers
            else "Add your courier or your own riders",
            None if api_couriers else "/settings/couriers",
        ),
        step(
            "posting",
            "done" if auto and auto.enabled else ("todo" if post else "blocked"),
            "New products are posted automatically"
            if auto and auto.enabled
            else (
                "Turn on automatic posting"
                if post
                else "Connect a Facebook Page or Instagram account to post"
            ),
            None if auto and auto.enabled else ("/content" if post else "/settings/channels"),
        ),
        step(
            "workflows",
            "done"
            if all(installed.get(k) == "active" for k in RECOMMENDED_WORKFLOWS)
            else ("blocked" if not ent.has("automation.workflows") else "todo"),
            f"{sum(1 for k in RECOMMENDED_WORKFLOWS if installed.get(k) == 'active')} of {len(RECOMMENDED_WORKFLOWS)} recommended automations on",
            "/automation",
            workflows=[
                {"code": k, "name": v, "status": installed.get(k)} for k, v in RECOMMENDED_WORKFLOWS.items()
            ],
        ),
        step(
            "campaigns",
            "done" if winback else ("blocked" if not ent.has("marketing.campaigns") else "todo"),
            "Win-back messages bring back quiet customers" if winback else "Start a win-back campaign",
            "/campaigns",
        ),
    ]
    done = sum(1 for s in steps if s["state"] == "done")
    return {"steps": steps, "done": done, "total": len(steps), "needs_reconnect": needs_reconnect}


def apply(db: Session, ctx: TenantContext, *, mode: str, posting: bool, campaigns: bool) -> dict[str, Any]:
    """Turn on what can be turned on. Returns what changed and what was skipped (and why)."""
    from app.domains.automation import engine
    from app.domains.automation.templates import BY_CODE
    from app.domains.content import autopost
    from app.domains.merchants import service as merchants
    from app.domains.retention import service as retention

    if not (ctx.has("automation.write") and ctx.has("automation.approve") and ctx.has("merchant.update")):
        raise PermissionDenied(details={"permission": "automation.approve"})
    ent = entitlements.resolve(db, ctx.merchant_id)
    changed: list[str] = []
    skipped: list[dict[str, str]] = []
    if mode == "autopilot" and not ent.has("automation.autopilot"):
        skipped.append({"item": "autopilot", "reason": "plan"})
        mode = "smart"
    merchants.update_merchant(db, ctx, automation_mode=mode)
    changed.append(f"mode:{mode}")
    if ent.has("automation.workflows"):
        existing = {
            w.template_code: w
            for w in db.scalars(
                select(Workflow).where(
                    Workflow.merchant_id == ctx.merchant_id, Workflow.template_code.is_not(None)
                )
            )
        }
        for code, name in RECOMMENDED_WORKFLOWS.items():
            w = existing.get(code)
            if w is None:
                w = engine.create(
                    db, ctx, name, BY_CODE[code]["definition"], description=None, template_code=code
                )
            if w.status != "active":
                engine.set_status(db, ctx, w.id, "active")
                changed.append(f"workflow:{code}")
    else:
        skipped.append({"item": "workflows", "reason": "plan"})
    if posting:
        can_post = [
            c.id
            for c in _connections(db, ctx.merchant_id)
            if c.status == "connected"
            and "content_publish" in c.capabilities
            and c.provider != "sandbox_channel"
        ]
        if can_post:
            row = autopost.get_settings_row(db, ctx.merchant_id)
            autopost.update_settings(
                db,
                ctx,
                enabled=True,
                connection_ids=can_post,
                kind=row.kind if row else "post",
                require_approval=row.require_approval if row else mode == "assisted",
            )
            changed.append("posting")
        else:
            skipped.append({"item": "posting", "reason": "no_account_can_post"})
    if campaigns:
        if ent.has("marketing.campaigns"):
            from app.domains.retention.models import Campaign

            c = db.scalar(
                select(Campaign)
                .where(Campaign.merchant_id == ctx.merchant_id, Campaign.kind == "win_back")
                .order_by(Campaign.created_at.desc())
            )
            if c is None:
                c = retention.create(
                    db,
                    ctx,
                    name="Win back quiet customers",
                    kind="win_back",
                    days=None,
                    segment=None,
                    message_en=None,
                    message_ne=None,
                    daily_limit=100,
                )
            if c.status in ("draft", "paused"):
                retention.set_status(db, ctx, c.id, "active")
                changed.append("campaign:win_back")
        else:
            skipped.append({"item": "campaigns", "reason": "plan"})
    audit.record(
        db,
        action="automation.setup_applied",
        resource_type="merchant",
        resource_id=ctx.merchant_id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"changed": changed, "skipped": skipped},
    )
    db.flush()  # the checklist below must see the changes (sessions don't autoflush)
    return {"changed": changed, "skipped": skipped, **readiness(db, ctx.merchant_id)}
