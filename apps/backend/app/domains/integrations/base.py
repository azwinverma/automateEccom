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
    CONTENT_METRICS = "content_metrics"  # CNT-013: views/engagement/clicks for published posts


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
    REATTEMPT = "reattempt"  # ask the courier to try delivering again (after a failed attempt)
    RETURN_TO_ORIGIN = "return_to_origin"
    COD_SETTLEMENT_REPORTS = "cod_settlement_reports"  # statements of cash collected, fetched by API
    MANUAL_UPDATES = "manual_updates"  # no API: the seller records tracking and statuses


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


@dataclass
class RemoteListing:
    """A listing as the provider currently has it (CHN-012 reconciliation).

    ``visible`` is False when the listing exists but is hidden/draft on the channel. ``prices`` and
    ``stock`` are keyed by SKU; a SKU absent from ``prices`` does not exist on the channel. ``stock``
    values are None when the channel doesn't manage stock for that SKU."""

    external_id: str
    visible: bool
    prices: dict[str, int] = field(default_factory=dict)
    stock: dict[str, int | None] = field(default_factory=dict)


# ----------------------------------------------------------------------------- channel orders (ORD-005)
@dataclass
class ExternalLine:
    sku: str | None
    title: str
    quantity: int
    unit_price_minor: int


@dataclass
class ExternalOrder:
    external_id: str
    number: str | None
    status: str  # Nivaro status vocabulary (the adapter maps the channel's own)
    currency: str
    customer_name: str
    customer_phone: str | None
    customer_email: str | None
    customer_external_id: str | None
    address_text: str | None
    district_hint: str | None
    lines: list[ExternalLine]
    delivery_fee_minor: int = 0
    discount_minor: int = 0
    payment_method: str = "cod"
    paid: bool = False
    placed_at: datetime | None = None
    raw_status: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalMessage:
    """An inbound customer message from a channel (Messenger, Instagram DM, WhatsApp…)."""

    thread_id: str
    message_id: str
    sender_id: str
    sender_name: str | None
    text: str
    product_ref: str | None = None  # the post/listing the customer wrote from, if the channel says
    post_ref: str | None = None  # CNT-014: external id of the post the customer replied to / came from


@dataclass(frozen=True)
class ContentMetrics:
    """Cumulative counts a channel reports for one published post. None = the channel doesn't say."""

    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None
    clicks: int | None = None


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

    def fetch_listings(self, external_ids: list[str]) -> dict[str, RemoteListing]:
        """Current provider state of these listings. An id missing from the result no longer exists
        on the channel. Read-only: reconciliation never writes from here."""
        self._require(ChannelCapability.PRODUCT_LISTING)
        raise CapabilityNotSupported(self.code, "fetch_listings")

    def update_inventory(self, external_sku: str, available: int, idempotency_key: str) -> None:
        self._require(ChannelCapability.INVENTORY_SYNC)
        raise NotImplementedError

    def publish_content(self, content: dict[str, Any], idempotency_key: str) -> str:
        self._require(ChannelCapability.CONTENT_PUBLISH)
        raise NotImplementedError

    def fetch_content_metrics(self, external_ids: list[str]) -> dict[str, ContentMetrics]:
        """CNT-013: insights for published posts (missing ids = not available yet)."""
        self._require(ChannelCapability.CONTENT_METRICS)
        raise NotImplementedError

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        self._require(ChannelCapability.MESSAGES)
        raise NotImplementedError

    def fetch_orders(self, since: datetime) -> list[dict[str, Any]]:
        self._require(ChannelCapability.ORDERS)
        raise NotImplementedError

    def normalize_message(self, raw: dict[str, Any]) -> ExternalMessage | None:
        """Channel webhook payload → ExternalMessage. None = not a customer text (echo, read receipt…)."""
        self._require(ChannelCapability.MESSAGES)
        raise CapabilityNotSupported(self.code, "normalize_message")

    def normalize_order(self, raw: dict[str, Any]) -> ExternalOrder | None:
        """Channel order → ExternalOrder. None = not a real order yet (e.g. a checkout draft)."""
        self._require(ChannelCapability.ORDERS)
        raise CapabilityNotSupported(self.code, "normalize_order")


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
    amount: Money | None = None  # what the provider says was actually paid (checked against the order)


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


