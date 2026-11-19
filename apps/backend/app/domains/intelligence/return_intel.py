"""Return Intelligence (RTI-001…005, spec 12 §Return Intelligence).

Finds products whose returns are out of line with the shop's own baseline, says what customers give
as the reason, points at likely causes, and measures whether a change helped.

Detection (per product, last 90 days, orders that reached the customer):
- needs >= MIN_SOLD units sold and >= MIN_RETURNED units returned;
- the product's return rate is at or above the seller's limit (profit settings) OR significantly above
  the shop's baseline (one-sided exact binomial test, p < 0.05, baseline needs >= 30 units shop-wide);
- if one reason accounts for >= 50% of returns (>= 3 units) the pattern is that reason
  ("reason:size_small"), which is more useful than "high return rate".
An open insight that no longer meets the rule is marked resolved.
"""

from __future__ import annotations

import math
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound
from app.domains.intelligence.models import ReturnInsight

METHOD_VERSION = "rti-1.0"
WINDOW_DAYS = 90
MIN_SOLD = 10
MIN_RETURNED = 3
MIN_BASELINE_UNITS = 30
REASON_SHARE = 0.5
VARIANT_SHARE = 0.6
POST_MIN_SOLD = 10
POST_MIN_DAYS = 30
SOLD_STATUSES = ("delivered", "completed", "returned")


@dataclass
class ProductReturns:
    sold: int = 0
    returned: int = 0
    reasons: Counter[str] = field(default_factory=Counter)
    variants: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"sold": 0, "returned": 0})
    )
    variant_titles: dict[str, str] = field(default_factory=dict)


def stats(
    db: Session,
    merchant_id: uuid.UUID,
    days: int = WINDOW_DAYS,
    *,
    since: Any = None,
    product_id: uuid.UUID | None = None,
) -> dict[uuid.UUID, ProductReturns]:
    """RTI-001: units sold and returned per product (and variant), with reasons."""
    from app.domains.orders.models import Order, OrderLine
    from app.domains.returns.models import ReturnLine, ReturnRequest

    start = since or (utcnow() - timedelta(days=days))
    out: dict[uuid.UUID, ProductReturns] = defaultdict(ProductReturns)
    # "returned" orders count as sold only when the customer sent them back after delivery.
    has_return = (
        select(ReturnRequest.id)
        .where(ReturnRequest.order_id == Order.id, ReturnRequest.status.not_in(("rejected", "cancelled")))
        .exists()
    )
    q = (
        select(
            OrderLine.product_id,
            OrderLine.variant_id,
            OrderLine.variant_title,
            func.sum(OrderLine.quantity - OrderLine.cancelled_quantity),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= start,
            OrderLine.product_id.is_not(None),
            (Order.status.in_(("delivered", "completed"))) | ((Order.status == "returned") & has_return),
        )
        .group_by(OrderLine.product_id, OrderLine.variant_id, OrderLine.variant_title)
    )
    if product_id:
        q = q.where(OrderLine.product_id == product_id)
    for pid, vid, vtitle, units in db.execute(q):
        if pid is None:
            continue
        pr = out[pid]
        pr.sold += int(units or 0)
        if vid:
            pr.variants[str(vid)]["sold"] += int(units or 0)
            pr.variant_titles[str(vid)] = vtitle or "Default"
    rq = (
        select(OrderLine.product_id, OrderLine.variant_id, ReturnLine.reason, func.sum(ReturnLine.quantity))
        .join(ReturnLine, ReturnLine.order_line_id == OrderLine.id)
        .join(ReturnRequest, ReturnRequest.id == ReturnLine.return_id)
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            Order.merchant_id == merchant_id,
            Order.placed_at >= start,
            OrderLine.product_id.is_not(None),
            ReturnRequest.status.not_in(("rejected", "cancelled")),
        )
        .group_by(OrderLine.product_id, OrderLine.variant_id, ReturnLine.reason)
    )
    if product_id:
        rq = rq.where(OrderLine.product_id == product_id)
    for pid, vid, reason, units in db.execute(rq):
        if pid is None:
            continue
        pr = out[pid]
        pr.returned += int(units or 0)
        pr.reasons[reason] += int(units or 0)
        if vid:
            pr.variants[str(vid)]["returned"] += int(units or 0)
    return out


