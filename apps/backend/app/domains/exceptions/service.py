"""Exception Inbox (UX-007 data source).

The seller should see *only* what needs a human. This module derives open exceptions from the
authoritative state of each domain (no separate copy that can drift): an exception disappears the
moment the underlying problem is fixed (e.g. reconnecting a channel clears its expiry exception).

Each item: stable ``id`` (type + resource), ``type`` (matches the web/mobile Exception Inbox types),
``severity``, ``resource`` link, ``occurred_at``, ``action`` (what fixes it) and safe ``details``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.catalog.models import Product, ProductAttribute
from app.domains.channels.models import ChannelConnection, ChannelListing
from app.domains.content.models import ContentPost
from app.domains.media.models import MediaAsset
from app.domains.studio.models import StudioJob

SEVERITY_ORDER = {"urgent": 0, "high": 1, "normal": 2}


def _item(
    type_: str,
    severity: str,
    resource_type: str,
    resource_id: uuid.UUID,
    occurred_at: datetime | None,
    action: str,
    **details: Any,
) -> dict[str, Any]:
    return {
        "id": f"{type_}:{resource_id}",
        "type": type_,
        "severity": severity,
        "resource": {"type": resource_type, "id": resource_id},
        "occurred_at": occurred_at,
        "action": action,
        "details": details,
    }


def _usage_items(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """BIL-009: a monthly plan allowance that's reached (high) or nearly reached (normal).

    Derived from live usage, so it disappears when the month resets, credits are added or the plan
    changes."""
    from app.domains.billing.service import entitlements

    out = []
    for u in entitlements.usage_summary(db, merchant_id):
        level, limit = u.get("alert_level"), u.get("limit")
        # Monthly allowances only: a gauge at capacity (1 of 1 store) is the plan's shape, not a problem.
        if u.get("kind") != "consumable" or not u.get("included") or not limit or level not in ("85", "100"):
            continue
        out.append(
            {
                "id": f"usage_limit:{u['resource']}",
                "type": "usage_limit",
                "severity": "high" if level == "100" else "normal",
                "resource": {"type": "plan_resource", "id": u["resource"]},
                "occurred_at": None,
                "action": "view_plan",
                "details": {
                    "resource": u["resource"],
                    "used": u.get("used"),
                    "limit": limit,
                    "level": int(str(level)),
                    "period": u.get("period"),
                },
            }
        )
    return out


def _automation_items(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """AUT-009/011: workflow steps waiting for approval; workflows paused by the circuit breaker."""
    from app.domains.automation.models import Workflow, WorkflowRun, WorkflowStepRun

    out: list[dict[str, Any]] = []
    for sr, name in db.execute(
        select(WorkflowStepRun, Workflow.name)
        .join(WorkflowRun, WorkflowRun.id == WorkflowStepRun.run_id)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .where(WorkflowStepRun.merchant_id == merchant_id, WorkflowStepRun.status == "awaiting_approval")
    ).all():
        out.append(
            _item(
                "automation_approval",
                "high",
                "workflow_step",
                sr.id,
                sr.started_at,
                "review_automation",
                name=name,
                step_action=sr.action or "",
            )
        )
    for w in db.scalars(
        select(Workflow).where(
            Workflow.merchant_id == merchant_id,
            Workflow.status == "paused",
            Workflow.paused_reason.like("circuit_breaker:%"),
        )
    ):
        out.append(
            _item(
                "automation_paused",
                "urgent",
                "workflow",
                w.id,
                w.updated_at,
                "open_workflow",
                name=w.name,
                step_action=(w.paused_reason or "").split(":", 1)[-1],
            )
        )
    return out


def _return_items(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """RET/PAY-007: returns to decide, items back to inspect, refunds waiting for approval or failed."""
    from app.domains.orders.models import Order
    from app.domains.returns.models import Refund, ReturnRequest

    out: list[dict[str, Any]] = []
    for r, number in db.execute(
        select(ReturnRequest, Order.number)
        .join(Order, Order.id == ReturnRequest.order_id)
        .where(
            ReturnRequest.merchant_id == merchant_id,
            ReturnRequest.status.in_(("requested", "received", "inspected")),
        )
    ).all():
        if r.status == "inspected" and (r.resolution != "refund" or r.refund_due_minor == 0):
            continue
        typ, sev, action, at = {
            "requested": (
                "return_requested",
                "high" if r.signals or not r.eligible else "normal",
                "review_return",
                r.created_at,
            ),
            "received": ("return_to_inspect", "normal", "inspect_return", r.received_at),
            "inspected": ("refund_due", "high", "issue_refund", r.inspected_at),
        }[r.status]
        out.append(
            _item(
                typ,
                sev,
                "return",
                r.id,
                at,
                action,
                number=number,
                return_number=r.number,
                order_id=str(r.order_id),
                resolution=r.resolution,
                eligible=r.eligible,
                signals=[s["code"] for s in r.signals],
                amount_minor=r.refund_due_minor,
                currency=r.currency,
            )
        )
    for ref, number in db.execute(
        select(Refund, Order.number)
        .join(Order, Order.id == Refund.order_id)
        .where(Refund.merchant_id == merchant_id, Refund.status.in_(("pending_approval", "failed")))
    ).all():
        pending = ref.status == "pending_approval"
        out.append(
            _item(
                "refund_above_threshold" if pending else "refund_failed",
                "high" if pending else "urgent",
                "refund",
                ref.id,
                ref.created_at,
                "approve_refund" if pending else "retry_refund",
                number=number,
                order_id=str(ref.order_id),
                return_id=str(ref.return_id) if ref.return_id else None,
                amount_minor=ref.amount_minor,
                currency=ref.currency,
                error_code=ref.failure_code if not pending else None,
            )
        )
    return out


def _fulfillment_items(db: Session, merchant_id: uuid.UUID) -> list[dict[str, Any]]:
    """FUL-008/010: failed deliveries a person must handle, stuck/lost parcels, returns to receive,
    courier statements that don't match, couriers whose credentials stopped working."""

    from app.core.db import utcnow
    from app.domains.fulfillment.models import (
        LIVE_STATUSES,
        CODSettlement,
        CourierAccount,
        DeliveryAttempt,
        Shipment,
    )
    from app.domains.fulfillment.service import STUCK_AFTER
    from app.domains.orders.models import Order

    out: list[dict[str, Any]] = []
    rows = db.execute(
        select(DeliveryAttempt, Order.number, Order.ship_name, Order.ship_phone)
        .join(Order, Order.id == DeliveryAttempt.order_id)
        .where(
            DeliveryAttempt.merchant_id == merchant_id,
            # awaiting_customer: we asked and are waiting; it becomes 'escalated' if nobody answers.
            DeliveryAttempt.recovery_status.in_(("open", "customer_replied", "escalated")),
        )
    ).all()
    for att, number, name, phone in rows:
        replied = att.recovery_status == "customer_replied"
        out.append(
            _item(
                "delivery_failed",
                "urgent" if att.recovery_status == "escalated" else "high",
                "shipment",
                att.shipment_id,
                att.customer_replied_at if replied else att.failed_at,
                "request_reattempt" if replied else "call_customer",
                number=number,
                name=name,
                phone=phone,
                reason=att.failure_reason,
                recovery_status=att.recovery_status,
                customer_reply=att.customer_reply,
                order_id=str(att.order_id),
            )
        )
    now = utcnow()
    for s, number in db.execute(
        select(Shipment, Order.number)
        .join(Order, Order.id == Shipment.order_id)
        .where(
            Shipment.merchant_id == merchant_id,
            (Shipment.status.in_(LIVE_STATUSES) & (Shipment.last_event_at < now - STUCK_AFTER))
            | (Shipment.status == "lost")
            | ((Shipment.status == "returned_to_origin") & Shipment.return_received_at.is_(None)),
        )
    ).all():
        typ, sev, action = {
            "lost": ("shipment_lost", "urgent", "contact_courier"),
            "returned_to_origin": ("return_to_receive", "normal", "confirm_received_back"),
        }.get(s.status, ("shipment_stuck", "normal", "contact_courier"))
        out.append(
            _item(
                typ,
                sev,
                "shipment",
                s.id,
                s.last_event_at,
                action,
                number=number,
                courier=s.courier_name,
                tracking_number=s.tracking_number,
                status=s.status,
                order_id=str(s.order_id),
                days_since_update=(now - s.last_event_at).days if s.last_event_at else None,
            )
        )
    for st in db.scalars(
        select(CODSettlement).where(
            CODSettlement.merchant_id == merchant_id, CODSettlement.status == "needs_review"
        )
    ):
        out.append(
            _item(
                "cod_settlement_mismatch",
                "high",
                "cod_settlement",
                st.id,
                st.created_at,
                "review_settlement",
                reference=st.reference,
                issues=st.issue_count,
                net_minor=st.net_minor,
                currency=st.currency,
            )
        )
    for a in db.scalars(
        select(CourierAccount).where(
            CourierAccount.merchant_id == merchant_id, CourierAccount.status == "error"
        )
    ):
        out.append(
            _item(
                "courier_error",
                "urgent",
                "courier_account",
                a.id,
                a.updated_at,
                "reconnect_courier",
                name=a.display_name,
                provider=a.provider,
                error_code=a.last_error_code,
            )
        )
    return out


