"""Adapter registry. Sandbox adapters are refused in production."""

from __future__ import annotations

from app.core.config import Environment, get_settings
from app.domains.integrations.base import (
    Adapter,
    ChannelAdapter,
    CourierAdapter,
    NotificationAdapter,
    PaymentAdapter,
)
from app.domains.integrations.sandbox import (
    CashOnDeliveryAdapter,
    ConsoleEmailAdapter,
    SandboxChannelAdapter,
    SandboxCourierAdapter,
    SandboxPaymentAdapter,
)

_REGISTRY: dict[str, dict[str, type[Adapter]]] = {
    "channel": {SandboxChannelAdapter.code: SandboxChannelAdapter},
    "payment": {
        SandboxPaymentAdapter.code: SandboxPaymentAdapter,
        CashOnDeliveryAdapter.code: CashOnDeliveryAdapter,
    },
    "courier": {SandboxCourierAdapter.code: SandboxCourierAdapter},
}


class AdapterNotAvailable(LookupError):
    pass


def register(kind: str, cls: type[Adapter]) -> None:
    _REGISTRY.setdefault(kind, {})[cls.code] = cls


def available(kind: str) -> list[dict[str, object]]:
    prod = get_settings().environment == Environment.PRODUCTION
    return [
        {
            "code": c.code,
            "name": c.display_name,
            "sandbox": c.is_sandbox,
            "capabilities": sorted(cap.value for cap in c.capabilities),
        }
        for c in _REGISTRY.get(kind, {}).values()
        if not (prod and c.is_sandbox)
    ]


def get(
    kind: str, code: str, credentials: dict[str, str] | None = None, config: dict | None = None
) -> Adapter:
    cls = _REGISTRY.get(kind, {}).get(code)
    if cls is None:
        raise AdapterNotAvailable(f"{kind}:{code}")
    if cls.is_sandbox and get_settings().environment == Environment.PRODUCTION:
        raise AdapterNotAvailable(f"{kind}:{code} is a sandbox adapter and is disabled in production")
    return cls(credentials, config)


def channel(code: str, **kw: object) -> ChannelAdapter:
    a = get("channel", code, **kw)  # type: ignore[arg-type]
    assert isinstance(a, ChannelAdapter)
    return a


def payment(code: str, **kw: object) -> PaymentAdapter:
    a = get("payment", code, **kw)  # type: ignore[arg-type]
    assert isinstance(a, PaymentAdapter)
    return a


def courier(code: str, **kw: object) -> CourierAdapter:
    a = get("courier", code, **kw)  # type: ignore[arg-type]
    assert isinstance(a, CourierAdapter)
    return a


def mailer() -> NotificationAdapter:
    if get_settings().environment == Environment.PRODUCTION:
        raise AdapterNotAvailable(
            "No production email provider configured (see docs/KNOWN_GAPS.md GAP-EMAIL)"
        )
    return ConsoleEmailAdapter()
