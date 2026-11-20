"""A seller's own payment gateways (Khalti, eSewa): sealed keys, verified payments, public checkout."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import select, text

from app.core.db import session_scope
from app.domains.payments import gateways
from app.domains.payments.models import PaymentGateway
from tests.test_payments import prepaid
from tests.test_returns import member

API = "/api/v1"
KHALTI_KEY = "test_secret_key_f59e8b7d18b4499ca40f68195a846e9b"
ESEWA_KEY = "esewa-test-secret-0042"


class FakeGateways:
    """Stands in for Khalti and eSewa over HTTP (httpx.MockTransport)."""

    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.khalti_status = "Completed"
        self.khalti_paid: int | None = None
        self.esewa_status = "COMPLETE"
        self.esewa_paid: str | None = None
        self.amounts: dict[str, int] = {}

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        host, path = req.url.host, req.url.path
        if "khalti" in host:
            if req.headers.get("authorization") != f"Key {KHALTI_KEY}":
                return httpx.Response(401, json={"detail": "Invalid token.", "status_code": 401})
            body = json.loads(req.content)
            if path.endswith("/epayment/initiate/"):
                pidx = "pidx-" + body["purchase_order_id"][-8:]
                self.amounts[pidx] = body["amount"]
                return httpx.Response(
                    200, json={"pidx": pidx, "payment_url": f"https://test-pay.khalti.com/?pidx={pidx}"}
                )
            if path.endswith("/epayment/lookup/"):
                pidx = body["pidx"]
                if pidx not in self.amounts:
                    return httpx.Response(400, json={"detail": "Not found.", "error_key": "validation_error"})
                paid = self.khalti_paid if self.khalti_paid is not None else self.amounts[pidx]
                return httpx.Response(
                    200, json={"pidx": pidx, "total_amount": paid, "status": self.khalti_status}
                )
        if "esewa" in host and path.endswith("/transaction/status/"):
            q = req.url.params
            return httpx.Response(
                200,
                json={
                    "product_code": q["product_code"],
                    "transaction_uuid": q["transaction_uuid"],
                    "total_amount": self.esewa_paid or q["total_amount"],
                    "status": self.esewa_status,
                    "ref_id": "0007ABC",
                },
            )
        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch):
    f = FakeGateways()
    monkeypatch.setattr(gateways, "_transport_override", httpx.MockTransport(f))
    return f


def connect(client, s, provider="khalti", key=KHALTI_KEY, **kw):
    body = {"provider": provider, "secret_key": key, "mode": "test", **kw}
    return client.post(f"{API}/payments/gateways", headers=s.h(), json=body)


def test_keys_are_sealed_never_returned_and_checked_with_the_gateway(client, seller, fake):
    r = connect(client, seller)
    assert r.status_code == 201, r.text
    g = r.json()
    assert g["verified"] is True and g["status"] == "active" and g["is_default"] is True
    assert g["secret_hint"] == "••••" + KHALTI_KEY[-4:]
    listed = client.get(f"{API}/payments/gateways", headers=seller.h()).text
    assert KHALTI_KEY not in listed and KHALTI_KEY not in r.text
    with session_scope() as db:
        raw = db.execute(
            text("select credentials_sealed from payment_gateways where id = :i"), {"i": g["id"]}
        ).scalar()
        audit_rows = (
            db.execute(text("select metadata::text from audit_logs where action like 'payments.gateway%'"))
            .scalars()
            .all()
        )
    assert raw and KHALTI_KEY not in raw  # encrypted at rest
    assert all(KHALTI_KEY not in (a or "") for a in audit_rows)
    # A wrong key is caught at once (Khalti answers 401).
    bad = connect(client, seller, key="test_secret_key_wrongwrongwrong").json()
    assert (
        bad["verified"] is False
        and bad["status"] == "error"
        and bad["last_error_code"] == "invalid_credentials"
    )
    fixed = connect(client, seller).json()
    assert fixed["id"] == g["id"] and fixed["status"] == "active"  # same gateway, keys replaced


def test_ciphertext_is_bound_to_its_shop(client, seller, fake):
    gid = connect(client, seller).json()["id"]
    with session_scope() as db:
        g = db.execute(
            select(PaymentGateway)
            .where(PaymentGateway.id == uuid.UUID(gid))
            .execution_options(skip_tenant_filter=True)
        ).scalar_one()
        assert gateways.adapter_for(g)._credentials["secret_key"] == KHALTI_KEY
        g.merchant_id = uuid.uuid4()  # same ciphertext, another shop: decryption must fail
        with pytest.raises(Exception):
            gateways.adapter_for(g)
        db.rollback()


def test_khalti_payment_is_confirmed_by_lookup_not_by_the_redirect(client, seller, fake):
    connect(client, seller)
    o = prepaid(client, seller)
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert p["provider"] == "khalti" and p["redirect_url"].startswith("https://test-pay.khalti.com/")
    init = next(c for c in fake.calls if c.url.path.endswith("/initiate/"))
    body = json.loads(init.content)
    assert body["amount"] == o["total"]["amount_minor"]  # paisa
    ret = urlparse(body["return_url"])
    assert ret.path == f"/pay/{p['id']}/return"
    # Customer comes back saying "Completed", but the gateway says Pending: nothing is marked paid.
    fake.khalti_status = "Pending"
    page = client.get(f"{ret.path}?{ret.query}&status=Completed&pidx=x")
    assert page.status_code == 200 and "processing" in page.text
    assert client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()["payment_status"] != "paid"
    fake.khalti_status = "Completed"
    page = client.get(f"{ret.path}?{ret.query}")
    assert "Payment received" in page.text and page.headers["content-security-policy"].startswith(
        "default-src 'none'"
    )
    order = client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()
    assert order["payment_status"] == "paid" and order["status"] == "ready_to_ship"
    gw = client.get(f"{API}/payments/gateways", headers=seller.h()).json()["items"][0]
    assert gw["last_payment_at"]


def test_khalti_short_payment_is_held_for_the_seller(client, seller, fake):
    connect(client, seller)
    o = prepaid(client, seller)
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    fake.khalti_paid = o["total"]["amount_minor"] - 10000
    assert (
        client.post(f"{API}/payments/{p['id']}/verify", headers=seller.h()).json()["status"] == "needs_review"
    )


def test_esewa_signed_form_and_status_check(client, seller, fake):
    r = connect(client, seller, provider="esewa", key=ESEWA_KEY, public_id="EPAYTEST")
    assert r.status_code == 201 and r.json()["verified"] is None  # only a real payment can prove eSewa keys
    o = prepaid(client, seller, price=150000, sku="ES-1")
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    link = urlparse(p["redirect_url"])
    assert link.path == f"/pay/{p['id']}"
    page = client.get(f"{link.path}?{link.query}")
    assert (
        page.status_code == 200 and 'action="https://rc-epay.esewa.com.np/api/epay/main/v2/form"' in page.text
    )
    fields = {k: v for k, v in __import__("re").findall(r'name="([^"]+)" value="([^"]*)"', page.text)}
    total = f"{o['total']['amount_minor'] / 100:.2f}"
    assert fields["total_amount"] == total and fields["product_code"] == "EPAYTEST"
    msg = f"total_amount={total},transaction_uuid={fields['transaction_uuid']},product_code=EPAYTEST"
    expected = base64.b64encode(hmac.new(ESEWA_KEY.encode(), msg.encode(), hashlib.sha256).digest()).decode()
    assert fields["signature"] == expected
    assert ESEWA_KEY not in page.text
    # A forged "success" redirect doesn't count; the status check does.
    fake.esewa_status = "NOT_FOUND"
    forged = base64.b64encode(
        json.dumps({"status": "COMPLETE", "signed_field_names": "status", "signature": "x"}).encode()
    ).decode()
    ret = urlparse(fields["success_url"])
    assert "processing" in client.get(f"{ret.path}?{ret.query}&data={forged}").text
    fake.esewa_status = "COMPLETE"
    assert "Payment received" in client.get(f"{ret.path}?{ret.query}").text
    assert client.get(f"{API}/orders/{o['id']}", headers=seller.h()).json()["payment_status"] == "paid"


def test_public_links_need_their_signature(client, seller, fake):
    connect(client, seller, provider="esewa", key=ESEWA_KEY, public_id="EPAYTEST")
    o = prepaid(client, seller, sku="ES-2")
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    assert client.get(f"/pay/{p['id']}?t=forged").status_code == 404
    assert client.get(f"/pay/{p['id']}/return").status_code == 404
    assert parse_qs(urlparse(p["redirect_url"]).query)["t"][0]


def test_only_owner_or_admin_manage_gateways_and_disconnect_destroys_keys(client, seller, fake):
    staff = member(client, seller, "staff", "staff-pg@example.com")
    manager = member(client, seller, "manager", "mgr-pg@example.com")
    assert connect(client, staff).status_code == 403
    assert connect(client, manager).status_code == 403
    assert client.get(f"{API}/payments/gateways", headers=manager.h()).status_code == 200
    gid = connect(client, seller).json()["id"]
    assert client.delete(f"{API}/payments/gateways/{gid}", headers=seller.h()).status_code == 204
    with session_scope() as db:
        assert (
            db.execute(
                text("select credentials_sealed from payment_gateways where id = :i"), {"i": gid}
            ).scalar()
            is None
        )
    assert client.get(f"{API}/payments/gateways", headers=seller.h()).json()["items"] == []


def test_gateway_payments_are_refunded_from_the_gateway_dashboard(client, seller, fake):
    connect(client, seller)
    o = prepaid(client, seller, sku="RF-1")
    p = client.post(f"{API}/orders/{o['id']}/payments/online", headers=seller.h(), json={}).json()
    client.post(f"{API}/payments/{p['id']}/verify", headers=seller.h())
    r = client.post(
        f"{API}/orders/{o['id']}/refunds",
        headers=seller.h(**{"Idempotency-Key": "refund-gw-0001"}),
        json={"amount_minor": 10000, "method": "original_payment"},
    )
    assert r.json()["error"]["code"] == "refund_via_gateway_dashboard", r.text