# Normalised shipment statuses (FUL-003). Adapters map provider statuses onto these.
SHIPMENT_STATUSES = (
    "booked",
    "pickup_requested",
    "picked_up",
    "in_transit",
    "out_for_delivery",
    "delivered",
    "delivery_failed",
    "reattempt_requested",
    "returning",
    "returned_to_origin",
    "cancelled",
    "lost",
)
# Why a delivery attempt failed (controlled vocabulary; feeds Courier/COD intelligence later).
FAILURE_REASONS = (
    "customer_unreachable",
    "customer_unavailable",
    "customer_refused",
    "address_incorrect",
    "cod_not_ready",
    "rescheduled_by_customer",
    "other",
)


@dataclass
class TrackingUpdate:
    """One courier status event, normalised. ``event_id`` is the provider's stable key (dedupe)."""

    event_id: str
    status: str
    occurred_at: datetime
    raw_status: str | None = None
    description: str | None = None
    location: str | None = None
    failure_reason: str | None = None
    cod_collected_minor: int | None = None
    tracking_number: str | None = None  # set by webhook parsing (polling already knows it)


@dataclass
class PickupResult:
    reference: str
    scheduled_for: datetime | None = None


@dataclass
class SettlementLineData:
    tracking_number: str
    collected_minor: int  # cash the courier collected at the door
    fee_minor: int = 0  # what the courier deducted (delivery charge, COD fee)
    note: str | None = None


@dataclass
class SettlementReport:
    reference: str  # the courier's statement id (dedupe key per courier account)
    currency: str
    lines: list[SettlementLineData] = field(default_factory=list)
    period_start: datetime | None = None
    period_end: datetime | None = None


class CourierAdapter(Adapter):
    # Credential fields the seller fills in when connecting (empty = none needed).
    auth_fields: ClassVar[tuple[str, ...]] = ()

    def verify_credentials(self) -> None:
        """Raise IntegrationError(auth=True) if the courier rejects the credentials."""
        return None

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
        *,
        service_code: str | None = None,
        description: str | None = None,
    ) -> ShipmentResult:
        self._require(CourierCapability.CREATE_SHIPMENT)
        raise NotImplementedError

    def request_pickup(self, provider_shipment_ids: list[str], idempotency_key: str) -> PickupResult:
        self._require(CourierCapability.PICKUP)
        raise NotImplementedError

    def track(self, tracking_number: str) -> list[TrackingUpdate]:
        self._require(CourierCapability.TRACKING)
        raise NotImplementedError

    def cancel(self, provider_shipment_id: str, idempotency_key: str) -> None:
        self._require(CourierCapability.CANCEL)
        raise NotImplementedError

    def request_reattempt(
        self, provider_shipment_id: str, note: str | None, destination: Address | None, idempotency_key: str
    ) -> None:
        self._require(CourierCapability.REATTEMPT)
        raise NotImplementedError

    def request_return(self, provider_shipment_id: str, idempotency_key: str) -> None:
        self._require(CourierCapability.RETURN_TO_ORIGIN)
        raise NotImplementedError

    def fetch_cod_settlements(self, since: datetime | None) -> list[SettlementReport]:
        self._require(CourierCapability.COD_SETTLEMENT_REPORTS)
        raise NotImplementedError

    def parse_tracking_webhook(self, headers: dict[str, str], body: bytes) -> list[TrackingUpdate]:
        """Courier push → normalised updates with ``tracking_number`` set. Default: no webhooks."""
        raise CapabilityNotSupported(self.code, "webhooks")


# ----------------------------------------------------------------------------- notifications
class NotificationAdapter(ABC):
    code: ClassVar[str]
    is_sandbox: ClassVar[bool] = False

    @abstractmethod
    def send_email(
        self, to: str, subject: str, text: str, *, idempotency_key: str, locale: str = "en"
    ) -> None: ...
