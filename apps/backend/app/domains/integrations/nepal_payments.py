"""Nepal payment gateways a seller connects with their own merchant account: Khalti and eSewa.

Both are redirect checkouts. A customer's return to the shop is never trusted as proof of payment:
every payment is confirmed server-side (Khalti lookup, eSewa status check) and the amount compared.

- Khalti ePayment (KPG-2), docs.khalti.com/khalti-epayment: POST /epayment/initiate/ and
  /epayment/lookup/ with `Authorization: Key <secret>`; amounts in paisa.
- eSewa ePay v2: the customer's browser POSTs a signed form to eSewa (we serve that page); the
  signature is base64(HMAC-SHA256(secret, "total_amount=…,transaction_uuid=…,product_code=…"));
  amounts in rupees. eSewa's sandbox status-check host differs between sources, so both hosts are
  settings (COS_ESEWA_STATUS_URL_TEST / _LIVE) to confirm during merchant onboarding.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, ClassVar

import httpx

from app.core.config import get_settings
from app.domains.integrations.base import (
    IntegrationError,
    Money,
    PaymentAdapter,
    PaymentCapability,
    PaymentIntentResult,
    PaymentStatus,
)
from app.domains.integrations.http import ResilientClient


def _transport(config: dict[str, Any]) -> httpx.BaseTransport | None:
    t = config.get("_transport")  # tests inject an httpx.MockTransport
    return t if isinstance(t, httpx.BaseTransport) else None


def _rupees(minor: int) -> str:
    return str((Decimal(minor) / 100).quantize(Decimal("0.01")))


def _minor(rupees: object) -> int:
    return int((Decimal(str(rupees).replace(",", "")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class _RedirectGateway(PaymentAdapter):
    """Shared: per-merchant credentials, test/live mode, no webhooks (status is pulled)."""

    is_sandbox = False
    credential_fields: ClassVar[tuple[str, ...]] = ()
    config_fields: ClassVar[tuple[str, ...]] = ()

    @property
    def live(self) -> bool:
        return self.config.get("mode") == "live"

    def _secret(self) -> str:
        s = self._credentials.get("secret_key")
        if not s:
            raise IntegrationError("missing_credentials", self.code)
        return s

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        return False  # neither gateway pushes server-to-server notifications we rely on

    def checkout_form(
        self, provider_payment_id: str, amount: Money, return_url: str
    ) -> tuple[str, dict[str, str]] | None:
        """For gateways that need a browser form POST: (action URL, fields). None = plain redirect."""
        return None

    def check_credentials(self) -> bool | None:
        """True/False if the provider can tell us; None if credentials can only be proven by a payment."""
        return None


class KhaltiAdapter(_RedirectGateway):
    code = "khalti"
    display_name = "Khalti"
    capabilities = frozenset({PaymentCapability.REDIRECT_CHECKOUT})
    credential_fields = ("secret_key",)
    BASE: ClassVar[dict[bool, str]] = {
        False: "https://dev.khalti.com/api/v2/",
        True: "https://khalti.com/api/v2/",
    }
    MIN_MINOR = 1000  # Khalti refuses payments below Rs 10

    def _client(self) -> ResilientClient:
        return ResilientClient("khalti", base_url=self.BASE[self.live], transport=_transport(self.config))

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Key {self._secret()}", "Content-Type": "application/json"}

    def create_payment(
        self, amount: Money, reference: str, return_url: str | None, idempotency_key: str
    ) -> PaymentIntentResult:
        if amount.currency != "NPR":
            raise IntegrationError("unsupported_currency", self.code)
        if amount.amount_minor < self.MIN_MINOR:
            raise IntegrationError("amount_below_minimum", self.code)
        if not return_url:
            raise IntegrationError("return_url_required", self.code)
        body = {
            "return_url": return_url,
            "website_url": get_settings().public_web_base_url,
            "amount": amount.amount_minor,
            "purchase_order_id": idempotency_key[:100],
            "purchase_order_name": reference[:100],
        }
        r = self._client().request(
            "POST", "epayment/initiate/", operation="initiate", json=body, headers=self._headers()
        )
        if r.status_code == 401:
            raise IntegrationError("invalid_credentials", self.code)
        if r.status_code >= 400:
            raise IntegrationError("provider_rejected", self.code)
        data = r.json()
        return PaymentIntentResult(
            str(data["pidx"]), PaymentStatus.PENDING, redirect_url=str(data["payment_url"])
        )

    _STATUS: ClassVar[dict[str, PaymentStatus]] = {
        "Completed": PaymentStatus.CAPTURED,
        "Pending": PaymentStatus.PENDING,
        "Initiated": PaymentStatus.PENDING,
        "Refunded": PaymentStatus.REFUNDED,
        "Partially refunded": PaymentStatus.PARTIALLY_REFUNDED,
        "Partially Refunded": PaymentStatus.PARTIALLY_REFUNDED,
        "Expired": PaymentStatus.FAILED,
        "User canceled": PaymentStatus.CANCELLED,
        "Canceled": PaymentStatus.CANCELLED,
        "Failed": PaymentStatus.FAILED,
    }

    def verify_payment(self, provider_payment_id: str, expected: Money) -> PaymentIntentResult:
        r = self._client().request(
            "POST",
            "epayment/lookup/",
            operation="lookup",
            retry_unsafe=True,  # lookup is read-only
            json={"pidx": provider_payment_id},
            headers=self._headers(),
        )
        if r.status_code == 401:
            raise IntegrationError("invalid_credentials", self.code)
        data = r.json() if r.content else {}
        if r.status_code >= 400 and "status" not in data:
            raise IntegrationError("provider_rejected", self.code)
        raw = str(data.get("status", ""))
        # Anything Khalti doesn't document stays pending ("hold and contact Khalti").
        status = self._STATUS.get(raw, PaymentStatus.PENDING)
        amount = Money(int(data["total_amount"]), "NPR") if data.get("total_amount") is not None else None
        return PaymentIntentResult(provider_payment_id, status, raw_status=raw or None, amount=amount)

    def get_status(self, provider_payment_id: str) -> PaymentIntentResult:
        return self.verify_payment(provider_payment_id, Money(0, "NPR"))

    def check_credentials(self) -> bool | None:
        # A lookup of a made-up pidx: 401 means the key is wrong; "Not found" means Khalti accepted it.
        r = self._client().request(
            "POST",
            "epayment/lookup/",
            operation="check",
            retry_unsafe=True,
            json={"pidx": "nivaro-credential-check"},
            headers=self._headers(),
        )
        if r.status_code == 401:
            return False
        if r.status_code in (200, 400, 404):
            return True
        raise IntegrationError("provider_unavailable", self.code, retryable=True)


class EsewaAdapter(_RedirectGateway):
    code = "esewa"
    display_name = "eSewa"
    capabilities = frozenset({PaymentCapability.REDIRECT_CHECKOUT})
    credential_fields = ("secret_key",)
    config_fields = ("product_code",)
    FORM: ClassVar[dict[bool, str]] = {
        False: "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
        True: "https://epay.esewa.com.np/api/epay/main/v2/form",
    }
    SIGNED = ("total_amount", "transaction_uuid", "product_code")

    def _product_code(self) -> str:
        pc = str(self.config.get("product_code") or "")
        if not pc:
            raise IntegrationError("missing_credentials", self.code)
        return pc

    def sign(self, fields: dict[str, str], names: tuple[str, ...] | list[str]) -> str:
        msg = ",".join(f"{n}={fields[n]}" for n in names)
        return base64.b64encode(
            hmac.new(self._secret().encode(), msg.encode(), hashlib.sha256).digest()
        ).decode()

    def create_payment(
        self, amount: Money, reference: str, return_url: str | None, idempotency_key: str
    ) -> PaymentIntentResult:
        if amount.currency != "NPR":
            raise IntegrationError("unsupported_currency", self.code)
        self._product_code(), self._secret()  # fail at link time, not at the customer's checkout
        # transaction_uuid: alphanumeric and hyphen only, unique per attempt.
        tx = "nv-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
        return PaymentIntentResult(tx, PaymentStatus.PENDING, redirect_url=None)

    def checkout_form(
        self, provider_payment_id: str, amount: Money, return_url: str
    ) -> tuple[str, dict[str, str]]:
        total = _rupees(amount.amount_minor)
        sep = "&" if "?" in return_url else "?"
        fields = {
            "amount": total,
            "tax_amount": "0",
            "total_amount": total,
            "transaction_uuid": provider_payment_id,
            "product_code": self._product_code(),
            "product_service_charge": "0",
            "product_delivery_charge": "0",
            "success_url": f"{return_url}{sep}result=success",
            "failure_url": f"{return_url}{sep}result=failure",
            "signed_field_names": ",".join(self.SIGNED),
        }
        fields["signature"] = self.sign(fields, self.SIGNED)
        return self.FORM[self.live], fields

    def verify_return(self, data_b64: str) -> dict[str, Any] | None:
        """eSewa's success redirect carries base64 JSON signed over its own signed_field_names.
        A valid signature only says eSewa sent it; payment is still confirmed by the status check."""
        try:
            data = json.loads(base64.b64decode(data_b64, validate=True))
            names = str(data["signed_field_names"]).split(",")
            fields = {n: str(data[n]) for n in names}
        except (ValueError, KeyError, TypeError):
            return None
        return data if hmac.compare_digest(self.sign(fields, names), str(data.get("signature", ""))) else None

    _STATUS: ClassVar[dict[str, PaymentStatus]] = {
        "COMPLETE": PaymentStatus.CAPTURED,
        "PENDING": PaymentStatus.PENDING,
        "AMBIGUOUS": PaymentStatus.PENDING,  # hold; eSewa resolves it
        "NOT_FOUND": PaymentStatus.PENDING,  # customer hasn't paid (yet); link may still be used
        "CANCELED": PaymentStatus.CANCELLED,
        "FULL_REFUND": PaymentStatus.REFUNDED,
        "PARTIAL_REFUND": PaymentStatus.PARTIALLY_REFUNDED,
    }

    def verify_payment(self, provider_payment_id: str, expected: Money) -> PaymentIntentResult:
        s = get_settings()
        url = s.esewa_status_url_live if self.live else s.esewa_status_url_test
        client = ResilientClient("esewa", transport=_transport(self.config))
        r = client.request(
            "GET",
            url,
            operation="status",
            params={
                "product_code": self._product_code(),
                "total_amount": _rupees(expected.amount_minor),
                "transaction_uuid": provider_payment_id,
            },
        )
        if r.status_code >= 500:
            raise IntegrationError("provider_unavailable", self.code, retryable=True)
        data = r.json() if r.content else {}
        raw = str(data.get("status", "")).upper()
        status = self._STATUS.get(raw, PaymentStatus.PENDING)
        amount = (
            Money(_minor(data["total_amount"]), "NPR") if data.get("total_amount") not in (None, "") else None
        )
        return PaymentIntentResult(provider_payment_id, status, raw_status=raw or None, amount=amount)

    def get_status(self, provider_payment_id: str) -> PaymentIntentResult:
        raise IntegrationError("needs_amount", self.code)  # eSewa's status check needs the amount
