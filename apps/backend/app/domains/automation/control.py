"""Autopilot Control Center (UX-016): "Your store is running." with real numbers, what automation did,
and what needs the seller. Everything is computed from Commerce Core and the action log."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.domains.automation import engine, policy
from app.domains.automation.models import AutomationActionLog, DecisionRecord


def overview(
    db: Session,
    merchant_id: uuid.UUID,
    days: int = 7,
    *,
    include_revenue: bool = True,
    include_usage: bool = True,
) -> dict[str, Any]:
    from app.domains.exceptions.service import open_exceptions
    from app.domains.fulfillment.models import Shipment
    from app.domains.inbox.models import Message
    from app.domains.merchants.models import Merchant
    from app.domains.orders.models import Order
    from app.domains.returns.models import ReturnRequest

    since = utcnow() - timedelta(days=days)
    m = db.get(Merchant, merchant_id)
    orders_n, revenue = db.execute(
        select(func.count(), func.coalesce(func.sum(Order.total_minor), 0)).where(
            Order.placed_at >= since, Order.status.not_in(("cancelled", "draft"))
        )
    ).one()
    ai_msgs = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.author_type == "ai", Message.status == "sent", Message.sent_at >= since)
    )
    all_out = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.direction == "out", Message.status == "sent", Message.sent_at >= since)
    )
    delivered = db.scalar(
        select(func.count())
        .select_from(Shipment)
        .where(Shipment.direction == "outbound", Shipment.delivered_at >= since)
    )
    in_transit = db.scalar(
        select(func.count())
        .select_from(Shipment)
        .where(
            Shipment.direction == "outbound",
            Shipment.status.in_(("picked_up", "in_transit", "out_for_delivery", "reattempt_requested")),
        )
    )
    returns_n = db.scalar(
        select(func.count()).select_from(ReturnRequest).where(ReturnRequest.created_at >= since)
    )
    by = dict(
        db.execute(
            select(AutomationActionLog.performed_by, func.count())
            .where(AutomationActionLog.occurred_at >= since, AutomationActionLog.outcome == "success")
            .group_by(AutomationActionLog.performed_by)
        ).all()
    )
    done_auto = int(by.get("automation", 0)) + int(by.get("ai", 0))
    done_total = done_auto + int(by.get("user", 0))
    approvals = engine.pending_approvals(db)
    exceptions = open_exceptions(db, merchant_id, include_usage=include_usage)
    urgent = sum(1 for e in exceptions if e["severity"] == "urgent")
    feed = list(
        db.scalars(
            select(DecisionRecord)
            .where(DecisionRecord.decision == "AUTO_EXECUTE", DecisionRecord.created_at >= since)
            .order_by(DecisionRecord.created_at.desc())
            .limit(15)
        )
    )
    return {
        "period_days": days,
        "mode": m.automation_mode if m else "assisted",
        "state": "attention" if urgent else ("waiting" if approvals or exceptions else "running"),
        "currency": m.currency if m else "NPR",
        "metrics": {
            "orders": int(orders_n),
            "revenue_minor": int(revenue) if include_revenue else None,
            "ai_messages": int(ai_msgs or 0),
            "messages_sent": int(all_out or 0),
            "delivered": int(delivered or 0),
            "in_transit": int(in_transit or 0),
            "returns": int(returns_n or 0),
        },
        "automation": {
            "done_automatically": done_auto,
            "done_by_team": int(by.get("user", 0)),
            "share_automatic": round(done_auto / done_total, 2) if done_total else None,
        },
        "needs_attention": {
            "approvals": len(approvals),
            "exceptions": len(exceptions),
            "urgent": urgent,
        },
        "feed": [policy.decision_view(d) for d in feed],
    }
