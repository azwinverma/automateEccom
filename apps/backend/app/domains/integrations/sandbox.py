"""Sandbox adapters for local development and tests. They are NOT production integrations: they are
marked ``is_sandbox`` and the registry refuses them in production. Real adapters (Meta, TikTok,
Shopify, WooCommerce, Nepal payment gateways, Nepal couriers) need credentials/approvals listed in
docs/KNOWN_GAPS.md."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import structlog

from app.domains.integrations.base import (
    Address,
    ChannelAdapter,
    ChannelCapability,
    CourierAdapter,
    CourierCapability,
    ExternalLine,
    ExternalOrder,
    IntegrationError,
    Money,
    NormalizedWebhook,
    NotificationAdapter,
    OAuthTokens,
    PaymentAdapter,
    PaymentCapability,
    PaymentIntentResult,
    PaymentStatus,
    RateQuote,
    RemoteListing,
    ShipmentResult,
)

log = structlog.get_logger(__name__)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class _HmacWebhookMixin:
    _credentials: dict[str, str]
    code: ClassVar[str]

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        secret = self._credentials.get("webhook_secret", "")
        sig = {k.lower(): v for k, v in headers.items()}.get("x-sandbox-signature", "")
        return bool(secret) and hmac.compare_digest(_sign(secret, body), sig)

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> list[NormalizedWebhook]:
        doc = json.loads(body)
        return [
            NormalizedWebhook(
                provider=self.code,
                external_event_id=str(doc["id"]),
                event_type=str(doc["type"]),
                occurred_at=None,
                payload=doc.get("data", {}),
            )
        ]


class _ScriptedFailures:
    """Test hook: queue IntegrationErrors to be raised by the next sandbox calls."""

    def __init__(self) -> None:
        self._q: deque[IntegrationError] = deque()
        self._lock = threading.Lock()

    def push(self, err: IntegrationError, times: int = 1) -> None:
        with self._lock:
            self._q.extend([err] * times)

    def pop(self) -> IntegrationError | None:
        with self._lock:
            return self._q.popleft() if self._q else None

    def clear(self) -> None:
        with self._lock:
            self._q.clear()


class SandboxChannelAdapter(_HmacWebhookMixin, ChannelAdapter):
    """A fake social/marketplace channel with real OAuth semantics (consent, expiring access tokens,
    refresh, revocation) so every connection/publish path can be exercised without a live platform."""

    code = "sandbox_channel"
    display_name = "Sandbox channel"
    is_sandbox = True
    capabilities = frozenset(
        {
            ChannelCapability.PRODUCT_LISTING,
            ChannelCapability.INVENTORY_SYNC,
            ChannelCapability.CONTENT_PUBLISH,
            ChannelCapability.MESSAGES,
            ChannelCapability.ORDERS,
        }
    )
    SCOPES: ClassVar[list[str]] = ["catalog.write", "content.publish", "messages.read"]
    TOKEN_TTL: ClassVar[timedelta] = timedelta(hours=1)
    failures: ClassVar[_ScriptedFailures] = _ScriptedFailures()
    revoked_refresh_tokens: ClassVar[set[str]] = set()
    published: ClassVar[dict[str, dict[str, Any]]] = {}
    stock: ClassVar[dict[str, int]] = {}  # sku → quantity last pushed by stock sync

    def _fail(self) -> None:
        err = self.failures.pop()
        if err is not None:
            raise err

    def _tokens(self, account: str) -> OAuthTokens:
        return OAuthTokens(
            access_token=f"sbx-at-{secrets.token_hex(8)}",
            refresh_token=f"sbx-rt-{secrets.token_hex(8)}",
            expires_at=datetime.now(UTC) + self.TOKEN_TTL,
            scopes=list(self.SCOPES),
            external_account_id=account,
        )

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        from urllib.parse import urlencode

        from app.core.config import get_settings

        base = get_settings().public_api_base_url.rstrip("/")
        query = urlencode({"state": state, "redirect_uri": redirect_uri})
        return f"{base}/_dev/channels/sandbox/authorize?{query}"

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        self._fail()
        if not code.startswith("sbx-code-"):
            raise IntegrationError("oauth_code_invalid", "sandbox")
        return self._tokens(f"sbx-acct-{code.removeprefix('sbx-code-')[:12]}")

    def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        self._fail()
        if refresh_token in self.revoked_refresh_tokens:
            raise IntegrationError("invalid_grant", "refresh token revoked", auth=True)
        return self._tokens(self.config.get("external_account_id", "sbx-acct"))

    def health_check(self) -> bool:
        self._fail()
        return self._credentials.get("access_token", "").startswith("sbx-at-")

    def publish_listing(
        self, listing: dict[str, Any], idempotency_key: str, external_id: str | None = None
    ) -> str:
        self._require(ChannelCapability.PRODUCT_LISTING)
        self._fail()
        ext = (
            external_id
            or "sbx-listing-" + hashlib.sha256(idempotency_key.split(":v")[0].encode()).hexdigest()[:10]
        )
        self.published[ext] = listing
        return ext

    def unpublish_listing(self, external_id: str, idempotency_key: str) -> None:
        self._fail()
        self.published.pop(external_id, None)

    def fetch_listings(self, external_ids: list[str]) -> dict[str, RemoteListing]:
        self._fail()
        out = {}
        for ext in external_ids:
            doc = self.published.get(ext)
            if doc is None:
                continue
            out[ext] = RemoteListing(
                external_id=ext,
                visible=doc.get("_visible", True),
                prices={v["sku"]: v["price_minor"] for v in doc.get("variants", []) if v.get("sku")},
                stock={v["sku"]: self.stock.get(v["sku"]) for v in doc.get("variants", []) if v.get("sku")},
            )
        return out

    def update_inventory(self, external_sku: str, available: int, idempotency_key: str) -> None:
        self._fail()
        self.stock[external_sku] = available

    def publish_content(self, content: dict[str, Any], idempotency_key: str) -> str:
        self._require(ChannelCapability.CONTENT_PUBLISH)
        self._fail()
        return "sbx-post-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        self._fail()
        return "sbx-msg-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]

    orders: ClassVar[list[dict[str, Any]]] = []  # what fetch_orders returns (tests append raw orders)

    def fetch_orders(self, since: datetime) -> list[dict[str, Any]]:
        self._fail()
        return list(self.orders)

    def normalize_order(self, raw: dict[str, Any]) -> ExternalOrder | None:
        """Sandbox orders already use Nivaro's status words; amounts are minor units."""
        if raw.get("status") == "draft":
            return None
        cust = raw.get("customer") or {}
        return ExternalOrder(
            external_id=str(raw["id"]),
            number=str(raw.get("number") or raw["id"]),
            status=str(raw.get("status", "confirmed")),
            currency=str(raw.get("currency", "NPR")),
            customer_name=str(cust.get("name") or "Customer"),
            customer_phone=cust.get("phone"),
            customer_email=cust.get("email"),
            customer_external_id=str(cust["id"]) if cust.get("id") else None,
            address_text=raw.get("address"),
            district_hint=raw.get("district"),
            lines=[
                ExternalLine(
                    sku=li.get("sku"),
                    title=li.get("title", "Item"),
                    quantity=int(li.get("quantity", 1)),
                    unit_price_minor=int(li.get("price_minor", 0)),
                )
                for li in raw.get("lines", [])
            ],
            delivery_fee_minor=int(raw.get("delivery_fee_minor", 0)),
            payment_method=raw.get("payment_method", "cod"),
            paid=bool(raw.get("paid")),
            raw_status=raw.get("status"),
        )

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> list[NormalizedWebhook]:
        doc = json.loads(body)
        return [
            NormalizedWebhook(
                provider=self.code,
                external_event_id=str(doc["id"]),
                event_type=str(doc["type"]),
                occurred_at=None,
                payload=doc.get("data", {}),
                external_account_id=doc.get("account_id"),
            )
        ]


