"""PAY-002…005, 008, 009: verified online payments, webhooks, mismatch, failure, manual, COD trail."""

from __future__ import annotations

import hashlib
import hmac
import json

from app.domains.integrations.sandbox import SandboxPaymentAdapter
from tests.conftest import onboard
from tests.test_channels import _dispatch
from tests.test_orders import ADDR, item, move, order

API = "/api/v1"
SECRET = b"dev-sandbox-payment-secret"


def pay_webhook(client, payload):
    body = json.dumps(payload).encode()
    sig = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return client.post(
        "/webhooks/payments/sandbox_wallet",
        content=body,
        headers={"X-Sandbox-Signature": sig, "Content-Type": "application/json"},
    )


def prepaid(client, s, price=245000, sku="PRE-1"):
    _, vid = item(client, s, price=price, sku=sku)
    return order(client, s, vid, payment_method="prepaid").json()


def test_online_payment_counts_only_after_server_verification(client, seller):
    o = prepaid(client, seller)
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert p["status"] == "pending" and p["redirect_url"].startswith("https://sandbox.invalid/pay/")
    again = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert again["id"] == p["id"]  # same link on a double tap
    assert client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()["payment_status"] == "pending"
    # A forged webhook is rejected; a signed one only triggers verification with the provider.
    bad = client.post(
        "/webhooks/payments/sandbox_wallet", content=b"{}", headers={"X-Sandbox-Signature": "0" * 64}
    )
    assert bad.status_code == 401
    ev = {
        "id": "pevt-1",
        "type": "payment.succeeded",
        "data": {"payment_id": p["redirect_url"].rsplit("/", 1)[1]},
    }
    assert pay_webhook(client, ev).json()["accepted"] == 1
    assert pay_webhook(client, ev).json()["duplicates"] == 1
    _dispatch()
    d = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert d["payment_status"] == "paid" and d["status"] == "ready_to_ship"  # R1: paid → ready to ship
    tl = client.get(f"{API}/orders/{o['id']}/timeline", headers=seller.h()).json()["items"]
    paid_ev = next(e for e in tl if e["kind"] == "payment_recorded")
    assert paid_ev["provider"] == "sandbox_wallet" and tl[-1]["automated"] is True


def test_paid_amount_mismatch_is_held_for_the_seller(client, seller):
    o = prepaid(client, seller)
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    SandboxPaymentAdapter.paid_amounts[p["redirect_url"].rsplit("/", 1)[1]] = (
        100000  # customer paid Rs 1,000 of 2,450
    )
    v = client.post(f"{API}/payments/{p['id']}/verify", headers=seller.h()).json()
    assert (
        v["status"] == "needs_review" and v["failure_code"] == "amount_mismatch" and v["paid_minor"] == 100000
    )
    d = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert (
        d["payment_status"] != "paid"
        and d["needs_review"] == "payment_mismatch"
        and d["status"] == "payment_pending"
    )


def test_failed_payment_then_switch_to_cod(client, seller):
    o = prepaid(client, seller, price=245013)  # sandbox: amounts ending in 13 fail
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    v = client.post(f"{API}/payments/{p['id']}/verify", headers=seller.h()).json()
    assert v["status"] == "failed"
    d = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert d["payment_status"] == "failed" and d["status"] == "payment_pending"
    retry = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert retry["id"] != p["id"]  # a fresh attempt
    c = client.post(f"{API}/orders/{o['id']}/switch-to-cod", headers=seller.h()).json()
    assert (
        c["status"] == "cod_pending" and c["payment_method"] == "cod" and c["payment_status"] == "cod_pending"
    )
    pays = client.get(f"{API}/orders/{o['id']}/payments", headers=seller.h()).json()["items"]
    assert [x["status"] for x in pays] == ["failed", "cancelled"]


def test_manual_payment_recorded_once_and_must_match_total(client, seller):
    o = prepaid(client, seller)
    url = f"{API}/orders/{o['id']}/payments/manual"
    total = o["totals"]["total"]["amount_minor"]
    assert (
        client.post(url, headers=seller.h(), json={"amount_minor": total, "method": "esewa"}).json()["error"][
            "code"
        ]
        == "idempotency_key_required"
    )
    h = seller.h(**{"Idempotency-Key": "esewa-ref-77812"})
    wrong = client.post(url, headers=h, json={"amount_minor": total - 1, "method": "esewa"})
    assert wrong.status_code == 400 and wrong.json()["error"]["code"] == "amount_mismatch"
    a = client.post(url, headers=h, json={"amount_minor": total, "method": "esewa", "reference": "77812"})
    b = client.post(url, headers=h, json={"amount_minor": total, "method": "esewa", "reference": "77812"})
    assert a.status_code == 201 and a.json()["id"] == b.json()["id"]
    d = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert d["payment_status"] == "paid" and d["status"] == "ready_to_ship"


def test_cod_paid_in_advance_becomes_prepaid(client, seller):
    _, vid = item(client, seller)
    o = order(client, seller, vid).json()
    total = o["totals"]["total"]["amount_minor"]
    client.post(
        f"{API}/orders/{o['id']}/payments/manual",
        headers=seller.h(**{"Idempotency-Key": "bank-0001-x"}),
        json={"amount_minor": total, "method": "bank_transfer"},
    )
    d = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert (
        d["payment_method"] == "prepaid" and d["payment_status"] == "paid" and d["status"] == "ready_to_ship"
    )


def test_cod_record_follows_the_order_and_summary(client, seller):
    _, vid = item(client, seller)
    a = order(client, seller, vid).json()
    b = order(client, seller, vid, customer_phone="9800000001").json()
    _dispatch()
    s = client.get(f"{API}/payments/cod/summary", headers=seller.h()).json()
    assert (
        s["outstanding"]["count"] == 2
        and s["outstanding"]["amount_minor"] == a["totals"]["total"]["amount_minor"] * 2
    )
    for to in ("ready_to_ship", "shipped", "delivered"):
        move(client, seller, a["id"], to)
    move(client, seller, b["id"], "cancelled", reason="no answer on phone")
    _dispatch()
    s = client.get(f"{API}/payments/cod/summary", headers=seller.h()).json()
    assert s["outstanding"]["count"] == 0
    assert s["pending_settlement"] == {"count": 1, "amount_minor": a["totals"]["total"]["amount_minor"]}


def test_online_payment_refused_without_provider_and_for_cod(client, seller, monkeypatch):
    _, vid = item(client, seller)
    cod = order(client, seller, vid).json()
    assert (
        client.post(f"{API}/orders/{cod['id']}/payments/online", headers=seller.h(), json={}).json()["error"][
            "code"
        ]
        == "payment_not_expected"
    )
    from app.core.config import get_settings

    o = prepaid(client, seller)
    monkeypatch.setattr(get_settings(), "payment_provider", None)
    r = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "payment_provider_not_configured"


def test_payments_are_tenant_isolated(client, seller):
    other = onboard(client, shop="Patan Crafts")
    o = prepaid(client, seller)
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert client.post(f"{API}/payments/{p['id']}/verify", headers=other.h()).status_code == 404
    assert client.get(f"{API}/orders/{o['id']}/payments", headers=other.h()).status_code == 404
    assert (
        client.post(
            f"{API}/orders/{o['id']}/payments/manual",
            headers=other.h(**{"Idempotency-Key": "x-12345678"}),
            json={"amount_minor": 1, "method": "cash"},
        ).status_code
        == 404
    )
    assert ADDR  # shared fixture data in use
