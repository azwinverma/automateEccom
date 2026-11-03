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
