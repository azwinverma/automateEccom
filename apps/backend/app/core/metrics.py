"""Prometheus metrics. Label cardinality is bounded: route templates, never raw paths or IDs."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
AI_REQUESTS = Counter("ai_requests_total", "AI provider attempts", ["provider", "model", "task", "status"])
AI_FALLBACKS = Counter("ai_fallback_total", "AI fallbacks to a non-primary candidate", ["task"])
AI_COST_USD = Counter("ai_cost_usd_total", "Estimated AI provider cost (USD)", ["provider", "task"])
AI_LATENCY = Histogram(
    "ai_request_duration_seconds",
    "AI provider latency",
    ["provider", "task"],
    buckets=(0.25, 0.5, 1, 2, 4, 8, 15, 30, 60, 120),
)
AI_CIRCUIT_OPEN = Gauge("ai_circuit_open", "1 if circuit open for provider:model", ["provider", "model"])
OUTBOX_DISPATCH = Counter("outbox_dispatch_total", "Outbox dispatch outcomes", ["event_type", "outcome"])
OUTBOX_PENDING = Gauge("outbox_pending_events", "Outbox events awaiting dispatch")
IDEMPOTENCY_REPLAYS = Counter("idempotency_replays_total", "Idempotent replays served", ["scope"])
USAGE_BLOCKS = Counter("usage_limit_blocks_total", "Requests blocked by usage limits", ["resource"])
INTEGRATION_CALLS = Counter(
    "integration_calls_total", "External integration HTTP calls", ["provider", "operation", "outcome"]
)
AUTH_EVENTS = Counter("auth_events_total", "Authentication events", ["event"])
