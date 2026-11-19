"""Commerce Memory (MEM-001…008, spec 04 §Intelligence).

Metrics: a small registry of named, defined numbers per subject and period, recomputed idempotently
(same key → same row). Facts: short, evidence-backed statements Nivaro has learned about the shop
("this kurta runs small", "customers reorder about every 40 days"). Each fact has a version, the
evidence and sample size behind it, and a status the seller controls:

- confirm → `confirmed` (only confirmed facts are used in customer conversations, e.g. fit hints);
- correct → a new version written by the seller; derivations never overwrite the seller's version;
- reject → `rejected_by_merchant`; the same fact isn't derived again until the method changes.

Privacy (MEM-006): no fact or metric is about an individual customer. Customer behaviour appears only
as shop-level aggregates, so deleting/anonymising a customer leaves nothing personal behind here.
"""

from __future__ import annotations

import statistics
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from itertools import pairwise
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.intelligence.models import CommerceMemoryFact, CommerceMemoryMetric

METHOD_VERSION = "mem-1.0"

# MEM-001: the metric registry. Definitions are shown to the seller and to auditors.
METRICS: dict[str, dict[str, str]] = {
    "units_sold": {
        "subject": "product",
        "period": "week",
        "definition": "Units on orders placed that week, excluding cancelled",
    },
    "return_rate": {
        "subject": "product",
        "period": "month",
        "definition": "Units returned ÷ units delivered, orders placed that month",
    },
    "orders": {
        "subject": "shop",
        "period": "day",
        "definition": "Orders placed that day, excluding drafts and cancelled",
    },
    "repeat_share": {
        "subject": "shop",
        "period": "month",
        "definition": "Share of that month's orders from customers who had ordered before",
    },
    "delivery_success": {
        "subject": "district",
        "period": "month",
        "definition": "Parcels delivered ÷ parcels finished, by destination district",
    },
}

# MEM-003: typed values per fact type: key → type. Seller corrections are validated against these.
FACT_TYPES: dict[str, dict[str, Any]] = {
    "fit_runs_small": {"subject": "product", "keys": {"share": float, "returns": int, "sold": int}},
    "fit_runs_large": {"subject": "product", "keys": {"share": float, "returns": int, "sold": int}},
    "repeat_cycle_days": {"subject": "shop", "keys": {"days": int, "customers": int}},
    "peak_order_hours": {"subject": "shop", "keys": {"start_hour": int, "end_hour": int, "share": float}},
    "best_courier_route": {"subject": "district", "keys": {"courier": str, "success": float, "n": int}},
}
# A change in these keys is a new version; other keys are refreshed in place.
IDENTITY_KEYS = {
    "fit_runs_small": (),
    "fit_runs_large": (),
    "repeat_cycle_days": ("days",),
    "peak_order_hours": ("start_hour",),
    "best_courier_route": ("courier",),
}
MIN_REPEAT_INTERVALS = 10
MIN_ORDERS_FOR_HOURS = 30
MIN_ROUTE_N = 20
ROUTE_GAP = 0.10


# ----------------------------------------------------------------------------- facts
def _validate(fact_type: str, value: dict[str, Any]) -> dict[str, Any]:
    spec = FACT_TYPES.get(fact_type)
    if spec is None:
        raise ValidationFailed("Unknown fact type", code="memory_fact_type_unknown")
    out: dict[str, Any] = {}
    for k, typ in spec["keys"].items():
        if k not in value:
            continue
        v = value[k]
        try:
            out[k] = typ(v)
        except (TypeError, ValueError) as e:
            raise ValidationFailed(f"{k} must be a {typ.__name__}", code="memory_fact_value_invalid") from e
    for k in value:
        if k not in spec["keys"] and k not in ("courier_account_id",):
            raise ValidationFailed(f"Unknown field {k}", code="memory_fact_value_invalid")
    if "courier_account_id" in value:
        out["courier_account_id"] = str(value["courier_account_id"])
    return out


