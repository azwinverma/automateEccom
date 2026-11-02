"""Resilient outbound HTTP for integrations: timeouts, bounded retries with full jitter on
429/5xx/transport errors (honoring Retry-After), per-provider metrics. Never logs bodies/headers."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any

import httpx
import structlog

from app.core.metrics import INTEGRATION_CALLS
from app.domains.integrations.base import IntegrationError

log = structlog.get_logger(__name__)
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class ResilientClient:
    def __init__(
        self,
        provider: str,
        *,
        base_url: str = "",
        timeout_s: float = 15,
        max_attempts: int = 3,
        base_delay_s: float = 0.5,
        max_delay_s: float = 8,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.provider = provider
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)
        self.max_attempts = max_attempts
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self._sleep = sleep

    def request(
        self, method: str, url: str, *, operation: str, retry_unsafe: bool = False, **kw: Any
    ) -> httpx.Response:
        """POST/PATCH are only retried when ``retry_unsafe`` (caller passed a provider idempotency key)."""
        idempotent = method.upper() in ("GET", "HEAD", "PUT", "DELETE", "OPTIONS") or retry_unsafe
        attempts = self.max_attempts if idempotent else 1
        for n in range(1, attempts + 1):
            try:
                resp = self._client.request(method, url, **kw)
            except httpx.TransportError as e:
                INTEGRATION_CALLS.labels(self.provider, operation, "transport_error").inc()
                if n == attempts:
                    raise IntegrationError("connection_error", self.provider, retryable=True) from e
                self._sleep(self._delay(n, None))
                continue
            if resp.status_code in RETRYABLE_STATUS and n < attempts:
                INTEGRATION_CALLS.labels(self.provider, operation, f"retry_{resp.status_code}").inc()
                self._sleep(self._delay(n, resp.headers.get("retry-after")))
                continue
            INTEGRATION_CALLS.labels(self.provider, operation, str(resp.status_code)).inc()
            return resp
        raise AssertionError("unreachable")  # pragma: no cover

    def _delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), self.max_delay_s)
        return random.uniform(0, min(self.max_delay_s, self.base_delay_s * 2 ** (attempt - 1)))  # noqa: S311

    def close(self) -> None:
        self._client.close()
