"""Integration adapter framework (CHN-001/002, PAY-001, FUL-001, FND-006).

All third-party platforms are reached through these interfaces. Each adapter declares capabilities;
callers (and the UI, via the API) must check ``supports()`` instead of assuming a provider can do
everything. Default method bodies raise CapabilityNotSupported.

Money is always integer minor units + ISO currency. Every mutating call takes an idempotency key that
adapters forward to providers that support one, and that our own ledger uses to dedupe otherwise.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar


class ChannelCapability(StrEnum):
    PRODUCT_LISTING = "product_listing"
    INVENTORY_SYNC = "inventory_sync"
    CONTENT_PUBLISH = "content_publish"
    MESSAGES = "messages"
    ORDERS = "orders"
    RETURNS = "returns"
    REFUNDS = "refunds"
    FULFILLMENT = "fulfillment"


class PaymentCapability(StrEnum):
    PAYMENT_LINK = "payment_link"
    REDIRECT_CHECKOUT = "redirect_checkout"
    CAPTURE = "capture"
    REFUND = "refund"
    PARTIAL_REFUND = "partial_refund"
    WEBHOOKS = "webhooks"
    COD = "cod"


class CourierCapability(StrEnum):
    RATES = "rates"
    CREATE_SHIPMENT = "create_shipment"
    LABEL = "label"
    PICKUP = "pickup"
    TRACKING = "tracking"
    CANCEL = "cancel"
    COD_COLLECTION = "cod_collection"
    WEBHOOKS = "webhooks"


class IntegrationError(Exception):
    """``auth`` = credentials rejected (token expired/revoked): the connection needs the seller to
    reconnect. ``retryable`` = transient (timeouts, 429, 5xx)."""

    def __init__(self, code: str, message: str = "", *, retryable: bool = False, auth: bool = False) -> None:
        super().__init__(f"{code}: {message}"[:500])
        self.code = code
        self.retryable = retryable
        self.auth = auth


class CapabilityNotSupported(IntegrationError):
    def __init__(self, provider: str, capability: str) -> None:
        super().__init__("capability_not_supported", f"{provider} does not support {capability}")


class WebhookVerificationFailed(IntegrationError):
    def __init__(self, provider: str) -> None:
        super().__init__("webhook_signature_invalid", provider)


@dataclass(frozen=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if len(self.currency) != 3:
            raise ValueError("currency must be ISO-4217")


@dataclass(frozen=True)
class NormalizedWebhook:
    """Provider webhook normalized for the webhook gateway (CHN-010)."""

    provider: str
    external_event_id: str  # dedupe key
    event_type: str
    occurred_at: datetime | None
    payload: dict[str, Any]
    external_account_id: str | None = None  # routes the event to a merchant's connection


class Adapter(ABC):
    code: ClassVar[str]
    display_name: ClassVar[str]
    is_sandbox: ClassVar[bool] = False
    capabilities: ClassVar[frozenset[StrEnum]] = frozenset()

    def __init__(
        self, credentials: dict[str, str] | None = None, config: dict[str, Any] | None = None
    ) -> None:
        self._credentials = credentials or {}
        self.config = config or {}

    def __repr__(self) -> str:
        return f"<{type(self).__name__} code={self.code}>"

    def supports(self, capability: StrEnum) -> bool:
        return capability in self.capabilities

    def _require(self, capability: StrEnum) -> None:
        if capability not in self.capabilities:
            raise CapabilityNotSupported(self.code, capability.value)

    @abstractmethod
    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool: ...

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> list[NormalizedWebhook]:
        raise IntegrationError("not_implemented", f"{self.code} webhook parsing")


# ----------------------------------------------------------------------------- channels
@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str] = field(default_factory=list)
    external_account_id: str | None = None


class ChannelAdapter(Adapter):
    # Which generated caption style suits this channel (instagram | facebook | tiktok | marketplace).
    caption_style: ClassVar[str] = "instagram"
    auth_kind: ClassVar[str] = "oauth"  # oauth | api_keys
    max_caption_chars: ClassVar[int] = 2200

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        raise IntegrationError("not_implemented", "oauth")

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        raise IntegrationError("not_implemented", "oauth")

    def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        raise IntegrationError("not_implemented", "oauth refresh")

    def health_check(self) -> bool:
        """Cheap authenticated call proving the stored token still works."""
        raise IntegrationError("not_implemented", "health check")

    def publish_listing(
        self, listing: dict[str, Any], idempotency_key: str, external_id: str | None = None
    ) -> str:
        """Create or update the listing; returns the provider's listing id."""
        self._require(ChannelCapability.PRODUCT_LISTING)
        raise NotImplementedError

    def unpublish_listing(self, external_id: str, idempotency_key: str) -> None:
        self._require(ChannelCapability.PRODUCT_LISTING)
        raise NotImplementedError

    def update_inventory(self, external_sku: str, available: int, idempotency_key: str) -> None:
        self._require(ChannelCapability.INVENTORY_SYNC)
        raise NotImplementedError

    def publish_content(self, content: dict[str, Any], idempotency_key: str) -> str:
        self._require(ChannelCapability.CONTENT_PUBLISH)
        raise NotImplementedError

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        self._require(ChannelCapability.MESSAGES)
        raise NotImplementedError

    def fetch_orders(self, since: datetime) -> list[dict[str, Any]]:
        self._require(ChannelCapability.ORDERS)
        raise NotImplementedError