def put_fact(
    db: Session,
    merchant_id: uuid.UUID,
    subject_type: str,
    subject_id: str,
    fact_type: str,
    value: dict[str, Any],
    confidence: float,
    evidence: list[dict[str, Any]],
) -> CommerceMemoryFact | None:
    """Derivation entry point: create, refresh or version a fact, respecting the seller's word."""
    value = _validate(fact_type, value)
    cur = db.scalar(
        select(CommerceMemoryFact).where(
            CommerceMemoryFact.subject_type == subject_type,
            CommerceMemoryFact.subject_id == subject_id,
            CommerceMemoryFact.fact_type == fact_type,
            CommerceMemoryFact.status == "active",
        )
    )
    if cur is not None:
        if cur.source == "merchant":
            return cur  # the seller's version wins
        same = all(cur.value.get(k) == value.get(k) for k in IDENTITY_KEYS[fact_type])
        if same and cur.method_version == METHOD_VERSION:
            cur.value, cur.confidence, cur.evidence = value, confidence, evidence
            return cur
        cur.status, cur.valid_to = "superseded", utcnow()
        db.flush()
        return _insert(
            db, merchant_id, subject_type, subject_id, fact_type, value, confidence, evidence, cur.version + 1
        )
    last = db.scalar(
        select(CommerceMemoryFact)
        .where(
            CommerceMemoryFact.subject_type == subject_type,
            CommerceMemoryFact.subject_id == subject_id,
            CommerceMemoryFact.fact_type == fact_type,
        )
        .order_by(CommerceMemoryFact.version.desc())
        .limit(1)
    )
    if last is not None and last.status == "rejected_by_merchant" and last.method_version == METHOD_VERSION:
        return None  # MEM-005: the seller rejected it; only a new method may suggest it again (MEM-008)
    return _insert(
        db,
        merchant_id,
        subject_type,
        subject_id,
        fact_type,
        value,
        confidence,
        evidence,
        (last.version + 1) if last else 1,
    )


def _insert(
    db: Session,
    merchant_id: uuid.UUID,
    subject_type: str,
    subject_id: str,
    fact_type: str,
    value: dict[str, Any],
    confidence: float,
    evidence: list[dict[str, Any]],
    version: int,
    *,
    source: str = "derived",
    confirmed: bool = False,
    user_id: uuid.UUID | None = None,
    note: str | None = None,
) -> CommerceMemoryFact:
    f = CommerceMemoryFact(
        id=uuid7(),
        merchant_id=merchant_id,
        subject_type=subject_type,
        subject_id=subject_id,
        fact_type=fact_type,
        value=value,
        confidence=round(confidence, 2),
        evidence=evidence,
        status="active",
        source=source,
        confirmed=confirmed,
        version=version,
        method_version=METHOD_VERSION,
        changed_by_user_id=user_id,
        note=note,
    )
    db.add(f)
    db.flush()
    return f


def derive_fit(
    db: Session, merchant_id: uuid.UUID, product_id: uuid.UUID, reason: str, n: int, returned: int, sold: int
) -> CommerceMemoryFact | None:
    """MEM-004 rule: >= 3 size returns that are >= 50% of the product's returns (from Return Intelligence)."""
    fact_type = "fit_runs_small" if reason == "size_small" else "fit_runs_large"
    share = n / returned if returned else 0
    return put_fact(
        db,
        merchant_id,
        "product",
        str(product_id),
        fact_type,
        {"share": round(share, 2), "returns": n, "sold": sold},
        confidence=min(0.95, 0.5 + 0.05 * n),
        evidence=[
            {
                "metric": "returns_by_reason",
                "reason": reason,
                "returns": n,
                "of_returns": returned,
                "sold": sold,
                "window_days": 90,
            }
        ],
    )


def _derive_shop(db: Session, merchant_id: uuid.UUID) -> int:
    from app.domains.merchants.models import Merchant
    from app.domains.orders.models import Order

    made = 0
    since = utcnow() - timedelta(days=180)
    rows = db.execute(
        select(Order.customer_id, Order.placed_at)
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= since,
            Order.customer_id.is_not(None),
            Order.status.not_in(("draft", "cancelled")),
        )
        .order_by(Order.customer_id, Order.placed_at)
    ).all()
    by_customer: dict[Any, list[datetime]] = defaultdict(list)
    for cid, at in rows:
        by_customer[cid].append(at)
    gaps = [(b - a).days for ts in by_customer.values() for a, b in pairwise(ts) if (b - a).days >= 1]
    repeaters = sum(1 for ts in by_customer.values() if len(ts) >= 2)
    if len(gaps) >= MIN_REPEAT_INTERVALS:
        made += bool(
            put_fact(
                db,
                merchant_id,
                "shop",
                str(merchant_id),
                "repeat_cycle_days",
                {"days": int(statistics.median(gaps)), "customers": repeaters},
                confidence=min(0.9, 0.4 + 0.02 * len(gaps)),
                evidence=[{"metric": "days_between_orders", "intervals": len(gaps), "window_days": 180}],
            )
        )
    m = db.get(Merchant, merchant_id)
    tz = ZoneInfo(getattr(m, "timezone", None) or "Asia/Kathmandu")
    all_recent = list(
        db.scalars(
            select(Order.placed_at).where(
                Order.merchant_id == merchant_id,
                Order.placed_at >= utcnow() - timedelta(days=60),
                Order.status.not_in(("draft", "cancelled")),
            )
        )
    )
    if len(all_recent) >= MIN_ORDERS_FOR_HOURS:
        hours = Counter(at.astimezone(tz).hour for at in all_recent)
        best = max(range(24), key=lambda h: sum(hours[(h + i) % 24] for i in range(3)))
        share = sum(hours[(best + i) % 24] for i in range(3)) / len(all_recent)
        if share >= 0.25:  # a 3-hour window holding a quarter of orders (uniform would be 12.5%)
            made += bool(
                put_fact(
                    db,
                    merchant_id,
                    "shop",
                    str(merchant_id),
                    "peak_order_hours",
                    {"start_hour": best, "end_hour": (best + 3) % 24, "share": round(share, 2)},
                    confidence=min(0.9, 0.4 + 0.005 * len(all_recent)),
                    evidence=[
                        {
                            "metric": "orders_by_hour",
                            "orders": len(all_recent),
                            "window_days": 60,
                            "timezone": str(tz),
                        }
                    ],
                )
            )
    return made


