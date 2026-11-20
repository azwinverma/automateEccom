"""Supplier Intelligence (SPI-001…004, PRO-007; spec 13 §Supplier Intelligence).

SPI-002 lot linkage: a sold unit is attributed to the supplier lot that was most recently received for
that variant before the order was placed (the batch that was on the shelf). Returns and quality complaints
on that line count against that supplier. Units sold before any receipt are unattributed.

True economics per unit (spec 13):
    selling price - landed cost - defect cost - return cost - fees & fulfilment
- defect cost: defective units are paid for but never sold, so each good unit carries
  defect_rate / (1 - defect_rate) x landed cost;
- return cost: per unit sold, the unrecoverable value of returned units that couldn't be restocked plus
  the shop's average return-shipping cost per return;
- fees & fulfilment: courier + packaging + payment fees per unit from the shop's 90-day P&L, shown as
  "not included" when the P&L lacks them.

Reorder (PRO-007/SPI-004): reorder a variant when (available + incoming) covers less than the supplier's
lead time + safety days at the current demand. Quantity covers lead time + safety + 30 days, rounded up
to the MOQ. The supplier is the one with the best true economics (preferred when there's no evidence).
Products that lose money or come back too often are never suggested (spec 14).
"""

from __future__ import annotations

import math
import statistics
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import bind_tenant, utcnow
from app.core.ids import uuid7
from app.domains.procurement.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
    SupplierPerformanceMetric,
)

METHOD_VERSION = "spi-1.0"
WINDOW_DAYS = 180
QUALITY_REASONS = ("quality_defect", "not_as_described", "wrong_item")
DEFAULT_LEAD_DAYS = 7
MIN_SAFETY_DAYS = 3
COVER_TARGET_DAYS = 30
MIN_UNITS_FOR_SWITCH = 20
SWITCH_GAIN_PCT = 0.05
SWITCH_GAIN_MIN_MINOR = 2000  # NPR 20 per unit


def _fulfilment_per_unit(db: Session, merchant_id: uuid.UUID) -> tuple[int | None, list[str]]:
    from app.domains.intelligence import profit

    pnl = profit.compute(db, merchant_id, 90)
    shop = pnl["shop"]
    units = shop["units"]
    missing: list[str] = []
    total = 0
    for code in ("courier", "packaging", "payment_fees"):
        c = next(x for x in shop["components"] if x["code"] == code)
        if c["status"] != "included":
            missing.append(code)
        total += -(c["amount_minor"] or 0)
    if not units:
        return None, ["no_sales"]
    return round(total / units), missing


def _attribution(db: Session, merchant_id: uuid.UUID, since: Any) -> dict[uuid.UUID, dict[str, Any]]:
    """Per supplier: units sold, revenue, returns (all / quality), unrecoverable value — via lot linkage."""
    from app.domains.orders.models import Order, OrderLine
    from app.domains.returns.models import ReturnLine, ReturnRequest

    lots = db.execute(
        select(
            PurchaseReceiptLine.variant_id,
            PurchaseReceiptLine.created_at,
            PurchaseReceipt.supplier_id,
            PurchaseReceiptLine.landed_unit_cost_minor,
        )
        .join(PurchaseReceipt, PurchaseReceipt.id == PurchaseReceiptLine.receipt_id)
        .where(PurchaseReceipt.merchant_id == merchant_id, PurchaseReceiptLine.quantity > 0)
        .order_by(PurchaseReceiptLine.created_at)
    ).all()
    by_variant: dict[uuid.UUID, list[tuple[Any, uuid.UUID, int]]] = defaultdict(list)
    for vid, at, sid, landed in lots:
        by_variant[vid].append((at, sid, landed))
    out: dict[uuid.UUID, dict[str, Any]] = defaultdict(
        lambda: {
            "sold": 0,
            "revenue": 0,
            "returned": 0,
            "quality_returned": 0,
            "unrecoverable": 0,
            "returns_count": 0,
        }
    )
    if not by_variant:
        return out
    has_return = (
        select(ReturnRequest.id)
        .where(ReturnRequest.order_id == Order.id, ReturnRequest.status.not_in(("rejected", "cancelled")))
        .exists()
    )
    rows = db.execute(
        select(OrderLine, Order.placed_at)
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= since,
            OrderLine.variant_id.in_(list(by_variant)),
            (Order.status.in_(("delivered", "completed"))) | ((Order.status == "returned") & has_return),
        )
    ).all()
    line_supplier: dict[uuid.UUID, tuple[uuid.UUID, int]] = {}
    for ln, placed in rows:
        cands = [x for x in by_variant.get(ln.variant_id, []) if x[0] <= placed] if ln.variant_id else []
        if not cands:
            continue
        _, sid, landed = cands[-1]
        line_supplier[ln.id] = (sid, landed)
        a = out[sid]
        a["sold"] += ln.active_quantity
        a["revenue"] += ln.unit_price_minor * ln.active_quantity - ln.line_discount_minor
    if line_supplier:
        for rl in db.scalars(
            select(ReturnLine)
            .join(ReturnRequest, ReturnRequest.id == ReturnLine.return_id)
            .where(
                ReturnLine.order_line_id.in_(list(line_supplier)),
                ReturnRequest.status.not_in(("rejected", "cancelled")),
            )
        ):
            sid, landed = line_supplier[rl.order_line_id]
            a = out[sid]
            a["returned"] += rl.quantity
            a["returns_count"] += 1
            if rl.reason in QUALITY_REASONS:
                a["quality_returned"] += rl.quantity
            a["unrecoverable"] += max(0, rl.quantity - rl.restocked_quantity) * landed
    return out


