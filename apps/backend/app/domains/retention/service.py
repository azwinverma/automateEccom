"""Retain: campaigns that bring customers back, sent through the channel they already chat on.

Rules that keep this from becoming spam:
* Only customers who have messaged the shop on a connected channel can be reached (no cold outreach).
* A customer who replies STOP (or बन्द / रोक) is never messaged by a campaign again.
* At most one campaign message per customer per 7 days, only between 09:00 and 20:00 shop time,
  and each campaign has a daily limit.
* WhatsApp, Messenger and Instagram only allow free-form messages within 24 hours of the
  customer's last message, so those customers are deferred until they write again (WhatsApp
  templates / Messenger tags: GAP-WA-TEMPLATES).
* A message counts as converting when the customer orders within 7 days of it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements
from app.domains.channels.models import ChannelConnection
from app.domains.customers.models import Customer
from app.domains.inbox.models import Conversation
from app.domains.orders.models import Order, OrderLine
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler
from app.domains.retention.models import Campaign, CampaignMessage

log = structlog.get_logger(__name__)
FEATURE = "marketing.campaigns"
FREQUENCY_CAP = timedelta(days=7)
ATTRIBUTION_WINDOW = timedelta(days=7)
WHATSAPP_WINDOW = timedelta(hours=24)
# Channels where a business may only send free-form messages within 24 h of the customer's last one.
WINDOWED_PROVIDERS = frozenset({"whatsapp_cloud", "facebook_page", "instagram"})
SEND_HOURS = range(9, 20)  # 09:00 to 19:59 shop time
DEFAULT_DAYS = {"win_back": 60, "repeat_reminder": 30}
SEGMENTS = ("all", "repeat", "new", "inactive")
STOP_WORDS = frozenset({"stop", "unsubscribe", "बन्द", "रोक", "stop please"})
PLACEHOLDERS = ("{name}", "{shop}", "{product}")
OPT_OUT_LINE = {"en": "Reply STOP to stop these messages.", "ne": "यस्ता सन्देश रोक्न STOP लेख्नुहोस्।"}
TEMPLATES: dict[str, dict[str, str]] = {
    "win_back": {
        "en": (
            "Namaste {name}! It's been a while. {shop} has new arrivals you might like. "
            "Reply here to see them."
        ),
        "ne": "नमस्ते {name}! धेरै भयो भेट नभएको। {shop} मा नयाँ सामान आएका छन्। हेर्न यहीँ लेख्नुहोस्।",
    },
    "repeat_reminder": {
        "en": (
            "Hi {name}, how is your {product}? If you'd like another or something to go with it, "
            "just reply here."
        ),
        "ne": "नमस्ते {name}, {product} कस्तो छ? अर्को चाहिएमा वा मिल्दो केही चाहिएमा यहीँ लेख्नुहोस्।",
    },
    "broadcast": {
        "en": "Hi {name}, {shop} here with something new this week. Reply to see it.",
        "ne": "नमस्ते {name}, {shop} बाट यो हप्ता नयाँ कुरा। हेर्न जवाफ दिनुहोस्।",
    },
}


# ----------------------------------------------------------------------------- campaigns
def _validate(
    kind: str, days: int | None, segment: str | None, message_en: str, message_ne: str | None
) -> None:
    if kind not in TEMPLATES:
        raise ValidationFailed("Unknown campaign type", code="invalid_kind")
    if kind == "broadcast" and segment not in SEGMENTS:
        raise ValidationFailed("Choose who receives this", code="segment_required")
    if kind != "broadcast" and days is not None and not 1 <= days <= 365:
        raise ValidationFailed("Days must be between 1 and 365", code="invalid_days")
    for text in (message_en, message_ne or ""):
        if len(text) > 900:
            raise ValidationFailed("Keep the message under 900 characters", code="message_too_long")
        stray = [w for w in _braces(text) if w not in PLACEHOLDERS]
        if stray:
            raise ValidationFailed(
                f"Unknown placeholder {stray[0]}. Use {{name}}, {{shop}} or {{product}}.",
                code="bad_placeholder",
            )
    if not message_en.strip():
        raise ValidationFailed("Write the message", code="message_required")


def _braces(text: str) -> list[str]:
    import re

    return re.findall(r"\{[^{}]*\}", text)


def create(
    db: Session,
    ctx: TenantContext,
    *,
    name: str,
    kind: str,
    days: int | None,
    segment: str | None,
    message_en: str | None,
    message_ne: str | None,
    daily_limit: int,
) -> Campaign:
    entitlements.require_feature(db, ctx.merchant_id, FEATURE)
    message_en = (message_en or TEMPLATES.get(kind, {}).get("en", "")).strip()
    message_ne = (
        message_ne if message_ne is not None else TEMPLATES.get(kind, {}).get("ne", "")
    ).strip() or None
    _validate(kind, days, segment, message_en, message_ne)
    c = Campaign(
        merchant_id=ctx.merchant_id,
        name=name.strip()[:120],
        kind=kind,
        days=None if kind == "broadcast" else (days or DEFAULT_DAYS[kind]),
        segment=segment if kind == "broadcast" else None,
        message_en=message_en,
        message_ne=message_ne,
        daily_limit=daily_limit,
        created_by_user_id=ctx.actor.id,
    )
    db.add(c)
    db.flush()
    audit.record(
        db,
        action="retention.campaign_created",
        resource_type="campaign",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"kind": kind},
    )
    return c


def get(db: Session, ctx: TenantContext, cid: uuid.UUID) -> Campaign:
    c = db.get(Campaign, cid)
    if c is None or c.merchant_id != ctx.merchant_id:
        raise NotFound(code="campaign_not_found")
    return c


def update(db: Session, ctx: TenantContext, cid: uuid.UUID, **fields: Any) -> Campaign:
    c = get(db, ctx, cid)
    if c.status == "completed":
        raise Conflict("A finished campaign can't be changed", code="campaign_completed")
    for k in ("name", "days", "segment", "message_en", "message_ne", "daily_limit"):
        if fields.get(k) is not None:
            setattr(c, k, fields[k].strip() if isinstance(fields[k], str) else fields[k])
    _validate(c.kind, c.days, c.segment, c.message_en, c.message_ne)
    return c


def set_status(db: Session, ctx: TenantContext, cid: uuid.UUID, status: str) -> Campaign:
    c = get(db, ctx, cid)
    allowed = {"draft": {"active"}, "active": {"paused", "completed"}, "paused": {"active", "completed"}}
    if status not in allowed.get(c.status, set()):
        raise Conflict(f"Can't go from {c.status} to {status}", code="invalid_transition")
    if status == "active":
        entitlements.require_feature(db, ctx.merchant_id, FEATURE)
        c.activated_at = c.activated_at or utcnow()
    if status == "completed":
        c.completed_at = utcnow()
    c.status = status
    audit.record(
        db,
        action=f"retention.campaign_{status}",
        resource_type="campaign",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"kind": c.kind},
    )
    return c


# ----------------------------------------------------------------------------- audience
def _live_orders(merchant_id: uuid.UUID) -> Any:
    return (
        select(
            Order.customer_id.label("customer_id"),
            func.count().label("n"),
            func.max(Order.placed_at).label("last"),
        )
        .where(Order.merchant_id == merchant_id, Order.status != "cancelled", Order.customer_id.is_not(None))
        .group_by(Order.customer_id)
        .subquery()
    )


def audience(db: Session, c: Campaign, now: datetime) -> list[tuple[uuid.UUID, str, dict[str, Any]]]:
    """(customer id, cycle key, context) for everyone this campaign is meant for right now."""
    live = _live_orders(c.merchant_id)
    if c.kind == "win_back":
        rows = db.execute(
            select(live.c.customer_id, live.c.last).where(live.c.last < now - timedelta(days=c.days or 60))
        ).all()
        # One win-back per lapse: the key is the last order, so a new order and a new lapse re-qualify.
        return [(r.customer_id, f"lapse:{r.last.date().isoformat()}", {}) for r in rows]
    if c.kind == "repeat_reminder":
        lo, hi = now - timedelta(days=(c.days or 30) + 7), now - timedelta(days=c.days or 30)
        rows = db.execute(
            select(Order.id, Order.customer_id)
            .where(
                Order.merchant_id == c.merchant_id,
                Order.status == "delivered",
                Order.customer_id.is_not(None),
                Order.placed_at.between(lo, hi),
            )
            .order_by(Order.placed_at)
        ).all()
        out = []
        for r in rows:
            title = db.scalar(
                select(OrderLine.title).where(OrderLine.order_id == r.id).order_by(OrderLine.id).limit(1)
            )
            out.append((r.customer_id, f"order:{r.id}", {"product": title or ""}))
        return out
    # broadcast: once per customer
    stmt = select(Customer.id).where(Customer.merchant_id == c.merchant_id, Customer.status == "active")
    if c.segment != "all":
        stmt = stmt.outerjoin(live, live.c.customer_id == Customer.id)
        if c.segment == "new":
            stmt = stmt.where(func.coalesce(live.c.n, 0) <= 1)
        elif c.segment == "repeat":
            stmt = stmt.where(live.c.n >= 2)
        else:
            stmt = stmt.where(live.c.last < now - timedelta(days=90))
    return [(cid, "once", {}) for cid in db.scalars(stmt)]


def _reachable(db: Session, customer_id: uuid.UUID, now: datetime) -> tuple[Conversation | None, str | None]:
    conv = db.scalar(
        select(Conversation)
        .join(ChannelConnection, ChannelConnection.id == Conversation.connection_id)
        .where(
            Conversation.customer_id == customer_id,
            ChannelConnection.status == "connected",
            ChannelConnection.capabilities.contains(["messages"]),
        )
        .order_by(Conversation.last_inbound_at.desc().nulls_last())
        .limit(1)
    )
    if conv is None:
        return None, "no_chat_channel"
    if conv.provider in WINDOWED_PROVIDERS and (
        conv.last_inbound_at is None or now - conv.last_inbound_at > WHATSAPP_WINDOW
    ):
        return None, "whatsapp_window_closed"
    return conv, None


def _render(c: Campaign, customer: Customer, shop: str, ctx: dict[str, Any], locale: str) -> str:
    body = c.message_ne if locale == "ne" and c.message_ne else c.message_en
    first = (customer.display_name or "").split(" ")[0] or ("साथी" if locale == "ne" else "there")
    product = ctx.get("product") or ("सामान" if locale == "ne" else "order")
    text = body.replace("{name}", first).replace("{shop}", shop).replace("{product}", product)
    return f"{text}\n\n{OPT_OUT_LINE['ne' if locale == 'ne' else 'en']}"


# ----------------------------------------------------------------------------- running
def _in_send_hours(tz: str, now: datetime) -> bool:
    try:
        local = now.astimezone(ZoneInfo(tz))
    except Exception:
        local = now.astimezone(ZoneInfo("Asia/Kathmandu"))
    return local.hour in SEND_HOURS


def run_merchant(db: Session, merchant_id: uuid.UUID, now: datetime | None = None) -> dict[str, int]:
    from app.domains.inbox import service as inbox
    from app.domains.merchants.models import Merchant
    from app.domains.platform.flags import killed

    now = now or utcnow()
    stats = {"sent": 0, "skipped": 0, "deferred": 0}
    bind_tenant(db, merchant_id)
    merchant = db.get(Merchant, merchant_id)
    if (
        merchant is None
        or killed(db, "ops.campaigns", merchant_id)
        or not _in_send_hours(merchant.timezone, now)
    ):
        return stats
    if not entitlements.resolve(db, merchant_id).has(FEATURE):
        return stats
    for c in db.scalars(select(Campaign).where(Campaign.status == "active").order_by(Campaign.created_at)):
        sent_today = (
            db.scalar(
                select(func.count())
                .select_from(CampaignMessage)
                .where(
                    CampaignMessage.campaign_id == c.id, CampaignMessage.sent_at >= now - timedelta(days=1)
                )
            )
            or 0
        )
        budget = max(0, c.daily_limit - sent_today)
        for customer_id, key, extra in audience(db, c, now):
            done = db.scalar(
                select(CampaignMessage.id).where(
                    CampaignMessage.campaign_id == c.id,
                    CampaignMessage.customer_id == customer_id,
                    CampaignMessage.cycle_key == key,
                )
            )
            if done is not None:
                continue
            customer = db.get(Customer, customer_id)
            if customer is None or customer.status != "active":
                continue
            if customer.marketing_opt_out_at is not None:
                _record(db, c, customer_id, key, "skipped", reason="opted_out")
                stats["skipped"] += 1
                continue
            recent = db.scalar(
                select(CampaignMessage.id).where(
                    CampaignMessage.customer_id == customer_id,
                    CampaignMessage.status == "sent",
                    CampaignMessage.sent_at >= now - FREQUENCY_CAP,
                )
            )
            if recent is not None or budget <= 0:
                stats["deferred"] += 1  # tried again on a later run
                continue
            conv, why = _reachable(db, customer_id, now)
            if conv is None:
                if why == "whatsapp_window_closed":
                    stats["deferred"] += 1  # may reopen if the customer writes again
                    continue
                _record(db, c, customer_id, key, "skipped", reason=why)
                stats["skipped"] += 1
                continue
            locale = customer.locale or conv.locale or merchant.default_locale
            msg = inbox.queue_reply(
                db,
                conv,
                _render(c, customer, merchant.name, extra, locale),
                author="system",
                grounding={"campaign_id": str(c.id)},
            )
            _record(db, c, customer_id, key, "sent", conversation_id=conv.id, message_id=msg.id, sent_at=now)
            stats["sent"] += 1
            budget -= 1
        c.last_run_at = now
        if c.kind == "broadcast":
            remaining = [a for a in audience(db, c, now) if not _done(db, c, a[0], a[1])]
            if not remaining:
                c.status, c.completed_at = "completed", now
    return stats


def _done(db: Session, c: Campaign, customer_id: uuid.UUID, key: str) -> bool:
    return (
        db.scalar(
            select(CampaignMessage.id).where(
                CampaignMessage.campaign_id == c.id,
                CampaignMessage.customer_id == customer_id,
                CampaignMessage.cycle_key == key,
            )
        )
        is not None
    )


def _record(
    db: Session,
    c: Campaign,
    customer_id: uuid.UUID,
    key: str,
    status: str,
    *,
    reason: str | None = None,
    **kw: Any,
) -> None:
    db.execute(
        pg_insert(CampaignMessage)
        .values(
            id=uuid.uuid4(),
            merchant_id=c.merchant_id,
            campaign_id=c.id,
            customer_id=customer_id,
            cycle_key=key,
            status=status,
            skip_reason=reason,
            meta={},
            created_at=utcnow(),
            updated_at=utcnow(),
            **kw,
        )
        .on_conflict_do_nothing(index_elements=["campaign_id", "customer_id", "cycle_key"])
    )


def run_all(db: Session) -> dict[str, int]:
    total = {"merchants": 0, "sent": 0, "skipped": 0, "deferred": 0}
    ids = list(
        db.scalars(
            select(Campaign.merchant_id)
            .where(Campaign.status == "active")
            .distinct()
            .execution_options(skip_tenant_filter=True)
        )
    )
    for mid in ids:
        with db.begin_nested():
            s = run_merchant(db, mid)
        total["merchants"] += 1
        for k in ("sent", "skipped", "deferred"):
            total[k] += s[k]
    return total


# ----------------------------------------------------------------------------- consent and results
def is_stop(text: str) -> bool:
    return text.strip().lower().strip(".!। ") in STOP_WORDS


def opt_out(db: Session, customer: Customer) -> bool:
    if customer.marketing_opt_out_at is not None:
        return False
    customer.marketing_opt_out_at = utcnow()
    audit.record(
        db,
        action="customers.marketing_opted_out",
        resource_type="customer",
        resource_id=customer.id,
        actor=_system(),
        merchant_id=customer.merchant_id,
    )
    return True


def _system() -> Any:
    from app.core.context import Actor

    return Actor.system("retention")


@handler("orders.created", name="retention.attribute_conversion")
def _attribute(db: Session, ev: OutboxEvent) -> None:
    o = db.get(Order, uuid.UUID(ev.payload["order_id"])) if ev.payload.get("order_id") else None
    if o is None or o.customer_id is None:
        return
    bind_tenant(db, o.merchant_id)
    m = db.scalar(
        select(CampaignMessage)
        .where(
            CampaignMessage.customer_id == o.customer_id,
            CampaignMessage.status == "sent",
            CampaignMessage.converted_order_id.is_(None),
            CampaignMessage.sent_at.between(o.placed_at - ATTRIBUTION_WINDOW, o.placed_at),
        )
        .order_by(CampaignMessage.sent_at.desc())
        .limit(1)
    )
    if m is not None:
        m.converted_order_id, m.converted_minor = o.id, o.total_minor


def stats(db: Session, c: Campaign) -> dict[str, Any]:
    rows = db.execute(
        select(
            CampaignMessage.status,
            CampaignMessage.skip_reason,
            func.count(),
            func.count(CampaignMessage.converted_order_id),
            func.coalesce(func.sum(CampaignMessage.converted_minor), 0),
        )
        .where(CampaignMessage.campaign_id == c.id)
        .group_by(CampaignMessage.status, CampaignMessage.skip_reason)
    ).all()
    out: dict[str, Any] = {"sent": 0, "skipped": {}, "orders": 0, "revenue_minor": 0}
    for status, reason, n, conv, rev in rows:
        if status == "sent":
            out["sent"] += n
            out["orders"] += conv
            out["revenue_minor"] += int(rev or 0)
        elif status == "skipped":
            out["skipped"][reason or "other"] = n
    replied = (
        db.scalar(
            select(func.count(func.distinct(CampaignMessage.id)))
            .select_from(CampaignMessage)
            .join(Conversation, Conversation.id == CampaignMessage.conversation_id)
            .where(
                CampaignMessage.campaign_id == c.id,
                and_(Conversation.last_inbound_at > CampaignMessage.sent_at),
            )
        )
        or 0
    )
    out["replied"] = replied
    return out


def preview(db: Session, ctx: TenantContext, cid: uuid.UUID) -> dict[str, Any]:
    """Who this campaign would reach now, and who can't be reached (and why). Sends nothing."""
    c = get(db, ctx, cid)
    now = utcnow()
    reach, why_not = 0, dict[str, int]()
    people = audience(db, c, now)
    for customer_id, key, _ in people[:2000]:
        if _done(db, c, customer_id, key):
            continue
        cust = db.get(Customer, customer_id)
        if cust is None:
            continue
        if cust.marketing_opt_out_at is not None:
            why_not["opted_out"] = why_not.get("opted_out", 0) + 1
            continue
        conv, why = _reachable(db, customer_id, now)
        if conv is None:
            why_not[why or "other"] = why_not.get(why or "other", 0) + 1
        else:
            reach += 1
    sample = _render(
        c, Customer(display_name="Sita Gurung"), ctx_name(db, ctx), {"product": "Dhaka Kurta"}, "en"
    )
    return {"audience": len(people), "reachable": reach, "unreachable": why_not, "sample_en": sample}


def ctx_name(db: Session, ctx: TenantContext) -> str:
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, ctx.merchant_id)
    return m.name if m else ""


def view(db: Session, c: Campaign, *, with_stats: bool = True) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "name": c.name,
        "kind": c.kind,
        "status": c.status,
        "days": c.days,
        "segment": c.segment,
        "message_en": c.message_en,
        "message_ne": c.message_ne,
        "daily_limit": c.daily_limit,
        "activated_at": c.activated_at.isoformat() if c.activated_at else None,
        "last_run_at": c.last_run_at.isoformat() if c.last_run_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        **({"stats": stats(db, c)} if with_stats else {}),
    }
