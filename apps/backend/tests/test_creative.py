"""Phase 7: post results (CNT-013), attribution (CNT-014, CGN-001), Creative Genome (CGN-002), experiments
(CGN-003), genome inputs to Studio/Reels/scheduling (CGN-004), panel data + tips (CGN-005), impact (CGN-006)."""

from __future__ import annotations

import math
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.content.models import ContentPost
from app.domains.inbox.models import Conversation
from app.domains.integrations.base import ContentMetrics
from app.domains.integrations.sandbox import SandboxChannelAdapter
from app.domains.intelligence import creative
from app.domains.intelligence.models import CreativePerformanceMetric
from app.domains.orders.models import Order, OrderLine
from tests.conftest import onboard, set_plan
from tests.test_channels import connect
from tests.test_content import _post, _tick
from tests.test_inbox import Chat
from tests.test_orders import item

API = "/api/v1"
_N = {"n": 9000}


def published(client, s, conn_id: str, **over: Any) -> dict[str, Any]:
    p = _post(client, s, conn_id, **over)
    client.post(f"{API}/content/posts/{p['id']}/submit", headers=s.h())
    r = client.post(f"{API}/content/posts/{p['id']}/schedule", headers=s.h(), json={})
    assert r.status_code == 200, r.text
    _tick()
    return client.get(f"{API}/content/posts/{p['id']}", headers=s.h()).json()


def db_post(
    merchant_id: str, conn_id: str, *, days_ago: float, product_id: str | None = None, **attrs: Any
) -> uuid.UUID:
    mid = uuid.UUID(merchant_id)
    _N["n"] += 1
    with session_scope(mid) as db:
        p = ContentPost(
            merchant_id=mid,
            connection_id=uuid.UUID(conn_id),
            product_id=uuid.UUID(product_id) if product_id else None,
            kind=attrs.pop("kind", "post"),
            caption="Post",
            status="published",
            published_at=utcnow() - timedelta(days=days_ago),
            external_id=f"sbx-post-db-{_N['n']}",
            language_mix=attrs.pop("language_mix", "en"),
            caption_bucket=attrs.pop("caption_bucket", "short"),
            cta_type=attrs.pop("cta_type", "dm"),
            **attrs,
        )
        db.add(p)
        db.flush()
        return p.id


def measured(
    merchant_id: str,
    post_id: uuid.UUID,
    orders: float,
    *,
    inquiries: int = 0,
    views: int | None = None,
    engagements: int | None = None,
) -> None:
    mid = uuid.UUID(merchant_id)
    with session_scope(mid) as db:
        db.add(
            CreativePerformanceMetric(
                merchant_id=mid,
                post_id=post_id,
                window_days=7,
                window_complete=True,
                orders=orders,
                inquiries=inquiries,
                views=views,
                engagements=engagements,
                method_version="cgn-1.0",
            )
        )


def order_at(
    merchant_id: str,
    product_id: str,
    variant_id: str,
    at,
    *,
    conversation_id: uuid.UUID | None = None,
    cost: int | None = 100000,
) -> uuid.UUID:
    mid = uuid.UUID(merchant_id)
    _N["n"] += 1
    with session_scope(mid) as db:
        o = Order(
            merchant_id=mid,
            number=_N["n"],
            status="confirmed",
            source="chat" if conversation_id else "seller",
            currency="NPR",
            subtotal_minor=245000,
            total_minor=245000,
            payment_method="cod",
            payment_status="cod_pending",
            placed_at=at,
            conversation_id=conversation_id,
        )
        db.add(o)
        db.flush()
        db.add(
            OrderLine(
                merchant_id=mid,
                order_id=o.id,
                product_id=uuid.UUID(product_id),
                variant_id=uuid.UUID(variant_id),
                title="Kurta",
                unit_price_minor=245000,
                quantity=1,
                unit_cost_minor=cost,
            )
        )
        return o.id


def genome_shop(client, seller) -> str:
    """24 measured posts: Nepali-English captions sell 4x more; evening posts get likes, not orders."""
    set_plan(seller.merchant_id, "pro")
    c = connect(client, seller)["id"]
    m = seller.merchant_id
    for i in range(12):
        pid = db_post(m, c, days_ago=20 + i, language_mix="ne_en_mixed", posting_hour=19 if i % 2 else 10)
        measured(m, pid, orders=2.0 + (i % 3) * 0.5, views=1000, engagements=200 if i % 2 else 50)
    for i in range(12):
        pid = db_post(m, c, days_ago=20 + i, language_mix="en", posting_hour=19 if i % 2 else 10)
        measured(m, pid, orders=0.5 + (i % 2) * 0.25, views=1000, engagements=200 if i % 2 else 50)
    return c