def binomial_p(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p): exact, n is small (units of one product)."""
    if n <= 0 or k <= 0:
        return 1.0
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    return min(1.0, sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def _causes(db: Session, pid: uuid.UUID, pr: ProductReturns, top_reason: str | None) -> list[dict[str, Any]]:
    """RTI-003: likely causes the seller can check. Content versions aren't tracked until Phase 7."""
    from app.domains.catalog.models import Supplier, Variant, VariantSupplier

    causes: list[dict[str, Any]] = []
    if pr.returned:
        for vid, v in pr.variants.items():
            share_ret = v["returned"] / pr.returned
            share_sold = v["sold"] / pr.sold if pr.sold else 0
            if v["returned"] >= MIN_RETURNED and share_ret >= VARIANT_SHARE and share_sold < share_ret - 0.2:
                causes.append(
                    {
                        "type": "variant",
                        "variant_id": vid,
                        "variant": pr.variant_titles.get(vid),
                        "returned_share": round(share_ret, 2),
                        "sold_share": round(share_sold, 2),
                    }
                )
    if top_reason in ("quality_defect", "not_as_described", "wrong_item"):
        sup = db.execute(
            select(Supplier.name)
            .join(VariantSupplier, VariantSupplier.supplier_id == Supplier.id)
            .join(Variant, Variant.id == VariantSupplier.variant_id)
            .where(Variant.product_id == pid, VariantSupplier.is_preferred.is_(True))
            .limit(1)
        ).scalar_one_or_none()
        if sup:
            causes.append({"type": "supplier", "supplier": sup})
    causes.append({"type": "content_version", "status": "not_tracked"})
    return causes


def detect(db: Session, merchant_id: uuid.UUID) -> dict[str, int]:
    """RTI-002: raise/update/resolve insights for one merchant."""
    from app.domains.intelligence import memory, profit
    from app.domains.platform.outbox import publish

    s = profit.settings_row(db, merchant_id)
    limit = s.max_return_rate_pct / 100
    by = stats(db, merchant_id)
    total_sold = sum(p.sold for p in by.values())
    total_ret = sum(p.returned for p in by.values())
    baseline = total_ret / total_sold if total_sold >= MIN_BASELINE_UNITS else None
    seen: set[tuple[uuid.UUID, str]] = set()
    raised = updated = 0
    new: list[ReturnInsight] = []
    for pid, pr in by.items():
        if pr.sold < MIN_SOLD or pr.returned < MIN_RETURNED:
            continue
        rate = pr.returned / pr.sold
        p_val = binomial_p(pr.returned, pr.sold, baseline) if baseline is not None else None
        if not (rate >= limit or (p_val is not None and p_val < 0.05)):
            continue
        top, top_n = pr.reasons.most_common(1)[0] if pr.reasons else (None, 0)
        pattern = (
            f"reason:{top}"
            if top and top_n >= MIN_RETURNED and top_n / pr.returned >= REASON_SHARE
            else "high_return_rate"
        )
        seen.add((pid, pattern))
        causes = _causes(db, pid, pr, top)
        variant_cause = next((c for c in causes if c["type"] == "variant"), None)
        ins = db.scalar(
            select(ReturnInsight).where(
                ReturnInsight.product_id == pid,
                ReturnInsight.pattern == pattern,
                ReturnInsight.status.in_(("open", "acted")),
            )
        )
        if ins is None:
            dismissed = db.scalar(
                select(ReturnInsight.id).where(
                    ReturnInsight.product_id == pid,
                    ReturnInsight.pattern == pattern,
                    ReturnInsight.status == "dismissed",
                    ReturnInsight.updated_at >= utcnow() - timedelta(days=WINDOW_DAYS),
                )
            )
            if dismissed:
                continue  # the seller said this isn't a problem; don't raise it again this quarter
            ins = ReturnInsight(
                merchant_id=merchant_id,
                product_id=pid,
                pattern=pattern,
                status="open",
                window_days=WINDOW_DAYS,
                method_version=METHOD_VERSION,
                sold=pr.sold,
                returned=pr.returned,
                rate=rate,
            )
            db.add(ins)
            new.append(ins)
            raised += 1
        else:
            updated += 1
        ins.variant_id = uuid.UUID(variant_cause["variant_id"]) if variant_cause else None
        if ins.status == "open":  # once acted on, keep the numbers from before the change
            ins.sold, ins.returned, ins.rate = pr.sold, pr.returned, round(rate, 4)
            ins.baseline_rate = round(baseline, 4) if baseline is not None else None
            ins.p_value = round(p_val, 5) if p_val is not None else None
            ins.reasons = dict(pr.reasons)
            ins.causes = causes
        if top in ("size_small", "size_large") and pattern.startswith("reason:"):
            memory.derive_fit(db, merchant_id, pid, top, top_n, pr.returned, pr.sold)
    db.flush()
    for ins in new:
        publish(
            db,
            event_type="returns.pattern_detected",
            aggregate_type="return_insight",
            aggregate_id=ins.id,
            payload={"insight_id": str(ins.id), "product_id": str(ins.product_id)},
            merchant_id=merchant_id,
        )
    resolved = 0
    for ins in db.scalars(select(ReturnInsight).where(ReturnInsight.status == "open")):
        if (ins.product_id, ins.pattern) not in seen:
            ins.status = "resolved"
            resolved += 1
    return {"raised": raised, "updated": updated, "resolved": resolved}


