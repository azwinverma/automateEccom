from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.db import session_scope, utcnow
from app.domains.content.models import ContentPost
from app.domains.content.service import publish_due
from app.domains.integrations.base import IntegrationError
from app.domains.integrations.sandbox import SandboxChannelAdapter
from app.domains.platform.models import OutboxEvent
from tests.conftest import onboard, register_and_login
from tests.test_channels import connect
from tests.test_media import phone_photo, upload
from tests.test_studio import DRAFT, _run

API = "/api/v1/content"


def _post(client, s, conn_id, **over):
    body = {
        "connection_id": conn_id,
        "caption": "Dashain collection is here. Message us to order.",
        "hashtags": ["#Dashain", "kurta"],
    } | over
    r = client.post(f"{API}/posts", headers=s.h(), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _act(client, s, pid, action, **json):
    return client.post(f"{API}/posts/{pid}/{action}", headers=s.h(), json=json)


def _tick() -> dict[str, int]:
    with session_scope() as db:
        return publish_due(db)


def test_seller_post_auto_approved_scheduled_and_published(client, seller):
    c = connect(client, seller)
    p = _post(client, seller, c["id"])
    assert p["hashtags"] == ["dashain", "kurta"] and p["status"] == "draft"
    assert _act(client, seller, p["id"], "submit").json()["status"] == "approved"  # seller's own words
    later = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    assert _act(client, seller, p["id"], "schedule", at=later).json()["status"] == "scheduled"
    assert _tick() == {"published": 0, "retrying": 0, "failed": 0}  # not due yet
    with session_scope() as db:
        db.execute(update(ContentPost).values(next_attempt_at=utcnow()))
    assert _tick()["published"] == 1
    posts = client.get(f"{API}/posts", headers=seller.h()).json()["items"]
    assert posts[0]["status"] == "published" and posts[0]["external_id"].startswith("sbx-post-")


def test_ai_posts_need_approval_in_assisted_mode_and_approver_permission(client, seller):
    from app.domains.ai.providers.sandbox import SandboxAdapter

    SandboxAdapter.override_data["sandbox-text"] = DRAFT
    c = connect(client, seller)
    job = _run(client, seller, [upload(client, seller, phone_photo())["id"]])
    r = client.post(
        f"{API}/posts/from-studio",
        headers=seller.h(),
        json={"job_id": job["id"], "connection_ids": [c["id"]]},
    )
    assert r.status_code == 201
    post = r.json()["items"][0]
    assert post["source"] == "ai_studio" and post["caption"] == DRAFT["captions"]["instagram"]
    assert len(post["asset_ids"]) == 1
    assert _act(client, seller, post["id"], "submit").json()["status"] == "pending_approval"

    from app.domains.merchants.models import Membership

    staff = register_and_login(client, "writer@example.com")
    uid = client.get("/api/v1/me", headers=staff.h()).json()["user"]["id"]
    with session_scope(uuid.UUID(seller.merchant_id)) as db:
        db.add(Membership(merchant_id=uuid.UUID(seller.merchant_id), user_id=uuid.UUID(uid), role="staff"))
    r = client.post(f"{API}/posts/{post['id']}/approve", headers=staff.h(merchant=seller.merchant_id))
    assert r.status_code == 403 and r.json()["error"]["details"]["permission"] == "content.approve"
    assert _act(client, seller, post["id"], "approve").json()["status"] == "approved"


def test_smart_mode_auto_approves_clean_ai_posts_but_not_flagged_ones(client, seller):
    from app.domains.ai.providers.sandbox import SandboxAdapter

    client.patch("/api/v1/merchant", headers=seller.h(), json={"automation_mode": "smart"})
    c = connect(client, seller)
    SandboxAdapter.override_data["sandbox-text"] = DRAFT
    clean = _run(client, seller, [upload(client, seller, phone_photo())["id"]])
    SandboxAdapter.override_data["sandbox-text"] = {
        **DRAFT,
        "captions": {**DRAFT["captions"], "instagram": "Only Rs 999!"},
    }
    flagged = _run(client, seller, [upload(client, seller, phone_photo())["id"]])
    p1 = client.post(
        f"{API}/posts/from-studio",
        headers=seller.h(),
        json={"job_id": clean["id"], "connection_ids": [c["id"]]},
    ).json()["items"][0]
    p2 = client.post(
        f"{API}/posts/from-studio",
        headers=seller.h(),
        json={"job_id": flagged["id"], "connection_ids": [c["id"]]},
    ).json()["items"][0]
    assert p2["issues"][0]["kind"] == "unsupported_claim:price"
    assert _act(client, seller, p1["id"], "submit").json()["status"] == "approved"
    assert _act(client, seller, p2["id"], "submit").json()["status"] == "pending_approval"


def test_edit_rules_and_state_machine(client, seller):
    c = connect(client, seller)
    p = _post(client, seller, c["id"])
    r = _act(client, seller, p["id"], "approve")
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_state_transition"
    _act(client, seller, p["id"], "submit")
    edited = client.patch(
        f"{API}/posts/{p['id']}", headers=seller.h(), json={"caption": "Updated caption"}
    ).json()
    assert edited["status"] == "draft"  # edits after approval require re-approval
    _act(client, seller, p["id"], "submit")
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    assert _act(client, seller, p["id"], "schedule", at=past).json()["error"]["code"] == "schedule_in_past"
    far = (datetime.now(UTC) + timedelta(days=120)).isoformat()
    assert _act(client, seller, p["id"], "schedule", at=far).json()["error"]["code"] == "schedule_too_far"
    _act(client, seller, p["id"], "schedule", at=(datetime.now(UTC) + timedelta(days=1)).isoformat())
    r = client.patch(f"{API}/posts/{p['id']}", headers=seller.h(), json={"caption": "x"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "post_locked"
    assert _act(client, seller, p["id"], "unschedule").json()["status"] == "approved"
    assert _act(client, seller, p["id"], "cancel").json()["status"] == "cancelled"


def test_validation(client, seller):
    c = connect(client, seller)
    r = client.post(
        f"{API}/posts", headers=seller.h(), json={"connection_id": c["id"], "caption": "x" * 2300}
    )
    assert r.json()["error"]["code"] == "caption_too_long"
    r = client.post(
        f"{API}/posts", headers=seller.h(), json={"connection_id": c["id"], "caption": "hi", "kind": "story"}
    )
    assert r.json()["error"]["code"] == "media_required"


def test_transient_failures_retry_then_fail_into_exception_event(client, seller):
    c = connect(client, seller)
    p = _post(client, seller, c["id"])
    _act(client, seller, p["id"], "submit")
    _act(client, seller, p["id"], "schedule")
    SandboxChannelAdapter.failures.push(IntegrationError("rate_limited", retryable=True), times=10)
    assert _tick() == {"published": 0, "retrying": 1, "failed": 0}
    for _ in range(4):
        with session_scope() as db:
            db.execute(update(ContentPost).values(next_attempt_at=utcnow()))
        _tick()
    SandboxChannelAdapter.failures.clear()
    post = client.get(f"{API}/posts", headers=seller.h()).json()["items"][0]
    assert post["status"] == "failed" and post["attempts"] == 5 and post["last_error_code"] == "rate_limited"
    with session_scope() as db:
        assert db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "content.publish_failed"))
    assert _act(client, seller, p["id"], "schedule").json()["status"] == "scheduled"  # seller can retry
    assert _tick()["published"] == 1


def test_revoked_channel_fails_post_and_blocks_scheduling(client, seller):
    c = connect(client, seller)
    p1, p2 = _post(client, seller, c["id"]), _post(client, seller, c["id"])
    for p in (p1, p2):
        _act(client, seller, p["id"], "submit")
    _act(client, seller, p1["id"], "schedule")
    SandboxChannelAdapter.failures.push(IntegrationError("token_revoked", auth=True))
    assert _tick()["failed"] == 1
    assert client.get("/api/v1/channels", headers=seller.h()).json()["items"][0]["status"] == "expired"
    r = _act(client, seller, p2["id"], "schedule")
    assert r.status_code == 409 and r.json()["error"]["code"] == "reconnect_required"


def test_content_is_tenant_scoped(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    b = onboard(client, shop="Patan Crafts")
    ca = connect(client, a)
    p = _post(client, a, ca["id"])
    assert client.get(f"{API}/posts", headers=b.h()).json()["items"] == []
    assert client.post(f"{API}/posts/{p['id']}/submit", headers=b.h()).status_code == 404
    r = client.post(f"{API}/posts", headers=b.h(), json={"connection_id": ca["id"], "caption": "x"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "connection_not_found"


def test_get_single_post_and_exception_links_connection(client, seller):
    c = connect(client, seller)
    p = _post(client, seller, c["id"])
    got = client.get(f"{API}/posts/{p['id']}", headers=seller.h())
    assert got.status_code == 200 and got.json()["id"] == p["id"]
    _act(client, seller, p["id"], "submit")
    _act(client, seller, p["id"], "schedule")
    SandboxChannelAdapter.failures.push(IntegrationError("token_revoked", auth=True))
    _tick()
    items = client.get("/api/v1/exceptions", headers=seller.h()).json()["items"]
    post_item = next(i for i in items if i["resource"]["type"] == "content_post")
    assert post_item["action"] == "reconnect" and post_item["details"]["connection_id"] == c["id"]