def _derive_routes(db: Session, merchant_id: uuid.UUID) -> int:
    from app.domains.fulfillment.models import CourierAccount
    from app.domains.intelligence.models import CourierPerformanceMetric

    by_dest: dict[str, dict[uuid.UUID, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for m in db.scalars(select(CourierPerformanceMetric)):
        agg = by_dest[m.destination][m.courier_account_id]
        agg[0] += m.delivered
        agg[1] += m.n
    names = {c.id: (c.display_name or c.provider) for c in db.scalars(select(CourierAccount))}
    made = 0
    for dest, couriers in by_dest.items():
        ranked = sorted(
            ((cid, d / n, n) for cid, (d, n) in couriers.items() if n >= MIN_ROUTE_N), key=lambda x: -x[1]
        )
        if len(ranked) < 2 or ranked[0][1] - ranked[1][1] < ROUTE_GAP:
            continue
        cid, success, n = ranked[0]
        made += bool(
            put_fact(
                db,
                merchant_id,
                "district",
                dest,
                "best_courier_route",
                {
                    "courier": names.get(cid, "courier"),
                    "courier_account_id": str(cid),
                    "success": round(success, 2),
                    "n": n,
                },
                confidence=min(0.9, 0.5 + 0.005 * n),
                evidence=[
                    {
                        "metric": "delivery_success",
                        "courier": names.get(x[0], "courier"),
                        "success": round(x[1], 2),
                        "n": x[2],
                    }
                    for x in ranked[:3]
                ],
            )
        )
    return made


# ----------------------------------------------------------------------------- metrics (MEM-002)
def _put_metric(
    db: Session,
    merchant_id: uuid.UUID,
    subject_type: str,
    subject_id: str,
    metric: str,
    period_start: date,
    value: float | None,
    n: int,
) -> None:
    db.execute(
        pg_insert(CommerceMemoryMetric)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            subject_type=subject_type,
            subject_id=subject_id,
            metric=metric,
            period=METRICS[metric]["period"],
            period_start=period_start,
            value=value,
            n=n,
            method_version=METHOD_VERSION,
            computed_at=utcnow(),
        )
        .on_conflict_do_update(
            index_elements=["merchant_id", "subject_type", "subject_id", "metric", "period", "period_start"],
            set_={"value": value, "n": n, "method_version": METHOD_VERSION, "computed_at": utcnow()},
        )
    )


def compute_metrics(db: Session, merchant_id: uuid.UUID) -> int:
    from app.domains.fulfillment.models import Shipment
    from app.domains.orders.models import Order, OrderLine

    n = 0
    today = utcnow().date()
    # shop.orders per day, last 30 days
    for day, cnt in db.execute(
        select(func.date(Order.placed_at), func.count())
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= utcnow() - timedelta(days=30),
            Order.status.not_in(("draft", "cancelled")),
        )
        .group_by(func.date(Order.placed_at))
    ):
        _put_metric(db, merchant_id, "shop", str(merchant_id), "orders", day, float(cnt), int(cnt))
        n += 1
    # product.units_sold per ISO week, last 12 weeks
    for pid, wk, units in db.execute(
        select(
            OrderLine.product_id,
            func.date_trunc(literal_column("'week'"), Order.placed_at),
            func.sum(OrderLine.quantity - OrderLine.cancelled_quantity),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= utcnow() - timedelta(weeks=12),
            Order.status.not_in(("draft", "cancelled")),
            OrderLine.product_id.is_not(None),
        )
        .group_by(OrderLine.product_id, func.date_trunc(literal_column("'week'"), Order.placed_at))
    ):
        _put_metric(
            db, merchant_id, "product", str(pid), "units_sold", wk.date(), float(units or 0), int(units or 0)
        )
        n += 1
    # product.return_rate and shop.repeat_share for the current and previous 2 months
    for back in range(3):
        start = (today.replace(day=1) - timedelta(days=31 * back)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
        start_dt = datetime(start.year, start.month, 1, tzinfo=ZoneInfo("UTC"))
        end_dt = datetime(end.year, end.month, 1, tzinfo=ZoneInfo("UTC"))
        month_stats = _month_returns(db, merchant_id, start_dt, end_dt)
        for pid, (sold, returned) in month_stats.items():
            _put_metric(
                db,
                merchant_id,
                "product",
                str(pid),
                "return_rate",
                start,
                (returned / sold) if sold else None,
                sold,
            )
            n += 1
        orders = db.execute(
            select(Order.id, Order.customer_id, Order.placed_at).where(
                Order.merchant_id == merchant_id,
                Order.placed_at >= start_dt,
                Order.placed_at < end_dt,
                Order.status.not_in(("draft", "cancelled")),
            )
        ).all()
        if orders:
            repeat = 0
            for _oid, cid, at in orders:
                if cid and db.scalar(
                    select(func.count())
                    .select_from(Order)
                    .where(
                        Order.customer_id == cid,
                        Order.placed_at < at,
                        Order.status.not_in(("draft", "cancelled")),
                    )
                ):
                    repeat += 1
            _put_metric(
                db,
                merchant_id,
                "shop",
                str(merchant_id),
                "repeat_share",
                start,
                repeat / len(orders),
                len(orders),
            )
            n += 1
        for dest, finished, delivered in db.execute(
            select(
                Shipment.destination_district,
                func.count(),
                func.count().filter(Shipment.status == "delivered"),
            )
            .where(
                Shipment.direction == "outbound",
                Shipment.status.in_(("delivered", "returned_to_origin", "lost")),
                Shipment.created_at >= start_dt,
                Shipment.created_at < end_dt,
                Shipment.destination_district.is_not(None),
            )
            .group_by(Shipment.destination_district)
        ):
            _put_metric(
                db,
                merchant_id,
                "district",
                str(dest),
                "delivery_success",
                start,
                delivered / finished if finished else None,
                int(finished),
            )
            n += 1
    return n


def _month_returns(
    db: Session, merchant_id: uuid.UUID, start: datetime, end: datetime
) -> dict[Any, tuple[int, int]]:
    from app.domains.orders.models import Order, OrderLine
    from app.domains.returns.models import ReturnLine, ReturnRequest

    sold = dict(
        db.execute(
            select(OrderLine.product_id, func.sum(OrderLine.quantity - OrderLine.cancelled_quantity))
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                Order.merchant_id == merchant_id,
                Order.placed_at >= start,
                Order.placed_at < end,
                Order.status.in_(("delivered", "completed", "returned")),
                OrderLine.product_id.is_not(None),
            )
            .group_by(OrderLine.product_id)
        ).all()
    )
    ret = dict(
        db.execute(
            select(OrderLine.product_id, func.sum(ReturnLine.quantity))
            .join(ReturnLine, ReturnLine.order_line_id == OrderLine.id)
            .join(ReturnRequest, ReturnRequest.id == ReturnLine.return_id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                Order.merchant_id == merchant_id,
                Order.placed_at >= start,
                Order.placed_at < end,
                ReturnRequest.status.not_in(("rejected", "cancelled")),
            )
            .group_by(OrderLine.product_id)
        ).all()
    )
    return {pid: (int(s or 0), int(ret.get(pid) or 0)) for pid, s in sold.items()}