def open_exceptions(
    db: Session, merchant_id: uuid.UUID, limit: int = 200, *, include_usage: bool = True
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _usage_items(db, merchant_id) if include_usage else []

    for c in db.scalars(
        select(ChannelConnection).where(
            ChannelConnection.merchant_id == merchant_id, ChannelConnection.status == "expired"
        )
    ):
        items.append(
            _item(
                "channel_expired",
                "urgent",
                "channel_connection",
                c.id,
                c.updated_at,
                "reconnect",
                provider=c.provider,
                name=c.display_name,
                error_code=c.last_error_code,
            )
        )

    rows = db.execute(
        select(ChannelListing, Product.title, ChannelConnection.status)
        .join(Product, Product.id == ChannelListing.product_id)
        .join(ChannelConnection, ChannelConnection.id == ChannelListing.connection_id)
        .where(ChannelListing.merchant_id == merchant_id, ChannelListing.status == "failed")
    ).all()
    for listing, title, conn_status in rows:
        # The fix depends on the connection's real state, not the last error string.
        action = "reconnect" if conn_status != "connected" else "retry_publish"
        items.append(
            _item(
                "publish_failed",
                "high",
                "product",
                listing.product_id,
                listing.updated_at,
                action,
                product_title=title,
                connection_id=str(listing.connection_id),
                error_code=listing.last_error_code,
            )
        )

    drift_rows = db.execute(
        select(ChannelListing, Product.title, ChannelConnection.display_name, ChannelConnection.provider)
        .join(Product, Product.id == ChannelListing.product_id)
        .join(ChannelConnection, ChannelConnection.id == ChannelListing.connection_id)
        .where(
            ChannelListing.merchant_id == merchant_id,
            ChannelListing.drift_code.is_not(None),
            ChannelListing.desired_state == "published",
        )
    ).all()
    for listing, title, channel_name, provider in drift_rows:
        # CHN-012: the channel's copy differs from Nivaro's; the seller decides which one wins.
        items.append(
            _item(
                "listing_drift",
                "high",
                "product",
                listing.product_id,
                listing.drift_detected_at,
                "resolve_drift",
                product_title=title,
                name=channel_name,
                provider=provider,
                connection_id=str(listing.connection_id),
                drift_code=listing.drift_code,
            )
        )

    from app.domains.customers.models import Customer
    from app.domains.inbox.models import Conversation
    from app.domains.orders.models import Order

    conv_rows = db.execute(
        select(Conversation, Customer.display_name)
        .join(Customer, Customer.id == Conversation.customer_id)
        .where(
            Conversation.merchant_id == merchant_id,
            Conversation.escalated.is_(True),
            Conversation.status != "closed",
        )
    ).all()
    for conv, name in conv_rows:
        items.append(
            _item(
                "customer_escalation",
                "urgent" if conv.escalation_reason in ("complaint", "refund") else "high",
                "conversation",
                conv.id,
                conv.last_inbound_at,
                "reply",
                name=name,
                reason=conv.escalation_reason,
            )
        )
    review_type = {
        "payment_mismatch": ("payment_mismatch", "urgent", "check_payment"),
        "paid_after_cancel": ("payment_mismatch", "urgent", "check_payment"),
        "stock_short": ("inventory_mismatch", "high", "fix_stock"),
        "unmatched_items": ("ambiguous_variant", "high", "review_order"),
        "address_incomplete": ("ambiguous_variant", "normal", "review_order"),
        "cod_risk": ("high_risk_cod", "high", "review_order"),
    }
    for o in db.scalars(
        select(Order).where(
            Order.merchant_id == merchant_id, Order.needs_review.is_not(None), Order.status != "cancelled"
        )
    ):
        typ, sev, action = review_type.get(
            o.needs_review or "", ("ambiguous_variant", "normal", "review_order")
        )
        items.append(
            _item(
                typ,
                sev,
                "order",
                o.id,
                o.updated_at,
                action,
                number=o.number,
                reason=o.needs_review,
                name=o.ship_name,
            )
        )

    items.extend(_fulfillment_items(db, merchant_id))
    items.extend(_return_items(db, merchant_id))
    items.extend(_automation_items(db, merchant_id))

    for p in db.scalars(
        select(ContentPost).where(ContentPost.merchant_id == merchant_id, ContentPost.status == "failed")
    ):
        items.append(
            _item(
                "publish_failed",
                "high",
                "content_post",
                p.id,
                p.updated_at,
                "reconnect" if p.last_error_code == "reconnect_required" else "reschedule",
                kind=p.kind,
                connection_id=str(p.connection_id),
                error_code=p.last_error_code,
            )
        )

    for p in db.scalars(
        select(ContentPost).where(
            ContentPost.merchant_id == merchant_id, ContentPost.status == "pending_approval"
        )
    ):
        items.append(
            _item(
                "low_confidence_ai",
                "normal",
                "content_post",
                p.id,
                p.updated_at,
                "review_post",
                issues=len(p.issues),
                connection_id=str(p.connection_id),
            )
        )

    for j in db.scalars(
        select(StudioJob).where(
            StudioJob.merchant_id == merchant_id,
            StudioJob.status == "ready",
            StudioJob.needs_review.is_(True),
        )
    ):
        items.append(
            _item(
                "low_confidence_ai",
                "normal",
                "studio_job",
                j.id,
                j.finished_at,
                "review_draft",
                confidence=j.confidence,
                issues=len(j.issues),
                needs_seller_input=(j.result or {}).get("needs_seller_input", []),
            )
        )

    for j in db.scalars(
        select(StudioJob).where(StudioJob.merchant_id == merchant_id, StudioJob.status == "failed")
    ):
        items.append(
            _item(
                "provider_failure",
                "normal",
                "studio_job",
                j.id,
                j.finished_at,
                "retry_draft",
                error_code=j.error_code,
            )
        )

    attr_rows = db.execute(
        select(Product.id, Product.title, Product.updated_at)
        .join(ProductAttribute, ProductAttribute.product_id == Product.id)
        .where(
            Product.merchant_id == merchant_id,
            Product.status != "archived",
            ProductAttribute.confirmed.is_(False),
        )
        .distinct()
    ).all()
    for pid, title, updated in attr_rows:
        items.append(
            _item(
                "low_confidence_ai",
                "normal",
                "product",
                pid,
                updated,
                "confirm_attributes",
                product_title=title,
            )
        )

    for a in db.scalars(
        select(MediaAsset).where(
            MediaAsset.merchant_id == merchant_id,
            MediaAsset.status == "rejected",
            MediaAsset.rejection_reason == "malware_detected",
        )
    ):
        items.append(
            _item(
                "provider_failure",
                "high",
                "media",
                a.id,
                a.processed_at,
                "dismiss",
                reason="malware_detected",
                file_name=a.file_name,
            )
        )

    items.sort(
        key=lambda i: (
            SEVERITY_ORDER[i["severity"]],
            -(i["occurred_at"].timestamp() if i["occurred_at"] else 0),
        )
    )
    return items[:limit]