class SandboxPaymentAdapter(_HmacWebhookMixin, PaymentAdapter):
    """Simulates a redirect-checkout wallet. Amounts ending in 13 minor units fail (failure testing)."""

    code = "sandbox_wallet"
    display_name = "Sandbox wallet"
    is_sandbox = True
    capabilities = frozenset(
        {
            PaymentCapability.REDIRECT_CHECKOUT,
            PaymentCapability.REFUND,
            PaymentCapability.PARTIAL_REFUND,
            PaymentCapability.WEBHOOKS,
        }
    )

    def create_payment(
        self, amount: Money, reference: str, return_url: str | None, idempotency_key: str
    ) -> PaymentIntentResult:
        pid = "sbx-pay-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]
        return PaymentIntentResult(
            pid, PaymentStatus.PENDING, redirect_url=f"https://sandbox.invalid/pay/{pid}"
        )

    def verify_payment(self, provider_payment_id: str, expected: Money) -> PaymentIntentResult:
        status = PaymentStatus.FAILED if expected.amount_minor % 100 == 13 else PaymentStatus.CAPTURED
        return PaymentIntentResult(provider_payment_id, status, raw_status=status.value)

    def refund(self, provider_payment_id: str, amount: Money, idempotency_key: str) -> str:
        return "sbx-ref-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]

    def get_status(self, provider_payment_id: str) -> PaymentIntentResult:
        return PaymentIntentResult(provider_payment_id, PaymentStatus.CAPTURED)


