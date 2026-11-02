"""AI Product Studio (photos → listing draft → seller review → product).

Flow:
  create_job (HTTP, fast)  → outbox ``studio.job_queued`` → Celery ``run_studio_job`` (worker)
  run_job: gateway PRODUCT_EXTRACTION with the photos' ``medium`` derivatives → schema-validated draft
           → length limits + commercial-fact grounding check → ready (needs_review when unsure)
  apply_job (HTTP): seller-confirmed fields + seller-entered prices → catalog product (draft) with
           AI attributes as suggestions (unconfirmed below the policy confidence threshold), photos attached.

The model never sets prices or stock: ``apply`` requires the seller's variants/prices.
"""

from __future__ import annotations

import base64
import uuid
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import session_scope, utcnow
from app.core.errors import AppError, Conflict, NotFound, ValidationFailed
from app.domains.ai.gateway import AIUnavailable, gateway
from app.domains.ai.policy import load_policy
from app.domains.ai.prompts import get_prompt
from app.domains.ai.types import AIRequest, ImageInput, Message
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements
from app.domains.catalog import service as catalog
from app.domains.catalog.models import Category
from app.domains.integrations.storage import get_storage
from app.domains.media.models import MediaAsset, MediaDerivative
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler
from app.domains.studio import grounding
from app.domains.studio import prompts as _prompts  # noqa: F401  (registers prompts)
from app.domains.studio.models import StudioJob
from app.domains.studio.schema import LIMITS

log = structlog.get_logger(__name__)
MAX_IMAGES = 6
TASK = "PRODUCT_EXTRACTION"
PROMPT = "studio.product_extraction"
MAX_ATTEMPTS = 3


def _get(db: Session, ctx: TenantContext, job_id: uuid.UUID) -> StudioJob:
    j = db.get(StudioJob, job_id)
    if j is None or j.merchant_id != ctx.merchant_id:
        raise NotFound()
    return j


def create_job(
    db: Session, ctx: TenantContext, asset_ids: list[uuid.UUID], locale: str, seller_notes: str | None
) -> StudioJob:
    entitlements.require_feature(db, ctx.merchant_id, "ai.product_studio")  # fail fast, before queueing
    if not 1 <= len(asset_ids) <= MAX_IMAGES:
        raise ValidationFailed(f"Choose 1 to {MAX_IMAGES} photos", code="invalid_photo_count")
    assets = db.scalars(
        select(MediaAsset).where(MediaAsset.merchant_id == ctx.merchant_id, MediaAsset.id.in_(asset_ids))
    ).all()
    found = {a.id: a for a in assets}
    missing = [str(i) for i in asset_ids if i not in found]
    if missing:
        raise NotFound("Some photos were not found", code="media_not_found", details={"asset_ids": missing})
    not_ready = [str(i) for i in asset_ids if found[i].status != "ready"]
    if not_ready:
        raise Conflict(
            "Some photos are still processing or were rejected",
            code="media_not_ready",
            details={"asset_ids": not_ready},
        )
    job = StudioJob(
        merchant_id=ctx.merchant_id,
        asset_ids=list(dict.fromkeys(asset_ids)),
        locale=locale,
        seller_notes=(seller_notes or "").strip()[:2000] or None,
        created_by_user_id=ctx.actor.id,
    )
    db.add(job)
    db.flush()
    audit.record(
        db,
        action="studio.job_created",
        resource_type="studio_job",
        resource_id=job.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"photos": len(job.asset_ids)},
    )
    outbox.publish(
        db,
        event_type="studio.job_queued",
        aggregate_type="studio_job",
        aggregate_id=job.id,
        merchant_id=ctx.merchant_id,
        payload={"job_id": str(job.id)},
    )
    return job


@handler("studio.job_queued")
def _enqueue(db: Session, ev: OutboxEvent) -> None:
    """Hand the slow AI work to a Celery task; the outbox guarantees the hand-off is not lost and the
    stale-job sweeper re-enqueues if the broker drops the message."""
    from app.worker.tasks import run_studio_job

    run_studio_job.delay(ev.payload["job_id"])


def _images(db: Session, job: StudioJob) -> list[ImageInput]:
    storage = get_storage()
    out = []
    for aid in job.asset_ids:
        d = db.scalar(
            select(MediaDerivative).where(MediaDerivative.asset_id == aid, MediaDerivative.kind == "medium")
        )
        if d is None:
            raise ValidationFailed("Photo derivative missing", code="media_not_ready")
        out.append(
            ImageInput(media_type=d.content_type, data_b64=base64.b64encode(storage.get(d.key)).decode())
        )
    return out