def compute(db: Session, merchant_id: uuid.UUID) -> dict[str, int]:
    return {
        "metrics": compute_metrics(db, merchant_id),
        "facts": _derive_shop(db, merchant_id) + _derive_routes(db, merchant_id),
    }


def compute_all(db: Session) -> int:
    """Nightly. Also the MEM-008 backfill: facts from an older method are re-derived on the next run."""
    from app.domains.billing.service import entitlements
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        if not entitlements.resolve(db, mid).has("intelligence.product_brain"):
            continue
        with db.begin_nested():
            compute(db, mid)
        n += 1
    return n


# ----------------------------------------------------------------------------- seller actions (MEM-005)
def get(db: Session, ctx: TenantContext, fact_id: uuid.UUID) -> CommerceMemoryFact:
    f = db.get(CommerceMemoryFact, fact_id)
    if f is None or f.merchant_id != ctx.merchant_id:
        raise NotFound(code="memory_fact_not_found")
    return f


def _audit(
    db: Session, ctx: TenantContext, f: CommerceMemoryFact, action: str, extra: dict[str, Any]
) -> None:
    from app.domains.audit import service as audit

    audit.record(
        db,
        action=f"intelligence.memory_fact_{action}",
        resource_type="memory_fact",
        resource_id=f.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"fact_type": f.fact_type, "subject": f"{f.subject_type}:{f.subject_id}", **extra},
    )


