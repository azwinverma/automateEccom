"""Provider adapter interface (specs/07: generate_text, generate_structured, analyze_image,
generate_image, generate_video, embed, moderate, health_check, estimate_cost)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.domains.ai.types import AIRequest, Capability, ProviderError, ProviderResult


class ProviderAdapter(ABC):
    code: ClassVar[str]
    capabilities: ClassVar[frozenset[Capability]]
    is_sandbox: ClassVar[bool] = False

    def __init__(self, api_key: str | None, *, options: dict[str, Any] | None = None) -> None:
        self._api_key = api_key
        self.options = options or {}

    def __repr__(self) -> str:  # never include the key
        return f"<{type(self).__name__} code={self.code}>"

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def _unsupported(self, op: str) -> ProviderError:
        return ProviderError(
            "capability_not_supported",
            f"{self.code} does not support {op}",
            retryable=False,
            counts_toward_circuit=False,
        )

    def generate_text(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        raise self._unsupported("generate_text")

    def generate_structured(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        raise self._unsupported("generate_structured")

    def analyze_image(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        # Vision requests are ordinary messages with images; structured if a schema is present.
        if req.json_schema is not None:
            return self.generate_structured(model, req, timeout_s=timeout_s, effort=effort)
        return self.generate_text(model, req, timeout_s=timeout_s, effort=effort)

    def generate_image(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        raise self._unsupported("generate_image")

    def generate_video(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        """Submit an async job; returns ProviderResult(job_id=...). The media pipeline polls it."""
        raise self._unsupported("generate_video")

    def embed(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        raise self._unsupported("embed")

    def moderate(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        raise self._unsupported("moderate")

    @abstractmethod
    def health_check(self, *, timeout_s: float = 10) -> bool: ...

    def estimate_cost(self, model: str, req: AIRequest, pricing: dict[str, Any] | None) -> int | None:
        """Pre-flight upper bound in micro-USD (input chars/4 + max_tokens). None if pricing unknown."""
        if not pricing:
            return None
        chars = sum(len(m.text) for m in req.messages) + len(req.system or "")
        return usage_cost_micros(pricing, chars // 4, req.max_tokens)


def usage_cost_micros(pricing: dict[str, Any] | None, input_tokens: int, output_tokens: int) -> int | None:
    if not pricing:
        return None
    usd = (
        input_tokens / 1e6 * pricing["input_usd_per_mtok"]
        + output_tokens / 1e6 * pricing["output_usd_per_mtok"]
    )
    return round(usd * 1e6)