def _clip(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Enforce length limits; return issues for anything clipped."""
    issues: list[dict[str, Any]] = []
    for field in ("title_en", "title_ne", "description_en", "description_ne"):
        if len(result.get(field) or "") > LIMITS[field]:
            result[field] = result[field][: LIMITS[field]].rstrip()
            issues.append({"field": field, "kind": "too_long"})
    for field, lim in (
        ("bullets_en", LIMITS["bullets_en"]),
        ("hashtags", LIMITS["hashtags"]),
        ("attributes", LIMITS["attributes"]),
    ):
        if len(result.get(field) or []) > lim:
            result[field] = result[field][:lim]
    result["hashtags"] = [
        h.lstrip("#").strip().lower().replace(" ", "") for h in result.get("hashtags", []) if h.strip()
    ]
    seo = result.get("seo") or {}
    seo["title"] = (seo.get("title") or "")[: LIMITS["seo.title"]]
    seo["description"] = (seo.get("description") or "")[: LIMITS["seo.description"]]
    for k, v in (result.get("captions") or {}).items():
        result["captions"][k] = v[: LIMITS["caption"]]
    return issues


def run_job(job_id: uuid.UUID) -> StudioJob | None:
    """Worker entry point. Never holds a DB transaction across the provider call."""
    with session_scope() as db:
        job = db.scalar(
            select(StudioJob)
            .where(StudioJob.id == job_id)
            .with_for_update(skip_locked=True)
            .execution_options(skip_tenant_filter=True)
        )
        if job is None or job.status not in ("queued", "running"):
            return job
        job.status, job.attempts = "running", job.attempts + 1
        merchant_id, locale, notes = job.merchant_id, job.locale, job.seller_notes or ""
        brand_voice = describe_brand_voice(db, merchant_id)
        images = _images(db, job)
        prompt = get_prompt(db, PROMPT, "en")
    request = AIRequest(
        system=prompt.system,
        messages=(
            Message(
                "user",
                prompt.render_user(notes=notes or "(none)", locale=locale, brand_voice=brand_voice),
                tuple(images),
            ),
        ),
        json_schema=prompt.schema,
        max_tokens=6000,
        locale=locale,
        prompt_name=prompt.name,
        prompt_version=prompt.version,
    )
    try:
        res = gateway.run(
            task=TASK,
            request=request,
            merchant_id=merchant_id,
            idempotency_key=f"studio:{job_id}:{job.attempts}",
            reference_type="studio_job",
            reference_id=str(job_id),
        )
    except (AIUnavailable, AppError) as e:
        with session_scope() as db:
            job = db.get(StudioJob, job_id)
            assert job is not None
            terminal = not isinstance(e, AIUnavailable) or job.attempts >= MAX_ATTEMPTS
            job.status = "failed" if terminal else "queued"
            job.error_code = e.code
            if terminal:
                job.finished_at = utcnow()
                audit.record(
                    db,
                    action="studio.job_failed",
                    resource_type="studio_job",
                    resource_id=job.id,
                    actor=Actor.system("studio"),
                    merchant_id=job.merchant_id,
                    metadata={"error_code": e.code, "attempts": job.attempts},
                )
        log.warning("studio_job_failed", job_id=str(job_id), error_code=e.code)
        return None

    data: dict[str, Any] = dict(res.data)
    issues = _clip(data)
    customer_facing = {
        "title_en": data["title_en"],
        "title_ne": data["title_ne"],
        "description_en": data["description_en"],
        "description_ne": data["description_ne"],
        **{f"captions.{k}": v for k, v in data["captions"].items()},
        **{f"bullets_en[{i}]": b for i, b in enumerate(data["bullets_en"])},
    }
    issues += [
        {"field": v.field, "kind": f"unsupported_claim:{v.kind}", "excerpt": v.excerpt}
        for v in grounding.check(customer_facing, notes)
    ]
    if not data.get("is_product_photo", True):
        issues.append({"field": "photos", "kind": "not_a_product_photo"})
    with session_scope() as db:
        job = db.get(StudioJob, job_id)
        assert job is not None
        job.result = data
        job.confidence = res.confidence
        job.issues = issues
        job.needs_review = res.needs_review or bool(issues) or bool(data.get("needs_seller_input"))
        job.status, job.finished_at = "ready", utcnow()
        job.ai_request_group = uuid.UUID(res.execution_id)
        job.ai_provider, job.ai_model, job.prompt_version = res.provider, res.model, prompt.version
        job.error_code = None
        audit.record(
            db,
            action="studio.job_ready",
            resource_type="studio_job",
            resource_id=job.id,
            actor=Actor(type="ai", display=f"{res.provider}:{res.model}"),
            merchant_id=job.merchant_id,
            metadata={"confidence": res.confidence, "issues": len(issues), "fallback": res.fallback_used},
        )
        return job


def describe_brand_voice(db: Session, merchant_id: uuid.UUID) -> str:
    """Plain-language brand voice for the prompt: style guidance only, never facts or claims."""
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, merchant_id)
    if m is None:
        return "warm and friendly; at most one or two emoji"
    tone = {
        "friendly": "warm and friendly",
        "premium": "polished and understated",
        "playful": "playful and upbeat",
        "minimal": "short and plain",
    }[m.brand_tone]
    emoji = {"none": "no emoji", "light": "at most one or two emoji", "lots": "emoji are welcome"}[
        m.brand_emoji
    ]
    parts = [tone, emoji]
    if m.brand_avoid_words:
        parts.append("never use these words: " + ", ".join(m.brand_avoid_words[:30]))
    if m.brand_sample_caption:
        parts.append(f'match the style (not the content) of this sample: "{m.brand_sample_caption[:600]}"')
    return "; ".join(parts)


def requeue_stale(db: Session, older_than: timedelta = timedelta(minutes=10)) -> int:
    from app.worker.tasks import run_studio_job

    rows = db.scalars(
        select(StudioJob)
        .where(StudioJob.status.in_(("queued", "running")), StudioJob.updated_at < utcnow() - older_than)
        .limit(100)
        .execution_options(skip_tenant_filter=True)
    ).all()
    for j in rows:
        if j.attempts >= MAX_ATTEMPTS:
            j.status, j.error_code, j.finished_at = "failed", "stalled", utcnow()
        else:
            j.status = "queued"
            j.updated_at = utcnow()
            run_studio_job.delay(str(j.id))
    return len(rows)


# ----------------------------------------------------------------------------- apply / discard
def apply_job(
    db: Session,
    ctx: TenantContext,
    job_id: uuid.UUID,
    product: catalog.ProductInput,
    accepted_attribute_keys: list[str],
    category_path: list[str] | None,
) -> uuid.UUID:
    job = _get(db, ctx, job_id)
    if job.status == "applied" and job.product_id:
        return job.product_id  # idempotent
    if job.status != "ready" or not job.result:
        raise Conflict(
            "This draft isn't ready to apply", code="draft_not_ready", details={"status": job.status}
        )
    if product.category_id is None and category_path:
        product.category_id = _ensure_category(db, ctx, category_path)
    p = catalog.create_product(db, ctx, product)
    threshold = load_policy().task(TASK).min_confidence or 0.75
    accepted = set(accepted_attribute_keys)
    suggestions = [
        (a["key"], a["value"], float(a["confidence"]))
        for a in job.result.get("attributes", [])
        if a.get("key") and a.get("value")
    ]
    catalog.suggest_attributes(db, ctx.merchant_id, p.id, suggestions, locale="en")
    auto = [k for k, _, c in suggestions if c >= threshold] + [k for k in accepted]
    if auto:
        catalog.confirm_attributes(db, ctx, p.id, sorted(set(auto)))
    catalog.set_product_media(db, ctx, p.id, [catalog.MediaInput(asset_id=a) for a in job.asset_ids])
    job.status, job.product_id = "applied", p.id
    audit.record(
        db,
        action="studio.job_applied",
        resource_type="studio_job",
        resource_id=job.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"product_id": str(p.id)},
    )
    return p.id


def _ensure_category(db: Session, ctx: TenantContext, path: list[str]) -> uuid.UUID | None:
    from app.domains.catalog import rules

    parent: uuid.UUID | None = None
    built = ""
    for name in [p.strip() for p in path if p.strip()][:6]:
        slug = rules.handleize(name)
        if not slug:
            continue
        built = f"{built}/{slug}" if built else slug
        found = db.scalar(
            select(Category).where(Category.merchant_id == ctx.merchant_id, Category.path == built)
        )
        parent = found.id if found else catalog.create_category(db, ctx, name, parent).id
    return parent


def discard_job(db: Session, ctx: TenantContext, job_id: uuid.UUID) -> None:
    job = _get(db, ctx, job_id)
    if job.status in ("applied", "discarded"):
        return
    job.status = "discarded"
    audit.record(
        db,
        action="studio.job_discarded",
        resource_type="studio_job",
        resource_id=job.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
    )


def retry_job(db: Session, ctx: TenantContext, job_id: uuid.UUID) -> StudioJob:
    job = _get(db, ctx, job_id)
    if job.status != "failed":
        raise Conflict("Only failed drafts can be retried", code="not_failed")
    job.status, job.attempts, job.error_code = "queued", 0, None
    outbox.publish(
        db,
        event_type="studio.job_queued",
        aggregate_type="studio_job",
        aggregate_id=job.id,
        merchant_id=ctx.merchant_id,
        payload={"job_id": str(job.id)},
    )
    return job


def job_view(j: StudioJob) -> dict[str, Any]:
    return {
        "id": j.id,
        "status": j.status,
        "asset_ids": j.asset_ids,
        "locale": j.locale,
        "seller_notes": j.seller_notes,
        "draft": j.result,
        "confidence": j.confidence,
        "needs_review": j.needs_review,
        "issues": j.issues,
        "error_code": j.error_code,
        "attempts": j.attempts,
        "product_id": j.product_id,
        "ai": {"provider": j.ai_provider, "model": j.ai_model, "prompt_version": j.prompt_version}
        if j.ai_provider
        else None,
        "created_at": j.created_at,
        "finished_at": j.finished_at,
    }
