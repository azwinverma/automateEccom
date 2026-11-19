"""Creative Intelligence (CNT-013/014, CGN-001…006; spec 09 §Creative Genome, §Closed-loop learning).

GENERATE → PUBLISH → MEASURE → ATTRIBUTE → LEARN → UPDATE GENOME → GENERATE BETTER

- Measure: channel insights where the adapter supports them (CONTENT_METRICS), or numbers the seller
  types in from the app's own insights ("manual"). Nothing is estimated.
- Attribute (per post, 7-day window after publishing):
  1. explicit: the customer wrote from the post (the channel said which post) → their chats and orders;
  2. window: orders with the post's product placed within 7 days, credited with a decay
     (exp(-days/3)) and shared between posts of the same product that were live at the time;
  3. everything else is unattributed. The method mix is stored on every metric.
- Learn: for each creative attribute value, average attributed orders per post, shrunk towards the shop's
  baseline (k = 5 posts) and compared with the shop's other posts. Needs >= 20 measured posts in total and
  >= 5 posts per value. Orders come first; with too few orders the outcome is inquiries (labelled).
  Engagement is shown but never makes a pattern "recommended" on its own (likes don't pay rent).
- Use: Studio caption guidance, Auto Reel settings and a posting-time suggestion, each recording the
  genome version it came from, so genome-informed posts can be compared with the rest (CGN-006).
"""

from __future__ import annotations

import math
import statistics
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.domains.intelligence.models import (
    ContentChannelMetric,
    CreativeExperiment,
    CreativeGenomeProfile,
    CreativePerformanceMetric,
)

log = structlog.get_logger(__name__)

METHOD_VERSION = "cgn-1.0"
WINDOW_DAYS = 7
DECAY_DAYS = 3.0
LOOKBACK_DAYS = 180
MIN_POSTS = 20
MIN_PER_VALUE = 5
SHRINK_K = 5
MIN_ORDERS_FOR_ORDER_OUTCOME = 5
MIN_LIFT = 0.10
ATTRIBUTES = (
    "format",
    "hook_type",
    "price_timing",
    "language_mix",
    "caption_length",
    "cta_type",
    "human_presence",
    "posting_window",
    "duration_band",
    "background",
)
WINDOWS = {"morning": (5, 11), "afternoon": (12, 16), "evening": (17, 20), "night": (21, 4)}
WINDOW_HOURS = {"morning": (8, 11), "afternoon": (12, 15), "evening": (18, 21), "night": (21, 23)}


# ----------------------------------------------------------------------------- features
def _window(hour: int | None) -> str | None:
    if hour is None:
        return None
    if 5 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 16:
        return "afternoon"
    if 17 <= hour <= 20:
        return "evening"
    return "night"


def features(p: Any) -> dict[str, str]:
    """Creative attribute values the genome learns from (unknowns are left out, never guessed)."""
    f: dict[str, str] = {"format": p.kind}
    if p.hook_type and p.hook_type != "unknown":
        f["hook_type"] = p.hook_type
    if not p.price_shown:
        f["price_timing"] = "no_price"
    elif p.price_timing_s is not None:
        f["price_timing"] = "first_2s" if p.price_timing_s <= 2 else "later"
    else:
        f["price_timing"] = "shown"
    if p.language_mix and p.language_mix != "none":
        f["language_mix"] = p.language_mix
    if p.caption_bucket:
        f["caption_length"] = p.caption_bucket
    if p.cta_type:
        f["cta_type"] = p.cta_type
    if p.human_presence is not None:
        f["human_presence"] = "yes" if p.human_presence else "no"
    w = _window(p.posting_hour)
    if w:
        f["posting_window"] = w
    if p.duration_s:
        d = p.duration_s
        f["duration_band"] = (
            "up_to_7s" if d <= 7 else "8_11s" if d <= 11 else "12_20s" if d <= 20 else "over_20s"
        )
    if p.background:
        f["background"] = p.background
    return f


