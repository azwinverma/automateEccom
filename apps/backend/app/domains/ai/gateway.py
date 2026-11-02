"""AI Gateway (AIG-001, AIG-007..010, AIG-013, AIG-014).

The single entry point for every model/media call. Business modules call ``gateway.run(task=...)``
with a provider-neutral ``AIRequest``; they never import a provider SDK.

Flow per call:
  1. entitlement: require the task's feature; reserve usage (short committed transaction)
  2. candidates: policy order → expand BYOK/platform keys → drop unsupported/unconfigured/open-circuit
  3. execute: per candidate bounded retries (exp. backoff + full jitter, honors Retry-After) on
     transient errors; non-transient errors and refusals move to the next candidate
  4. validate structured output against the JSON schema; low confidence → needs_review
  5. ledger: one AIExecution row per attempt (provider, model, tokens, cost, latency, outcome);
     finalize usage on success, release it on failure (second short transaction)

Must run in workers / background jobs, never inside a synchronous HTTP request (provider latency
is unbounded relative to HTTP timeouts). Holding no DB transaction during provider calls is
deliberate: reservations lock counter rows.
"""

from __future__ import annotations

import random
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import jsonschema
import structlog

from app.core.config import get_settings
from app.core.db import session_scope
from app.core.errors import DependencyUnavailable
from app.core.ids import uuid7
from app.core.metrics import AI_COST_USD, AI_FALLBACKS, AI_LATENCY, AI_REQUESTS
from app.core.tracing import current_trace_id, tracer
from app.domains.ai.circuit import BreakerConfig, CircuitBreaker
from app.domains.ai.models import AIExecution
from app.domains.ai.policy import Candidate, RoutingPolicy, TaskPolicy, load_policy
from app.domains.ai.providers.anthropic_adapter import AnthropicAdapter
from app.domains.ai.providers.base import ProviderAdapter, usage_cost_micros
from app.domains.ai.providers.gemini_adapter import GeminiAdapter
from app.domains.ai.providers.openai_adapter import OpenAIAdapter
from app.domains.ai.providers.sandbox import SandboxAdapter, SandboxMediaAdapter
from app.domains.ai.types import AIRequest, AIResult, Capability, ProviderError, ProviderResult, Usage
from app.domains.billing.service import entitlements
from app.domains.platform import outbox

log = structlog.get_logger(__name__)

ADAPTERS: dict[str, type[ProviderAdapter]] = {
    "anthropic": AnthropicAdapter,
    "openai": OpenAIAdapter,
    "gemini": GeminiAdapter,
    "sandbox": SandboxAdapter,
    "sandbox_media": SandboxMediaAdapter,
}


class AIUnavailable(DependencyUnavailable):
    code = "ai_unavailable"
    message = "AI is temporarily unavailable. Your request was not charged."


@dataclass
class _Route:
    candidate: Candidate
    index: int
    adapter: ProviderAdapter
    byok: bool


@dataclass
class _Attempt:
    route: _Route
    attempt: int
    status: str
    latency_ms: int
    error_code: str | None = None
    usage: Usage = field(default_factory=Usage)
    cost: int | None = None
    confidence: float | None = None


def _platform_key(provider: str) -> str | None:
    s = get_settings()
    secret = {"anthropic": s.anthropic_api_key, "openai": s.openai_api_key, "gemini": s.gemini_api_key}.get(
        provider
    )
    return secret.get_secret_value() if secret else None


