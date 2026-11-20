"""What-if simulation (SIM-001…006; spec 14 §Simulation).

Every output is an ESTIMATE with its assumptions, a range and a confidence. Nothing is executed: acting
on a result is a separate step (a price change or a purchase order) that goes through its own approval.

- Discount (SIM-002): demand at the discounted price = baseline demand x (1 - d)^elasticity. Elasticity
  comes from the shop's own history (days sold below list price vs full-price days); without enough
  promotion history a typical range is used and confidence is low. Units are capped by stock (available +
  incoming); stockout probability uses a Poisson demand model.
- Purchase quantity (SIM-003): stock-out risk before the delivery arrives (lead time from supplier
  performance or terms), days of cover after it arrives, chance of selling through in 60 days, cash tied up
  and what's likely left after 90 days.
- Ad budget (SIM-004): needs connected ad spend; refused until an ad account is connected.
- Calibration (SIM-006): a 14-day holdout backtest of the demand model per product, plus a comparison of
  discount runs with what happened when the seller actually ran that discount.

Runs are queued and executed by the worker (outbox `simulation.requested`), then `simulation.completed`.
"""

from __future__ import annotations

import math
import statistics
import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler, publish
from app.domains.twin.models import SimulationRun

log = structlog.get_logger(__name__)

METHOD_VERSION = "sim-1.0"
PRIOR_ELASTICITY = -1.5
PRIOR_RANGE = (-0.5, -3.0)
MIN_DISCOUNT_DAYS = 5
MIN_FULL_DAYS = 10
DISCOUNT_THRESHOLD = 0.95  # a day counts as discounted when the average paid price ≤ 95% of list
BACKTEST_HOLDOUT = 14
BACKTEST_MIN_SALE_DAYS = 20


# ----------------------------------------------------------------------------- maths
def poisson_sf(k: float, lam: float) -> float:
    """P(X > k) for X ~ Poisson(lam). Normal approximation (continuity-corrected) for large lam."""
    if lam <= 0:
        return 0.0
    k = math.floor(k)
    if k < 0:
        return 1.0
    if lam > 200:
        z = (k + 0.5 - lam) / math.sqrt(lam)
        return 0.5 * math.erfc(z / math.sqrt(2))
    term = math.exp(-lam)
    cdf = term
    for i in range(1, int(k) + 1):
        term *= lam / i
        cdf += term
    return max(0.0, min(1.0, 1 - cdf))


def expected_sold(lam: float, stock: float) -> float:
    """E[min(X, stock)] for X ~ Poisson(lam): demand you can actually serve."""
    if stock <= 0 or lam <= 0:
        return 0.0
    s = int(stock)
    if lam > 200 or s > 2000:
        return min(lam, stock)
    total, term = 0.0, math.exp(-lam)
    p_le = term
    for i in range(1, s):
        term *= lam / i
        total += i * term
        p_le += term
    # E[min(X,s)] = sum_{i<s} i P(X=i) + s P(X>=s)
    return total + s * max(0.0, 1 - p_le)


# ----------------------------------------------------------------------------- shared inputs
def _product_inputs(db: Session, merchant_id: uuid.UUID, product_id: uuid.UUID) -> dict[str, Any]:
    from app.domains.catalog.models import Product, Variant
    from app.domains.intelligence import product_brain
    from app.domains.inventory import service as inventory
    from app.domains.procurement.service import incoming

    p = db.get(Product, product_id)
    if p is None or p.merchant_id != merchant_id:
        raise NotFound(code="product_not_found")
    variants = list(db.scalars(select(Variant).where(Variant.product_id == p.id, Variant.status == "active")))
    if not variants:
        raise ValidationFailed("This product has no active variants", code="simulation_no_variants")
    prof = product_brain.get_or_compute(db, merchant_id, p.id)
    vids = [v.id for v in variants]
    av = inventory.availability(db, merchant_id, vids)
    tracked = [a for a in av.values() if a.tracked]
    inc = incoming(db, merchant_id, vids)
    costs = [v.cost_minor for v in variants if v.cost_minor is not None]
    return {
        "product": p,
        "variants": variants,
        "profile": prof,
        "price": round(sum(v.price_minor for v in variants) / len(variants)),
        "cost": round(sum(costs) / len(costs)) if len(costs) == len(variants) else None,
        "stock": (sum(max(0, a.available) for a in tracked) + sum(inc.values())) if tracked else None,
        "incoming": sum(inc.values()),
    }