def measure(db: Session, merchant_id: uuid.UUID) -> int:
    """RTI-005: return rate on sales placed after the seller acted, once there's enough of it."""
    n = 0
    for ins in db.scalars(
        select(ReturnInsight).where(ReturnInsight.status == "acted", ReturnInsight.post_change_rate.is_(None))
    ):
        if ins.acted_at is None or ins.acted_at > utcnow() - timedelta(days=POST_MIN_DAYS):
            continue
        pr = stats(db, merchant_id, since=ins.acted_at, product_id=ins.product_id).get(ins.product_id)
        if pr is None or pr.sold < POST_MIN_SOLD:
            continue
        ins.post_change_sold = pr.sold
        ins.post_change_rate = round(pr.returned / pr.sold, 4)
        n += 1
    return n


def detect_all(db: Session) -> int:
    from app.domains.billing.service import entitlements
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        if not entitlements.resolve(db, mid).has("intelligence.returns"):
            continue
        with db.begin_nested():
            detect(db, mid)
            measure(db, mid)
        n += 1
    return n


def get(db: Session, ctx: TenantContext, insight_id: uuid.UUID) -> ReturnInsight:
    ins = db.get(ReturnInsight, insight_id)
    if ins is None or ins.merchant_id != ctx.merchant_id:
        raise NotFound(code="return_insight_not_found")
    return ins


def dismiss(db: Session, ctx: TenantContext, insight_id: uuid.UUID, reason: str) -> ReturnInsight:
    from app.domains.audit import service as audit

    ins = get(db, ctx, insight_id)
    if ins.status not in ("open", "acted"):
        raise Conflict("This insight is closed", code="return_insight_closed")
    ins.status = "dismissed"
    audit.record(
        db,
        action="intelligence.return_insight_dismissed",
        resource_type="return_insight",
        resource_id=ins.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"pattern": ins.pattern, "reason": reason[:300]},
    )
    return ins


def mark_acted(db: Session, merchant_id: uuid.UUID, insight_id: uuid.UUID) -> None:
    ins = db.get(ReturnInsight, insight_id)
    if ins is not None and ins.merchant_id == merchant_id and ins.status == "open":
        ins.status, ins.acted_at = "acted", utcnow()


def view(ins: ReturnInsight, title: str | None = None, variant: str | None = None) -> dict[str, Any]:
    reason = ins.pattern.split(":", 1)[1] if ins.pattern.startswith("reason:") else None
    return {
        "id": str(ins.id),
        "product_id": str(ins.product_id),
        "title": title,
        "variant_id": str(ins.variant_id) if ins.variant_id else None,
        "variant": variant,
        "pattern": ins.pattern,
        "reason": reason,
        "reason_share": round(ins.reasons.get(reason, 0) / ins.returned, 2)
        if reason and ins.returned
        else None,
        "status": ins.status,
        "window_days": ins.window_days,
        "sold": ins.sold,
        "returned": ins.returned,
        "rate": ins.rate,
        "baseline_rate": ins.baseline_rate,
        "p_value": ins.p_value,
        "reasons": ins.reasons,
        "causes": ins.causes,
        "acted_at": ins.acted_at.isoformat() if ins.acted_at else None,
        "post_change_rate": ins.post_change_rate,
        "post_change_sold": ins.post_change_sold,
        "method_version": ins.method_version,
        "created_at": ins.created_at.isoformat() if ins.created_at else None,
    }
