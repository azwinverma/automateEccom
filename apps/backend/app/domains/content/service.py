"""Content engine: drafts, approval, scheduling, publishing with retry, calendar (CNT-008..011).

State machine::

    draft → (submit) → pending_approval → (approve) → approved → (schedule) → scheduled
    scheduled → publishing → published
    publishing → scheduled (transient error, retried with backoff) | failed (after retries / reconnect needed)
    pending_approval → draft (reject);  approved/scheduled → draft/approved (edit / unschedule)
    draft | pending_approval | approved | scheduled | failed → cancelled

Approval policy (Assisted / Smart / Autopilot, specs/01):
* Seller-written posts never need approval.
* AI-written posts need approval in Assisted mode, or in any mode when the grounding check raised issues.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, InvalidStateTransition, NotFound, PermissionDenied, ValidationFailed
from app.domains.audit import service as audit
from app.domains.channels.models import ChannelConnection
from app.domains.channels.service import _mark_expired, adapter_for
from app.domains.content.models import ContentPost
from app.domains.integrations.base import ChannelCapability, IntegrationError
from app.domains.media.models import MediaAsset
from app.domains.merchants.models import Merchant
from app.domains.platform import outbox
from app.domains.studio import grounding
from app.domains.studio.models import StudioJob

log = structlog.get_logger(__name__)
MAX_ATTEMPTS = 5
MAX_SCHEDULE_AHEAD = timedelta(days=90)

TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"pending_approval", "approved", "cancelled"}),
    "pending_approval": frozenset({"approved", "draft", "cancelled"}),
    "approved": frozenset({"scheduled", "cancelled", "draft"}),
    "scheduled": frozenset({"publishing", "cancelled", "approved"}),
    "publishing": frozenset({"published", "scheduled", "failed"}),
    "failed": frozenset({"scheduled", "cancelled"}),
    "published": frozenset(),
    "cancelled": frozenset(),
}


def _move(p: ContentPost, to: str) -> str:
    if to not in TRANSITIONS[p.status]:
        raise InvalidStateTransition(
            details={"from": p.status, "to": to, "allowed": sorted(TRANSITIONS[p.status])}
        )
    old, p.status = p.status, to
    return old


def _get(db: Session, ctx: TenantContext, post_id: uuid.UUID) -> ContentPost:
    p = db.get(ContentPost, post_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound()
    return p


def _connection(db: Session, ctx: TenantContext, connection_id: uuid.UUID) -> ChannelConnection:
    c = db.get(ChannelConnection, connection_id)
    if c is None or c.merchant_id != ctx.merchant_id or c.status == "disconnected":
        raise NotFound("Channel not found", code="connection_not_found")
    if ChannelCapability.CONTENT_PUBLISH.value not in c.capabilities:
        raise Conflict(
            f"{c.display_name} doesn't support posting content",
            code="capability_not_supported",
            details={"capability": "content_publish"},
        )
    return c


def _check_assets(db: Session, ctx: TenantContext, asset_ids: list[uuid.UUID]) -> None:
    if not asset_ids:
        return
    ready = set(
        db.scalars(
            select(MediaAsset.id).where(
                MediaAsset.merchant_id == ctx.merchant_id,
                MediaAsset.id.in_(asset_ids),
                MediaAsset.status == "ready",
            )
        )
    )
    bad = [str(a) for a in asset_ids if a not in ready]
    if bad:
        raise Conflict(
            "Some photos are missing or still processing", code="media_not_ready", details={"asset_ids": bad}
        )


def _audit(db: Session, ctx: TenantContext, p: ContentPost, action: str, **meta: Any) -> None:
    audit.record(
        db,
        action=f"content.{action}",
        resource_type="content_post",
        resource_id=p.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata=meta or None,
    )


def needs_approval(db: Session, p: ContentPost) -> bool:
    if p.source == "seller":
        return False
    if p.issues:
        return True
    m = db.get(Merchant, p.merchant_id)
    return m is None or m.automation_mode == "assisted"


# ----------------------------------------------------------------------------- create / edit
def create_post(
    db: Session,
    ctx: TenantContext,
    *,
    connection_id: uuid.UUID,
    caption: str,
    hashtags: list[str],
    asset_ids: list[uuid.UUID],
    kind: str = "post",
    product_id: uuid.UUID | None = None,
    campaign: str | None = None,
    source: str = "seller",
    studio_job_id: uuid.UUID | None = None,
    issues: list[dict[str, Any]] | None = None,
    video_job_id: uuid.UUID | None = None,
    hook_type: str | None = None,
    human_presence: bool | None = None,
    background: str | None = None,
) -> ContentPost:
    c = _connection(db, ctx, connection_id)
    limit = adapter_for(c).max_caption_chars
    caption = caption.strip()
    if not caption:
        raise ValidationFailed("Write a caption", code="caption_required")
    if len(caption) > limit:
        raise ValidationFailed(
            f"Caption is longer than {limit} characters", code="caption_too_long", details={"max": limit}
        )
    video = _ready_video(db, ctx, video_job_id) if video_job_id else None
    if video is not None and video.output_asset_id and video.output_asset_id not in asset_ids:
        asset_ids = [video.output_asset_id, *asset_ids]
    if kind in ("story", "reel") and not asset_ids:
        raise ValidationFailed("Stories and reels need a photo or video", code="media_required")
    _check_assets(db, ctx, asset_ids)
    tags = list(dict.fromkeys(t.lstrip("#").strip().lower() for t in hashtags if t.strip()))[:30]
    p = ContentPost(
        merchant_id=ctx.merchant_id,
        connection_id=c.id,
        product_id=product_id,
        kind=kind,
        caption=caption,
        hashtags=tags,
        asset_ids=list(asset_ids),
        campaign=campaign,
        source=source,
        studio_job_id=studio_job_id,
        issues=issues or [],
        created_by_user_id=ctx.actor.id,
        video_job_id=video.id if video else None,
    )
    _apply_declared(p, hook_type, human_presence, background)
    apply_creative_attributes(db, p, video)
    db.add(p)
    db.flush()
    _audit(db, ctx, p, "post_created", source=source, connection=str(c.id))
    return p


def update_post(
    db: Session, ctx: TenantContext, post_id: uuid.UUID, version: int | None, fields: dict[str, Any]
) -> ContentPost:
    p = _get(db, ctx, post_id)
    if version is not None and version != p.version:
        raise Conflict(
            "This post was changed by someone else",
            code="version_conflict",
            details={"current_version": p.version},
        )
    if p.status not in ("draft", "pending_approval", "approved"):
        raise Conflict("Only unscheduled posts can be edited. Unschedule it first.", code="post_locked")
    edited = False
    if "caption" in fields and fields["caption"] is not None:
        p.caption, edited = fields["caption"].strip(), True
    if "hashtags" in fields and fields["hashtags"] is not None:
        p.hashtags, edited = (
            [t.lstrip("#").strip().lower() for t in fields["hashtags"] if t.strip()][:30],
            True,
        )
    declared = {k: fields[k] for k in ("hook_type", "human_presence", "background") if k in fields}
    if declared:
        _apply_declared(
            p,
            declared.get("hook_type"),
            declared.get("human_presence"),
            declared.get("background"),
            clear_missing=False,
        )
    if edited or declared:
        apply_creative_attributes(db, p)
    if edited and p.source != "seller":
        # Seller edited AI copy: re-check claims; seller-confirmed text clears previous AI issues.
        p.issues = []
    if edited and p.status != "draft":
        p.status = "draft"  # edits after approval require re-approval
        p.approved_at = p.approved_by_user_id = None
    try:
        db.flush()
    except StaleDataError as e:
        raise Conflict("This post was changed by someone else", code="version_conflict") from e
    _audit(db, ctx, p, "post_updated")
    return p


def from_studio(
    db: Session, ctx: TenantContext, job_id: uuid.UUID, connection_ids: list[uuid.UUID], kind: str = "post"
) -> list[ContentPost]:
    """Create per-channel drafts from a Studio draft, picking the caption style each channel suits."""
    job = db.get(StudioJob, job_id)
    if job is None or job.merchant_id != ctx.merchant_id or not job.result:
        raise NotFound("Draft not found or not ready", code="draft_not_ready")
    captions: dict[str, str] = job.result.get("captions") or {}
    hashtags: list[str] = job.result.get("hashtags") or []
    out = []
    for cid in dict.fromkeys(connection_ids):
        c = _connection(db, ctx, cid)
        style = adapter_for(c).caption_style
        caption = captions.get(style) or captions.get("instagram") or job.result.get("description_ne") or ""
        issues = [
            {"field": f"caption.{style}", "kind": f"unsupported_claim:{v.kind}", "excerpt": v.excerpt}
            for v in grounding.check({"caption": caption}, job.seller_notes or "")
        ]
        out.append(
            create_post(
                db,
                ctx,
                connection_id=c.id,
                caption=caption,
                hashtags=hashtags,
                asset_ids=list(job.asset_ids),
                kind=kind,
                product_id=job.product_id,
                source="ai_studio",
                studio_job_id=job.id,
                issues=issues,
            )
        )
    return out


# ----------------------------------------------------------------------------- workflow
def submit(db: Session, ctx: TenantContext, post_id: uuid.UUID) -> ContentPost:
    p = _get(db, ctx, post_id)
    if needs_approval(db, p):
        _move(p, "pending_approval")
        _audit(db, ctx, p, "submitted_for_approval", issues=len(p.issues))
    else:
        _move(p, "approved")
        p.approved_at = utcnow()
        _audit(db, ctx, p, "auto_approved", policy="seller_or_smart_mode")
    return p


def approve(db: Session, ctx: TenantContext, post_id: uuid.UUID) -> ContentPost:
    if not ctx.has("content.approve"):
        raise PermissionDenied(details={"permission": "content.approve"})
    p = _get(db, ctx, post_id)
    if p.status != "pending_approval":  # approval is a review step, not a way to skip the queue
        raise InvalidStateTransition(details={"from": p.status, "to": "approved", "allowed": ["submit"]})
    _move(p, "approved")
    p.approved_by_user_id, p.approved_at = ctx.actor.id, utcnow()
    _audit(db, ctx, p, "approved", acknowledged_issues=len(p.issues))
    return p


def reject(db: Session, ctx: TenantContext, post_id: uuid.UUID, note: str | None) -> ContentPost:
    if not ctx.has("content.approve"):
        raise PermissionDenied(details={"permission": "content.approve"})
    p = _get(db, ctx, post_id)
    if p.status != "pending_approval":
        raise InvalidStateTransition(details={"from": p.status, "to": "draft"})
    _move(p, "draft")
    p.rejection_note = (note or "")[:500] or None
    _audit(db, ctx, p, "rejected")
    return p


def schedule(db: Session, ctx: TenantContext, post_id: uuid.UUID, when: datetime | None) -> ContentPost:
    p = _get(db, ctx, post_id)
    now = utcnow()
    when = when or now
    if when < now - timedelta(minutes=1):
        raise ValidationFailed("Pick a time in the future", code="schedule_in_past")
    if when > now + MAX_SCHEDULE_AHEAD:
        raise ValidationFailed("Posts can be scheduled up to 90 days ahead", code="schedule_too_far")
    c = db.get(ChannelConnection, p.connection_id)
    if c is None or c.status != "connected":
        raise Conflict("Reconnect this channel before scheduling", code="reconnect_required")
    _move(p, "scheduled")
    p.scheduled_at = p.next_attempt_at = when
    apply_creative_attributes(db, p)  # posting window = merchant-local hour of the slot
    p.attempts, p.last_error_code = 0, None
    _audit(db, ctx, p, "scheduled", at=when.isoformat())
    return p


def unschedule(db: Session, ctx: TenantContext, post_id: uuid.UUID) -> ContentPost:
    p = _get(db, ctx, post_id)
    _move(p, "approved")
    p.next_attempt_at = None
    _audit(db, ctx, p, "unscheduled")
    return p


def cancel(db: Session, ctx: TenantContext, post_id: uuid.UUID) -> ContentPost:
    p = _get(db, ctx, post_id)
    _move(p, "cancelled")
    p.next_attempt_at = None
    _audit(db, ctx, p, "cancelled")
    return p


# ----------------------------------------------------------------------------- scheduler (worker)
def publish_due(db: Session, limit: int = 50) -> dict[str, int]:
    stats = {"published": 0, "retrying": 0, "failed": 0}
    rows = db.scalars(
        select(ContentPost)
        .where(ContentPost.status == "scheduled", ContentPost.next_attempt_at <= utcnow())
        .order_by(ContentPost.next_attempt_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
        .execution_options(skip_tenant_filter=True)
    ).all()
    for p in rows:
        outcome = _publish_one(db, p)
        stats[outcome] += 1
    return stats


def _publish_one(db: Session, p: ContentPost) -> str:
    bind_tenant(db, p.merchant_id)
    actor = Actor.system("content-scheduler")
    c = db.get(ChannelConnection, p.connection_id)
    p.status = "publishing"
    p.attempts += 1
    if c is None or c.status != "connected":
        return _fail(db, p, "reconnect_required", actor)
    try:
        ext = adapter_for(c).publish_content(
            {
                "kind": p.kind,
                "caption": p.caption,
                "hashtags": p.hashtags,
                "asset_ids": [str(a) for a in p.asset_ids],
            },
            idempotency_key=f"content:{p.id}",
        )
    except IntegrationError as e:
        if e.auth:
            _mark_expired(db, c, e.code)
            return _fail(db, p, "reconnect_required", actor)
        if e.retryable and p.attempts < MAX_ATTEMPTS:
            p.status, p.last_error_code = "scheduled", e.code
            p.next_attempt_at = utcnow() + timedelta(seconds=min(60 * 2**p.attempts, 3600))
            return "retrying"
        return _fail(db, p, e.code, actor)
    p.status, p.external_id, p.published_at, p.last_error_code = "published", ext, utcnow(), None
    if p.scheduled_at is None:
        apply_creative_attributes(db, p)  # published immediately: window = actual publish hour
    p.next_attempt_at = None
    audit.record(
        db,
        action="content.published",
        resource_type="content_post",
        resource_id=p.id,
        actor=actor,
        merchant_id=p.merchant_id,
        metadata={"external_id": ext, "attempts": p.attempts},
    )
    return "published"


def _fail(db: Session, p: ContentPost, code: str, actor: Actor) -> str:
    p.status, p.last_error_code, p.next_attempt_at = "failed", code, None
    audit.record(
        db,
        action="content.publish_failed",
        resource_type="content_post",
        resource_id=p.id,
        actor=actor,
        merchant_id=p.merchant_id,
        metadata={"error_code": code, "attempts": p.attempts},
    )
    outbox.publish(
        db,
        event_type="content.publish_failed",
        aggregate_type="content_post",
        aggregate_id=p.id,
        merchant_id=p.merchant_id,
        payload={"post_id": str(p.id), "error_code": code},
    )
    return "failed"


def post_view(p: ContentPost) -> dict[str, Any]:
    return {
        "id": p.id,
        "connection_id": p.connection_id,
        "product_id": p.product_id,
        "kind": p.kind,
        "caption": p.caption,
        "hashtags": p.hashtags,
        "asset_ids": p.asset_ids,
        "campaign": p.campaign,
        "source": p.source,
        "status": p.status,
        "issues": p.issues,
        "scheduled_at": p.scheduled_at,
        "published_at": p.published_at,
        "external_id": p.external_id,
        "attempts": p.attempts,
        "last_error_code": p.last_error_code,
        "approved_at": p.approved_at,
        "rejection_note": p.rejection_note,
        "version": p.version,
        "created_at": p.created_at,
        "creative": creative_view(p),
    }


# ----------------------------------------------------------------------------- creative attributes (CNT-012)
def _ready_video(db: Session, ctx: TenantContext, video_job_id: uuid.UUID) -> Any:
    from app.domains.media.models import VideoJob

    v = db.get(VideoJob, video_job_id)
    if v is None or v.merchant_id != ctx.merchant_id:
        raise NotFound("Video not found", code="video_not_found")
    if v.status != "ready":
        raise Conflict("This video isn't ready yet", code="video_not_ready", details={"status": v.status})
    return v


def _apply_declared(
    p: ContentPost,
    hook_type: str | None,
    human_presence: bool | None,
    background: str | None,
    clear_missing: bool = True,
) -> None:
    from app.domains.content import creative

    if hook_type is not None:
        if hook_type not in creative.HOOK_TYPES:
            raise ValidationFailed(
                "Unknown hook type", code="invalid_hook_type", details={"allowed": creative.HOOK_TYPES}
            )
        p.hook_type = hook_type
    if background is not None:
        if background not in creative.BACKGROUNDS:
            raise ValidationFailed(
                "Unknown background", code="invalid_background", details={"allowed": creative.BACKGROUNDS}
            )
        p.background = background
    if human_presence is not None or clear_missing:
        p.human_presence = human_presence


def apply_creative_attributes(db: Session, p: ContentPost, video: Any = None) -> None:
    """Recompute derived creative attributes. Seller-declared values are kept; video-derived values
    fill hook/background only when the seller hasn't declared them."""
    from app.domains.content import creative

    p.language_mix = creative.language_mix(p.caption)
    p.caption_bucket = creative.caption_bucket(p.caption)
    p.cta_type = creative.cta_type(p.caption)
    tz = db.get(Merchant, p.merchant_id).timezone  # type: ignore[union-attr]
    p.posting_hour = creative.posting_window(p.scheduled_at or p.published_at, tz)
    if video is None and p.video_job_id is not None:
        from app.domains.media.models import VideoJob

        video = db.get(VideoJob, p.video_job_id)
    if video is not None:
        attrs = creative.from_video_job(video.duration_s, video.show_price, video.template)
        p.duration_s, p.price_shown, p.price_timing_s = (
            attrs.duration_s,
            attrs.price_shown,
            attrs.price_timing_s,
        )
        p.template_id = attrs.template_id
        if p.hook_type in (None, "unknown"):  # None = not yet flushed (column default not applied)
            p.hook_type = attrs.hook_type
        if p.background is None:
            p.background = attrs.background
    if p.hook_type is None:
        p.hook_type = "unknown"
    p.creative_attrs_version = creative.ATTRS_VERSION


def creative_view(p: ContentPost) -> dict[str, Any]:
    return {
        "version": p.creative_attrs_version,
        "format": p.kind,
        "duration_s": p.duration_s,
        "hook_type": p.hook_type,
        "price_shown": p.price_shown,
        "price_timing_s": p.price_timing_s,
        "language_mix": p.language_mix,
        "caption_bucket": p.caption_bucket,
        "cta_type": p.cta_type,
        "human_presence": p.human_presence,
        "background": p.background,
        "template_id": p.template_id,
        "posting_hour": p.posting_hour,
        "video_job_id": p.video_job_id,
    }