def _return_shipping_per_return(db: Session, merchant_id: uuid.UUID, since: Any) -> int | None:
    from app.domains.fulfillment.models import Shipment

    avg = db.scalar(
        select(func.avg(Shipment.charge_minor)).where(
            Shipment.merchant_id == merchant_id,
            Shipment.direction == "return",
            Shipment.charge_minor.is_not(None),
            Shipment.created_at >= since,
        )
    )
    return round(avg) if avg is not None else None


def compute(db: Session, merchant_id: uuid.UUID, window_days: int = WINDOW_DAYS) -> int:
    since = utcnow() - timedelta(days=window_days)
    recv = db.execute(
        select(
            PurchaseReceipt.supplier_id,
            func.sum(PurchaseReceiptLine.quantity),
            func.sum(PurchaseReceiptLine.defective_quantity),
            func.sum(
                (PurchaseReceiptLine.quantity + PurchaseReceiptLine.defective_quantity)
                * PurchaseReceiptLine.unit_cost_minor
            ),
            func.sum(
                (PurchaseReceiptLine.quantity + PurchaseReceiptLine.defective_quantity)
                * PurchaseReceiptLine.landed_unit_cost_minor
            ),
        )
        .join(PurchaseReceipt, PurchaseReceipt.id == PurchaseReceiptLine.receipt_id)
        .where(PurchaseReceipt.merchant_id == merchant_id, PurchaseReceipt.received_at >= since)
        .group_by(PurchaseReceipt.supplier_id)
    ).all()
    attrib = _attribution(db, merchant_id, since)
    fulfil, fulfil_missing = _fulfilment_per_unit(db, merchant_id)
    ret_ship = _return_shipping_per_return(db, merchant_id, since)
    n = 0
    for sid, good, bad, cost_total, landed_total in recv:
        good, bad = int(good or 0), int(bad or 0)
        units = good + bad
        if units == 0:
            continue
        avg_cost = round(cost_total / units)
        avg_landed = round(landed_total / units)
        defect = bad / units
        pos = list(
            db.scalars(
                select(PurchaseOrder).where(
                    PurchaseOrder.supplier_id == sid,
                    PurchaseOrder.created_at >= since,
                    PurchaseOrder.status.in_(("partially_received", "received")),
                )
            )
        )
        leads, on_time, fills = [], [], []
        for po in pos:
            first = db.scalar(
                select(func.min(PurchaseReceipt.received_at)).where(PurchaseReceipt.po_id == po.id)
            )
            start = po.sent_at or po.approved_at
            if first and start:
                leads.append(max(0.0, (first - start).total_seconds() / 86400))
            if first and po.expected_at:
                on_time.append(first <= po.expected_at)
            if po.status == "received":
                q = db.execute(
                    select(
                        func.sum(PurchaseOrderLine.quantity),
                        func.sum(PurchaseOrderLine.received_quantity - PurchaseOrderLine.defective_quantity),
                    ).where(PurchaseOrderLine.po_id == po.id)
                ).one()
                if q[0]:
                    fills.append(min(1.0, (q[1] or 0) / q[0]))
        a = attrib.get(
            sid,
            {
                "sold": 0,
                "revenue": 0,
                "returned": 0,
                "quality_returned": 0,
                "unrecoverable": 0,
                "returns_count": 0,
            },
        )
        sold = a["sold"]
        return_rate = a["returned"] / sold if sold else None
        quality_rate = a["quality_returned"] / sold if sold else None
        defect_cost = round(defect / (1 - defect) * avg_landed) if defect < 1 else None
        return_cost = None
        if sold:
            ship = (ret_ship or 0) * a["returns_count"]
            return_cost = round((a["unrecoverable"] + ship) / sold)
        price = round(a["revenue"] / sold) if sold else None
        not_included = list(fulfil_missing)
        if a["returns_count"] and ret_ship is None:
            not_included.append("return_shipping")
        contribution = None
        if price is not None and defect_cost is not None and return_cost is not None:
            contribution = price - avg_landed - defect_cost - return_cost - (fulfil or 0)
        vals = {
            "received_units": units,
            "avg_unit_cost_minor": avg_cost,
            "avg_landed_cost_minor": avg_landed,
            "defect_rate": round(defect, 4),
            "sold_units": sold,
            "return_rate": round(return_rate, 4) if return_rate is not None else None,
            "quality_return_rate": round(quality_rate, 4) if quality_rate is not None else None,
            "on_time_rate": round(sum(on_time) / len(on_time), 3) if on_time else None,
            "lead_time_days_avg": round(statistics.fmean(leads), 2) if leads else None,
            "lead_time_days_sd": round(statistics.pstdev(leads), 2) if len(leads) >= 2 else None,
            "fill_rate": round(statistics.fmean(fills), 3) if fills else None,
            "contribution_per_unit_minor": contribution,
            "data": {
                "components": {
                    "price": price,
                    "landed": avg_landed,
                    "defect_cost": defect_cost,
                    "return_cost": return_cost,
                    "fees_fulfilment": fulfil,
                },
                "not_included": not_included,
                "purchase_orders": len(pos),
                "lead_samples": len(leads),
                "basis": "sold" if sold else "no_sales_yet",
            },
            "method_version": METHOD_VERSION,
            "computed_at": utcnow(),
        }
        db.execute(
            pg_insert(SupplierPerformanceMetric)
            .values(id=uuid7(), merchant_id=merchant_id, supplier_id=sid, window_days=window_days, **vals)
            .on_conflict_do_update(index_elements=["merchant_id", "supplier_id", "window_days"], set_=vals)
        )
        n += 1
    db.flush()
    return n


