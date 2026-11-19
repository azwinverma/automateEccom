"""True profit and product P&L (ANA-007/008, spec 14 §True profit).

Waterfall for orders PLACED in the window:

    Goods revenue (line prices) + delivery fees charged
     - discounts - cost of goods - payment fees - channel fees - courier cost - packaging
     - return shipping - refunds - failed-delivery cost - ad spend
     = Contribution (profit before fixed costs)

Order classes:
- sold: delivered/completed, or returned by the customer after delivery (a return request exists);
- failed: delivery failed / returned to origin without being delivered → only its costs count
  (outbound + return shipping + handling), no revenue;
- open: not finished yet → not counted, reported as a count.

Cost of goods uses the cost recorded on the order line when the order was placed; for older lines it
falls back to the variant's current cost (counted and shown). Units the customer sent back and that
went back on the shelf carry no cost; damaged/missing returns keep their cost (the unrecoverable value).

Every component has a status: "included", "partial" (some data missing, with counts) or
"not_included" (no data). Nothing missing is ever shown as a silent zero.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import utcnow
from app.domains.intelligence.courier_brain import HANDLING_COST_MINOR
from app.domains.intelligence.models import ProfitSettings

METHOD_VERSION = "profit-1.0"
SOLD = ("delivered", "completed")
FAILED = ("delivery_failed", "returned")
NOT_COUNTED = ("draft", "cancelled")
COMPONENTS = (
    "goods",
    "delivery_fees",
    "discounts",
    "cogs",
    "payment_fees",
    "channel_fees",
    "courier",
    "packaging",
    "return_shipping",
    "refunds",
    "failed_delivery",
    "ads",
)


def settings_row(db: Session, merchant_id: uuid.UUID) -> ProfitSettings:
    s = db.scalar(select(ProfitSettings).where(ProfitSettings.merchant_id == merchant_id))
    if s is None:
        s = ProfitSettings(merchant_id=merchant_id)
        db.add(s)
        db.flush()
    return s


def settings_view(s: ProfitSettings) -> dict[str, Any]:
    return {
        "packaging_cost_minor": s.packaging_cost_minor,
        "min_margin_pct": s.min_margin_pct,
        "min_contribution_minor": s.min_contribution_minor,
        "max_return_rate_pct": s.max_return_rate_pct,
    }


def update_settings(db: Session, ctx: TenantContext, changes: dict[str, Any]) -> ProfitSettings:
    from app.domains.audit import service as audit

    s = settings_row(db, ctx.merchant_id)
    before = settings_view(s)
    for k, v in changes.items():
        setattr(s, k, v)
    audit.record(
        db,
        action="intelligence.profit_settings_updated",
        resource_type="profit_settings",
        resource_id=s.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"before": before, "after": settings_view(s)},
    )
    return s


@dataclass
class Ledger:
    """Accumulates one waterfall (shop-wide or one product)."""

    amounts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    missing: dict[str, int] = field(default_factory=lambda: defaultdict(int))  # count of items without data
    present: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    units: int = 0
    orders: int = 0

    def add(self, comp: str, minor: int | None) -> None:
        if minor is None:
            self.missing[comp] += 1
        else:
            self.amounts[comp] += int(minor)
            self.present[comp] += 1

    def result(self, *, not_included: dict[str, str]) -> dict[str, Any]:
        comps: list[dict[str, Any]] = []
        for c in COMPONENTS:
            if c in not_included:
                status = "not_included"
            elif self.missing.get(c):
                status = "partial" if self.present.get(c) else "not_included"
            else:
                status = "included"
            sign = 1 if c in ("goods", "delivery_fees") else -1
            comps.append(
                {
                    "code": c,
                    "amount_minor": sign * self.amounts.get(c, 0) if status != "not_included" else None,
                    "status": status,
                    "missing": self.missing.get(c, 0),
                    "reason": not_included.get(c),
                }
            )
        revenue = self.amounts["goods"] + self.amounts["delivery_fees"]
        contribution = sum(x["amount_minor"] or 0 for x in comps)
        return {
            "components": comps,
            "revenue_minor": revenue,
            "contribution_minor": contribution,
            "margin_pct": round(100 * contribution / revenue, 1) if revenue else None,
            "complete": all(x["status"] == "included" for x in comps if x["code"] != "ads"),
            "units": self.units,
            "orders": self.orders,
        }


def compute(
    db: Session, merchant_id: uuid.UUID, days: int = 30, product_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """Shop waterfall + per-product P&L for orders placed in the last `days` days."""
    from app.domains.catalog.models import Product, Variant
    from app.domains.fulfillment.models import Shipment
    from app.domains.orders.models import Order, OrderLine
    from app.domains.payments.models import CODRecord, Payment
    from app.domains.returns.models import Refund, ReturnLine, ReturnRequest

    since = utcnow() - timedelta(days=days)
    s = settings_row(db, merchant_id)
    orders = list(
        db.scalars(
            select(Order).where(
                Order.merchant_id == merchant_id,
                Order.placed_at >= since,
                Order.status.not_in(NOT_COUNTED),
            )
        )
    )
    ids = [o.id for o in orders]
    lines_by: dict[uuid.UUID, list[OrderLine]] = defaultdict(list)
    ships_by: dict[uuid.UUID, list[Shipment]] = defaultdict(list)
    returns_by: dict[uuid.UUID, list[ReturnRequest]] = defaultdict(list)
    refunds_by: dict[uuid.UUID, int] = defaultdict(int)
    restocked: dict[uuid.UUID, int] = defaultdict(int)  # order_line_id → units back on the shelf
    cod_fee: dict[uuid.UUID, int] = {}
    online_paid: set[uuid.UUID] = set()
    if ids:
        for ln in db.scalars(select(OrderLine).where(OrderLine.order_id.in_(ids))):
            lines_by[ln.order_id].append(ln)
        for sh in db.scalars(
            select(Shipment).where(Shipment.order_id.in_(ids), Shipment.status != "cancelled")
        ):
            ships_by[sh.order_id].append(sh)
        for r in db.scalars(
            select(ReturnRequest).where(
                ReturnRequest.order_id.in_(ids), ReturnRequest.status.not_in(("rejected", "cancelled"))
            )
        ):
            returns_by[r.order_id].append(r)
        rids = [r.id for rs in returns_by.values() for r in rs]
        if rids:
            for rl in db.scalars(select(ReturnLine).where(ReturnLine.return_id.in_(rids))):
                restocked[rl.order_line_id] += rl.restocked_quantity
        for rf in db.scalars(select(Refund).where(Refund.order_id.in_(ids), Refund.status == "succeeded")):
            refunds_by[rf.order_id] += rf.amount_minor
        for c in db.scalars(select(CODRecord).where(CODRecord.order_id.in_(ids))):
            cod_fee[c.order_id] = c.fee_minor if c.settlement_id else None  # type: ignore[assignment]
        for p in db.scalars(
            select(Payment).where(
                Payment.order_id.in_(ids), Payment.kind == "online", Payment.status.in_(("paid", "refunded"))
            )
        ):
            online_paid.add(p.order_id)
    current_cost: dict[uuid.UUID, int | None] = {}
    var_ids = {ln.variant_id for ls in lines_by.values() for ln in ls if ln.variant_id}
    if var_ids:
        current_cost = dict(
            db.execute(select(Variant.id, Variant.cost_minor).where(Variant.id.in_(var_ids))).all()
        )

    shop = Ledger()
    per_product: dict[uuid.UUID, Ledger] = defaultdict(Ledger)
    counts = {"sold": 0, "failed": 0, "open": 0, "cost_from_current": 0}
    has_channel = has_online = False

    for o in orders:
        lines = [ln for ln in lines_by[o.id] if ln.active_quantity > 0]
        returned_by_customer = bool(returns_by[o.id])
        if o.status in SOLD or (o.status == "returned" and returned_by_customer):
            kind = "sold"
        elif o.status in FAILED:
            kind = "failed"
        else:
            counts["open"] += 1
            continue
        counts[kind] += 1
        outbound = [sh for sh in ships_by[o.id] if sh.direction == "outbound"]
        back = [sh for sh in ships_by[o.id] if sh.direction == "return"]
        # Order-level amounts are shared across lines by line value (allocation shown in the API).
        total_value = sum(ln.unit_price_minor * ln.active_quantity for ln in lines) or 1
        shares = [(ln, (ln.unit_price_minor * ln.active_quantity) / total_value) for ln in lines]

        def add_order(comp: str, minor: int | None, _shares: list[Any] = shares) -> None:
            shop.add(comp, minor)
            for ln, share in _shares:
                if ln.product_id and (product_id is None or ln.product_id == product_id):
                    per_product[ln.product_id].add(comp, None if minor is None else round(minor * share))

        if kind == "failed":
            # No sale: the cost of trying (outbound + return trip + handling).
            if outbound:
                charges = [sh.charge_minor for sh in outbound + back]
                cost = None if any(c is None for c in charges) else sum(charges) + HANDLING_COST_MINOR  # type: ignore[arg-type]
                if cost is not None and not back:
                    cost += max((sh.charge_minor or 0) for sh in outbound)  # return trip billed like outbound
                add_order("failed_delivery", cost)
            continue

        shop.orders += 1
        has_channel |= o.source == "channel"
        has_online |= o.id in online_paid
        for ln, _share in shares:
            led = per_product[ln.product_id] if ln.product_id else None
            if product_id is not None and ln.product_id != product_id:
                led = None
            goods = ln.unit_price_minor * ln.active_quantity
            unit_cost = ln.unit_cost_minor
            if unit_cost is None and ln.variant_id:
                unit_cost = current_cost.get(ln.variant_id)
                counts["cost_from_current"] += int(unit_cost is not None)
            kept = ln.active_quantity - min(restocked.get(ln.id, 0), ln.active_quantity)
            cogs = None if unit_cost is None else unit_cost * kept
            for led_ in (shop, led):
                if led_ is None:
                    continue
                led_.add("goods", goods)
                led_.add("discounts", ln.line_discount_minor)
                led_.add("cogs", cogs)
                led_.units += ln.active_quantity
            if led is not None:
                led.orders += 1
        add_order("delivery_fees", o.delivery_fee_minor)
        line_disc = sum(ln.line_discount_minor for ln in lines)
        add_order("discounts", max(0, o.discount_minor - line_disc))
        if o.payment_method == "cod":
            add_order("payment_fees", cod_fee.get(o.id))  # None until the courier statement shows the fee
        add_order(
            "courier",
            None
            if not outbound or any(sh.charge_minor is None for sh in outbound)
            else sum(sh.charge_minor or 0 for sh in outbound),
        )
        add_order("packaging", s.packaging_cost_minor)
        if returned_by_customer:
            paid_by_customer = sum(
                r.return_shipping_fee_minor for r in returns_by[o.id] if r.customer_pays_shipping
            )
            if back:
                charges = [sh.charge_minor for sh in back]
                add_order(
                    "return_shipping",
                    None if any(c is None for c in charges) else max(0, sum(charges) - paid_by_customer),  # type: ignore[arg-type]
                )
        if refunds_by.get(o.id):
            add_order("refunds", refunds_by[o.id])

    not_included = {"ads": "no_ad_account"}
    if has_channel:
        not_included["channel_fees"] = "channel_fees_unknown"
    if s.packaging_cost_minor is None:
        not_included["packaging"] = "packaging_not_set"

    def finish(led: Ledger) -> dict[str, Any]:
        r = led.result(not_included=not_included)
        if has_online and not led.missing.get("payment_fees"):
            for c in r["components"]:
                if c["code"] == "payment_fees" and c["status"] == "included":
                    c["status"], c["reason"] = "partial", "provider_fees_unknown"
        r["complete"] = all(c["status"] == "included" for c in r["components"] if c["code"] != "ads")
        return r

    products = []
    if per_product:
        titles = dict(
            db.execute(select(Product.id, Product.title).where(Product.id.in_(per_product.keys()))).all()
        )
        for pid, led in per_product.items():
            row = finish(led)
            row["product_id"], row["title"] = str(pid), titles.get(pid)
            row["contribution_per_unit_minor"] = (
                round(row["contribution_minor"] / led.units) if led.units else None
            )
            products.append(row)
        products.sort(key=lambda x: x["contribution_minor"])
    return {
        "window_days": days,
        "shop": finish(shop),
        "products": products,
        "counts": counts,
        "allocation": "order_amounts_by_line_value",
        "method_version": METHOD_VERSION,
        "as_of": utcnow().isoformat(),
    }
