"""Sandbox adapters for local development and tests. They are NOT production integrations: they are
marked ``is_sandbox`` and the registry refuses them in production. Real adapters (Meta, TikTok,
Shopify, WooCommerce, Nepal payment gateways, Nepal couriers) need credentials/approvals listed in
docs/KNOWN_GAPS.md."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

import structlog

from app.domains.integrations.base import (
    Address,
    ChannelAdapter,
    ChannelCapability,
    CourierAdapter,
    CourierCapability,
    Money,
    NormalizedWebhook,
    NotificationAdapter,
    PaymentAdapter,
    PaymentCapability,
    PaymentIntentResult,
    PaymentStatus,
    RateQuote,
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


class SandboxChannelAdapter(_HmacWebhookMixin, ChannelAdapter):
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

    def publish_listing(self, listing: dict[str, Any], idempotency_key: str) -> str:
        return "sbx-listing-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]

    def update_inventory(self, external_sku: str, available: int, idempotency_key: str) -> None:
        return None

    def publish_content(self, content: dict[str, Any], idempotency_key: str) -> str:
        return "sbx-post-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        return "sbx-msg-" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]

    def fetch_orders(self, since: datetime) -> list[dict[str, Any]]:
        return []


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
        path.write_text(f"To: {to}\nSubject: {subject}\nLocale: {locale}\n\n{text}\n")
        log.info("email_sent_dev", to_domain=to.split("@")[-1], subject=subject, file=path.name)
