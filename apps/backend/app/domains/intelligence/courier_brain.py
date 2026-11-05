"""Courier Brain (CRI-001…005, FUL-009, spec 12).

Learns from this merchant's own finished parcels how each courier performs per route (pickup district →
destination district), weight band and COD flag, then ranks the courier options for a new order:

* cheapest — lowest price whose delivery success is at least MIN_SUCCESS
* fastest  — lowest median delivery time
* smart    — lowest expected cost: price + P(failure) * failure cost + cash-held-back cost
* preferred — the merchant's default courier only

Success is smoothed ((delivered + 1) / (n + 2)). With fewer than MIN_SAMPLE finished parcels for the
route, the rules recommendation is kept and the response says so (cold start, CRI-005).
"""

from __future__ import annotations

import statistics
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import bind_tenant, utcnow
from app.domains.intelligence.models import CourierPerformanceMetric

METHOD_VERSION = "cri-1.0"
PERIOD_DAYS = 90
MIN_SAMPLE = 20
MIN_SUCCESS = 0.8
HANDLING_COST_MINOR = 5000  # packing again, calls, restocking (documented estimate, NPR 50)
CASH_COST_PER_DAY = 0.0005  # 0.05% of COD value per day the courier holds the cash (estimate)
MODES = ("rules", "cheapest", "fastest", "smart", "preferred")
FINISHED = ("delivered", "returned_to_origin", "lost")


def weight_band(grams: int) -> str:
    return "le1kg" if grams <= 1000 else "1to3kg" if grams <= 3000 else "gt3kg"


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    k = max(0, min(len(v) - 1, round(q * (len(v) - 1))))
    return round(v[k], 2)


def recompute(db: Session, merchant_id: uuid.UUID) -> int:
    """CRI-001: rebuild this merchant's metrics from finished outbound parcels in the period."""
    from app.domains.fulfillment.models import Shipment
    from app.domains.payments.models import CODRecord

    since = utcnow() - timedelta(days=PERIOD_DAYS)
    rows = db.execute(
        select(Shipment, CODRecord.settled_at)
        .outerjoin(CODRecord, CODRecord.order_id == Shipment.order_id)
        .where(
            Shipment.merchant_id == merchant_id,
            Shipment.direction == "outbound",
            Shipment.status.in_(FINISHED),
            Shipment.created_at >= since,
            Shipment.origin_district.is_not(None),
            Shipment.destination_district.is_not(None),
        )
    ).all()
    groups: dict[tuple[uuid.UUID, str | None, str | None, str, bool], list[tuple[Any, Any]]] = {}
    for s, settled_at in rows:
        key = (
            s.courier_account_id,
            s.origin_district,
            s.destination_district,
            weight_band(s.weight_grams),
            s.cod_amount_minor > 0,
        )
        groups.setdefault(key, []).append((s, settled_at))
    db.execute(delete(CourierPerformanceMetric).where(CourierPerformanceMetric.merchant_id == merchant_id))
    for (acct, origin, dest, band, cod), items in groups.items():
        delivered = [s for s, _ in items if s.status == "delivered"]
        etas = [
            (s.delivered_at - (s.picked_up_at or s.created_at)).total_seconds() / 86400
            for s in delivered
            if s.delivered_at
        ]
        prices = [s.charge_minor for s, _ in items if s.charge_minor is not None]
        settle = [(st - s.delivered_at).total_seconds() / 86400 for s, st in items if st and s.delivered_at]
        db.add(
            CourierPerformanceMetric(
                merchant_id=merchant_id,
                courier_account_id=acct,
                origin=origin or "",
                destination=dest or "",
                weight_band=band,
                cod=cod,
                period_days=PERIOD_DAYS,
                n=len(items),
                delivered=len(delivered),
                first_attempt=sum(1 for s in delivered if s.attempt_count == 0),
                failed_any=sum(1 for s, _ in items if s.attempt_count > 0),
                returned=sum(1 for s, _ in items if s.status == "returned_to_origin"),
                lost=sum(1 for s, _ in items if s.status == "lost"),
                eta_p50_days=_pct(etas, 0.5),
                eta_p90_days=_pct(etas, 0.9),
                avg_price_minor=round(statistics.mean(prices)) if prices else None,
                cod_settlement_days=round(statistics.mean(settle), 1) if settle else None,
            )
        )
    db.flush()
    return len(groups)


def recompute_all(db: Session) -> int:
    from app.domains.fulfillment.models import Shipment

    mids = db.scalars(
        select(Shipment.merchant_id)
        .where(Shipment.status.in_(FINISHED), Shipment.created_at >= utcnow() - timedelta(days=PERIOD_DAYS))
        .distinct()
        .execution_options(skip_tenant_filter=True)
    ).all()
    for mid in mids:
        bind_tenant(db, mid)
        recompute(db, mid)
    return len(mids)


def route_stats(
    db: Session,
    merchant_id: uuid.UUID,
    account_id: uuid.UUID,
    origin: str | None,
    dest: str | None,
    cod: bool,
) -> dict[str, Any] | None:
    """All weight bands pooled for the route and COD flag (more samples, same route behaviour)."""
    if not origin or not dest:
        return None
    rows = list(
        db.scalars(
            select(CourierPerformanceMetric).where(
                CourierPerformanceMetric.merchant_id == merchant_id,
                CourierPerformanceMetric.courier_account_id == account_id,
                CourierPerformanceMetric.origin == origin,
                CourierPerformanceMetric.destination == dest,
                CourierPerformanceMetric.cod.is_(cod),
            )
        )
    )
    if not rows:
        return None
    n = sum(r.n for r in rows)
    delivered = sum(r.delivered for r in rows)
    etas = [r.eta_p50_days for r in rows if r.eta_p50_days is not None]
    settle = [r.cod_settlement_days for r in rows if r.cod_settlement_days is not None]
    return {
        "n": n,
        "delivered": delivered,
        "success": (delivered + 1) / (n + 2),
        "success_raw": delivered / n if n else None,
        "first_attempt": sum(r.first_attempt for r in rows) / n if n else None,
        "eta_p50_days": round(statistics.mean(etas), 1) if etas else None,
        "cod_settlement_days": round(statistics.mean(settle), 1) if settle else None,
    }


