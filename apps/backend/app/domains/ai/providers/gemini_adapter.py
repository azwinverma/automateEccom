"""Gemini adapter (AIG-004) over the Generative Language REST API.

Status: implemented against documented REST shapes, NOT exercised against the live API.
See docs/KNOWN_GAPS.md GAP-AI-PROVIDER-VERIFY. The API key is sent in a header, never the URL,
so it cannot leak into access logs.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.domains.ai.providers.base import ProviderAdapter
from app.domains.ai.providers.http_util import post_json
from app.domains.ai.types import AIRequest, Capability, ProviderError, ProviderResult, Usage

BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiAdapter(ProviderAdapter):
    code = "gemini"
    capabilities = frozenset(
        {
            Capability.TEXT,
            Capability.STRUCTURED,
            Capability.VISION,
            Capability.VISION_STRUCTURED,
            Capability.EMBEDDING,
        }
    )

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError("not_configured", "Gemini API key missing", counts_toward_circuit=False)
        return {"x-goog-api-key": self._api_key}

    @staticmethod
    def _contents(req: AIRequest) -> list[dict[str, Any]]:
        out = []
        for m in req.messages:
            parts: list[dict[str, Any]] = []
            for img in m.images:
                if img.data_b64:
                    parts.append({"inline_data": {"mime_type": img.media_type, "data": img.data_b64}})
                elif img.url:
                    parts.append({"file_data": {"mime_type": img.media_type, "file_uri": img.url}})
            parts.append({"text": m.text})
            out.append({"role": "model" if m.role == "assistant" else "user", "parts": parts})
        return out

    def _generate(
        self, model: str, req: AIRequest, timeout_s: float, gen_cfg: dict[str, Any]
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": self._contents(req),
            "generationConfig": {"maxOutputTokens": req.max_tokens, **gen_cfg},
        }
        if req.system:
            body["systemInstruction"] = {"parts": [{"text": req.system}]}
        return post_json(
            f"{BASE}/models/{model}:generateContent",
            headers=self._headers(),
            body=body,
            timeout_s=timeout_s,
            provider=self.code,
        )

    @staticmethod
    def _parse(data: dict[str, Any]) -> tuple[str, Usage, str | None]:
        cands = data.get("candidates") or []
        if not cands:
            block = (data.get("promptFeedback") or {}).get("blockReason")
            raise ProviderError(
                "refusal" if block else "empty_response", str(block), counts_toward_circuit=False
            )
        c = cands[0]
        if c.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
            raise ProviderError("refusal", c["finishReason"], counts_toward_circuit=False)
        text = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []))
        u = data.get("usageMetadata") or {}
        return (
            text,
            Usage(int(u.get("promptTokenCount", 0)), int(u.get("candidatesTokenCount", 0))),
            c.get("finishReason"),
        )

    def generate_text(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        text, usage, stop = self._parse(self._generate(model, req, timeout_s, {}))
        return ProviderResult(text=text, usage=usage, raw_model=model, stop_reason=stop)

    def generate_structured(
        self, model: str, req: AIRequest, *, timeout_s: float, effort: str | None
    ) -> ProviderResult:
        text, usage, stop = self._parse(
            self._generate(
                model,
                req,
                timeout_s,
                {"responseMimeType": "application/json", "responseJsonSchema": req.json_schema},
            )
        )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ProviderError("invalid_json", "gemini", counts_toward_circuit=False) from e
        return ProviderResult(text=text, data=data, usage=usage, raw_model=model, stop_reason=stop)

    def embed(self, model: str, req: AIRequest, *, timeout_s: float) -> ProviderResult:
        body = {
            "requests": [
                {"model": f"models/{model}", "content": {"parts": [{"text": t}]}} for t in req.embed_texts
            ]
        }
        data = post_json(
            f"{BASE}/models/{model}:batchEmbedContents",
            headers=self._headers(),
            body=body,
            timeout_s=timeout_s,
            provider=self.code,
        )
        return ProviderResult(embeddings=[e["values"] for e in data.get("embeddings", [])])

    def health_check(self, *, timeout_s: float = 10) -> bool:
        try:
            return httpx.get(f"{BASE}/models", headers=self._headers(), timeout=timeout_s).status_code == 200
        except Exception:
            return False