# ----------------------------------------------------------------------------- measure
def test_channel_insights_and_typed_in_results_keep_their_source(client, seller):
    set_plan(seller.merchant_id, "pro")
    c = connect(client, seller)
    p = published(client, seller, c["id"])
    assert p["status"] == "published" and p["external_id"]
    SandboxChannelAdapter.insights[p["external_id"]] = ContentMetrics(
        views=1200, likes=80, comments=12, shares=3, saves=5, clicks=40
    )
    r = client.post(f"{API}/intelligence/creative/refresh", headers=seller.h()).json()
    assert r["metrics"] == 1
    row = client.get(f"{API}/intelligence/creative/posts", headers=seller.h()).json()["items"][0]
    assert row["metrics"]["views"] == 1200 and row["metrics"]["engagements"] == 100
    assert row["metrics"]["source"] == "channel" and row["metrics"]["window_complete"] is False
    one = client.get(f"{API}/intelligence/creative/posts/{p['id']}", headers=seller.h()).json()
    assert one["metrics"]["views"] == 1200 and one["currency"] == "NPR"
    # The seller copies newer numbers from the app's insights.
    typed = client.post(
        f"{API}/intelligence/creative/posts/{p['id']}/metrics",
        headers=seller.h(),
        json={"views": 1500, "likes": 90},
    )
    assert typed.status_code == 201, typed.text
    assert typed.json()["metrics"]["source"] == "manual" and typed.json()["metrics"]["views"] == 1500
    assert (
        client.post(
            f"{API}/intelligence/creative/posts/{p['id']}/metrics", headers=seller.h(), json={}
        ).status_code
        == 400
    )
    draft = _post(client, seller, c["id"])
    assert (
        client.post(
            f"{API}/intelligence/creative/posts/{draft['id']}/metrics", headers=seller.h(), json={"views": 5}
        ).status_code
        == 409
    )
    other = onboard(client, shop="Other Creative")
    assert (
        client.post(
            f"{API}/intelligence/creative/posts/{p['id']}/metrics", headers=other.h(), json={"views": 5}
        ).status_code
        == 404
    )


# ----------------------------------------------------------------------------- attribute
def test_explicit_beats_window_and_shared_credit_never_exceeds_one_order(client, seller):
    prod, vid = item(client, seller, stock=0)
    chat = Chat(client, seller, plan="pro")
    m = seller.merchant_id
    conn = chat.conn["id"]
    a = db_post(m, conn, days_ago=3, product_id=prod["id"])
    b = db_post(m, conn, days_ago=2, product_id=prod["id"])
    with session_scope() as db:
        a_ext = db.get(ContentPost, a).external_id
        a_at = db.get(ContentPost, a).published_at
    # The customer writes from post A: explicit attribution.
    chat.say("Yo kurta kati ho?", post_id=a_ext)
    with session_scope() as db:
        conv = db.scalar(select(Conversation).execution_options(skip_tenant_filter=True))
        assert conv is not None and conv.content_post_id == a
        conv_id = conv.id
    order_at(m, prod["id"], vid, a_at + timedelta(hours=5), conversation_id=conv_id)
    # A walk-in order for the product 2 days after A (1 day after B): shared by decay.
    order_at(m, prod["id"], vid, a_at + timedelta(days=2))
    out = client.post(f"{API}/intelligence/creative/refresh", headers=seller.h()).json()
    assert out["attributed"] == 2
    rows = {
        r["post_id"]: r["metrics"]
        for r in client.get(f"{API}/intelligence/creative/posts", headers=seller.h()).json()["items"]
    }
    ra, rb = rows[str(a)], rows[str(b)]
    wa, wb = math.exp(-2 / 3), math.exp(-1 / 3)
    share_a, share_b = wb * wa / (wa + wb), wb * wb / (wa + wb)
    assert ra["attribution"]["explicit_orders"] == 1 and ra["attribution"]["explicit_inquiries"] == 1
    assert abs(ra["attribution"]["window_orders"] - share_a) < 0.002
    assert abs(rb["attribution"]["window_orders"] - share_b) < 0.002
    assert (
        abs(ra["attribution"]["window_orders"] + rb["attribution"]["window_orders"] - wb) < 0.002
    )  # ≤ 1 order
    assert rb["attribution"]["explicit_orders"] == 0  # A's chat order is never shared with B
    assert ra["attribution"]["method"] == "mixed" and ra["inquiries"] == 1
    assert ra["revenue_minor"] == round(245000 + 245000 * share_a)
    assert ra["contribution_minor"] == round(145000 + 145000 * share_a)


