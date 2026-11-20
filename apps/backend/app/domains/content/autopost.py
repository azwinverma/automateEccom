"""Autopost: when a product goes live, post it to the accounts the seller chose.

* Caption: the AI Product Studio's caption for that channel's style when the product came from the
  Studio; otherwise a plain caption built from the product's own title, price and description
  (nothing invented). Photos: the product's photos, in order (up to 10).
* Timing: the shop's busiest order hour (Commerce Memory) or 7 pm shop time, the next time it comes.
* Approval: by default every autopost waits for the seller's approval (content.approve), and is
  scheduled for the next slot as soon as it's approved. Sellers can turn approval off; the shop's
  automation mode still applies (assisted mode always asks).
* Once per product per account; products without photos are skipped (and the seller is told why).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import ValidationFailed
from app.domains.audit import service as audit
from app.domains.channels.models import ChannelConnection
from app.domains.content.models import AutopostSettings, ContentPost
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)
DEFAULT_HOUR = 19
MIN_LEAD = timedelta(minutes=20)


def get_settings_row(db: Session, merchant_id: uuid.UUID) -> AutopostSettings | None:
    return db.scalar(select(AutopostSettings).where(AutopostSettings.merchant_id == merchant_id))


def _publishable(db: Session, merchant_id: uuid.UUID) -> list[ChannelConnection]:
    return list(
        db.scalars(
            select(ChannelConnection).where(
                ChannelConnection.merchant_id == merchant_id,
                ChannelConnection.status == "connected",
                ChannelConnection.capabilities.contains(["content_publish"]),
            )
        )
    )


def update_settings(
    db: Session,
    ctx: TenantContext,
    *,
    enabled: bool,
    connection_ids: list[uuid.UUID],
    kind: str,
    require_approval: bool,
) -> AutopostSettings:
    allowed = {c.id for c in _publishable(db, ctx.merchant_id)}
    bad = [str(c) for c in connection_ids if c not in allowed]
    if bad:
        raise ValidationFailed(
            "Choose connected accounts that can post", code="connection_cannot_post", details={"ids": bad}
        )
    if enabled and not connection_ids:
        raise ValidationFailed("Choose at least one account", code="connections_required")
    row = get_settings_row(db, ctx.merchant_id)
    if row is None:
        row = AutopostSettings(merchant_id=ctx.merchant_id)
        db.add(row)
    before = {"enabled": row.enabled, "require_approval": row.require_approval}
    row.enabled, row.connection_ids, row.kind = enabled, list(dict.fromkeys(connection_ids)), kind
    row.require_approval, row.updated_by_user_id = require_approval, ctx.actor.id
    db.flush()
    audit.record(
        db,
        action="content.autopost_updated",
        resource_type="autopost_settings",
        resource_id=row.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={k: [before[k], getattr(row, k)] for k in before if before[k] != getattr(row, k)},
        metadata={"connections": len(row.connection_ids)},
    )
    return row


def view(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    row = get_settings_row(db, merchant_id)
    return {
        "enabled": bool(row and row.enabled),
        "connection_ids": [str(c) for c in (row.connection_ids if row else [])],
        "kind": row.kind if row else "post",
        "require_approval": row.require_approval if row else True,
        "available": [
            {"id": str(c.id), "provider": c.provider, "display_name": c.display_name}
            for c in _publishable(db, merchant_id)
        ],
        "default_hour": DEFAULT_HOUR,
    }


# ----------------------------------------------------------------------------- slot and caption
def posting_hour(db: Session, merchant_id: uuid.UUID) -> int:
    from app.domains.intelligence.models import CommerceMemoryFact

    f = db.scalar(
        select(CommerceMemoryFact)
        .where(
            CommerceMemoryFact.merchant_id == merchant_id,
            CommerceMemoryFact.fact_type == "peak_order_hours",
            CommerceMemoryFact.status == "active",
        )
        .order_by(CommerceMemoryFact.valid_from.desc())
        .limit(1)
    )
    try:
        return int(f.value["start_hour"]) if f is not None else DEFAULT_HOUR
    except (KeyError, TypeError, ValueError):
        return DEFAULT_HOUR


def next_slot(db: Session, merchant_id: uuid.UUID, now: datetime | None = None) -> datetime:
    from app.domains.merchants.models import Merchant

    now = now or utcnow()
    m = db.get(Merchant, merchant_id)
    tz = ZoneInfo((m.timezone if m else None) or "Asia/Kathmandu")
    hour = posting_hour(db, merchant_id)
    local = (now + MIN_LEAD).astimezone(tz)
    slot = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if slot < local:
        slot += timedelta(days=1)
    return slot.astimezone(now.tzinfo)


def _price(minor: int) -> str:
    return f"{minor / 100:,.0f}"


def plain_caption(db: Session, product: Any, locale: str) -> str:
    from app.domains.catalog.models import Variant

    prices = [
        v.price_minor
        for v in db.scalars(select(Variant).where(Variant.product_id == product.id))
        if v.price_minor
    ]
    price = ""
    if prices:
        lo, hi = min(prices), max(prices)
        price = _price(lo) if lo == hi else f"{_price(lo)} - {_price(hi)}"
    source = (
        product.description_ne if locale == "ne" and product.description_ne else product.description
    ) or ""
    desc = source.strip().split("\n")[0][:280]
    if locale == "ne":
        lines = [product.title, f"रू {price}" if price else "", desc, "", "अर्डर गर्न म्यासेज गर्नुहोस्।"]
    else:
        lines = [product.title, f"Rs {price}" if price else "", desc, "", "Message us to order."]
    return "\n".join(x for x in lines if x is not None).replace("\n\n\n", "\n\n").strip()


# ----------------------------------------------------------------------------- the trigger
@handler("catalog.product_status_changed", name="content.autopost")
def _on_status(db: Session, ev: OutboxEvent) -> None:
    if ev.payload.get("to") != "active" or ev.merchant_id is None:
        return
    run_for_product(db, ev.merchant_id, uuid.UUID(ev.payload["product_id"]))


def run_for_product(db: Session, merchant_id: uuid.UUID, product_id: uuid.UUID) -> list[ContentPost]:
    from app.domains.catalog.models import Product, ProductMedia
    from app.domains.content import service as content
    from app.domains.merchants.models import Merchant
    from app.domains.studio.models import StudioJob

    bind_tenant(db, merchant_id)
    row = get_settings_row(db, merchant_id)
    if row is None or not row.enabled or not row.connection_ids:
        return []
    product = db.get(Product, product_id)
    merchant = db.get(Merchant, merchant_id)
    if product is None or merchant is None or product.status != "active":
        return []
    ctx = TenantContext(merchant_id=merchant_id, actor=Actor(type="automation", display="Autopost"))
    assets = list(
        db.scalars(
            select(ProductMedia.asset_id)
            .where(ProductMedia.product_id == product_id)
            .order_by(ProductMedia.position)
        )
    )[:10]
    if not assets:
        audit.record(
            db,
            action="content.autopost_skipped",
            resource_type="product",
            resource_id=product_id,
            actor=ctx.actor,
            merchant_id=merchant_id,
            metadata={"reason": "no_photos"},
        )
        return []
    job = db.scalar(
        select(StudioJob)
        .where(StudioJob.product_id == product_id, StudioJob.result.is_not(None))
        .order_by(StudioJob.created_at.desc())
        .limit(1)
    )
    captions: dict[str, str] = (job.result or {}).get("captions") or {} if job else {}
    hashtags: list[str] = (job.result or {}).get("hashtags") or [] if job else []
    out = []
    for cid in row.connection_ids:
        c = db.get(ChannelConnection, cid)
        if c is None or c.status != "connected" or "content_publish" not in c.capabilities:
            continue
        done = db.scalar(
            select(ContentPost.id).where(
                ContentPost.product_id == product_id,
                ContentPost.connection_id == cid,
                ContentPost.source == "autopost",
            )
        )
        if done is not None:
            continue
        style = content.adapter_for(c).caption_style
        caption = (
            captions.get(style)
            or captions.get("instagram")
            or plain_caption(db, product, merchant.default_locale)
        )
        kind = row.kind if row.kind == "post" or c.provider in ("instagram", "facebook_page") else "post"
        try:
            with db.begin_nested():
                p = content.create_post(
                    db,
                    ctx,
                    connection_id=cid,
                    caption=caption,
                    hashtags=hashtags,
                    asset_ids=assets,
                    kind=kind,
                    product_id=product_id,
                    source="autopost",
                    studio_job_id=job.id if job else None,
                )
                if row.require_approval:
                    content._move(p, "pending_approval")
                    content._audit(db, ctx, p, "submitted_for_approval", reason="autopost_requires_approval")
                else:
                    content.submit(db, ctx, p.id)  # the shop's automation mode may still ask
                    if p.status == "approved":
                        content.schedule(db, ctx, p.id, next_slot(db, merchant_id))
        except ValidationFailed as e:
            log.info("autopost_skipped", product_id=str(product_id), connection_id=str(cid), code=e.code)
            continue
        out.append(p)
    return out


def on_approved(db: Session, ctx: TenantContext, p: ContentPost) -> None:
    """An approved autopost goes out at the next good slot without another click."""
    from app.domains.content import service as content

    if p.source == "autopost" and p.status == "approved":
        content.schedule(db, ctx, p.id, next_slot(db, p.merchant_id))
