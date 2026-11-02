from __future__ import annotations

import threading
import uuid

import pytest
from sqlalchemy import func, select

from app.core.db import session_scope
from app.core.errors import FeatureNotInPlan, UsageLimitReached
from app.domains.billing.models import EntitlementOverride, UsageEvent
from app.domains.billing.service import entitlements, window
from app.domains.platform.models import OutboxEvent
from tests.conftest import onboard, set_plan


def _mid(s) -> uuid.UUID:
    return uuid.UUID(s.merchant_id)


def test_feature_gating_is_data_driven(client, seller):
    with session_scope() as db:
        with pytest.raises(FeatureNotInPlan):
            entitlements.require_feature(db, _mid(seller), "video.premium")
    set_plan(seller.merchant_id, "growth")
    with session_scope() as db:
        entitlements.require_feature(db, _mid(seller), "video.premium")
        # Admin override can turn a feature off for one merchant without touching the plan.
        db.add(
            EntitlementOverride(
                merchant_id=_mid(seller),
                feature_code="video.premium",
                enabled=False,
                reason="chargeback review",
            )
        )
    with session_scope() as db:
        with pytest.raises(FeatureNotInPlan):
            entitlements.require_feature(db, _mid(seller), "video.premium")


def test_reserve_finalize_release_accounting(client, seller):
    m = _mid(seller)
    with session_scope() as db:
        r1 = entitlements.reserve(db, m, "ai_text_generations", 5, "k1")
        r2 = entitlements.reserve(db, m, "ai_text_generations", 3, "k2")
        assert entitlements.reserve(db, m, "ai_text_generations", 5, "k1").id == r1.id  # idempotent
    with session_scope() as db:
        entitlements.finalize(db, r1.id, actual_quantity=4)
        entitlements.finalize(db, r1.id)  # idempotent
        entitlements.release(db, r2.id)
    with session_scope() as db:
        row = next(x for x in entitlements.usage_summary(db, m) if x["resource"] == "ai_text_generations")
        assert row["used"] == 4 and row["reserved"] == 0
        assert db.scalar(select(func.count()).select_from(UsageEvent)) == 1


def test_premium_video_daily_burst_and_monthly_quota(client, seller):
    set_plan(seller.merchant_id, "growth")  # 20/month, max 4/day (specs/08)
    m = _mid(seller)
    with session_scope() as db:
        for i in range(4):
            entitlements.record(db, m, "premium_video_clips", 1, f"v{i}")
    with session_scope() as db, pytest.raises(UsageLimitReached) as e:
        entitlements.reserve(db, m, "premium_video_clips", 1, "v5")
    assert e.value.details["period"] == "day"
    assert "wait_for_renewal" in e.value.details["options"]


def test_monthly_overrun_uses_credits_when_policy_allows(client, seller):
    m = _mid(seller)  # starter: ai_images 30/month, policy credits, 4 credits/unit
    with session_scope() as db:
        entitlements.record(db, m, "ai_images", 30, "fill")
    with session_scope() as db, pytest.raises(UsageLimitReached) as e:
        entitlements.reserve(db, m, "ai_images", 1, "over-1")
    assert e.value.details["credits_needed"] == 4 and e.value.details["options"][0] == "buy_credits"
    with session_scope() as db:
        entitlements.grant_credits(db, m, 10, "grant-1", kind="purchase")
    with session_scope() as db:
        r = entitlements.reserve(db, m, "ai_images", 2, "over-2")
        assert r.funding == "credits" and entitlements.balance(db, m) == 2
    with session_scope() as db:
        entitlements.finalize(db, r.id, actual_quantity=1)  # partial: refund unused hold
        assert entitlements.balance(db, m) == 6


def test_usage_alerts_emitted_once_per_threshold(client, seller):
    m = _mid(seller)  # starter: ai_text 300/month
    with session_scope() as db:
        entitlements.record(db, m, "ai_text_generations", 215, "a")  # 71.6%
        entitlements.record(db, m, "ai_text_generations", 1, "b")
        entitlements.record(db, m, "ai_text_generations", 45, "c")  # 87%
    with session_scope() as db:
        evs = db.scalars(
            select(OutboxEvent).where(OutboxEvent.event_type == "billing.usage_threshold_reached")
        ).all()
        assert sorted(e.payload["threshold"] for e in evs) == [70, 85]


def test_resource_missing_from_plan_is_denied_by_default(client, seller):
    with session_scope() as db, pytest.raises(UsageLimitReached):
        entitlements.reserve(db, _mid(seller), "not_a_resource", 1, "x")


def test_concurrent_reservations_never_exceed_limit(client):
    s = onboard(client, shop="Flash Sale Store")
    set_plan(s.merchant_id, "growth")
    m = _mid(s)
    ok, blocked = [], []

    def worker(i: int) -> None:
        try:
            with session_scope() as db:
                entitlements.reserve(db, m, "premium_video_clips", 1, f"race-{i}")
            ok.append(i)
        except UsageLimitReached:
            blocked.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 4 and len(blocked) == 8  # daily burst 4


def test_window_month_rolls_forward_without_renewal_job():
    from datetime import UTC, datetime

    class Sub:
        current_period_start = datetime(2026, 1, 31, 10, tzinfo=UTC)

    start, end = window("month", datetime(2026, 3, 5, tzinfo=UTC), Sub(), "Asia/Kathmandu")  # type: ignore[arg-type]
    assert start == datetime(2026, 2, 28, 10, tzinfo=UTC) and end == datetime(2026, 3, 28, 10, tzinfo=UTC)
    d0, _d1 = window("day", datetime(2026, 3, 5, 20, 0, tzinfo=UTC), None, "Asia/Kathmandu")
    assert d0.isoformat() == "2026-03-05T18:15:00+00:00"  # local midnight NPT (UTC+5:45)


def test_usage_summary_reports_real_gauges_and_included_flag(client, seller):
    r = client.get("/api/v1/billing/entitlements", headers=seller.h()).json()
    by = {x["resource"]: x for x in r["limits"]}
    assert by["team_members"]["used"] == 1 and by["team_members"]["limit"] == 2
    assert by["stores"]["used"] == 1
    assert by["products"]["used"] == 0  # counted by the catalog domain
    assert by["channels"]["used"] == 0
    assert (
        by["automation_workflows"]["used"] is None
    )  # automation domain not built yet: "not counted", never a fake 0
    assert by["ai_inbox_replies"]["included"] is False and by["ai_text_generations"]["included"] is True
    client.post(
        "/api/v1/invitations", headers=seller.h(), json={"email": "packer@example.com", "role": "staff"}
    )
    by = {
        x["resource"]: x
        for x in client.get("/api/v1/billing/entitlements", headers=seller.h()).json()["limits"]
    }
    assert by["team_members"]["used"] == 2 and by["team_members"]["alert_level"] == "100"


def test_gauge_counters_are_tenant_scoped_without_bound_session(client):
    a = onboard(client, shop="Asan Bazaar Goods")
    onboard(client, shop="Patan Crafts")
    from app.domains.merchants.service import team_size

    with session_scope() as db:  # admin-style session, no tenant bound
        assert team_size(db, _mid(a)) == 1
