"""Provider-neutral AI request/response types. Business modules only ever see these."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Capability(StrEnum):
    TEXT = "text"
    STRUCTURED = "structured"
    VISION = "vision"
    VISION_STRUCTURED = "vision_structured"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    EMBEDDING = "embedding"
    MODERATION = "moderation"


@dataclass(frozen=True)
class ImageInput:
    media_type: str  # image/jpeg | image/png | image/webp
    data_b64: str | None = None
    url: str | None = None  # signed, short-lived URL to private storage


@dataclass(frozen=True)
class Message:
    role: str  # user | assistant
    text: str
    images: tuple[ImageInput, ...] = ()


@dataclass(frozen=True)
class AIRequest:
    messages: tuple[Message, ...]
    system: str | None = None
    json_schema: dict[str, Any] | None = None  # set → structured output, validated by the gateway
    max_tokens: int = 4096
    locale: str | None = None
    quality: str = "standard"  # economy | standard | premium
    prompt_name: str | None = None
    prompt_version: int | None = None
    # media
    image_prompt: str | None = None
    video_spec: dict[str, Any] | None = None  # duration_s, aspect_ratio, resolution, style...
    embed_texts: tuple[str, ...] = ()


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    units: float = 0  # images / seconds of video when not token-billed


@dataclass
class ProviderResult:
    text: str | None = None
    data: Any = None
    embeddings: list[list[float]] | None = None
    job_id: str | None = None  # async media jobs
    usage: Usage = field(default_factory=Usage)
    raw_model: str | None = None
    stop_reason: str | None = None


@dataclass
class AIResult:
    task: str
    provider: str
    model: str
    text: str | None
    data: Any
    embeddings: list[list[float]] | None
    job_id: str | None
    usage: Usage
    cost_usd_micros: int | None
    latency_ms: int
    attempts: int
    fallback_used: bool
    byok: bool
    execution_id: str
    confidence: float | None = None
    needs_review: bool = False


class ProviderError(Exception):
    """Normalized provider failure.

    retryable: transient (timeouts, 429, 5xx, connection) → retry same candidate with backoff.
    counts_toward_circuit: provider health problem (not our bad input / refusal).
    """

    def __init__(
        self,
        code: str,
        message: str = "",
        *,
        retryable: bool = False,
        counts_toward_circuit: bool = True,
        retry_after_s: float | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}"[:500])
        self.code = code
        self.retryable = retryable
        self.counts_toward_circuit = counts_toward_circuit
        self.retry_after_s = retry_after_s
