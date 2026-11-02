"""Deterministic sandbox providers for development and tests. Refused in production by Settings.

Outputs are clearly marked as sandbox content and never pretend to be real model output. Failure
injection lets tests drive retry, circuit-breaker and failover paths.
"""

from __future__ import annotations

import hashlib
import threading
from collections import deque
from typing import Any, ClassVar

from app.domains.ai.providers.base import ProviderAdapter
from app.domains.ai.types import AIRequest, Capability, ProviderError, ProviderResult, Usage

SANDBOX_MARK = "[sandbox]"


def example_for_schema(schema: dict[str, Any]) -> Any:
    """Smallest value satisfying common JSON-schema shapes (object/array/enum/const/primitives)."""
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema:
        return example_for_schema(schema["anyOf"][0])
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "null")
    if t == "object":
        props = schema.get("properties", {})
        return {k: example_for_schema(props[k]) for k in schema.get("required", list(props))}
    if t == "array":
        n = schema.get("minItems", 0)
        return [example_for_schema(schema.get("items", {"type": "string"})) for _ in range(n)]
    if t == "string":
        return SANDBOX_MARK
    if t == "integer":
        return int(schema.get("minimum", 0))
    if t == "number":
        lo = schema.get("minimum", 0)
        hi = schema.get("maximum")
        return float(hi) if hi is not None and hi <= 1 and lo >= 0 else float(lo)
    if t == "boolean":
        return False
    return None


class _FailureScript:
    def __init__(self) -> None:
        self._q: deque[ProviderError] = deque()
        self._lock = threading.Lock()

    def push(self, err: ProviderError, times: int = 1) -> None:
        with self._lock:
            self._q.extend([err] * times)

    def pop(self) -> ProviderError | None:
        with self._lock:
            return self._q.popleft() if self._q else None

    def clear(self) -> None:
        with self._lock:
            self._q.clear()


class SandboxAdapter(ProviderAdapter):
    code = "sandbox"
    is_sandbox = True
    capabilities = frozenset(
        {
            Capability.TEXT,
            Capability.STRUCTURED,
            Capability.VISION,
            Capability.VISION_STRUCTURED,
            Capability.EMBEDDING,
            Capability.MODERATION,
        }
    )
    failures: ClassVar[_FailureScript] = _FailureScript()
    override_data: ClassVar[dict[str, Any]] = {}  # model -> forced structured output (tests)

    def _maybe_fail(self) -> None:
        err = self.failures.pop()
        if err is not None:
            raise err

    def generate_text(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        self._maybe_fail()
        prompt = req.messages[-1].text if req.messages else ""
        digest = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        text = f"{SANDBOX_MARK} response {digest} (locale={req.locale or 'en'})"
        return ProviderResult(
            text=text, usage=Usage(len(prompt) // 4, len(text) // 4), raw_model=model, stop_reason="end_turn"
        )

    def generate_structured(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        self._maybe_fail()
        assert req.json_schema is not None
        data = self.override_data.get(model, example_for_schema(req.json_schema))
        return ProviderResult(
            text=None, data=data, usage=Usage(50, 50), raw_model=model, stop_reason="end_turn"
        )

    def embed(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        self._maybe_fail()
        vecs = []
        for t in req.embed_texts:
            h = hashlib.sha256(t.encode()).digest()
            vecs.append([b / 255 for b in h[:16]])
        return ProviderResult(embeddings=vecs)

    def moderate(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        self._maybe_fail()
        return ProviderResult(data={"flagged": False, "categories": {}})

    def health_check(self, *, timeout_s: float = 10) -> bool:
        return True


class SandboxMediaAdapter(ProviderAdapter):
    """Sandbox image/video provider: returns a job id; the media pipeline (MED-009) will poll it."""

    code = "sandbox_media"
    is_sandbox = True
    capabilities = frozenset({Capability.IMAGE_GENERATION, Capability.VIDEO_GENERATION})

    def generate_image(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        jid = "sbx-img-" + hashlib.sha256((req.image_prompt or "").encode()).hexdigest()[:12]
        return ProviderResult(job_id=jid, usage=Usage(units=1))

    def generate_video(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        spec = req.video_spec or {}
        jid = "sbx-vid-" + hashlib.sha256(repr(sorted(spec.items())).encode()).hexdigest()[:12]
        return ProviderResult(job_id=jid, usage=Usage(units=float(spec.get("duration_s", 0))))

    def health_check(self, *, timeout_s: float = 10) -> bool:
        return True
