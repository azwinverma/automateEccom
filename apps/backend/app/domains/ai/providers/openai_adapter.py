"""OpenAI adapter (AIG-003) over plain HTTP (Chat Completions + Embeddings + Moderations).

Status: implemented against the documented public REST shapes but NOT yet exercised against the live
API (no credentials in this environment). Contract tests use respx. See docs/KNOWN_GAPS.md
GAP-AI-PROVIDER-VERIFY before enabling in production.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.domains.ai.providers.base import ProviderAdapter
from app.domains.ai.providers.http_util import post_json
from app.domains.ai.types import AIRequest, Capability, ProviderError, ProviderResult, Usage

BASE = "https://api.openai.com/v1"


class OpenAIAdapter(ProviderAdapter):
    code = "openai"
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

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError("not_configured", "OpenAI API key missing", counts_toward_circuit=False)
        return {"Authorization": f"Bearer {self._api_key}"}

    @staticmethod
    def _messages(req: AIRequest) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if req.system:
            msgs.append({"role": "system", "content": req.system})
        for m in req.messages:
            if not m.images:
                msgs.append({"role": m.role, "content": m.text})
                continue
            parts: list[dict[str, Any]] = [{"type": "text", "text": m.text}]
            for img in m.images:
                url = img.url or f"data:{img.media_type};base64,{img.data_b64}"
                parts.append({"type": "image_url", "image_url": {"url": url}})
            msgs.append({"role": m.role, "content": parts})
        return msgs

    def _chat(self, model: str, req: AIRequest, timeout_s: float, extra: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": model,
            "messages": self._messages(req),
            "max_completion_tokens": req.max_tokens,
            **extra,
        }
        return post_json(
            f"{BASE}/chat/completions",
            headers=self._headers(),
            body=body,
            timeout_s=timeout_s,
            provider=self.code,
        )

    @staticmethod
    def _usage(data: dict[str, Any]) -> Usage:
        u = data.get("usage") or {}
        return Usage(
            input_tokens=int(u.get("prompt_tokens", 0)), output_tokens=int(u.get("completion_tokens", 0))
        )

    def generate_text(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        data = self._chat(model, req, timeout_s, {})
        choice = data["choices"][0]
        if choice.get("message", {}).get("refusal"):
            raise ProviderError("refusal", "openai refusal", counts_toward_circuit=False)
        return ProviderResult(
            text=choice["message"].get("content") or "",
            usage=self._usage(data),
            raw_model=data.get("model"),
            stop_reason=choice.get("finish_reason"),
        )

    def generate_structured(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        fmt = {
            "type": "json_schema",
            "json_schema": {"name": "output", "strict": True, "schema": req.json_schema},
        }
        data = self._chat(model, req, timeout_s, {"response_format": fmt})
        choice = data["choices"][0]
        msg = choice.get("message", {})
        if msg.get("refusal"):
            raise ProviderError("refusal", "openai refusal", counts_toward_circuit=False)
        try:
            parsed = json.loads(msg.get("content") or "")
        except json.JSONDecodeError as e:
            raise ProviderError("invalid_json", "openai", counts_toward_circuit=False) from e
        return ProviderResult(
            text=msg.get("content"),
            data=parsed,
            usage=self._usage(data),
            raw_model=data.get("model"),
            stop_reason=choice.get("finish_reason"),
        )

    def embed(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        data = post_json(
            f"{BASE}/embeddings",
            headers=self._headers(),
            body={"model": model, "input": list(req.embed_texts)},
            timeout_s=timeout_s,
            provider=self.code,
        )
        vecs = [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]
        return ProviderResult(
            embeddings=vecs, usage=Usage(input_tokens=int(data.get("usage", {}).get("prompt_tokens", 0)))
        )

    def moderate(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        text = "\n".join(m.text for m in req.messages)
        data = post_json(
            f"{BASE}/moderations",
            headers=self._headers(),
            body={"model": model, "input": text},
            timeout_s=timeout_s,
            provider=self.code,
        )
        r = data["results"][0]
        return ProviderResult(data={"flagged": bool(r.get("flagged")), "categories": r.get("categories", {})})

    def health_check(self, *, timeout_s: float = 10) -> bool:
        try:
            resp = httpx.get(f"{BASE}/models", headers=self._headers(), timeout=timeout_s)
            return resp.status_code == 200
        except Exception:
            return False