def rank(db: Session, merchant_id: uuid.UUID, order: Any, data: dict[str, Any], mode: str) -> dict[str, Any]:
    """Re-rank courier options (from ``couriers.courier_options``) by the chosen mode."""
    from app.domains.fulfillment.models import CourierAccount

    cod = data["cod_amount_minor"] > 0
    priced = [o for o in data["options"] if o["price"] is not None]
    enriched = []
    for o in priced:
        acct = db.get(CourierAccount, o["courier_account_id"])
        st = route_stats(
            db,
            merchant_id,
            o["courier_account_id"],
            acct.pickup_district if acct else None,
            order.ship_district,
            cod,
        )
        o["route_stats"] = (
            {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items() if k != "success"}
            if st
            else None
        )
        enriched.append((o, st))
    known = [(o, st) for o, st in enriched if st and st["n"] >= MIN_SAMPLE]
    if mode == "preferred":
        pick = next((o for o in priced if o["is_default"]), None)
        return _result(data, pick, "preferred_only", "courier_brain", known, None)
    if not known:
        data["recommendation"] = data["recommendation"] and {
            **data["recommendation"],
            "note": "not_enough_route_data",
            "min_sample": MIN_SAMPLE,
        }
        return data
    best: tuple[dict[str, Any], dict[str, Any]] | None = None
    if mode == "cheapest":
        ok = [(o, st) for o, st in known if st["success"] >= MIN_SUCCESS] or known
        best = min(ok, key=lambda x: x[0]["price"]["amount_minor"])
    elif mode == "fastest":
        timed = [(o, st) for o, st in known if st["eta_p50_days"] is not None]
        best = min(timed, key=lambda x: x[1]["eta_p50_days"]) if timed else None
    else:  # smart

        def cost(x: tuple[dict[str, Any], dict[str, Any]]) -> float:
            o, st = x
            price = o["price"]["amount_minor"]
            failure_cost = 2 * price + HANDLING_COST_MINOR  # return shipping + wasted outbound + handling
            hold = (
                data["cod_amount_minor"] * CASH_COST_PER_DAY * (st["cod_settlement_days"] or 0) if cod else 0
            )
            o["expected_cost_minor"] = round(price + (1 - st["success"]) * failure_cost + hold)
            return o["expected_cost_minor"]

        best = min(known, key=cost)
    if best is None:
        return data
    cheapest = min((o["price"]["amount_minor"] for o in priced), default=None)
    return _result(data, best[0], "route_history", "courier_brain", known, best[1], cheapest)


def _result(
    data: dict[str, Any],
    pick: dict[str, Any] | None,
    reason: str,
    method: str,
    known: list[Any],
    st: dict[str, Any] | None,
    cheapest: int | None = None,
) -> dict[str, Any]:
    if pick is None:
        return data
    for o in data["options"]:
        o["recommended"] = o is pick
    evidence = {}
    if st:
        evidence = {
            "success_pct": round(100 * (st["success_raw"] or 0)),
            "n": st["n"],
            "period_days": PERIOD_DAYS,
            "eta_p50_days": st["eta_p50_days"],
            "price_above_cheapest_minor": (pick["price"]["amount_minor"] - cheapest)
            if cheapest is not None
            else 0,
        }
    data["recommendation"] = {
        "courier_account_id": pick["courier_account_id"],
        "service_code": pick["service_code"],
        "reason": reason,
        "method": method,
        "evidence": evidence,
        "method_version": METHOD_VERSION,
        "alternatives": [
            {
                "courier_account_id": o["courier_account_id"],
                "service_code": o["service_code"],
                "success_pct": round(100 * (s["success_raw"] or 0)),
                "n": s["n"],
            }
            for o, s in known
            if o is not pick
        ],
    }
    return data


def performance(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    from app.domains.fulfillment.models import CourierAccount

    out = []
    for r in db.scalars(
        select(CourierPerformanceMetric)
        .where(CourierPerformanceMetric.merchant_id == merchant_id)
        .order_by(CourierPerformanceMetric.destination)
    ):
        a = db.get(CourierAccount, r.courier_account_id)
        out.append(
            {
                "courier_account_id": r.courier_account_id,
                "courier_name": a.display_name if a else None,
                "origin": r.origin,
                "destination": r.destination,
                "weight_band": r.weight_band,
                "cod": r.cod,
                "n": r.n,
                "delivery_success": round(r.delivered / r.n, 3) if r.n else None,
                "first_attempt_success": round(r.first_attempt / r.n, 3) if r.n else None,
                "failed_rate": round(r.failed_any / r.n, 3) if r.n else None,
                "eta_p50_days": r.eta_p50_days,
                "eta_p90_days": r.eta_p90_days,
                "avg_price_minor": r.avg_price_minor,
                "cod_settlement_days": r.cod_settlement_days,
                "enough_data": r.n >= MIN_SAMPLE,
                "period_days": r.period_days,
                "computed_at": r.computed_at,
            }
        )
    return out