def compute_all(db: Session) -> int:
    from app.domains.billing.service import entitlements
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        if not entitlements.resolve(db, mid).has("intelligence.supplier"):
            continue
        with db.begin_nested():
            compute(db, mid)
        n += 1
    return n


def metrics(db: Session, merchant_id: uuid.UUID) -> dict[uuid.UUID, SupplierPerformanceMetric]:
    return {
        m.supplier_id: m
        for m in db.scalars(
            select(SupplierPerformanceMetric).where(
                SupplierPerformanceMetric.merchant_id == merchant_id,
                SupplierPerformanceMetric.window_days == WINDOW_DAYS,
            )
        )
    }


def unit_economics(
    m: SupplierPerformanceMetric | None, landed_fallback: int | None, price: int
) -> int | None:
    """Per-unit value of buying a variant from this supplier at this selling price (fees cancel out)."""
    if m is None:
        return None if landed_fallback is None else price - landed_fallback
    landed = m.avg_landed_cost_minor if m.avg_landed_cost_minor is not None else landed_fallback
    if landed is None:
        return None
    defect = m.defect_rate or 0.0
    defect_cost = defect / (1 - defect) * landed if defect < 1 else landed
    ret = (m.data or {}).get("components", {}).get("return_cost") or 0
    return round(price - landed - defect_cost - ret)


def view(m: SupplierPerformanceMetric) -> dict[str, Any]:
    return {
        "supplier_id": str(m.supplier_id),
        "window_days": m.window_days,
        "received_units": m.received_units,
        "avg_unit_cost_minor": m.avg_unit_cost_minor,
        "avg_landed_cost_minor": m.avg_landed_cost_minor,
        "defect_rate": m.defect_rate,
        "sold_units": m.sold_units,
        "return_rate": m.return_rate,
        "quality_return_rate": m.quality_return_rate,
        "on_time_rate": m.on_time_rate,
        "lead_time_days_avg": m.lead_time_days_avg,
        "lead_time_days_sd": m.lead_time_days_sd,
        "fill_rate": m.fill_rate,
        "contribution_per_unit_minor": m.contribution_per_unit_minor,
        **m.data,
        "method_version": m.method_version,
        "computed_at": m.computed_at.isoformat(),
    }