# ----------------------------------------------------------------------------- measure (CNT-013)
def ingest_channel_metrics(db: Session, merchant_id: uuid.UUID) -> int:
    from app.domains.channels.models import ChannelConnection
    from app.domains.channels.service import adapter_for
    from app.domains.content.models import ContentPost
    from app.domains.integrations.base import ChannelCapability, IntegrationError

    since = utcnow() - timedelta(days=30)
    posts = list(
        db.scalars(
            select(ContentPost).where(
                ContentPost.merchant_id == merchant_id,
                ContentPost.status == "published",
                ContentPost.published_at >= since,
                ContentPost.external_id.is_not(None),
            )
        )
    )
    by_conn: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for p in posts:
        by_conn[p.connection_id].append(p)
    n = 0
    for cid, ps in by_conn.items():
        c = db.get(ChannelConnection, cid)
        if c is None or c.status != "connected":
            continue
        adapter = adapter_for(c)
        if not adapter.supports(ChannelCapability.CONTENT_METRICS):
            continue
        try:
            got = adapter.fetch_content_metrics([p.external_id for p in ps])
        except (IntegrationError, NotImplementedError) as e:
            log.warning("content_metrics_fetch_failed", connection=str(cid), error=type(e).__name__)
            continue
        for p in ps:
            m = got.get(p.external_id)
            if m is None:
                continue
            db.add(
                ContentChannelMetric(
                    merchant_id=merchant_id,
                    post_id=p.id,
                    source="channel",
                    provider=c.provider,
                    views=m.views,
                    likes=m.likes,
                    comments=m.comments,
                    shares=m.shares,
                    saves=m.saves,
                    clicks=m.clicks,
                )
            )
            n += 1
    db.flush()
    return n