def elasticity(db: Session, merchant_id: uuid.UUID, product_id: uuid.UUID) -> dict[str, Any]:
    """Own-history price elasticity: discounted days vs full-price days over the last year."""
    from app.domains.catalog.models import Variant
    from app.domains.orders.models import Order, OrderLine

    list_price = {
        v.id: v.price_minor for v in db.scalars(select(Variant).where(Variant.product_id == product_id))
    }
    rows = db.execute(
        select(
            func.date(Order.placed_at),
            OrderLine.variant_id,
            OrderLine.unit_price_minor,
            OrderLine.line_discount_minor,
            OrderLine.quantity - OrderLine.cancelled_quantity,
        )
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            Order.merchant_id == merchant_id,
            OrderLine.product_id == product_id,
            Order.placed_at >= utcnow() - timedelta(days=365),
            Order.status.not_in(("draft", "cancelled")),
        )
    ).all()
    days: dict[date, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])  # units, paid, list
    for d, vid, unit, disc, qty in rows:
        if not qty or vid not in list_price:
            continue
        days[d][0] += qty
        days[d][1] += unit * qty - disc
        days[d][2] += list_price[vid] * qty
    disc_days = {d: x for d, x in days.items() if x[2] and x[1] / x[2] <= DISCOUNT_THRESHOLD}
    full_days = {d: x for d, x in days.items() if d not in disc_days}
    if len(disc_days) >= MIN_DISCOUNT_DAYS and len(full_days) >= MIN_FULL_DAYS:
        q_d = statistics.fmean(x[0] for x in disc_days.values())
        q_f = statistics.fmean(x[0] for x in full_days.values())
        p_ratio = statistics.fmean(x[1] / x[2] for x in disc_days.values())
        if q_d > 0 and q_f > 0 and 0 < p_ratio < 1:
            e = max(-6.0, min(-0.2, math.log(q_d / q_f) / math.log(p_ratio)))
            return {
                "value": round(e, 2),
                "range": (round(e * 0.6, 2), round(e * 1.4, 2)),
                "source": "history",
                "discount_days": len(disc_days),
                "full_price_days": len(full_days),
                "avg_discount_pct": round((1 - p_ratio) * 100, 1),
                "confidence": "medium" if len(disc_days) >= 10 else "low",
            }
    return {
        "value": PRIOR_ELASTICITY,
        "range": PRIOR_RANGE,
        "source": "typical_range",
        "discount_days": len(disc_days),
        "full_price_days": len(full_days),
        "confidence": "low",
    }


