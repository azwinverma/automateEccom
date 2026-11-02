"""Claude adapter (AIG-002). The only module allowed to import the Anthropic SDK.

* SDK retries are disabled (max_retries=0): the gateway owns retry/backoff, circuit breaking and
  cross-provider failover, so attempts are counted and costed in one place.
* Structured output uses ``output_config.format`` (json_schema); the gateway still validates.
* ``stop_reason == "refusal"`` is a non-retryable, non-circuit failure → gateway falls back.
* Optional server-side refusal fallback (beta ``server-side-fallback-2026-07-01``,
  ``fallbacks: "default"``) for Opus 5.5 / Sonnet 5.5, controlled by routing policy.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from app.domains.ai.providers.base import ProviderAdapter
from app.domains.ai.types import AIRequest, Capability, ProviderError, ProviderResult, Usage

_SERVER_FALLBACK_MODELS = frozenset({"claude-opus-5-5", "claude-sonnet-5-5"})
_SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicAdapter(ProviderAdapter):
    code = "anthropic"
    capabilities = frozenset(
        {Capability.TEXT, Capability.STRUCTURED, Capability.VISION, Capability.VISION_STRUCTURED}
    )

    def _client(self, timeout_s: float) -> anthropic.Anthropic:
        if not self._api_key:
            raise ProviderError("not_configured", "Anthropic API key missing", counts_toward_circuit=False)
        return anthropic.Anthropic(api_key=self._api_key, max_retries=0, timeout=timeout_s)

    @staticmethod
    def _content(req: AIRequest) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in req.messages:
            blocks: list[dict[str, Any]] = []
            for img in m.images:
                if img.data_b64:
                    blocks.append(
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": img.media_type, "data": img.data_b64},
                        }
                    )
                elif img.url:
                    blocks.append({"type": "image", "source": {"type": "url", "url": img.url}})
            blocks.append({"type": "text", "text": m.text})
            out.append({"role": m.role, "content": blocks})
        return out

    def _call(self, model: str, req: AIRequest, timeout_s: float, output_config: dict[str, Any]) -> Any:
        client = self._client(timeout_s)
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": req.max_tokens,
            "messages": self._content(req),
        }
        if req.system:
            kwargs["system"] = req.system
        if output_config:
            kwargs["output_config"] = output_config
        try:
            if self.options.get("server_side_refusal_fallback") and model in _SERVER_FALLBACK_MODELS:
                return client.beta.messages.create(
                    betas=[_SERVER_FALLBACK_BETA], extra_body={"fallbacks": "default"}, **kwargs
                )
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            ra = e.response.headers.get("retry-after") if e.response is not None else None
            raise ProviderError(
                "rate_limited",
                str(e),
                retryable=True,
                retry_after_s=float(ra) if ra and ra.replace(".", "").isdigit() else None,
            ) from e
        except anthropic.AuthenticationError as e:
            raise ProviderError("auth_failed", "invalid credentials", counts_toward_circuit=False) from e
        except anthropic.PermissionDeniedError as e:
            raise ProviderError("permission_denied", str(e), counts_toward_circuit=False) from e
        except anthropic.BadRequestError as e:
            raise ProviderError("bad_request", str(e), counts_toward_circuit=False) from e
        except anthropic.APITimeoutError as e:
            raise ProviderError("timeout", str(e), retryable=True) from e
        except anthropic.APIConnectionError as e:
            raise ProviderError("connection_error", str(e), retryable=True) from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500 or e.status_code == 529:
                raise ProviderError("provider_unavailable", str(e), retryable=True) from e
            raise ProviderError(f"http_{e.status_code}", str(e), counts_toward_circuit=False) from e

    @staticmethod
    def _text(resp: Any) -> str:
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    @staticmethod
    def _usage(resp: Any) -> Usage:
        u = resp.usage
        return Usage(
            input_tokens=int(getattr(u, "input_tokens", 0) or 0)
            + int(getattr(u, "cache_read_input_tokens", 0) or 0)
            + int(getattr(u, "cache_creation_input_tokens", 0) or 0),
            output_tokens=int(getattr(u, "output_tokens", 0) or 0),
        )

    @staticmethod
    def _check_stop(resp: Any) -> None:
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise ProviderError("refusal", f"category={category}", counts_toward_circuit=False)

    def generate_text(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        resp = self._call(model, req, timeout_s, {"effort": effort} if effort else {})
        self._check_stop(resp)
        return ProviderResult(
            text=self._text(resp), usage=self._usage(resp), raw_model=resp.model, stop_reason=resp.stop_reason
        )

    def generate_structured(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        assert req.json_schema is not None
        cfg: dict[str, Any] = {"format": {"type": "json_schema", "schema": req.json_schema}}
        if effort:
            cfg["effort"] = effort
        resp = self._call(model, req, timeout_s, cfg)
        self._check_stop(resp)
        if resp.stop_reason == "max_tokens":
            raise ProviderError("output_truncated", "max_tokens reached", counts_toward_circuit=False)
        text = self._text(resp)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ProviderError(
                "invalid_json", "structured output was not JSON", counts_toward_circuit=False
            ) from e
        return ProviderResult(
            text=text, data=data, usage=self._usage(resp), raw_model=resp.model, stop_reason=resp.stop_reason
        )

    def health_check(self, *, timeout_s: float = 10) -> bool:
        try:
            self._client(timeout_s).models.list(limit=1)
            return True
        except Exception:
            return False