# ----------------------------------------------------------------------------- payments
class PaymentStatus(StrEnum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class PaymentIntentResult:
    provider_payment_id: str
    status: PaymentStatus
    redirect_url: str | None = None
    raw_status: str | None = None


class PaymentAdapter(Adapter):
    """Never trust a client redirect as payment confirmation: always verify server-side."""

    def create_payment(
        self, amount: Money, reference: str, return_url: str | None, idempotency_key: str
    ) -> PaymentIntentResult:
        raise CapabilityNotSupported(self.code, "create_payment")

    def verify_payment(self, provider_payment_id: str, expected: Money) -> PaymentIntentResult:
        raise CapabilityNotSupported(self.code, "verify_payment")

    def capture(self, provider_payment_id: str, amount: Money, idempotency_key: str) -> PaymentIntentResult:
        self._require(PaymentCapability.CAPTURE)
        raise NotImplementedError

    def refund(self, provider_payment_id: str, amount: Money, idempotency_key: str) -> str:
        self._require(PaymentCapability.REFUND)
        raise NotImplementedError

    def get_status(self, provider_payment_id: str) -> PaymentIntentResult:
        raise CapabilityNotSupported(self.code, "get_status")


# ----------------------------------------------------------------------------- couriers
@dataclass
class Address:
    name: str
    phone: str
    line1: str
    city: str
    district: str | None = None
    province: str | None = None
    area: str | None = None
    landmark: str | None = None
    country: str = "NP"


@dataclass
class RateQuote:
    service_code: str
    price: Money
    eta_days_min: int | None
    eta_days_max: int | None
    cod_supported: bool


@dataclass
class ShipmentResult:
    provider_shipment_id: str
    tracking_number: str
    label_url: str | None
    status: str


class CourierAdapter(Adapter):
    def get_rates(
        self, origin: Address, destination: Address, weight_grams: int, cod_amount: Money | None
    ) -> list[RateQuote]:
        self._require(CourierCapability.RATES)
        raise NotImplementedError

    def create_shipment(
        self,
        origin: Address,
        destination: Address,
        weight_grams: int,
        cod_amount: Money | None,
        reference: str,
        idempotency_key: str,
    ) -> ShipmentResult:
        self._require(CourierCapability.CREATE_SHIPMENT)
        raise NotImplementedError

    def track(self, tracking_number: str) -> list[dict[str, Any]]:
        self._require(CourierCapability.TRACKING)
        raise NotImplementedError

    def cancel(self, provider_shipment_id: str, idempotency_key: str) -> None:
        self._require(CourierCapability.CANCEL)
        raise NotImplementedError


# ----------------------------------------------------------------------------- notifications
class NotificationAdapter(ABC):
    code: ClassVar[str]
    is_sandbox: ClassVar[bool] = False

    @abstractmethod
    def send_email(
        self, to: str, subject: str, text: str, *, idempotency_key: str, locale: str = "en"
    ) -> None: ...