class AIGateway:
    def __init__(
        self,
        policy: RoutingPolicy | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._policy = policy
        self._breaker = breaker
        self._sleep = sleep

    @property
    def policy(self) -> RoutingPolicy:
        return self._policy or load_policy()

    @property
    def breaker(self) -> CircuitBreaker:
        if self._breaker is None:
            p = self.policy
            self._breaker = CircuitBreaker(
                BreakerConfig(p.breaker_failure_threshold, p.breaker_window_s, p.breaker_open_s)
            )
        return self._breaker

    # ------------------------------------------------------------------ routing
    def _routes(self, tp: TaskPolicy, byok_keys: dict[str, tuple[str, bool]]) -> list[_Route]:
        s = get_settings()
        routes: list[_Route] = []
        for i, cand in enumerate(tp.candidates):
            cls = ADAPTERS.get(cand.provider)
            if cls is None or not cls.capabilities.__contains__(tp.capability):
                continue
            if cls.is_sandbox and not s.ai_enable_sandbox_provider:
                continue
            opts = self.policy.providers.get(cand.provider, {})
            byok = byok_keys.get(cand.provider)
            if byok is not None:
                routes.append(_Route(cand, i, cls(byok[0], options=opts), byok=True))
                if not byok[1]:  # merchant chose BYOK-only for this provider
                    continue
            if cls.is_sandbox:
                routes.append(_Route(cand, i, cls(None, options=opts), byok=False))
            elif (key := _platform_key(cand.provider)) is not None:
                routes.append(_Route(cand, i, cls(key, options=opts), byok=False))
        return routes

    # ------------------------------------------------------------------ execution
    @staticmethod
    def _invoke(
        adapter: ProviderAdapter,
        cap: Capability,
        model: str,
        req: AIRequest,
        timeout_s: float,
        effort: str | None,
    ) -> ProviderResult:
        if cap == Capability.TEXT:
            return adapter.generate_text(model, req, timeout_s=timeout_s, effort=effort)
        if cap == Capability.STRUCTURED:
            return adapter.generate_structured(model, req, timeout_s=timeout_s, effort=effort)
        if cap in (Capability.VISION, Capability.VISION_STRUCTURED):
            return adapter.analyze_image(model, req, timeout_s=timeout_s, effort=effort)
        if cap == Capability.IMAGE_GENERATION:
            return adapter.generate_image(model, req, timeout_s=timeout_s)
        if cap == Capability.VIDEO_GENERATION:
            return adapter.generate_video(model, req, timeout_s=timeout_s)
        if cap == Capability.EMBEDDING:
            return adapter.embed(model, req, timeout_s=timeout_s)
        if cap == Capability.MODERATION:
            return adapter.moderate(model, req, timeout_s=timeout_s)
        raise ProviderError("capability_not_supported", str(cap), counts_toward_circuit=False)

    def _backoff(self, attempt: int, retry_after: float | None) -> float:
        p = self.policy
        if retry_after is not None:
            return min(retry_after, p.retry_max_delay_s)
        cap = min(p.retry_max_delay_s, p.retry_base_delay_s * (2 ** (attempt - 1)))
        return random.uniform(0, cap)  # noqa: S311 - full jitter

    def _cost(self, route: _Route, usage: Usage) -> int | None:
        pricing = self.policy.price(route.candidate.provider, route.candidate.model)
        if pricing and "per_unit_usd" in pricing:
            return round(usage.units * pricing["per_unit_usd"] * 1e6)
        return usage_cost_micros(pricing, usage.input_tokens, usage.output_tokens)

    def run(
        self,
        *,
        task: str,
        request: AIRequest,
        merchant_id: uuid.UUID | None,
        idempotency_key: str,
        usage_quantity: int = 1,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> AIResult:
        tp = self.policy.task(task)
        is_structured = request.json_schema is not None
        if tp.capability in (Capability.STRUCTURED, Capability.VISION_STRUCTURED) and not is_structured:
            raise ValueError(f"task {task} requires request.json_schema")
        group = uuid7()

        # 1. entitlement + usage reservation (committed before any provider call)
        reservation_id: uuid.UUID | None = None
        plan_code: str | None = None
        byok_keys: dict[str, tuple[str, bool]] = {}
        if merchant_id is not None:
            from app.domains.ai.credentials import active_keys

            with session_scope() as db:
                ent = (
                    entitlements.require_feature(db, merchant_id, tp.feature)
                    if tp.feature
                    else entitlements.resolve(db, merchant_id)
                )
                plan_code = ent.plan_code
                if tp.usage_resource:
                    res = entitlements.reserve(
                        db,
                        merchant_id,
                        tp.usage_resource,
                        usage_quantity,
                        f"ai:{idempotency_key}",
                        reference_type=reference_type,
                        reference_id=reference_id,
                    )
                    reservation_id = res.id
                if ent.has("ai.byok"):
                    byok_keys = active_keys(db, merchant_id)

        # 2-4. route + execute
        attempts: list[_Attempt] = []
        result: ProviderResult | None = None
        winner: _Attempt | None = None
        opened: list[tuple[str, str]] = []
        with tracer().start_as_current_span(f"ai.{task}") as span:
            span.set_attribute("ai.task", task)
            for route in self._routes(tp, byok_keys):
                prov, model = route.candidate.provider, route.candidate.model
                if not self.breaker.allow(prov, model):
                    attempts.append(_Attempt(route, 0, "skipped", 0, "circuit_open"))
                    continue
                for n in range(1, tp.max_attempts_per_candidate + 1):
                    t0 = time.perf_counter()
                    try:
                        out = self._invoke(
                            route.adapter, tp.capability, model, request, tp.timeout_s, route.candidate.effort
                        )
                        latency = int((time.perf_counter() - t0) * 1000)
                        if is_structured:
                            try:
                                jsonschema.validate(out.data, request.json_schema)
                            except jsonschema.ValidationError as ve:
                                raise ProviderError(
                                    "schema_validation_failed", ve.message[:200], counts_toward_circuit=False
                                ) from ve
                        conf = out.data.get("confidence") if isinstance(out.data, dict) else None
                        att = _Attempt(
                            route,
                            n,
                            "succeeded",
                            latency,
                            usage=out.usage,
                            cost=self._cost(route, out.usage),
                            confidence=float(conf) if isinstance(conf, int | float) else None,
                        )
                        attempts.append(att)
                        self.breaker.record_success(prov, model, latency)
                        result, winner = out, att
                        break
                    except ProviderError as e:
                        latency = int((time.perf_counter() - t0) * 1000)
                        attempts.append(_Attempt(route, n, "failed", latency, e.code))
                        AI_REQUESTS.labels(prov, model, task, "failed").inc()
                        log.warning(
                            "ai_attempt_failed",
                            task=task,
                            provider=prov,
                            model=model,
                            attempt=n,
                            error_code=e.code,
                            byok=route.byok,
                        )
                        if e.counts_toward_circuit and self.breaker.record_failure(prov, model):
                            opened.append((prov, model))
                        if e.retryable and n < tp.max_attempts_per_candidate:
                            self._sleep(self._backoff(n, e.retry_after_s))
                            continue
                        break
                if result is not None:
                    break

        # 5. ledger + settle usage
        credits_charged = 0
        with session_scope() as db:
            if reservation_id is not None:
                if result is not None:
                    ev = entitlements.finalize(db, reservation_id)
                    credits_charged = ev.credits_charged if ev else 0
                else:
                    entitlements.release(db, reservation_id)
            trace_id = current_trace_id()
            for a in attempts:
                db.add(
                    AIExecution(
                        merchant_id=merchant_id,
                        request_group=group,
                        task=task,
                        provider=a.route.candidate.provider,
                        model=a.route.candidate.model,
                        attempt=a.attempt,
                        candidate_index=a.route.index,
                        status=a.status,
                        error_code=a.error_code,
                        byok=a.route.byok,
                        input_tokens=a.usage.input_tokens,
                        output_tokens=a.usage.output_tokens,
                        units=a.usage.units or None,
                        cost_usd_micros=a.cost,
                        credits_charged=credits_charged if a is winner else 0,
                        latency_ms=a.latency_ms,
                        prompt_name=request.prompt_name,
                        prompt_version=request.prompt_version,
                        plan_code=plan_code,
                        usage_reservation_id=reservation_id,
                        trace_id=trace_id,
                        confidence=a.confidence,
                    )
                )
            for prov, model in opened:
                outbox.publish(
                    db,
                    event_type="ai.provider_circuit_opened",
                    aggregate_type="ai_provider",
                    aggregate_id=f"{prov}:{model}",
                    merchant_id=None,
                    payload={"provider": prov, "model": model},
                )

        if result is None or winner is None:
            last = next((a.error_code for a in reversed(attempts) if a.error_code), "no_provider_available")
            raise AIUnavailable(
                details={
                    "task": task,
                    "attempts": len(attempts),
                    "last_error_code": last,
                    "request_group": str(group),
                }
            )

        prov, model = winner.route.candidate.provider, winner.route.candidate.model
        AI_REQUESTS.labels(prov, model, task, "succeeded").inc()
        AI_LATENCY.labels(prov, task).observe(winner.latency_ms / 1000)
        if winner.cost:
            AI_COST_USD.labels(prov, task).inc(winner.cost / 1e6)
        fallback_used = winner.route.index != 0 or any(a.status != "succeeded" for a in attempts)
        if winner.route.index != 0:
            AI_FALLBACKS.labels(task).inc()
        needs_review = tp.min_confidence is not None and (
            winner.confidence is None or winner.confidence < tp.min_confidence
        )
        return AIResult(
            task=task,
            provider=prov,
            model=model,
            text=result.text,
            data=result.data,
            embeddings=result.embeddings,
            job_id=result.job_id,
            usage=winner.usage,
            cost_usd_micros=winner.cost,
            latency_ms=winner.latency_ms,
            attempts=len(attempts),
            fallback_used=fallback_used,
            byok=winner.route.byok,
            execution_id=str(group),
            confidence=winner.confidence,
            needs_review=bool(needs_review and is_structured),
        )

    def provider_health(self) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        out = []
        for tp in self.policy.tasks.values():
            for c in tp.candidates:
                if (c.provider, c.model) in seen:
                    continue
                seen.add((c.provider, c.model))
                cls = ADAPTERS.get(c.provider)
                configured = bool(
                    cls
                    and (
                        (cls.is_sandbox and get_settings().ai_enable_sandbox_provider)
                        or _platform_key(c.provider)
                    )
                )
                out.append(
                    {
                        "provider": c.provider,
                        "model": c.model,
                        "configured": configured,
                        **self.breaker.health(c.provider, c.model),
                    }
                )
        return out


gateway = AIGateway()