def confirm(db: Session, ctx: TenantContext, fact_id: uuid.UUID) -> CommerceMemoryFact:
    f = get(db, ctx, fact_id)
    if f.status != "active":
        raise Conflict("Only current facts can be confirmed", code="memory_fact_not_active")
    if not f.confirmed:
        f.confirmed, f.changed_by_user_id = True, ctx.actor.id
        _audit(db, ctx, f, "confirmed", {"version": f.version})
    return f


def confirm_by_subject(
    db: Session, ctx: TenantContext, subject_type: str, subject_id: str, fact_type: str
) -> CommerceMemoryFact:
    f = db.scalar(
        select(CommerceMemoryFact).where(
            CommerceMemoryFact.subject_type == subject_type,
            CommerceMemoryFact.subject_id == subject_id,
            CommerceMemoryFact.fact_type == fact_type,
            CommerceMemoryFact.status == "active",
        )
    )
    if f is None:
        raise NotFound(code="memory_fact_not_found")
    return confirm(db, ctx, f.id)


def reject(db: Session, ctx: TenantContext, fact_id: uuid.UUID, note: str) -> CommerceMemoryFact:
    f = get(db, ctx, fact_id)
    if f.status != "active":
        raise Conflict("Only current facts can be rejected", code="memory_fact_not_active")
    f.status, f.valid_to, f.changed_by_user_id, f.note, f.confirmed = (
        "rejected_by_merchant",
        utcnow(),
        ctx.actor.id,
        note[:300],
        False,
    )
    _audit(db, ctx, f, "rejected", {"version": f.version, "note": note[:300]})
    return f


def correct(
    db: Session, ctx: TenantContext, fact_id: uuid.UUID, value: dict[str, Any], note: str
) -> CommerceMemoryFact:
    f = get(db, ctx, fact_id)
    if f.status != "active":
        raise Conflict("Only current facts can be corrected", code="memory_fact_not_active")
    clean = _validate(f.fact_type, {**f.value, **value})
    f.status, f.valid_to = "superseded", utcnow()
    db.flush()
    new = _insert(
        db,
        ctx.merchant_id,
        f.subject_type,
        f.subject_id,
        f.fact_type,
        clean,
        1.0,
        [*f.evidence, {"metric": "seller_correction", "previous_version": f.version}],
        f.version + 1,
        source="merchant",
        confirmed=True,
        user_id=ctx.actor.id,
        note=note[:300],
    )
    _audit(
        db,
        ctx,
        new,
        "corrected",
        {"from_version": f.version, "before": f.value, "after": clean, "note": note[:300]},
    )
    return new


def confirmed_fit(db: Session, merchant_id: uuid.UUID, product_id: uuid.UUID) -> str | None:
    """RTI-006: the fit hint the Sales Agent may use: only facts the seller confirmed."""
    ft = db.scalar(
        select(CommerceMemoryFact.fact_type).where(
            CommerceMemoryFact.merchant_id == merchant_id,
            CommerceMemoryFact.subject_type == "product",
            CommerceMemoryFact.subject_id == str(product_id),
            CommerceMemoryFact.fact_type.in_(("fit_runs_small", "fit_runs_large")),
            CommerceMemoryFact.status == "active",
            CommerceMemoryFact.confirmed.is_(True),
        )
    )
    return {"fit_runs_small": "small", "fit_runs_large": "large"}.get(ft or "")


def view(f: CommerceMemoryFact, subject_label: str | None = None) -> dict[str, Any]:
    return {
        "id": str(f.id),
        "subject_type": f.subject_type,
        "subject_id": f.subject_id,
        "subject_label": subject_label,
        "fact_type": f.fact_type,
        "value": f.value,
        "confidence": f.confidence,
        "evidence": f.evidence,
        "status": f.status,
        "source": f.source,
        "confirmed": f.confirmed,
        "version": f.version,
        "method_version": f.method_version,
        "valid_from": f.valid_from.isoformat(),
        "valid_to": f.valid_to.isoformat() if f.valid_to else None,
        "note": f.note,
    }