# ----------------------------------------------------------------------------- suggestions
def switch_proposals(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """SPI-003: a variant bought from the less profitable of two measured suppliers."""
    from app.domains.catalog.models import Product, Supplier, Variant, VariantSupplier

    ms = metrics(db, merchant_id)
    by_variant: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for vs in db.scalars(select(VariantSupplier).where(VariantSupplier.merchant_id == merchant_id)):
        by_variant[vs.variant_id].append(vs)
    out = []
    for vid, rows in by_variant.items():
        measured = [
            r
            for r in rows
            if (m := ms.get(r.supplier_id)) is not None and m.received_units >= MIN_UNITS_FOR_SWITCH
        ]
        if len(measured) < 2:
            continue
        v = db.get(Variant, vid)
        if v is None or v.status != "active":
            continue
        econ = {
            r.supplier_id: unit_economics(ms.get(r.supplier_id), r.cost_minor, v.price_minor)
            for r in measured
        }
        known_econ: dict[uuid.UUID, int] = {k: x for k, x in econ.items() if x is not None}
        econ = known_econ  # type: ignore[assignment]
        if len(known_econ) < 2:
            continue
        best = max(known_econ, key=lambda k: known_econ[k])
        pref = next((r.supplier_id for r in rows if r.is_preferred), None)
        if pref is None or pref == best or pref not in known_econ:
            continue
        gain = known_econ[best] - known_econ[pref]
        if gain < max(SWITCH_GAIN_MIN_MINOR, SWITCH_GAIN_PCT * v.price_minor):
            continue
        p = db.get(Product, v.product_id)
        names = {s.id: s.name for s in db.scalars(select(Supplier).where(Supplier.id.in_([best, pref])))}
        mb, mp = ms[best], ms[pref]
        out.append(
            {
                "type": "supplier_switch",
                "dedupe_key": f"supplier_switch:{vid}",
                "subject_type": "variant",
                "subject_id": str(vid),
                "explanation": {
                    "what": "switch_supplier",
                    "why": "true_economics",
                    "vars": {
                        "title": p.title if p else None,
                        "variant": None if v.title == "Default" else v.title,
                        "from": names.get(pref),
                        "to": names.get(best),
                        "gain_per_unit": gain,
                        "from_landed": mp.avg_landed_cost_minor,
                        "to_landed": mb.avg_landed_cost_minor,
                        "from_defect_pct": round((mp.defect_rate or 0) * 100, 1),
                        "to_defect_pct": round((mb.defect_rate or 0) * 100, 1),
                        "from_return_pct": round((mp.return_rate or 0) * 100, 1)
                        if mp.return_rate is not None
                        else None,
                        "to_return_pct": round((mb.return_rate or 0) * 100, 1)
                        if mb.return_rate is not None
                        else None,
                    },
                },
                "evidence": [
                    {
                        "metric": "unit_economics",
                        "supplier": names.get(s),
                        "value": econ[s],
                        "received": ms[s].received_units,
                    }
                    for s in (pref, best)
                ],
                "confidence": 0.8 if min(mb.received_units, mp.received_units) >= 50 else 0.6,
                "estimated_impact": {"gain_per_unit_minor": gain},
                "action": {
                    "type": "set_preferred_supplier",
                    "params": {"variant_id": str(vid), "supplier_id": str(best)},
                },
                "baseline": {"from": str(pref), "to": str(best), "gain_per_unit_minor": gain},
            }
        )
    return out[:3]


def reorder_proposals(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """PRO-007 / SPI-004: what to buy, from whom, how many and by when."""
    from app.domains.catalog.models import Product, Supplier, Variant, VariantSupplier
    from app.domains.intelligence import profit
    from app.domains.intelligence.models import ProductIntelligenceProfile
    from app.domains.inventory import service as inventory
    from app.domains.orders.models import Order, OrderLine
    from app.domains.procurement.service import incoming

    links: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for vs in db.scalars(select(VariantSupplier).where(VariantSupplier.merchant_id == merchant_id)):
        links[vs.variant_id].append(vs)
    if not links:
        return []
    ms = metrics(db, merchant_id)
    limits = profit.settings_row(db, merchant_id)
    vids = list(links)
    since = utcnow() - timedelta(days=90)
    units_v = dict(
        db.execute(
            select(OrderLine.variant_id, func.sum(OrderLine.quantity - OrderLine.cancelled_quantity))
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                Order.merchant_id == merchant_id,
                Order.placed_at >= since,
                Order.status.not_in(("draft", "cancelled")),
                OrderLine.variant_id.in_(vids),
            )
            .group_by(OrderLine.variant_id)
        ).all()
    )
    av = inventory.availability(db, merchant_id, vids)
    inc = incoming(db, merchant_id, vids)
    out: list[dict[str, Any]] = []
    for vid, rows in links.items():
        v = db.get(Variant, vid)
        if v is None or v.status != "active" or not av.get(vid) or not av[vid].tracked:
            continue
        p = db.get(Product, v.product_id)
        if p is None or p.status == "archived":
            continue
        prof = db.scalar(
            select(ProductIntelligenceProfile).where(ProductIntelligenceProfile.product_id == p.id)
        )
        sold_v = int(units_v.get(vid) or 0)
        if sold_v <= 0:
            continue
        if prof is not None and prof.demand_per_day and prof.units_90d:
            demand = prof.demand_per_day * sold_v / prof.units_90d  # the variant's share of product demand
        else:
            demand = sold_v / 90
        if prof is not None:
            if (
                prof.contribution_per_unit_minor is not None
                and prof.contribution_per_unit_minor < limits.min_contribution_minor
            ):
                continue
            if prof.return_rate is not None and prof.return_rate * 100 > limits.max_return_rate_pct:
                continue
        econ = {
            r.supplier_id: unit_economics(ms.get(r.supplier_id), r.cost_minor, v.price_minor) for r in rows
        }
        known = {k: x for k, x in econ.items() if x is not None and ms.get(k) is not None}
        pick = (
            max(known, key=lambda k: known[k])
            if known
            else next((r.supplier_id for r in rows if r.is_preferred), rows[0].supplier_id)
        )
        vs = next(r for r in rows if r.supplier_id == pick)
        s = db.get(Supplier, pick)
        if s is None or s.status != "active":
            continue
        m = ms.get(pick)
        lead = (
            m.lead_time_days_avg
            if m is not None and m.lead_time_days_avg is not None
            else vs.lead_time_days or s.default_lead_time_days or DEFAULT_LEAD_DAYS
        )
        sd = m.lead_time_days_sd if m is not None and m.lead_time_days_sd is not None else 0.0
        safety = max(MIN_SAFETY_DAYS, math.ceil(1.65 * sd))
        available = max(0, av[vid].available)
        on_way = inc.get(vid, 0)
        cover = (available + on_way) / demand if demand > 0 else None
        if cover is None or cover >= lead + safety:
            continue
        qty = math.ceil(demand * (lead + safety + COVER_TARGET_DAYS)) - available - on_way
        if vs.moq:
            qty = max(qty, vs.moq)
        if qty <= 0:
            continue
        cost = vs.cost_minor if vs.cost_minor is not None else v.cost_minor
        days_left = round(available / demand, 1)
        out.append(
            {
                "type": "reorder",
                "dedupe_key": f"reorder:{vid}",
                "subject_type": "variant",
                "subject_id": str(vid),
                "explanation": {
                    "what": "reorder",
                    "why": "runs_out_before_delivery",
                    "vars": {
                        "title": p.title,
                        "variant": None if v.title == "Default" else v.title,
                        "days_left": days_left,
                        "per_day": round(demand, 2),
                        "available": available,
                        "incoming": on_way,
                        "lead_days": round(lead, 1),
                        "safety_days": safety,
                        "quantity": qty,
                        "supplier": s.name,
                        "moq": vs.moq,
                        "unit_cost": cost,
                        "chosen_by": "true_economics" if known else "preferred",
                    },
                },
                "evidence": [
                    {"metric": "units_sold", "window_days": 90, "value": sold_v},
                    {"metric": "available", "value": available},
                    {"metric": "incoming", "value": on_way},
                    {
                        "metric": "lead_time_days",
                        "value": round(lead, 1),
                        "source": "measured" if m and m.lead_time_days_avg is not None else "supplier_terms",
                    },
                ],
                "confidence": 0.8 if sold_v >= 10 else 0.6,
                "estimated_impact": {
                    "stockout_in_days": days_left,
                    "order_value_minor": qty * cost if cost is not None else None,
                },
                "action": {
                    "type": "create_po_draft",
                    "params": {
                        "supplier_id": str(pick),
                        "variant_id": str(vid),
                        "quantity": qty,
                        "unit_cost_minor": cost,
                    },
                },
                "baseline": {"available": available, "incoming": on_way, "per_day": round(demand, 3)},
            }
        )
    out.sort(key=lambda x: float(x["baseline"]["available"]) / max(float(x["baseline"]["per_day"]), 1e-9))
    return out[:5]