class CashOnDeliveryAdapter(PaymentAdapter):
    """COD is a first-class payment method, not a provider integration; settlement comes from couriers."""

    code = "cod"
    display_name = "Cash on delivery"
    capabilities = frozenset({PaymentCapability.COD})

    def create_payment(
        self, amount: Money, reference: str, return_url: str | None, idempotency_key: str
    ) -> PaymentIntentResult:
        return PaymentIntentResult(f"cod-{reference}", PaymentStatus.PENDING, raw_status="cod_requested")

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        return False  # COD has no inbound webhooks


class SandboxCourierAdapter(_HmacWebhookMixin, CourierAdapter):
    code = "sandbox_courier"
    display_name = "Sandbox courier"
    is_sandbox = True
    capabilities = frozenset(
        {
            CourierCapability.RATES,
            CourierCapability.CREATE_SHIPMENT,
            CourierCapability.LABEL,
            CourierCapability.TRACKING,
            CourierCapability.CANCEL,
            CourierCapability.COD_COLLECTION,
        }
    )
    INSIDE_VALLEY = frozenset({"kathmandu", "lalitpur", "bhaktapur"})

    def get_rates(
        self, origin: Address, destination: Address, weight_grams: int, cod_amount: Money | None
    ) -> list[RateQuote]:
        inside = destination.city.strip().lower() in self.INSIDE_VALLEY
        base = 10000 if inside else 17500  # NPR 100 / 175 in paisa — sandbox values, not real tariffs
        extra = max(0, (weight_grams - 1000 + 999) // 1000) * 5000
        return [
            RateQuote("standard", Money(base + extra, "NPR"), 1 if inside else 3, 2 if inside else 5, True)
        ]

    def create_shipment(
        self,
        origin: Address,
        destination: Address,
        weight_grams: int,
        cod_amount: Money | None,
        reference: str,
        idempotency_key: str,
    ) -> ShipmentResult:
        sid = "sbx-shp-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]
        return ShipmentResult(sid, sid.upper()[-10:], None, "created")

    def track(self, tracking_number: str) -> list[dict[str, Any]]:
        return [{"status": "created", "at": datetime.now(UTC).isoformat()}]

    def cancel(self, provider_shipment_id: str, idempotency_key: str) -> None:
        return None


class ConsoleEmailAdapter(NotificationAdapter):
    """Dev mailer: logs that an email was sent (subject + recipient domain), writes the body to the
    local dev mailbox directory. Bodies may contain one-time links, so they never go to logs."""

    code = "console_email"
    is_sandbox = True

    def __init__(self, mailbox_dir: Any = None) -> None:
        from app.core.config import REPO_ROOT

        self.mailbox_dir = mailbox_dir or (REPO_ROOT / ".data" / "mailbox")

    def send_email(
        self, to: str, subject: str, text: str, *, idempotency_key: str, locale: str = "en"
    ) -> None:
        self.mailbox_dir.mkdir(parents=True, exist_ok=True)
        path = self.mailbox_dir / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}.txt"
        from app.core.config import get_settings

        st = get_settings()
        sender = f"{st.email_from_name} <{st.email_from_address}>"
        path.write_text(f"From: {sender}\nTo: {to}\nSubject: {subject}\nLocale: {locale}\n\n{text}\n")
        log.info("email_sent_dev", to_domain=to.split("@")[-1], subject=subject, file=path.name)
