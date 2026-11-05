"""Triggers, facts and conditions (AUT-002/003).

Facts are read from Commerce Core at the moment a step runs (never copied from the trigger), so a
condition or action always sees the current price/stock/payment state. A condition on a missing fact
is false: missing data never passes (spec 06 safety rules).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed

INSIDE_VALLEY = {"kathmandu", "lalitpur", "bhaktapur"}


@dataclass(frozen=True)
class Trigger:
    code: str
    source_event: str  # outbox event type
    subject: str  # order | shipment | return | variant | channel | none
    filter_field: str | None = None  # payload/facts field the trigger filter applies to
    filter_values: tuple[str, ...] = ()


ORDER_STATUSES = (
    "cod_pending",
    "payment_pending",
    "ready_to_ship",
    "shipped",
    "delivered",
    "completed",
    "cancelled",
    "delivery_failed",
    "returned",
)
SHIPMENT_STATUSES = (
    "picked_up",
    "out_for_delivery",
    "delivered",
    "delivery_failed",
    "returned_to_origin",
    "lost",
)
RETURN_STATUSES = ("requested", "approved", "received", "inspected", "refunded", "exchanged")

TRIGGERS: dict[str, Trigger] = {
    t.code: t
    for t in (
        Trigger("order.created", "orders.created", "order"),
        Trigger("order.status_changed", "orders.status_changed", "order", "order.status", ORDER_STATUSES),
        Trigger(
            "shipment.status_changed",
            "fulfillment.shipment_status_changed",
            "shipment",
            "shipment.status",
            SHIPMENT_STATUSES,
        ),
        Trigger("inventory.low_stock", "inventory.level_changed", "variant"),
        Trigger(
            "return.status_changed", "returns.status_changed", "return", "return.status", RETURN_STATUSES
        ),
        Trigger("channel.expired", "channels.connection_expired", "channel"),
    )
}

# Fields a condition may use, per subject (and the order behind shipments/returns).
ORDER_FIELDS = {
    "order.status": "str",
    "order.payment_method": "str",
    "order.payment_status": "str",
    "order.total_minor": "int",
    "order.source": "str",
    "order.district": "str",
    "order.inside_valley": "bool",
    "order.address_complete": "bool",
    "order.needs_review": "bool",
    "order.has_chat": "bool",
    "customer.orders_count": "int",
    "customer.first_order": "bool",
}
FIELDS: dict[str, dict[str, str]] = {
    "order": ORDER_FIELDS,
    "shipment": {
        **ORDER_FIELDS,
        "shipment.status": "str",
        "shipment.attempt_count": "int",
        "shipment.manual": "bool",
        "shipment.cod_amount_minor": "int",
    },
    "return": {
        **ORDER_FIELDS,
        "return.status": "str",
        "return.resolution": "str",
        "return.refund_due_minor": "int",
        "return.eligible": "bool",
        "return.has_signals": "bool",
    },
    "variant": {"variant.available": "int", "variant.sku": "str", "product.title": "str"},
    "channel": {"channel.provider": "str"},
}
OPS = ("eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "is_true", "is_false")


def subject_of(trigger: Trigger, payload: dict[str, Any]) -> tuple[str | None, str | None]:
    key = {
        "order": "order_id",
        "shipment": "shipment_id",
        "return": "return_id",
        "variant": "variant_id",
        "channel": "connection_id",
    }.get(trigger.subject)
    return (trigger.subject, str(payload.get(key))) if key and payload.get(key) else (None, None)


# ----------------------------------------------------------------------------- facts
def _order_facts(db: Session, order_id: uuid.UUID) -> dict[str, Any]:
    from app.domains.fulfillment.service import _conversation_for
    from app.domains.orders.models import Order

    o = db.get(Order, order_id)
    if o is None:
        return {}
    n = (
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(Order.customer_id == o.customer_id, Order.status != "cancelled")
        )
        if o.customer_id
        else 0
    ) or 0
    return {
        "_order": o,
        "order.id": str(o.id),
        "order.number": o.number,
        "order.status": o.status,
        "order.payment_method": o.payment_method,
        "order.payment_status": o.payment_status,
        "order.total_minor": o.total_minor,
        "order.currency": o.currency,
        "order.source": o.source,
        "order.district": o.ship_district,
        "order.inside_valley": o.ship_district in INSIDE_VALLEY if o.ship_district else None,
        "order.address_complete": o.address_completeness >= 0.99,
        "order.needs_review": o.needs_review is not None,
        "order.has_chat": _conversation_for(db, o) is not None,
        "order.customer_name": o.ship_name,
        "customer.orders_count": int(n),
        "customer.first_order": int(n) <= 1,
    }


def facts_for(db: Session, subject_type: str | None, subject_id: str | None) -> dict[str, Any]:
    if not subject_type or not subject_id:
        return {}
    sid = uuid.UUID(subject_id)
    if subject_type == "order":
        return _order_facts(db, sid)
    if subject_type == "shipment":
        from app.domains.fulfillment.models import Shipment

        s = db.get(Shipment, sid)
        if s is None:
            return {}
        return {
            **_order_facts(db, s.order_id),
            "_shipment": s,
            "shipment.id": str(s.id),
            "shipment.status": s.status,
            "shipment.attempt_count": s.attempt_count,
            "shipment.manual": s.provider == "manual",
            "shipment.cod_amount_minor": s.cod_amount_minor,
            "shipment.tracking_number": s.tracking_number,
            "shipment.direction": s.direction,
        }
    if subject_type == "return":
        from app.domains.returns.models import ReturnRequest

        r = db.get(ReturnRequest, sid)
        if r is None:
            return {}
        return {
            **_order_facts(db, r.order_id),
            "_return": r,
            "return.id": str(r.id),
            "return.number": r.number,
            "return.status": r.status,
            "return.resolution": r.resolution,
            "return.refund_due_minor": r.refund_due_minor,
            "return.eligible": r.eligible,
            "return.has_signals": bool(r.signals),
        }
    if subject_type == "variant":
        from app.domains.catalog.models import Product, Variant
        from app.domains.inventory import service as inventory

        v = db.get(Variant, sid)
        if v is None:
            return {}
        p = db.get(Product, v.product_id)
        av = inventory.availability(db, v.merchant_id, [v.id])[v.id]
        return {
            "variant.id": str(v.id),
            "variant.available": av.available if av.tracked else None,
            "variant.sku": v.sku,
            "product.title": p.title if p else None,
            "product.id": str(v.product_id),
        }
    if subject_type == "channel":
        from app.domains.channels.models import ChannelConnection

        c = db.get(ChannelConnection, sid)
        return {"channel.provider": c.provider, "channel.name": c.display_name} if c else {}
    return {}


# ----------------------------------------------------------------------------- conditions
def evaluate(cond: dict[str, Any] | None, facts: dict[str, Any]) -> bool:
    if not cond:
        return True
    if "all" in cond:
        return all(evaluate(c, facts) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, facts) for c in cond["any"])
    field, op, value = cond.get("field"), cond.get("op"), cond.get("value")
    if field not in facts or facts[field] is None:
        return False  # missing data never passes
    have = facts[field]
    try:
        return {
            "eq": lambda: have == value,
            "ne": lambda: have != value,
            "gt": lambda: have > value,
            "gte": lambda: have >= value,
            "lt": lambda: have < value,
            "lte": lambda: have <= value,
            "in": lambda: have in (value or []),
            "not_in": lambda: have not in (value or []),
            "is_true": lambda: have is True,
            "is_false": lambda: have is False,
        }[str(op)]()
    except TypeError:
        return False


def validate_condition(cond: dict[str, Any], subject: str, path: str) -> None:
    if "all" in cond or "any" in cond:
        items = cond.get("all") or cond.get("any") or []
        if not isinstance(items, list) or not items or len(items) > 10:
            raise ValidationFailed(
                code="workflow_invalid", details={"path": path, "reason": "condition_group"}
            )
        for i, c in enumerate(items):
            validate_condition(c, subject, f"{path}.{i}")
        return
    allowed = FIELDS.get(subject, {})
    field, op = cond.get("field"), cond.get("op")
    if field not in allowed:
        raise ValidationFailed(
            code="workflow_invalid", details={"path": path, "reason": "unknown_field", "field": field}
        )
    if op not in OPS:
        raise ValidationFailed(
            code="workflow_invalid", details={"path": path, "reason": "unknown_op", "op": op}
        )
    kind = allowed[field]
    value = cond.get("value")
    if op in ("is_true", "is_false"):
        if kind != "bool":
            raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "op_type"})
    elif op in ("in", "not_in"):
        if not isinstance(value, list) or not value:
            raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "value_type"})
    elif (kind == "int" and (not isinstance(value, int) or isinstance(value, bool))) or (
        kind == "str" and not isinstance(value, str)
    ):
        raise ValidationFailed(code="workflow_invalid", details={"path": path, "reason": "value_type"})