def test_unknown_cost_leaves_contribution_empty(client, seller):
    set_plan(seller.merchant_id, "pro")
    prod, vid = item(client, seller, stock=0)
    c = connect(client, seller)["id"]
    a = db_post(seller.merchant_id, c, days_ago=1, product_id=prod["id"])
    with session_scope() as db:
        at = db.get(ContentPost, a).published_at
    order_at(seller.merchant_id, prod["id"], vid, at + timedelta(hours=2), cost=None)
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    row = client.get(f"{API}/intelligence/creative/posts", headers=seller.h()).json()["items"][0]
    assert row["metrics"]["orders"] > 0.9 and row["metrics"]["contribution_minor"] is None


# ----------------------------------------------------------------------------- learn
def test_genome_needs_enough_posts_learns_orders_not_likes_and_stays_stable(client, seller):
    set_plan(seller.merchant_id, "pro")
    c = connect(client, seller)["id"]
    for i in range(6):
        measured(seller.merchant_id, db_post(seller.merchant_id, c, days_ago=20 + i), orders=1)
    g = client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).json()
    assert g["status"] == "learning" and g["measured_posts"] == 6 and g["min_posts"] == 20
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    g = client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).json()
    assert g["status"] == "learning" and g["preferences"] == []


def test_genome_recommends_what_sells_with_shrinkage(client, seller):
    genome_shop(client, seller)
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    g = client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).json()
    assert g["status"] == "ready" and g["posts"] == 24 and g["baseline"]["outcome"] == "orders"
    mixed = next(
        x for x in g["preferences"] if x["attribute"] == "language_mix" and x["value"] == "ne_en_mixed"
    )
    en = next(x for x in g["preferences"] if x["attribute"] == "language_mix" and x["value"] == "en")
    assert mixed["recommended"] is True and mixed["confidence"] == "high" and en["recommended"] is False
    raw_lift = mixed["mean"] / g["baseline"]["mean"] - 1
    assert 0 < mixed["lift"] < raw_lift  # shrunk towards the shop's average
    evening = next(
        x for x in g["preferences"] if x["attribute"] == "posting_window" and x["value"] == "evening"
    )
    assert evening["engagement_lift"] > 0.2 and evening["recommended"] is False  # likes alone don't count
    v = g["version"]
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    assert client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).json()["version"] == v
    s = client.get(f"{API}/intelligence/creative/suggestions", headers=seller.h()).json()
    assert s["genome_version"] == v and "mix Nepali and English" in s["studio_guidance"]
    # A strong pattern becomes a tip on Home (informational).
    client.post(f"{API}/intelligence/recommendations/refresh", headers=seller.h())
    tip = next(
        r
        for r in client.get(f"{API}/intelligence/recommendations", headers=seller.h()).json()["items"]
        if r["type"] == "creative_tip"
    )
    assert tip["explanation"]["vars"]["value"] == "ne_en_mixed" and tip["action"]["type"] == "none"


# ----------------------------------------------------------------------------- use
def test_genome_version_is_recorded_on_studio_drafts_reels_and_scheduled_posts(client, seller, monkeypatch):
    from app.domains.ai.providers.sandbox import SandboxAdapter
    from tests.test_media import phone_photo, upload
    from tests.test_studio import DRAFT, _run

    c = genome_shop(client, seller)
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    v = client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).json()["version"]
    seen: dict[str, str] = {}
    original = SandboxAdapter.generate_structured

    def capture(self, model, req, **kw):
        seen["text"] = req.messages[-1].text
        return original(self, model, req, **kw)

    monkeypatch.setattr(SandboxAdapter, "generate_structured", capture)
    SandboxAdapter.override_data["sandbox-text"] = DRAFT
    job = _run(client, seller, [upload(client, seller, phone_photo())["id"]], notes="cotton")
    assert "mix Nepali and English" in seen["text"]
    from app.domains.studio.models import StudioJob

    with session_scope() as db:
        assert db.get(StudioJob, uuid.UUID(job["id"])).genome_version == v
    posts = client.post(
        f"{API}/content/posts/from-studio",
        headers=seller.h(),
        json={"job_id": job["id"], "connection_ids": [c]},
    )
    assert posts.status_code == 201, posts.text
    assert posts.json()["items"][0]["genome_version"] == v  # the post inherits the draft's genome version
    draft = _post(client, seller, c)
    client.post(f"{API}/content/posts/{draft['id']}/submit", headers=seller.h())
    bad = client.post(
        f"{API}/content/posts/{draft['id']}/schedule",
        headers=seller.h(),
        json={"at": (utcnow() + timedelta(days=1)).isoformat(), "genome_version": 999},
    )
    assert bad.status_code == 400
    ok = client.post(
        f"{API}/content/posts/{draft['id']}/schedule",
        headers=seller.h(),
        json={"at": (utcnow() + timedelta(days=1)).isoformat(), "genome_version": v},
    )
    assert ok.status_code == 200 and ok.json()["genome_version"] == v
    photos = [upload(client, seller, phone_photo())["id"] for _ in range(2)]
    reel = client.post(
        f"{API}/media/videos/auto-reels", headers=seller.h(), json={"asset_ids": photos, "genome_version": v}
    )
    assert reel.status_code == 202, reel.text
    assert reel.json()["genome_version"] == v


