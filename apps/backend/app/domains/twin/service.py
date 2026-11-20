"""Digital Store Twin (TWIN-001…006; spec 03 §Digital Store Twin: synchronisation model).

- Registry (TWIN-001): each section has an owner domain, the events that change it, a TTL and the
  maximum staleness each consumer accepts (UI, automation).
- Event-driven updates (TWIN-002): outbox handlers recompute the affected sections. `source_version` is
  the event's creation time in µs; an older event never overwrites a newer section (monotonic).
- Reconciliation (TWIN-003): every 6 h each merchant's sections are recomputed; reads recompute a section
  older than its TTL (all sections are cheap aggregate queries) and flag it stale if that fails.
- Snapshots (TWIN-004): one compact copy per merchant per day for trends and simulation baselines.
- Freshness (TWIN-006): event→update lag is recorded per section and as a Prometheus histogram; the
  freshness report shows age, last lag and whether the p95 target (60 s) is met.

Material changes emit `twin.updated` (thresholded by each section's key numbers), never every recompute.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from prometheus_client import Histogram
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import bind_tenant, utcnow
from app.core.ids import uuid7
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler, publish
from app.domains.twin.models import StoreTwinSection, StoreTwinSnapshot

log = structlog.get_logger(__name__)

TWIN_LAG = Histogram(
    "twin_update_lag_seconds",
    "Event created → Twin section updated",
    ["section"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300, 900),
)
LAG_TARGET_S = 60  # spec 03: p95 < 60 s
RECONCILE_EVERY = timedelta(hours=6)


def _us(d: datetime) -> int:
    return int(d.timestamp() * 1_000_000)


# ----------------------------------------------------------------------------- section computations
def _catalog(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.catalog.models import Product, Variant

    by = dict(
        db.execute(
            select(Product.status, func.count()).where(Product.merchant_id == mid).group_by(Product.status)
        ).all()
    )
    no_cost = (
        db.scalar(
            select(func.count())
            .select_from(Variant)
            .join(Product, Product.id == Variant.product_id)
            .where(
                Variant.merchant_id == mid,
                Variant.status == "active",
                Product.status == "active",
                Variant.cost_minor.is_(None),
            )
        )
        or 0
    )
    return {
        "active": by.get("active", 0),
        "draft": by.get("draft", 0),
        "archived": by.get("archived", 0),
        "variants_without_cost": no_cost,
    }


def _inventory(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.catalog.models import Variant
    from app.domains.inventory.models import InventoryLevel

    row = db.execute(
        select(
            func.count(func.distinct(InventoryLevel.variant_id)),
            func.coalesce(func.sum(InventoryLevel.on_hand), 0),
            func.coalesce(func.sum(InventoryLevel.reserved), 0),
            func.coalesce(func.sum(InventoryLevel.damaged), 0),
        ).where(InventoryLevel.merchant_id == mid)
    ).one()
    per_variant = db.execute(
        select(
            InventoryLevel.variant_id,
            func.sum(InventoryLevel.on_hand - InventoryLevel.reserved),
            func.min(InventoryLevel.low_stock_threshold),
            func.sum(InventoryLevel.on_hand),
        )
        .where(InventoryLevel.merchant_id == mid)
        .group_by(InventoryLevel.variant_id)
    ).all()
    out = sum(1 for _, a, _t, _o in per_variant if (a or 0) <= 0)
    low = sum(1 for _, a, t, _o in per_variant if t is not None and 0 < (a or 0) <= t)
    costs = dict(db.execute(select(Variant.id, Variant.cost_minor).where(Variant.merchant_id == mid)).all())
    value = 0
    missing = 0
    for vid, _a, _t, on_hand in per_variant:
        c = costs.get(vid)
        if c is None:
            missing += 1 if (on_hand or 0) > 0 else 0
        else:
            value += c * int(on_hand or 0)
    incoming = 0
    try:
        from app.domains.procurement.models import PurchaseOrder, PurchaseOrderLine

        incoming = int(
            db.scalar(
                select(
                    func.coalesce(
                        func.sum(PurchaseOrderLine.quantity - PurchaseOrderLine.received_quantity), 0
                    )
                )
                .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.po_id)
                .where(
                    PurchaseOrder.merchant_id == mid,
                    PurchaseOrder.status.in_(("approved", "sent", "partially_received")),
                )
            )
            or 0
        )
    except Exception:  # pragma: no cover - procurement always installed; defensive for partial deploys
        incoming = 0
    return {
        "tracked_variants": int(row[0] or 0),
        "on_hand": int(row[1] or 0),
        "reserved": int(row[2] or 0),
        "damaged": int(row[3] or 0),
        "out_of_stock": out,
        "low_stock": low,
        "stock_value_minor": value,
        "stock_value_missing_cost": missing,
        "incoming": incoming,
    }


def _orders(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.orders.models import Order

    by = dict(
        db.execute(
            select(Order.status, func.count())
            .where(
                Order.merchant_id == mid,
                Order.status.not_in(
                    ("draft", "delivered", "completed", "cancelled", "returned")
                ),  # delivered = done for the seller
            )
            .group_by(Order.status)
        ).all()
    )
    now = utcnow()
    week = db.execute(
        select(func.count(), func.coalesce(func.sum(Order.total_minor), 0)).where(
            Order.merchant_id == mid,
            Order.placed_at >= now - timedelta(days=7),
            Order.status.not_in(("draft", "cancelled")),
        )
    ).one()
    today = (
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.merchant_id == mid,
                Order.placed_at >= now - timedelta(hours=24),
                Order.status.not_in(("draft", "cancelled")),
            )
        )
        or 0
    )
    review = (
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.merchant_id == mid,
                Order.needs_review.is_not(None),
                Order.status.not_in(("cancelled", "completed")),
            )
        )
        or 0
    )
    return {
        "open_by_status": {k: int(v) for k, v in by.items()},
        "open": int(sum(by.values())),
        "needs_review": int(review),
        "orders_24h": int(today),
        "orders_7d": int(week[0] or 0),
        "revenue_7d_minor": int(week[1] or 0),
    }


def _cod(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.payments.models import CODRecord

    rows = dict(
        db.execute(
            select(CODRecord.status, func.coalesce(func.sum(CODRecord.amount_minor), 0))
            .where(
                CODRecord.merchant_id == mid,
                CODRecord.status.in_(
                    (
                        "requested",
                        "approved",
                        "handed_to_courier",
                        "delivered",
                        "cash_collected",
                        "settlement_pending",
                    )
                ),
            )
            .group_by(CODRecord.status)
        ).all()
    )
    with_courier = sum(int(rows.get(s, 0)) for s in ("delivered", "cash_collected", "settlement_pending"))
    in_transit = sum(int(rows.get(s, 0)) for s in ("handed_to_courier",))
    pending = sum(int(rows.get(s, 0)) for s in ("requested", "approved"))
    return {
        "cash_with_courier_minor": with_courier,
        "cod_in_transit_minor": in_transit,
        "cod_not_shipped_minor": pending,
    }


def _shipments(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.fulfillment.models import LIVE_STATUSES, Shipment

    by = dict(
        db.execute(
            select(Shipment.status, func.count())
            .where(Shipment.merchant_id == mid, Shipment.status.in_(LIVE_STATUSES))
            .group_by(Shipment.status)
        ).all()
    )
    return {
        "live": int(sum(by.values())),
        "by_status": {k: int(v) for k, v in by.items()},
        "failed_attempts": int(by.get("delivery_failed", 0)),
    }


def _returns(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.returns.models import OPEN_RETURN_STATUSES, Refund, ReturnRequest

    by = dict(
        db.execute(
            select(ReturnRequest.status, func.count())
            .where(ReturnRequest.merchant_id == mid, ReturnRequest.status.in_(OPEN_RETURN_STATUSES))
            .group_by(ReturnRequest.status)
        ).all()
    )
    pend = db.execute(
        select(func.count(), func.coalesce(func.sum(Refund.amount_minor), 0)).where(
            Refund.merchant_id == mid, Refund.status == "pending_approval"
        )
    ).one()
    return {
        "open": int(sum(by.values())),
        "by_status": {k: int(v) for k, v in by.items()},
        "refunds_pending": int(pend[0] or 0),
        "refunds_pending_minor": int(pend[1] or 0),
    }


def _suppliers(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.procurement.models import OPEN_PO_STATUSES, PurchaseOrder

    pos = list(
        db.scalars(
            select(PurchaseOrder).where(
                PurchaseOrder.merchant_id == mid, PurchaseOrder.status.in_(OPEN_PO_STATUSES)
            )
        )
    )
    now = utcnow()
    return {
        "open_pos": len(pos),
        "by_status": {
            s: sum(1 for p in pos if p.status == s)
            for s in OPEN_PO_STATUSES
            if any(p.status == s for p in pos)
        },
        "open_value_minor": sum(p.total_minor for p in pos if p.status != "draft"),
        "awaiting_approval": sum(1 for p in pos if p.status == "pending_approval"),
        "overdue": sum(
            1
            for p in pos
            if p.expected_at
            and p.expected_at < now
            and p.status in ("approved", "sent", "partially_received")
        ),
    }


def _automation(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.automation.models import DecisionRecord, Workflow, WorkflowRun
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, mid)
    active = (
        db.scalar(
            select(func.count())
            .select_from(Workflow)
            .where(Workflow.merchant_id == mid, Workflow.status == "active")
        )
        or 0
    )
    waiting = (
        db.scalar(
            select(func.count())
            .select_from(DecisionRecord)
            .where(
                DecisionRecord.merchant_id == mid,
                DecisionRecord.decision == "REQUIRE_APPROVAL",
                DecisionRecord.outcome.is_(None),
            )
        )
        or 0
    )
    failed = (
        db.scalar(
            select(func.count())
            .select_from(WorkflowRun)
            .where(
                WorkflowRun.merchant_id == mid,
                WorkflowRun.status == "failed",
                WorkflowRun.updated_at >= utcnow() - timedelta(hours=24),
            )
        )
        or 0
    )
    return {
        "mode": m.automation_mode if m else "assisted",
        "active_workflows": int(active),
        "waiting_for_approval": int(waiting),
        "failed_runs_24h": int(failed),
    }


def _exceptions(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from collections import Counter

    from app.domains.exceptions.service import open_exceptions

    items = open_exceptions(db, mid, include_usage=True)
    return {
        "total": len(items),
        "by_severity": dict(Counter(i["severity"] for i in items)),
        "by_type": dict(Counter(i["type"] for i in items)),
    }


def _content(db: Session, mid: uuid.UUID) -> dict[str, Any]:
    from app.domains.channels.models import ChannelConnection
    from app.domains.content.models import ContentPost

    now = utcnow()
    scheduled = (
        db.scalar(
            select(func.count())
            .select_from(ContentPost)
            .where(
                ContentPost.merchant_id == mid,
                ContentPost.status == "scheduled",
                ContentPost.scheduled_at <= now + timedelta(days=7),
            )
        )
        or 0
    )
    failed = (
        db.scalar(
            select(func.count())
            .select_from(ContentPost)
            .where(ContentPost.merchant_id == mid, ContentPost.status == "failed")
        )
        or 0
    )
    conns = dict(
        db.execute(
            select(ChannelConnection.status, func.count())
            .where(ChannelConnection.merchant_id == mid)
            .group_by(ChannelConnection.status)
        ).all()
    )
    return {
        "scheduled_7d": int(scheduled),
        "failed_posts": int(failed),
        "channels_connected": int(conns.get("connected", 0)),
        "channels_need_attention": int(sum(v for k, v in conns.items() if k != "connected")),
    }


@dataclass(frozen=True)
class SectionDef:
    owner: str
    compute: Callable[[Session, uuid.UUID], dict[str, Any]]
    events: tuple[str, ...]
    ttl_s: int
    max_staleness_s: dict[str, int]  # consumer → seconds
    material: tuple[str, ...]  # keys whose change emits twin.updated


SECTIONS: dict[str, SectionDef] = {
    "catalog": SectionDef(
        "catalog",
        _catalog,
        (
            "catalog.product_created",
            "catalog.product_updated",
            "catalog.product_status_changed",
            "catalog.variant_updated",
        ),
        3600,
        {"ui": 3600, "automation": 3600},
        ("active", "variants_without_cost"),
    ),
    "inventory": SectionDef(
        "inventory",
        _inventory,
        ("inventory.level_changed", "orders.created", "orders.status_changed"),
        600,
        {"ui": 900, "automation": 300},
        ("out_of_stock", "low_stock", "incoming"),
    ),
    "orders": SectionDef(
        "orders",
        _orders,
        ("orders.created", "orders.status_changed"),
        300,
        {"ui": 600, "automation": 120},
        ("open", "needs_review"),
    ),
    "cod": SectionDef(
        "payments",
        _cod,
        ("orders.status_changed", "fulfillment.shipment_status_changed"),
        900,
        {"ui": 1800, "automation": 600},
        ("cash_with_courier_minor",),
    ),
    "shipments": SectionDef(
        "fulfillment",
        _shipments,
        ("fulfillment.shipment_status_changed", "orders.status_changed"),
        600,
        {"ui": 900, "automation": 300},
        ("live", "failed_attempts"),
    ),
    "returns": SectionDef(
        "returns",
        _returns,
        ("returns.status_changed",),
        900,
        {"ui": 1800, "automation": 600},
        ("open", "refunds_pending"),
    ),
    "suppliers": SectionDef(
        "procurement",
        _suppliers,
        (),
        1800,
        {"ui": 3600, "automation": 1800},
        ("open_pos", "awaiting_approval", "overdue"),
    ),
    "automation": SectionDef(
        "automation",
        _automation,
        (),
        600,
        {"ui": 900, "automation": 300},
        ("waiting_for_approval", "failed_runs_24h"),
    ),
    "exceptions": SectionDef(
        "exceptions",
        _exceptions,
        (
            "orders.status_changed",
            "returns.status_changed",
            "fulfillment.shipment_status_changed",
            "content.publish_failed",
        ),
        600,
        {"ui": 900, "automation": 600},
        ("total",),
    ),
    "content": SectionDef(
        "content",
        _content,
        ("content.publish_failed", "channels.connected", "channels.connection_expired"),
        1800,
        {"ui": 3600, "automation": 1800},
        ("failed_posts", "channels_need_attention"),
    ),
}


# ----------------------------------------------------------------------------- refresh
def refresh(
    db: Session,
    merchant_id: uuid.UUID,
    section: str,
    *,
    trigger: str,
    source_version: int | None = None,
    event_at: datetime | None = None,
) -> StoreTwinSection | None:
    d = SECTIONS[section]
    now = utcnow()
    version = source_version if source_version is not None else _us(now)
    cur = db.scalar(
        select(StoreTwinSection).where(
            StoreTwinSection.merchant_id == merchant_id, StoreTwinSection.section == section
        )
    )
    if cur is not None and cur.source_version > version:
        return cur  # monotonic: an older event never overwrites newer state
    state = d.compute(db, merchant_id)
    lag_ms = round((now - event_at).total_seconds() * 1000) if event_at else None
    if lag_ms is not None:
        TWIN_LAG.labels(section).observe(lag_ms / 1000)
    material = cur is None or any(cur.state.get(k) != state.get(k) for k in d.material)
    vals = {
        "state": state,
        "source_version": max(version, cur.source_version if cur else 0),
        "as_of": now,
        "computed_at": now,
        "trigger": trigger[:40],
        "lag_ms": lag_ms,
    }
    db.execute(
        pg_insert(StoreTwinSection)
        .values(id=uuid7(), merchant_id=merchant_id, section=section, **vals)
        .on_conflict_do_update(index_elements=["merchant_id", "section"], set_=vals)
    )
    db.flush()
    if material and cur is not None:
        publish(
            db,
            event_type="twin.updated",
            aggregate_type="store_twin",
            aggregate_id=str(merchant_id),
            payload={
                "section": section,
                "source_version": str(vals["source_version"]),
                "changes": {k: state.get(k) for k in d.material if cur.state.get(k) != state.get(k)},
            },
            merchant_id=merchant_id,
        )
    return db.scalar(
        select(StoreTwinSection)
        .where(StoreTwinSection.merchant_id == merchant_id, StoreTwinSection.section == section)
        .execution_options(populate_existing=True)  # the upsert ran in SQL; don't return the cached row
    )


def reconcile(db: Session, merchant_id: uuid.UUID) -> int:
    n = 0
    for name in SECTIONS:
        try:
            with db.begin_nested():
                refresh(db, merchant_id, name, trigger="reconcile")
            n += 1
        except Exception:
            log.exception("twin_reconcile_failed", section=name, merchant_id=str(merchant_id))
    return n


def reconcile_all(db: Session) -> int:
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        n += reconcile(db, mid)
    return n


def _age_s(s: StoreTwinSection) -> float:
    return (utcnow() - s.as_of).total_seconds()


def read(db: Session, merchant_id: uuid.UUID, names: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """On-read freshness check: anything older than its TTL is recomputed; failures come back stale."""
    out: dict[str, dict[str, Any]] = {}
    rows = {
        s.section: s
        for s in db.scalars(select(StoreTwinSection).where(StoreTwinSection.merchant_id == merchant_id))
    }
    for name in names or list(SECTIONS):
        d = SECTIONS[name]
        s = rows.get(name)
        if s is None or _age_s(s) > d.ttl_s:
            try:
                with db.begin_nested():
                    s = refresh(db, merchant_id, name, trigger="read")
            except Exception:
                log.exception("twin_read_refresh_failed", section=name)
        if s is None:
            continue
        age = _age_s(s)
        out[name] = {
            "section": name,
            "owner": d.owner,
            "state": s.state,
            "as_of": s.as_of.isoformat(),
            "computed_at": s.computed_at.isoformat(),
            "source_version": s.source_version,
            "age_s": round(age),
            "stale": age > d.ttl_s,
            "max_staleness_s": d.max_staleness_s,
        }
    return out


def is_fresh_for(
    db: Session, merchant_id: uuid.UUID, section: str, consumer: str = "automation"
) -> tuple[bool, float | None]:
    """Decision Policy staleness gate (spec 06): is the section recent enough for this consumer?"""
    s = db.scalar(
        select(StoreTwinSection).where(
            StoreTwinSection.merchant_id == merchant_id, StoreTwinSection.section == section
        )
    )
    if s is None:
        return False, None
    age = _age_s(s)
    return age <= SECTIONS[section].max_staleness_s.get(consumer, SECTIONS[section].ttl_s), age


def snapshot(db: Session, merchant_id: uuid.UUID) -> StoreTwinSnapshot:
    data = {k: v["state"] for k, v in read(db, merchant_id).items()}
    today = utcnow().date()
    db.execute(
        pg_insert(StoreTwinSnapshot)
        .values(id=uuid7(), merchant_id=merchant_id, snapshot_on=today, sections=data, created_at=utcnow())
        .on_conflict_do_update(
            index_elements=["merchant_id", "snapshot_on"], set_={"sections": data, "created_at": utcnow()}
        )
    )
    db.flush()
    snap = db.scalar(
        select(StoreTwinSnapshot).where(
            StoreTwinSnapshot.merchant_id == merchant_id, StoreTwinSnapshot.snapshot_on == today
        )
    )
    assert snap is not None
    return snap


def snapshot_all(db: Session) -> int:
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        with db.begin_nested():
            snapshot(db, mid)
        n += 1
    return n


def freshness(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    """TWIN-006: age and last event lag per section against the 60 s p95 target."""
    rows = list(db.scalars(select(StoreTwinSection).where(StoreTwinSection.merchant_id == merchant_id)))
    lags = sorted(s.lag_ms for s in rows if s.lag_ms is not None)
    p95 = lags[min(len(lags) - 1, int(0.95 * len(lags)))] if lags else None
    return {
        "target_p95_s": LAG_TARGET_S,
        "p95_lag_s": round(p95 / 1000, 1) if p95 is not None else None,
        "meets_target": None if p95 is None else p95 / 1000 <= LAG_TARGET_S,
        "sections": [
            {
                "section": s.section,
                "age_s": round(_age_s(s)),
                "ttl_s": SECTIONS[s.section].ttl_s if s.section in SECTIONS else None,
                "last_lag_ms": s.lag_ms,
                "trigger": s.trigger,
            }
            for s in sorted(rows, key=lambda r: r.section)
        ],
        "note": "Lag is per section from its last event-driven update; reconciliation runs every 6 h.",
    }


# ----------------------------------------------------------------------------- event-driven updates
def _on_event(db: Session, ev: OutboxEvent) -> None:
    if ev.merchant_id is None:
        return
    bind_tenant(db, ev.merchant_id)
    for name, d in SECTIONS.items():
        if ev.event_type in d.events:
            with db.begin_nested():
                refresh(
                    db,
                    ev.merchant_id,
                    name,
                    trigger=ev.event_type,
                    source_version=_us(ev.created_at),
                    event_at=ev.created_at,
                )


for _evt in sorted({e for d in SECTIONS.values() for e in d.events}):
    handler(_evt, name="twin.update")(_on_event)