def record_manual(
    db: Session, ctx: TenantContext, post_id: uuid.UUID, counts: dict[str, int | None]
) -> ContentChannelMetric:
    """The seller copies the numbers from Instagram/TikTok/Facebook insights (no API needed)."""
    from app.domains.audit import service as audit
    from app.domains.content.models import ContentPost

    p = db.get(ContentPost, post_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound(code="post_not_found")
    if p.status != "published":
        raise Conflict("Results can be added once the post is published", code="post_not_published")
    if not any(v is not None for v in counts.values()):
        raise ValidationFailed("Enter at least one number", code="metrics_empty")
    m = ContentChannelMetric(
        merchant_id=ctx.merchant_id, post_id=p.id, source="manual", entered_by_user_id=ctx.actor.id, **counts
    )
    db.add(m)
    db.flush()
    audit.record(
        db,
        action="content.metrics_entered",
        resource_type="content_post",
        resource_id=p.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={k: v for k, v in counts.items() if v is not None},
    )
    attribute_post(db, p)
    return m


def latest_metrics(db: Session, post_id: uuid.UUID) -> ContentChannelMetric | None:
    return db.scalar(
        select(ContentChannelMetric)
        .where(ContentChannelMetric.post_id == post_id)
        .order_by(ContentChannelMetric.captured_at.desc())
        .limit(1)
    )


# ----------------------------------------------------------------------------- attribute (CNT-014, CGN-001)
def _decay(delta: timedelta) -> float:
    return math.exp(-max(0.0, delta.total_seconds() / 86400) / DECAY_DAYS)


def attribute_post(db: Session, p: Any, now: datetime | None = None) -> CreativePerformanceMetric | None:
    from app.domains.content.models import ContentPost
    from app.domains.inbox.models import Conversation, Message
    from app.domains.orders.models import Order, OrderLine

    if p.published_at is None:
        return None
    now = now or utcnow()
    start, end = p.published_at, p.published_at + timedelta(days=WINDOW_DAYS)
    live_end = min(end, now)
    # 1. explicit: chats that came from this post, and their orders.
    convs = list(db.scalars(select(Conversation.id).where(Conversation.content_post_id == p.id)))
    explicit_orders = list(
        db.scalars(
            select(Order).where(
                Order.conversation_id.in_(convs) if convs else Order.id.is_(None),
                Order.status.not_in(("draft", "cancelled")),
                Order.placed_at >= start,
            )
        )
    )
    orders_w = float(len(explicit_orders))
    revenue = 0.0
    contribution: float | None = 0.0
    explicit_ids = {o.id for o in explicit_orders}
    for o in explicit_orders:
        lines = list(db.scalars(select(OrderLine).where(OrderLine.order_id == o.id)))
        for ln in lines:
            value = ln.unit_price_minor * ln.active_quantity - ln.line_discount_minor
            revenue += value
            if contribution is not None:
                contribution = (
                    None
                    if ln.unit_cost_minor is None
                    else contribution + value - ln.unit_cost_minor * ln.active_quantity
                )
    window_orders = 0.0
    window_inquiries = 0
    if p.product_id:
        # 2. window: orders with the product while the post was fresh, shared with sibling posts.
        siblings = list(
            db.scalars(
                select(ContentPost).where(
                    ContentPost.product_id == p.product_id,
                    ContentPost.status == "published",
                    ContentPost.published_at.is_not(None),
                    ContentPost.published_at > start - timedelta(days=WINDOW_DAYS),
                    ContentPost.published_at < live_end,
                )
            )
        )
        rows = db.execute(
            select(Order, OrderLine)
            .join(OrderLine, OrderLine.order_id == Order.id)
            .where(
                OrderLine.product_id == p.product_id,
                Order.status.not_in(("draft", "cancelled")),
                Order.placed_at >= start,
                Order.placed_at < live_end,
            )
        ).all()
        explicit_elsewhere = set(
            db.scalars(
                select(Order.id)
                .join(Conversation, Conversation.id == Order.conversation_id)
                .where(Conversation.content_post_id.is_not(None), Conversation.content_post_id != p.id)
            )
        )
        for o, ln in rows:
            if o.id in explicit_ids or o.id in explicit_elsewhere:
                continue
            ws = {
                s.id: _decay(o.placed_at - s.published_at)
                for s in siblings
                if s.published_at is not None
                and s.published_at <= o.placed_at < s.published_at + timedelta(days=WINDOW_DAYS)
            }
            mine = ws.get(p.id)
            if not mine:
                continue
            credit = max(ws.values()) * mine / sum(ws.values())
            window_orders += credit
            value = ln.unit_price_minor * ln.active_quantity - ln.line_discount_minor
            revenue += value * credit
            if contribution is not None:
                contribution = (
                    None
                    if ln.unit_cost_minor is None
                    else contribution + (value - ln.unit_cost_minor * ln.active_quantity) * credit
                )
        # Inquiries in the window: chats where the customer wrote from the product (channel product ref).
        window_inquiries = int(
            db.scalar(
                select(func.count(func.distinct(Message.conversation_id))).where(
                    Message.direction == "in",
                    Message.created_at >= start,
                    Message.created_at < live_end,
                    Message.grounding["product_ref"].astext == str(p.product_id),
                    Message.conversation_id.not_in(convs) if convs else Message.id.is_not(None),
                )
            )
            or 0
        )
    orders_w += window_orders
    m = latest_metrics(db, p.id)
    engagements = None
    if m is not None and any(x is not None for x in (m.likes, m.comments, m.shares, m.saves)):
        engagements = sum(x or 0 for x in (m.likes, m.comments, m.shares, m.saves))
    method = (
        "explicit"
        if explicit_orders and not window_orders
        else "window"
        if window_orders and not explicit_orders
        else "mixed"
        if explicit_orders
        else "none"
    )
    vals = {
        "window_complete": now >= end,
        "views": m.views if m else None,
        "engagements": engagements,
        "clicks": m.clicks if m else None,
        "metrics_source": m.source if m else None,
        "inquiries": len(convs) + window_inquiries,
        "orders": round(orders_w, 3),
        "revenue_minor": round(revenue),
        "contribution_minor": round(contribution) if contribution is not None else None,
        "attribution": {
            "method": method,
            "explicit_orders": len(explicit_orders),
            "window_orders": round(window_orders, 3),
            "explicit_inquiries": len(convs),
            "window_inquiries": window_inquiries,
            "decay_days": DECAY_DAYS,
        },
        "method_version": METHOD_VERSION,
        "computed_at": now,
    }
    db.execute(
        pg_insert(CreativePerformanceMetric)
        .values(id=uuid7(), merchant_id=p.merchant_id, post_id=p.id, window_days=WINDOW_DAYS, **vals)
        .on_conflict_do_update(index_elements=["post_id", "window_days"], set_=vals)
    )
    db.flush()
    return db.scalar(select(CreativePerformanceMetric).where(CreativePerformanceMetric.post_id == p.id))


def attribute_all(db: Session, merchant_id: uuid.UUID) -> int:
    """Re-attribute posts whose window is open or closed recently (late orders still count)."""
    from app.domains.content.models import ContentPost

    n = 0
    for p in db.scalars(
        select(ContentPost).where(
            ContentPost.merchant_id == merchant_id,
            ContentPost.status == "published",
            ContentPost.published_at >= utcnow() - timedelta(days=WINDOW_DAYS + 3),
        )
    ):
        attribute_post(db, p)
        n += 1
    return n


# ----------------------------------------------------------------------------- learn (CGN-002)
def _measured(
    db: Session, merchant_id: uuid.UUID, since: datetime | None = None
) -> list[tuple[Any, CreativePerformanceMetric]]:
    from app.domains.content.models import ContentPost

    rows = db.execute(
        select(ContentPost, CreativePerformanceMetric)
        .join(CreativePerformanceMetric, CreativePerformanceMetric.post_id == ContentPost.id)
        .where(
            ContentPost.merchant_id == merchant_id,
            CreativePerformanceMetric.window_complete.is_(True),
            ContentPost.published_at >= (since or utcnow() - timedelta(days=LOOKBACK_DAYS)),
        )
    ).all()
    return [(p, m) for p, m in rows]


def _z(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    va, vb = statistics.pvariance(a), statistics.pvariance(b)
    se = math.sqrt(va / len(a) + vb / len(b))
    diff = statistics.fmean(a) - statistics.fmean(b)
    if se == 0:
        return 0.0 if diff == 0 else math.copysign(10.0, diff)
    return diff / se


def compute_genome(db: Session, merchant_id: uuid.UUID) -> CreativeGenomeProfile:
    rows = _measured(db, merchant_id)
    total_orders = sum(m.orders for _, m in rows)
    outcome = "orders" if total_orders >= MIN_ORDERS_FOR_ORDER_OUTCOME else "inquiries"

    def y(m: CreativePerformanceMetric) -> float:
        return float(m.orders if outcome == "orders" else m.inquiries)

    ys = [y(m) for _, m in rows]
    base = statistics.fmean(ys) if ys else 0.0
    rates = [m.engagements / m.views for _, m in rows if m.views and m.engagements is not None]
    base_eng = statistics.fmean(rates) if rates else None
    prefs: list[dict[str, Any]] = []
    ready = len(rows) >= MIN_POSTS
    if ready:
        by: dict[tuple[str, str], list[tuple[Any, CreativePerformanceMetric]]] = defaultdict(list)
        for p, m in rows:
            for a, v in features(p).items():
                by[(a, v)].append((p, m))
        for (a, v), items in by.items():
            n = len(items)
            if n < MIN_PER_VALUE:
                continue
            vy = [y(m) for _, m in items]
            ids = {p.id for p, _ in items}
            rest = [y(m) for p, m in rows if p.id not in ids]
            mean = statistics.fmean(vy)
            shrunk = (n * mean + SHRINK_K * base) / (n + SHRINK_K)
            lift = (shrunk / base - 1) if base > 0 else 0.0
            z = _z(vy, rest)
            conf = "high" if abs(z) >= 2 and n >= 10 else "medium" if abs(z) >= 1.5 else "low"
            vr = [m.engagements / m.views for _, m in items if m.views and m.engagements is not None]
            eng = statistics.fmean(vr) if len(vr) >= MIN_PER_VALUE else None
            eng_lift = (eng / base_eng - 1) if eng is not None and base_eng else None
            prefs.append(
                {
                    "attribute": a,
                    "value": v,
                    "n": n,
                    "mean": round(mean, 3),
                    "shrunk": round(shrunk, 3),
                    "lift": round(lift, 3),
                    "z": round(z, 2),
                    "confidence": conf,
                    "engagement_rate": round(eng, 4) if eng is not None else None,
                    "engagement_lift": round(eng_lift, 3) if eng_lift is not None else None,
                    "engagement_only": bool(eng_lift is not None and eng_lift >= 0.2 and conf == "low"),
                    "recommended": False,
                }
            )
        for a in ATTRIBUTES:
            cands = [
                x for x in prefs if x["attribute"] == a and x["confidence"] != "low" and x["lift"] >= MIN_LIFT
            ]
            if cands:
                max(cands, key=lambda x: x["shrunk"])["recommended"] = True
        prefs.sort(key=lambda x: (not x["recommended"], -x["lift"]))
    status = "ready" if ready else "learning"
    baseline = {
        "outcome": outcome,
        "mean": round(base, 3),
        "orders": round(total_orders, 2),
        "engagement_rate": round(base_eng, 4) if base_eng is not None else None,
        "min_posts": MIN_POSTS,
        "min_per_value": MIN_PER_VALUE,
        "window_days": WINDOW_DAYS,
        "lookback_days": LOOKBACK_DAYS,
    }
    last = latest(db, merchant_id)
    if (
        last is not None
        and last.posts == len(rows)
        and last.preferences == prefs
        and last.status == status
        and last.method_version == METHOD_VERSION
    ):
        return last  # nothing new learned: keep the version stable
    g = CreativeGenomeProfile(
        merchant_id=merchant_id,
        version=(last.version + 1) if last else 1,
        posts=len(rows),
        baseline=baseline,
        preferences=prefs,
        status=status,
        method_version=METHOD_VERSION,
    )
    db.add(g)
    db.flush()
    return g


def latest(db: Session, merchant_id: uuid.UUID) -> CreativeGenomeProfile | None:
    return db.scalar(
        select(CreativeGenomeProfile)
        .where(CreativeGenomeProfile.merchant_id == merchant_id)
        .order_by(CreativeGenomeProfile.version.desc())
        .limit(1)
    )


def recommended(g: CreativeGenomeProfile | None) -> dict[str, dict[str, Any]]:
    if g is None or g.status != "ready":
        return {}
    return {x["attribute"]: x for x in g.preferences if x.get("recommended")}


# ----------------------------------------------------------------------------- experiments (CGN-003)
def create_experiment(db: Session, ctx: TenantContext, data: dict[str, Any]) -> CreativeExperiment:
    if data["attribute"] not in ATTRIBUTES:
        raise ValidationFailed("Unknown attribute", code="experiment_attribute_unknown")
    if data["variant_a"] == data["variant_b"]:
        raise ValidationFailed("Pick two different options", code="experiment_same_variants")
    running = db.scalar(
        select(CreativeExperiment.id).where(
            CreativeExperiment.attribute == data["attribute"], CreativeExperiment.status == "running"
        )
    )
    if running:
        raise Conflict("A test on this is already running", code="experiment_already_running")
    e = CreativeExperiment(merchant_id=ctx.merchant_id, created_by_user_id=ctx.actor.id, **data)
    db.add(e)
    db.flush()
    return evaluate(db, e)  # progress from the start (0 posts per option), never a blank result


def evaluate(db: Session, e: CreativeExperiment, *, force: bool = False) -> CreativeExperiment:
    """Stopping rule: both options reach min_posts measured posts, or max_days pass (then no verdict)."""
    rows = _measured(db, e.merchant_id, since=e.started_at)
    groups: dict[str, list[float]] = {e.variant_a: [], e.variant_b: []}
    for p, m in rows:
        v = features(p).get(e.attribute)
        if v in groups:
            groups[v].append(float(m.orders if e.metric == "orders" else m.inquiries))
    a, b = groups[e.variant_a], groups[e.variant_b]
    enough = len(a) >= e.min_posts and len(b) >= e.min_posts
    timed_out = utcnow() >= e.started_at + timedelta(days=e.max_days)
    progress = {
        "a": {"n": len(a), "mean": round(statistics.fmean(a), 3) if a else None},
        "b": {"n": len(b), "mean": round(statistics.fmean(b), 3) if b else None},
    }
    if not (enough or timed_out or force):
        e.result = {**progress, "status": "collecting"}
        return e
    z = _z(a, b) if enough else 0.0
    winner = None
    if enough and abs(z) >= 1.96:
        winner = "a" if z > 0 else "b"
    e.result = {
        **progress,
        "z": round(z, 2),
        "winner": winner,
        "verdict": "clear" if winner else ("no_clear_difference" if enough else "not_enough_posts"),
    }
    if e.status == "running":
        e.status = "concluded" if not force else "stopped"
        e.ended_at = utcnow()
    return e


def stop_experiment(db: Session, ctx: TenantContext, exp_id: uuid.UUID) -> CreativeExperiment:
    e = db.get(CreativeExperiment, exp_id)
    if e is None or e.merchant_id != ctx.merchant_id:
        raise NotFound(code="experiment_not_found")
    if e.status != "running":
        raise Conflict("This test has ended", code="experiment_ended")
    return evaluate(db, e, force=True)


# ----------------------------------------------------------------------------- impact (CGN-006)
def impact(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    rows = _measured(db, merchant_id, since=utcnow() - timedelta(days=90))
    g = [m.orders for p, m in rows if p.genome_version is not None]
    o = [m.orders for p, m in rows if p.genome_version is None]
    out: dict[str, Any] = {
        "genome_posts": len(g),
        "other_posts": len(o),
        "genome_mean_orders": round(statistics.fmean(g), 3) if g else None,
        "other_mean_orders": round(statistics.fmean(o), 3) if o else None,
        "method": "observational",
        "note": "Same 90 days; other differences between the posts can contribute.",
    }
    if len(g) >= MIN_PER_VALUE and len(o) >= MIN_PER_VALUE and out["other_mean_orders"]:
        out["lift"] = round(out["genome_mean_orders"] / out["other_mean_orders"] - 1, 3)
        out["z"] = round(_z(g, o), 2)
    return out


# ----------------------------------------------------------------------------- use (CGN-004)
_CAPTION_TEXT = {
    ("language_mix", "ne"): "write captions in Nepali",
    ("language_mix", "en"): "write captions in English",
    ("language_mix", "ne_en_mixed"): "mix Nepali and English in captions the way customers talk",
    ("cta_type", "dm"): "end with an invitation to send a message",
    ("cta_type", "comment"): "invite customers to comment",
    ("cta_type", "call"): "invite customers to call",
    ("cta_type", "link"): "point customers to the link",
    ("caption_length", "short"): "keep captions short (under 80 characters)",
    ("caption_length", "medium"): "keep captions medium length",
    ("caption_length", "long"): "longer, detailed captions work well",
}


def suggestions(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    g = latest(db, merchant_id)
    rec = recommended(g)
    version = g.version if g is not None and rec else None
    caption = [
        {"attribute": a, "value": rec[a]["value"], "lift": rec[a]["lift"], "n": rec[a]["n"]}
        for a in ("language_mix", "cta_type", "caption_length")
        if a in rec
    ]
    guidance = "; ".join(
        _CAPTION_TEXT[(c["attribute"], c["value"])]
        for c in caption
        if (c["attribute"], c["value"]) in _CAPTION_TEXT
    )
    reel: dict[str, Any] = {}
    if "duration_band" in rec:
        band = rec["duration_band"]["value"]
        reel["target_seconds"] = {
            "up_to_7s": [5, 7],
            "8_11s": [8, 11],
            "12_20s": [12, 20],
            "over_20s": [21, 30],
        }[band]
    if "price_timing" in rec:
        reel["show_price"] = rec["price_timing"]["value"] in ("first_2s", "shown", "later")
    if "hook_type" in rec:
        reel["hook_type"] = rec["hook_type"]["value"]
    schedule: dict[str, Any] = {}
    if "posting_window" in rec:
        w = rec["posting_window"]["value"]
        schedule = {
            "window": w,
            "hours": list(WINDOW_HOURS[w]),
            "source": "genome",
            "lift": rec["posting_window"]["lift"],
        }
    else:
        from app.domains.intelligence.models import CommerceMemoryFact

        peak = db.scalar(
            select(CommerceMemoryFact).where(
                CommerceMemoryFact.merchant_id == merchant_id,
                CommerceMemoryFact.fact_type == "peak_order_hours",
                CommerceMemoryFact.status == "active",
            )
        )
        if peak is not None:
            schedule = {
                "hours": [peak.value["start_hour"], peak.value["end_hour"]],
                "source": "orders",  # when customers order, not a learned content pattern
            }
    return {
        "genome_version": version,
        "status": g.status if g else "learning",
        "caption": caption,
        "studio_guidance": guidance or None,
        "reel": reel,
        "schedule": schedule,
    }


def studio_guidance(db: Session, merchant_id: uuid.UUID) -> tuple[str | None, int | None]:
    from app.domains.billing.service import entitlements

    if not entitlements.resolve(db, merchant_id).has("intelligence.creative_genome"):
        return None, None
    s = suggestions(db, merchant_id)
    return (s["studio_guidance"], s["genome_version"]) if s["studio_guidance"] else (None, None)


def valid_version(db: Session, merchant_id: uuid.UUID, version: int | None) -> int | None:
    if version is None:
        return None
    ok = db.scalar(
        select(CreativeGenomeProfile.id).where(
            CreativeGenomeProfile.merchant_id == merchant_id, CreativeGenomeProfile.version == version
        )
    )
    if ok is None:
        raise ValidationFailed("Unknown genome version", code="genome_version_unknown")
    return version


# ----------------------------------------------------------------------------- jobs
def run(db: Session, merchant_id: uuid.UUID) -> dict[str, Any]:
    stats = {
        "metrics": ingest_channel_metrics(db, merchant_id),
        "attributed": attribute_all(db, merchant_id),
    }
    g = compute_genome(db, merchant_id)
    stats["genome_version"] = g.version
    stats["experiments"] = 0
    for e in db.scalars(select(CreativeExperiment).where(CreativeExperiment.status == "running")):
        evaluate(db, e)
        stats["experiments"] += 1
    return stats


def run_all(db: Session) -> int:
    from app.domains.billing.service import entitlements
    from app.domains.merchants.models import Merchant

    n = 0
    for mid in db.scalars(
        select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    ).all():
        bind_tenant(db, mid)
        if not entitlements.resolve(db, mid).has("intelligence.creative_genome"):
            continue
        try:
            with db.begin_nested():
                run(db, mid)
            n += 1
        except Exception:
            log.exception("creative_run_failed", merchant_id=str(mid))
    return n


# ----------------------------------------------------------------------------- views
def genome_view(g: CreativeGenomeProfile | None, measured: int) -> dict[str, Any]:
    return {
        "version": g.version if g else None,
        "status": g.status if g else "learning",
        "posts": g.posts if g else measured,
        "measured_posts": measured,
        "min_posts": MIN_POSTS,
        "baseline": g.baseline if g else None,
        "preferences": g.preferences if g else [],
        "method_version": METHOD_VERSION,
        "computed_at": g.computed_at.isoformat() if g else None,
    }


def experiment_view(e: CreativeExperiment) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "name": e.name,
        "hypothesis": e.hypothesis,
        "attribute": e.attribute,
        "variant_a": e.variant_a,
        "variant_b": e.variant_b,
        "metric": e.metric,
        "min_posts": e.min_posts,
        "max_days": e.max_days,
        "status": e.status,
        "started_at": e.started_at.isoformat(),
        "ends_by": (e.started_at + timedelta(days=e.max_days)).isoformat(),
        "ended_at": e.ended_at.isoformat() if e.ended_at else None,
        "result": e.result,
    }


def performance_view(p: Any, m: CreativePerformanceMetric | None) -> dict[str, Any]:
    return {
        "post_id": str(p.id),
        "kind": p.kind,
        "caption": p.caption[:120],
        "product_id": str(p.product_id) if p.product_id else None,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "genome_version": p.genome_version,
        "features": features(p),
        "metrics": None
        if m is None
        else {
            "window_days": m.window_days,
            "window_complete": m.window_complete,
            "views": m.views,
            "engagements": m.engagements,
            "clicks": m.clicks,
            "source": m.metrics_source,
            "inquiries": m.inquiries,
            "orders": m.orders,
            "revenue_minor": m.revenue_minor,
            "contribution_minor": m.contribution_minor,
            "attribution": m.attribution,
        },
    }