def test_impact_compares_genome_informed_posts_with_the_rest(client, seller):
    set_plan(seller.merchant_id, "pro")
    c = connect(client, seller)["id"]
    for i in range(6):
        measured(
            seller.merchant_id, db_post(seller.merchant_id, c, days_ago=20 + i, genome_version=1), orders=2
        )
        measured(
            seller.merchant_id, db_post(seller.merchant_id, c, days_ago=20 + i), orders=1 + (i % 2) * 0.2
        )
    imp = client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).json()["impact"]
    assert imp["genome_posts"] == 6 and imp["other_posts"] == 6 and imp["method"] == "observational"
    assert imp["lift"] == round(2 / 1.1 - 1, 3)


# ----------------------------------------------------------------------------- experiments
def test_experiment_follows_its_stopping_rule(client, seller):
    set_plan(seller.merchant_id, "pro")
    c = connect(client, seller)["id"]
    body = {
        "name": "Price first?",
        "hypothesis": "Showing the price first brings more orders",
        "attribute": "hook_type",
        "variant_a": "price_first",
        "variant_b": "product_closeup",
        "min_posts": 3,
        "max_days": 30,
    }
    e = client.post(f"{API}/intelligence/creative/experiments", headers=seller.h(), json=body)
    assert e.status_code == 201, e.text
    eid = e.json()["id"]
    assert (
        client.post(f"{API}/intelligence/creative/experiments", headers=seller.h(), json=body).status_code
        == 409
    )
    with session_scope() as db:
        from app.domains.intelligence.models import CreativeExperiment

        db.execute(
            update(CreativeExperiment)
            .values(started_at=utcnow() - timedelta(days=20))
            .execution_options(skip_tenant_filter=True)
        )
    for i in range(3):
        measured(
            seller.merchant_id,
            db_post(seller.merchant_id, c, days_ago=10 + i, hook_type="price_first"),
            orders=3 + i * 0.1,
        )
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    x = client.get(f"{API}/intelligence/creative/experiments", headers=seller.h()).json()["items"][0]
    assert x["status"] == "running" and x["result"]["status"] == "collecting" and x["result"]["a"]["n"] == 3
    for i in range(3):
        measured(
            seller.merchant_id,
            db_post(seller.merchant_id, c, days_ago=10 + i, hook_type="product_closeup"),
            orders=0.5 + i * 0.1,
        )
    client.post(f"{API}/intelligence/creative/refresh", headers=seller.h())
    x = client.get(f"{API}/intelligence/creative/experiments", headers=seller.h()).json()["items"][0]
    assert x["status"] == "concluded" and x["result"]["winner"] == "a" and x["result"]["verdict"] == "clear"
    assert (
        client.post(f"{API}/intelligence/creative/experiments/{eid}/stop", headers=seller.h()).status_code
        == 409
    )
    e2 = client.post(
        f"{API}/intelligence/creative/experiments",
        headers=seller.h(),
        json={**body, "attribute": "cta_type", "variant_a": "dm", "variant_b": "comment"},
    ).json()
    stopped = client.post(
        f"{API}/intelligence/creative/experiments/{e2['id']}/stop", headers=seller.h()
    ).json()
    assert stopped["status"] == "stopped" and stopped["result"]["verdict"] == "not_enough_posts"


def test_creative_genome_needs_the_plan_but_post_results_dont(client, seller):
    set_plan(seller.merchant_id, "growth")
    assert client.get(f"{API}/intelligence/creative/genome", headers=seller.h()).status_code == 403
    assert client.get(f"{API}/intelligence/creative/suggestions", headers=seller.h()).status_code == 403
    assert client.get(f"{API}/intelligence/creative/posts", headers=seller.h()).status_code == 200
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        assert creative.studio_guidance(db, uuid.UUID(seller.merchant_id)) == (None, None)
