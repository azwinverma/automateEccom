from __future__ import annotations

import httpx

from app.domains.ai.types import ProviderError


def raise_for_status(resp: httpx.Response, provider: str) -> None:
    if resp.status_code < 400:
        return
    code = resp.status_code
    if code == 429:
        ra = resp.headers.get("retry-after")
        raise ProviderError(
            "rate_limited",
            provider,
            retryable=True,
            retry_after_s=float(ra) if ra and ra.replace(".", "").isdigit() else None,
        )
    if code in (401, 403):
        raise ProviderError("auth_failed", provider, counts_toward_circuit=False)
    if code >= 500:
        raise ProviderError("provider_unavailable", f"{provider} HTTP {code}", retryable=True)
    raise ProviderError("bad_request", f"{provider} HTTP {code}", counts_toward_circuit=False)


def post_json(url: str, *, headers: dict[str, str], body: dict, timeout_s: float, provider: str) -> dict:
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=timeout_s)
    except httpx.TimeoutException as e:
        raise ProviderError("timeout", provider, retryable=True) from e
    except httpx.TransportError as e:
        raise ProviderError("connection_error", provider, retryable=True) from e
    raise_for_status(resp, provider)
    try:
        return resp.json()
    except ValueError as e:
        raise ProviderError("invalid_response", provider, retryable=True) from e