# ----------------------------------------------------------------------------- SIM-002 discount
def simulate_discount(
    db: Session, merchant_id: uuid.UUID, inputs: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    from app.domains.intelligence import profit

    x = _product_inputs(db, merchant_id, uuid.UUID(inputs["product_id"]))
    prof = x["profile"]
    d = inputs["discount_pct"] / 100
    days = int(inputs["days"])
    q0 = prof.demand_per_day
    if q0 is None or q0 <= 0:
        raise ValidationFailed("Not enough sales to estimate demand", code="simulation_not_enough_sales")
    el = elasticity(db, merchant_id, x["product"].id)
    mult = (1 - d) ** el["value"]
    lo_mult, hi_mult = sorted(((1 - d) ** el["range"][0], (1 - d) ** el["range"][1]))
    q, q_lo, q_hi = q0 * mult, q0 * lo_mult, q0 * hi_mult
    stock = x["stock"]
    price = x["price"]
    cpu0 = prof.contribution_per_unit_minor
    if cpu0 is None and x["cost"] is not None:
        cpu0 = price - x["cost"]
    cpu1 = None if cpu0 is None else round(cpu0 - price * d)

    def served(rate: float) -> float:
        lam = rate * days
        return expected_sold(lam, stock) if stock is not None else lam

    units = {k: round(served(r), 1) for k, r in (("expected", q), ("low", q_lo), ("high", q_hi))}
    base_units = round(served(q0), 1)
    contrib = None if cpu1 is None else {k: round(v * cpu1) for k, v in units.items()}
    base_contrib = None if cpu0 is None else round(base_units * cpu0)
    margin_before = round(100 * (price - x["cost"]) / price, 1) if x["cost"] is not None and price else None
    after_price = price * (1 - d)
    margin_after = (
        round(100 * (after_price - x["cost"]) / after_price, 1)
        if x["cost"] is not None and after_price
        else None
    )
    limits = profit.settings_row(db, merchant_id)
    warnings = []
    if margin_after is not None and margin_after < limits.min_margin_pct:
        warnings.append({"code": "below_min_margin", "min_margin_pct": limits.min_margin_pct})
    if contrib is not None and base_contrib is not None and contrib["expected"] < base_contrib:
        warnings.append(
            {"code": "earns_less_than_no_discount", "difference_minor": contrib["expected"] - base_contrib}
        )
    if cpu1 is not None and cpu1 < 0:
        warnings.append({"code": "loses_money_per_unit", "per_unit_minor": cpu1})
    stockout = round(poisson_sf(stock, q * days), 3) if stock is not None else None
    if stockout is not None and stockout >= 0.5:
        warnings.append({"code": "stockout_likely", "probability": stockout})
    outputs = {
        "label": "estimate",
        "product_id": str(x["product"].id),
        "title": x["product"].title,
        "days": days,
        "discount_pct": inputs["discount_pct"],
        "price_minor": price,
        "discounted_price_minor": round(after_price),
        "demand_per_day": {
            "baseline": round(q0, 2),
            "expected": round(q, 2),
            "low": round(q_lo, 2),
            "high": round(q_hi, 2),
        },
        "units": {**units, "baseline": base_units},
        "stock": stock,
        "stock_days": round(stock / q, 1) if stock is not None and q > 0 else None,
        "stockout_probability": stockout,
        "margin_pct": {"before": margin_before, "after": margin_after},
        "contribution_per_unit_minor": {"before": cpu0, "after": cpu1},
        "contribution_minor": {"with_discount": contrib, "without_discount": base_contrib},
        "difference_minor": (contrib["expected"] - base_contrib)
        if contrib is not None and base_contrib is not None
        else None,
        "return_rate": prof.return_rate,
        "warnings": warnings,
        "not_included": [] if cpu0 is not None else ["contribution_cost_not_set"],
    }
    assumptions = [
        {
            "code": "baseline_demand",
            "vars": {
                "per_day": round(q0, 2),
                "in_stock_days": prof.in_stock_days_90d,
                "source": "product_brain",
            },
        },
        {
            "code": f"elasticity_{el['source']}",
            "vars": {k: v for k, v in el.items() if k not in ("confidence",)},
        },
        {"code": "stock_caps_sales", "vars": {"stock": stock, "incoming": x["incoming"]}}
        if stock is not None
        else {"code": "stock_not_tracked", "vars": {}},
        {"code": "other_costs_per_unit_unchanged", "vars": {"contribution_per_unit_minor": cpu0}},
        {"code": "returns_like_recent_sales", "vars": {"return_rate": prof.return_rate}},
        {"code": "no_seasonality", "vars": {}},
    ]
    return outputs, assumptions, el["confidence"]


# ----------------------------------------------------------------------------- SIM-003 purchase quantity
def simulate_purchase(
    db: Session, merchant_id: uuid.UUID, inputs: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    from app.domains.catalog.models import Product, Supplier, Variant, VariantSupplier
    from app.domains.intelligence.models import ProductIntelligenceProfile
    from app.domains.inventory import service as inventory
    from app.domains.orders.models import Order, OrderLine
    from app.domains.procurement import supplier_intel
    from app.domains.procurement.service import incoming

    v = db.get(Variant, uuid.UUID(inputs["variant_id"]))
    if v is None or v.merchant_id != merchant_id:
        raise NotFound(code="variant_not_found")
    p = db.get(Product, v.product_id)
    qty = int(inputs["quantity"])
    sold90 = int(
        db.scalar(
            select(func.coalesce(func.sum(OrderLine.quantity - OrderLine.cancelled_quantity), 0))
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                OrderLine.variant_id == v.id,
                Order.placed_at >= utcnow() - timedelta(days=90),
                Order.status.not_in(("draft", "cancelled")),
            )
        )
        or 0
    )
    if sold90 <= 0:
        raise ValidationFailed(
            "No sales in the last 90 days to estimate demand", code="simulation_not_enough_sales"
        )
    prof = db.scalar(
        select(ProductIntelligenceProfile).where(ProductIntelligenceProfile.product_id == v.product_id)
    )
    q = (
        prof.demand_per_day * sold90 / prof.units_90d
        if prof and prof.demand_per_day and prof.units_90d
        else sold90 / 90
    )
    links = list(db.scalars(select(VariantSupplier).where(VariantSupplier.variant_id == v.id)))
    sid = (
        uuid.UUID(inputs["supplier_id"])
        if inputs.get("supplier_id")
        else next((r.supplier_id for r in links if r.is_preferred), links[0].supplier_id if links else None)
    )
    vs = next((r for r in links if r.supplier_id == sid), None)
    s = db.get(Supplier, sid) if sid else None
    m = supplier_intel.metrics(db, merchant_id).get(sid) if sid else None
    lead = (
        m.lead_time_days_avg
        if m is not None and m.lead_time_days_avg is not None
        else (
            vs.lead_time_days
            if vs and vs.lead_time_days is not None
            else (
                s.default_lead_time_days
                if s and s.default_lead_time_days is not None
                else supplier_intel.DEFAULT_LEAD_DAYS
            )
        )
    )
    lead_source = (
        "measured"
        if m is not None and m.lead_time_days_avg is not None
        else (
            "supplier_terms"
            if (vs and vs.lead_time_days is not None) or (s and s.default_lead_time_days is not None)
            else "default"
        )
    )
    av = inventory.availability(db, merchant_id, [v.id]).get(v.id)
    available = max(0, av.available) if av and av.tracked else 0
    inc = incoming(db, merchant_id, [v.id]).get(v.id, 0)
    unit_cost = (
        (m.avg_landed_cost_minor if m is not None and m.avg_landed_cost_minor is not None else None)
        or (vs.cost_minor if vs else None)
        or v.cost_minor
    )
    lam_lead = q * lead
    stockout_before = round(poisson_sf(available + inc, lam_lead), 3)
    left_at_arrival = max(0.0, available + inc - lam_lead)
    stock_after = left_at_arrival + qty
    sell_out_60 = round(1 - poisson_sf(stock_after - 1, q * 60), 3) if stock_after > 0 else 1.0
    sold_90 = expected_sold(q * 90, stock_after)
    leftover_90 = round(max(0.0, stock_after - sold_90), 1)
    cpu = prof.contribution_per_unit_minor if prof else None
    warnings = []
    if vs and vs.moq and qty < vs.moq:
        warnings.append({"code": "below_moq", "moq": vs.moq})
    if stockout_before >= 0.3:
        warnings.append({"code": "may_sell_out_before_delivery", "probability": stockout_before})
    if leftover_90 > qty * 0.5:
        warnings.append({"code": "slow_to_sell", "leftover_90": leftover_90})
    outputs = {
        "label": "estimate",
        "variant_id": str(v.id),
        "title": p.title if p else None,
        "variant": None if v.title == "Default" else v.title,
        "quantity": qty,
        "supplier": s.name if s else None,
        "per_day": round(q, 2),
        "lead_days": round(lead, 1),
        "available": available,
        "incoming": inc,
        "stockout_before_arrival_probability": stockout_before,
        "stock_after_arrival": round(stock_after, 1),
        "cover_days_after_arrival": round(stock_after / q, 1) if q > 0 else None,
        "sell_out_within_60d_probability": sell_out_60,
        "units_sold_90d": round(sold_90, 1),
        "leftover_after_90d": leftover_90,
        "cash_tied_up_minor": qty * unit_cost if unit_cost is not None else None,
        "contribution_90d_minor": round(min(sold_90, qty) * cpu) if cpu is not None else None,
        "warnings": warnings,
        "not_included": [k for k, val in (("unit_cost", unit_cost), ("contribution", cpu)) if val is None],
    }
    assumptions = [
        {"code": "variant_demand", "vars": {"per_day": round(q, 2), "sold_90d": sold90}},
        {"code": f"lead_time_{lead_source}", "vars": {"days": round(lead, 1)}},
        {"code": "incoming_arrives_first", "vars": {"incoming": inc}},
        {"code": "poisson_demand", "vars": {}},
        {
            "code": "unit_cost_"
            + ("landed" if m is not None and m.avg_landed_cost_minor is not None else "purchase_price"),
            "vars": {"unit_cost_minor": unit_cost},
        },
        {"code": "no_seasonality", "vars": {}},
    ]
    conf = "medium" if sold90 >= 20 and lead_source == "measured" else "low" if sold90 < 10 else "medium"
    return outputs, assumptions, conf


# ----------------------------------------------------------------------------- runs (SIM-001/005)
KINDS = {"discount": simulate_discount, "purchase_quantity": simulate_purchase}


def create(db: Session, ctx: TenantContext, kind: str, inputs: dict[str, Any]) -> SimulationRun:
    if kind == "ad_budget":
        raise Conflict(
            "Connect an ad account first: ad-budget estimates need your real ad spend",
            code="simulation_needs_ad_account",
        )
    if kind not in KINDS:
        raise ValidationFailed("Unknown simulation", code="simulation_kind_unknown")
    r = SimulationRun(
        merchant_id=ctx.merchant_id,
        kind=kind,
        inputs=inputs,
        method_version=METHOD_VERSION,
        created_by_user_id=ctx.actor.id,
        status="queued",
    )
    db.add(r)
    db.flush()
    publish(
        db,
        event_type="simulation.requested",
        aggregate_type="simulation",
        aggregate_id=r.id,
        payload={"simulation_id": str(r.id)},
        merchant_id=ctx.merchant_id,
    )
    return r


def execute(db: Session, run_id: uuid.UUID) -> SimulationRun | None:
    from app.domains.twin.models import StoreTwinSection

    r = db.scalar(
        select(SimulationRun)
        .where(SimulationRun.id == run_id)
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if r is None or r.status not in ("queued", "running"):
        return r
    bind_tenant(db, r.merchant_id)
    r.status = "running"
    inv = db.scalar(
        select(StoreTwinSection).where(
            StoreTwinSection.merchant_id == r.merchant_id, StoreTwinSection.section == "inventory"
        )
    )
    r.baseline_as_of = inv.as_of if inv else utcnow()
    try:
        with db.begin_nested():
            outputs, assumptions, conf = KINDS[r.kind](db, r.merchant_id, r.inputs)
        r.outputs, r.assumptions, r.confidence, r.status = outputs, assumptions, conf, "completed"
    except (ValidationFailed, NotFound) as e:
        r.status, r.error_code = "failed", e.code
    except Exception:
        log.exception("simulation_failed", run_id=str(r.id))
        r.status, r.error_code = "failed", "simulation_error"
    r.completed_at = utcnow()
    publish(
        db,
        event_type="simulation.completed",
        aggregate_type="simulation",
        aggregate_id=r.id,
        payload={"simulation_id": str(r.id), "status": r.status},
        merchant_id=r.merchant_id,
    )
    return r


@handler("simulation.requested", name="twin.simulation_run")
def _on_requested(db: Session, ev: OutboxEvent) -> None:
    execute(db, uuid.UUID(ev.payload["simulation_id"]))


def get(db: Session, ctx: TenantContext, run_id: uuid.UUID) -> SimulationRun:
    r = db.get(SimulationRun, run_id)
    if r is None or r.merchant_id != ctx.merchant_id:
        raise NotFound(code="simulation_not_found")
    return r


def view(r: SimulationRun) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "kind": r.kind,
        "status": r.status,
        "inputs": r.inputs,
        "outputs": r.outputs,
        "assumptions": r.assumptions,
        "confidence": r.confidence,
        "label": "estimate",
        "executes_nothing": True,
        "method_version": r.method_version,
        "baseline_as_of": r.baseline_as_of.isoformat() if r.baseline_as_of else None,
        "error_code": r.error_code,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "actual": r.actual,
        "abs_pct_error": r.abs_pct_error,
    }


# ----------------------------------------------------------------------------- SIM-006 calibration
def demand_backtest(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    """Holdout: predict the last 14 days of units from the EWMA before them; compare with what sold."""
    from app.domains.intelligence.product_brain import ewma
    from app.domains.orders.models import Order, OrderLine

    today = utcnow().date()
    start = today - timedelta(days=120)
    cut = today - timedelta(days=BACKTEST_HOLDOUT)
    rows = db.execute(
        select(
            OrderLine.product_id,
            func.date(Order.placed_at),
            func.sum(OrderLine.quantity - OrderLine.cancelled_quantity),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= utcnow() - timedelta(days=120),
            Order.status.not_in(("draft", "cancelled")),
            OrderLine.product_id.is_not(None),
        )
        .group_by(OrderLine.product_id, func.date(Order.placed_at))
    ).all()
    by: dict[uuid.UUID, dict[date, int]] = defaultdict(dict)
    for pid, d, u in rows:
        by[pid][d] = int(u or 0)
    errors = []
    items: list[dict[str, Any]] = []
    for pid, series in by.items():
        train_days = [start + timedelta(days=i) for i in range((cut - start).days)]
        first = min(series)
        train = [float(series.get(d, 0)) for d in train_days if d >= first]
        if sum(1 for d in series if d < cut) < BACKTEST_MIN_SALE_DAYS:
            continue
        rate = ewma(train) or 0.0
        predicted = rate * BACKTEST_HOLDOUT
        actual = sum(u for d, u in series.items() if d >= cut)
        if actual <= 0:
            continue
        ape = abs(predicted - actual) / actual
        errors.append(ape)
        items.append(
            {
                "product_id": str(pid),
                "predicted": round(predicted, 1),
                "actual": actual,
                "abs_pct_error": round(ape, 3),
            }
        )
    return {
        "holdout_days": BACKTEST_HOLDOUT,
        "products": len(items),
        "mape": round(statistics.fmean(errors), 3) if errors else None,
        "median_ape": round(statistics.median(errors), 3) if errors else None,
        "items": sorted(items, key=lambda x: -float(x["abs_pct_error"]))[:20],
        "note": "Out-of-stock days aren't excluded here; promotions in the holdout inflate the error.",
    }


def realized(db: Session, merchant_id: uuid.UUID) -> int:
    """Discount runs whose window has passed: did the seller run it, and how close was the estimate?"""
    from app.domains.catalog.models import Variant
    from app.domains.orders.models import Order, OrderLine

    n = 0
    for r in db.scalars(
        select(SimulationRun).where(
            SimulationRun.kind == "discount",
            SimulationRun.status == "completed",
            SimulationRun.actual.is_(None),
        )
    ):
        if r.outputs is None or r.created_at is None:
            continue
        end = r.created_at + timedelta(days=int(r.inputs["days"]))
        if utcnow() < end:
            continue
        pid = uuid.UUID(r.inputs["product_id"])
        list_price = {
            v.id: v.price_minor for v in db.scalars(select(Variant).where(Variant.product_id == pid))
        }
        lines = db.execute(
            select(
                OrderLine.variant_id,
                OrderLine.unit_price_minor,
                OrderLine.line_discount_minor,
                OrderLine.quantity - OrderLine.cancelled_quantity,
            )
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                OrderLine.product_id == pid,
                Order.placed_at >= r.created_at,
                Order.placed_at < end,
                Order.status.not_in(("draft", "cancelled")),
            )
        ).all()
        units = int(sum(int(q or 0) for *_x, q in lines))
        paid = sum(u * q - dsc for _v, u, dsc, q in lines if q)
        listed = sum((list_price.get(v, u) if v is not None else u) * q for v, u, _d, q in lines if q)
        applied = round((1 - paid / listed) * 100, 1) if listed else 0.0
        comparable = abs(applied - r.inputs["discount_pct"]) <= 5 and units > 0
        r.actual = {"units": units, "discount_applied_pct": applied, "comparable": comparable}
        if comparable:
            r.abs_pct_error = round(abs(r.outputs["units"]["expected"] - units) / units, 3)
        n += 1
    db.flush()  # sessions don't autoflush; calibration reads these right after
    return n


def calibration(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    realized(db, merchant_id)
    runs = list(db.scalars(select(SimulationRun).where(SimulationRun.abs_pct_error.is_not(None))))
    return {
        "demand_backtest": demand_backtest(db, merchant_id),
        "discount_runs_compared": len(runs),
        "discount_runs_mape": round(
            statistics.fmean(r.abs_pct_error for r in runs if r.abs_pct_error is not None), 3
        )
        if runs
        else None,
    }
