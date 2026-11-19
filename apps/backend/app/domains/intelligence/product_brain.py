"""Product Brain (PBR-001…005, 008, 009; spec 04 ProductIntelligenceProfile, spec 13 demand rate).

One profile per product, recomputable from Commerce Core:
- demand: units per day as an EWMA over days the product was IN STOCK (a sold-out week is not "no
  demand"), with 7/30/90-day unit counts;
- stock: available units, days of cover at the current demand, stockouts in the last 90 days;
- money: margin at today's price and cost, contribution per unit from the 90-day product P&L;
- returns: return rate, top reasons and the size/variant that's returned most.

Inputs that don't exist yet are listed in `not_included` (channel conversion and content performance
need content metrics, Phase 7; seasonality needs a year of history; promotion response needs
promotions). Completeness = share of the profile's sections that have data.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import bind_tenant, utcnow
from app.core.ids import uuid7
from app.domains.intelligence.models import ProductIntelligenceProfile

METHOD_VERSION = "pbr-1.0"
ALPHA = 0.2  # EWMA weight of the newest in-stock day (~9-day memory)
MIN_IN_STOCK_DAYS = 7
MIN_UNITS_FOR_CONTRIBUTION = 5
DEBOUNCE = timedelta(minutes=10)
SECTIONS = ("demand", "stock", "margin", "contribution", "returns")
NOT_INCLUDED_ALWAYS = {
    "channel_conversion": "needs_content_metrics",
    "content_performance": "needs_content_metrics",
    "seasonality": "needs_12_months",
    "promotion_response": "no_promotions",
}


def ewma(series: list[float], alpha: float = ALPHA) -> float | None:
    if not series:
        return None
    level = series[0]
    for x in series[1:]:
        level = alpha * x + (1 - alpha) * level
    return level


def _in_stock_days(
    db: Session, merchant_id: uuid.UUID, variant_ids: list[uuid.UUID], start: date, end: date
) -> tuple[set[date] | None, int]:
    """Days with stock on hand > 0 for any variant (None = stock not tracked) and stockouts counted."""
    from app.domains.inventory.models import InventoryLedgerEntry, InventoryLevel

    tracked = list(
        db.scalars(
            select(InventoryLevel.variant_id).where(InventoryLevel.variant_id.in_(variant_ids)).distinct()
        )
    )
    if not tracked:
        return None, 0
    start_dt = utcnow() - timedelta(days=(end - start).days + 1)
    # Opening stock per (variant, location): the last entry before the window.
    opening: dict[tuple[Any, Any], int] = {}
    last_before = (
        select(
            InventoryLedgerEntry.variant_id,
            InventoryLedgerEntry.location_id,
            func.max(InventoryLedgerEntry.created_at).label("at"),
        )
        .where(InventoryLedgerEntry.variant_id.in_(tracked), InventoryLedgerEntry.created_at < start_dt)
        .group_by(InventoryLedgerEntry.variant_id, InventoryLedgerEntry.location_id)
        .subquery()
    )
    for vid, lid, on_hand in db.execute(
        select(
            InventoryLedgerEntry.variant_id,
            InventoryLedgerEntry.location_id,
            InventoryLedgerEntry.on_hand_after,
        ).join(
            last_before,
            (InventoryLedgerEntry.variant_id == last_before.c.variant_id)
            & (InventoryLedgerEntry.location_id == last_before.c.location_id)
            & (InventoryLedgerEntry.created_at == last_before.c.at),
        )
    ):
        opening[(vid, lid)] = on_hand
    entries = db.execute(
        select(
            InventoryLedgerEntry.variant_id,
            InventoryLedgerEntry.location_id,
            InventoryLedgerEntry.on_hand_after,
            InventoryLedgerEntry.created_at,
        )
        .where(InventoryLedgerEntry.variant_id.in_(tracked), InventoryLedgerEntry.created_at >= start_dt)
        .order_by(InventoryLedgerEntry.created_at)
    ).all()
    level = dict(opening)
    by_day: dict[date, list[tuple[Any, Any, int]]] = defaultdict(list)
    for vid, lid, after, at in entries:
        by_day[at.date()].append((vid, lid, after))
    days: set[date] = set()
    stockouts = 0
    was_in = sum(level.values()) > 0
    d = start
    while d <= end:
        peak = sum(level.values())
        for vid, lid, after in by_day.get(d, []):
            level[(vid, lid)] = after
            peak = max(peak, sum(level.values()))
        now_in = sum(level.values()) > 0
        if peak > 0:
            days.add(d)
        if was_in and not now_in:
            stockouts += 1
        was_in = now_in
        d += timedelta(days=1)
    return days, stockouts


def compute_profile(
    db: Session,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    pnl: dict[str, Any] | None = None,
    returns: Any = None,
) -> dict[str, Any]:
    from app.domains.catalog.models import Variant
    from app.domains.intelligence import profit, return_intel
    from app.domains.inventory import service as inventory
    from app.domains.orders.models import Order, OrderLine

    today = utcnow().date()
    start = today - timedelta(days=89)
    variants = list(
        db.scalars(select(Variant).where(Variant.product_id == product_id, Variant.status != "archived"))
    )
    vids = [v.id for v in variants]
    daily: dict[date, int] = defaultdict(int)
    for day, units in db.execute(
        select(func.date(Order.placed_at), func.sum(OrderLine.quantity - OrderLine.cancelled_quantity))
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            OrderLine.product_id == product_id,
            Order.merchant_id == merchant_id,
            Order.placed_at >= utcnow() - timedelta(days=90),
            Order.status.not_in(("draft", "cancelled")),
        )
        .group_by(func.date(Order.placed_at))
    ):
        daily[day] += int(units or 0)
    units_n = {n: sum(u for d, u in daily.items() if d > today - timedelta(days=n)) for n in (7, 30, 90)}
    stock_days, stockouts = _in_stock_days(db, merchant_id, vids, start, today) if vids else (None, 0)
    window = [start + timedelta(days=i) for i in range(90)]
    selling_days = window if stock_days is None else [d for d in window if d in stock_days]
    first_sale = min(daily) if daily else None
    if first_sale and stock_days is None:
        selling_days = [d for d in selling_days if d >= first_sale]  # untracked: count from the first sale
    demand = (
        ewma([float(daily.get(d, 0)) for d in selling_days])
        if len(selling_days) >= MIN_IN_STOCK_DAYS
        else None
    )
    av = inventory.availability(db, merchant_id, vids) if vids else {}
    tracked = [a for a in av.values() if a.tracked]
    available = sum(max(0, a.available) for a in tracked) if tracked else None
    cover = round(available / demand, 1) if available is not None and demand and demand > 0 else None

    prices = [v.price_minor for v in variants]
    costs = [v.cost_minor for v in variants if v.cost_minor is not None]
    margin = None
    if prices and costs and len(costs) == len(variants):
        avg_price = sum(prices) / len(prices)
        margin = round(100 * (avg_price - sum(costs) / len(costs)) / avg_price, 1) if avg_price else None
    if pnl is None:
        pnl = profit.compute(db, merchant_id, 90, product_id=product_id)
    row = next((p for p in pnl["products"] if p["product_id"] == str(product_id)), None)
    contribution = None
    contribution_note = "not_enough_sales"
    if row and row["units"] >= MIN_UNITS_FOR_CONTRIBUTION:
        cogs = next(c for c in row["components"] if c["code"] == "cogs")
        if cogs["status"] == "not_included":
            contribution_note = "cost_not_set"
        else:
            contribution = row["contribution_per_unit_minor"]
            contribution_note = "partial" if not row["complete"] else "complete"

    if returns is None:
        returns = return_intel.stats(db, merchant_id, product_id=product_id)
    pr = returns.get(product_id)
    return_rate = round(pr.returned / pr.sold, 4) if pr and pr.sold >= 1 else None
    by_variant = []
    if pr:
        for vid, v in pr.variants.items():
            if v["sold"]:
                by_variant.append(
                    {
                        "variant_id": vid,
                        "variant": pr.variant_titles.get(vid),
                        "sold": v["sold"],
                        "returned": v["returned"],
                        "rate": round(v["returned"] / v["sold"], 3),
                    }
                )
        by_variant.sort(key=lambda x: -x["rate"])
    sections = {
        "demand": demand is not None,
        "stock": available is not None,
        "margin": margin is not None,
        "contribution": contribution is not None,
        "returns": return_rate is not None,
    }
    not_included = dict(NOT_INCLUDED_ALWAYS)
    if demand is None:
        not_included["demand"] = "not_enough_days_in_stock" if daily else "no_sales"
    if available is None:
        not_included["stock"] = "stock_not_tracked"
    if margin is None:
        not_included["margin"] = "cost_not_set"
    if contribution is None:
        not_included["contribution"] = contribution_note
    if return_rate is None:
        not_included["returns"] = "no_delivered_sales"
    return {
        "units_7d": units_n[7],
        "units_30d": units_n[30],
        "units_90d": units_n[90],
        "in_stock_days_90d": len(selling_days),
        "demand_per_day": round(demand, 3) if demand is not None else None,
        "available": available,
        "cover_days": cover,
        "stockouts_90d": stockouts,
        "margin_pct": margin,
        "contribution_per_unit_minor": contribution,
        "return_rate": return_rate,
        "completeness": round(sum(sections.values()) / len(SECTIONS), 2),
        "data": {
            "sold_90d_delivered": pr.sold if pr else 0,
            "returned_90d": pr.returned if pr else 0,
            "top_reasons": [{"reason": r, "units": n} for r, n in (pr.reasons.most_common(3) if pr else [])],
            "by_variant": by_variant[:6],
            "contribution_basis": contribution_note,
            "stock_tracked": available is not None,
            "not_included": not_included,
        },
    }


def recompute(
    db: Session,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    pnl: dict[str, Any] | None = None,
    returns: Any = None,
) -> ProductIntelligenceProfile:
    vals = compute_profile(db, merchant_id, product_id, pnl=pnl, returns=returns)
    now = utcnow()
    db.execute(
        pg_insert(ProductIntelligenceProfile)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            product_id=product_id,
            method_version=METHOD_VERSION,
            as_of=now,
            **vals,
        )
        .on_conflict_do_update(
            index_elements=["product_id"], set_={**vals, "method_version": METHOD_VERSION, "as_of": now}
        )
    )
    db.flush()
    p = db.scalar(
        select(ProductIntelligenceProfile).where(ProductIntelligenceProfile.product_id == product_id)
    )
    assert p is not None
    db.refresh(p)
    return p


def recompute_merchant(db: Session, merchant_id: uuid.UUID) -> int:
    """PBR-008 nightly full recompute (one P&L and one returns pass for all products)."""
    from app.domains.catalog.models import Product
    from app.domains.intelligence import profit, return_intel

    pnl = profit.compute(db, merchant_id, 90)
    returns = return_intel.stats(db, merchant_id)
    n = 0
    for pid in db.scalars(
        select(Product.id).where(Product.merchant_id == merchant_id, Product.status != "archived")
    ):
        recompute(db, merchant_id, pid, pnl=pnl, returns=returns)
        n += 1
    return n


def recompute_all(db: Session) -> int:
    from app.domains.billing.service import entitlements
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        if entitlements.resolve(db, mid).has("intelligence.product_brain"):
            with db.begin_nested():
                n += recompute_merchant(db, mid)
    return n


def get_or_compute(db: Session, merchant_id: uuid.UUID, product_id: uuid.UUID) -> ProductIntelligenceProfile:
    p = db.scalar(
        select(ProductIntelligenceProfile).where(ProductIntelligenceProfile.product_id == product_id)
    )
    if p is None or p.as_of < utcnow() - timedelta(hours=26):  # freshness SLO: never older than a day
        p = recompute(db, merchant_id, product_id)
    return p


def view(p: ProductIntelligenceProfile, *, fit: str | None = None) -> dict[str, Any]:
    return {
        "product_id": str(p.product_id),
        "units_7d": p.units_7d,
        "units_30d": p.units_30d,
        "units_90d": p.units_90d,
        "in_stock_days_90d": p.in_stock_days_90d,
        "demand_per_day": p.demand_per_day,
        "available": p.available,
        "cover_days": p.cover_days,
        "stockouts_90d": p.stockouts_90d,
        "margin_pct": p.margin_pct,
        "contribution_per_unit_minor": p.contribution_per_unit_minor,
        "return_rate": p.return_rate,
        "completeness": p.completeness,
        "stock_risk": stock_risk(p),
        "fit": fit,
        **p.data,
        "method_version": p.method_version,
        "as_of": p.as_of.isoformat(),
    }


def stock_risk(p: ProductIntelligenceProfile, lead_days: int = 7) -> str | None:
    """UX-012: high = runs out within the reorder lead time; medium = within twice that."""
    if p.available is None or p.demand_per_day is None:
        return None
    if p.available <= 0:
        return "out"
    if p.cover_days is None:
        return "low" if p.demand_per_day == 0 else None
    if p.cover_days <= lead_days:
        return "high"
    if p.cover_days <= 2 * lead_days:
        return "medium"
    return "low"


# PBR-008 incremental: refresh the products on an order when it is delivered/returned (debounced).
from app.domains.platform.models import OutboxEvent  # noqa: E402
from app.domains.platform.outbox import handler  # noqa: E402


@handler("orders.status_changed", name="intelligence.product_brain_refresh")
def _on_status(db: Session, ev: OutboxEvent) -> None:
    from app.domains.billing.service import entitlements
    from app.domains.orders.models import Order, OrderLine

    if ev.payload.get("status") not in ("delivered", "returned", "cancelled"):
        return
    o = db.scalar(
        select(Order)
        .where(Order.id == uuid.UUID(ev.payload["order_id"]))
        .execution_options(skip_tenant_filter=True)
    )
    if o is None:
        return
    bind_tenant(db, o.merchant_id)
    if not entitlements.resolve(db, o.merchant_id).has("intelligence.product_brain"):
        return
    for pid in set(
        db.scalars(
            select(OrderLine.product_id).where(OrderLine.order_id == o.id, OrderLine.product_id.is_not(None))
        )
    ):
        cur = db.scalar(
            select(ProductIntelligenceProfile.as_of).where(ProductIntelligenceProfile.product_id == pid)
        )
        if pid is not None and (cur is None or cur < utcnow() - DEBOUNCE):
            recompute(db, o.merchant_id, pid)
