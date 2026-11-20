"""Autopilot setup: the end-to-end selling checklist and one-click recommended automations."""

from __future__ import annotations

from tests.conftest import set_plan
from tests.test_returns import member

API = "/api/v1"


def _steps(body: dict) -> dict[str, dict]:
    return {s["key"]: s for s in body["steps"]}


def test_checklist_shows_what_is_missing_on_a_new_shop(client, seller):
    set_plan(seller.merchant_id, "growth")
    r = client.get(f"{API}/automation/setup", headers=seller.h())
    assert r.status_code == 200
    s = _steps(r.json())
    assert s["chat"]["state"] == "todo" and s["chat"]["action"] == "/settings/channels"
    assert s["payments"]["state"] == "partial"  # COD works, online needs a gateway
    assert s["posting"]["state"] == "blocked"  # no account that can post
    assert s["workflows"]["state"] == "todo" and len(s["workflows"]["workflows"]) == 5
    assert r.json()["done"] < r.json()["total"]


def test_apply_turns_on_the_recommended_set_once(client, seller):
    set_plan(seller.merchant_id, "growth")
    r = client.post(f"{API}/automation/setup/apply", headers=seller.h(), json={"mode": "autopilot"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert {"item": "autopilot", "reason": "plan"} in body["skipped"]  # Growth has no Autopilot mode
    assert "mode:smart" in body["changed"] and "campaign:win_back" in body["changed"]
    assert {"item": "posting", "reason": "no_account_can_post"} in body["skipped"]
    s = _steps(body)
    assert s["workflows"]["state"] == "done" and s["campaigns"]["state"] == "done"
    assert s["sales_agent"]["state"] == "done"
    wfs = client.get(f"{API}/automation/workflows", headers=seller.h()).json()["items"]
    assert sorted(w["template_code"] for w in wfs if w["status"] == "active") == sorted(
        [
            "book_courier_when_packed",
            "failed_delivery_followup",
            "review_request_after_delivery",
            "thank_first_order",
            "low_stock_alert",
        ]
    )
    # Applying again changes nothing and creates no duplicates.
    again = client.post(f"{API}/automation/setup/apply", headers=seller.h(), json={}).json()
    assert [c for c in again["changed"] if c.startswith("workflow:")] == []
    assert len(client.get(f"{API}/automation/workflows", headers=seller.h()).json()["items"]) == 5


def test_starter_plan_and_staff_are_handled(client, seller):
    set_plan(seller.merchant_id, "starter")
    body = client.post(f"{API}/automation/setup/apply", headers=seller.h(), json={}).json()
    assert {"item": "workflows", "reason": "plan"} in body["skipped"]
    assert {"item": "campaigns", "reason": "plan"} in body["skipped"]
    staff = member(client, seller, "staff", "staff-setup@example.com")
    assert client.post(f"{API}/automation/setup/apply", headers=staff.h(), json={}).status_code == 403
