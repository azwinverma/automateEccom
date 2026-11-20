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

# ----------------------------------------------------------------------------- operational state (ops.py)
# Platform-wide gauges computed from the database when /metrics is scraped (cached briefly). Labels are
# bounded (queue, section, job, status) — never merchant or record ids.
OUTBOX_OLDEST_PENDING = Gauge("outbox_oldest_pending_seconds", "Age of the oldest pending outbox event")
OUTBOX_DEAD = Gauge("outbox_dead_events", "Outbox events that exhausted retries (dead letter)")
WEBHOOK_UNPROCESSED = Gauge("webhook_events_unprocessed", "Webhook events received/failed, not yet processed")
WEBHOOK_OLDEST_UNPROCESSED = Gauge(
    "webhook_oldest_unprocessed_seconds", "Age of the oldest unprocessed webhook"
)
WEBHOOK_DEAD = Gauge("webhook_events_dead", "Webhook events that exhausted retries")
CONNECTIONS_NEED_ATTENTION = Gauge(
    "channel_connections_need_attention", "Channel connections expired/revoked/error"
)
LISTINGS_FAILED = Gauge("listings_failed", "Channel listings failed or out of sync")
POSTS_FAILED = Gauge("content_posts_failed", "Content posts that failed to publish")
REFUNDS_FAILED = Gauge("refunds_failed", "Refunds in failed state")
COD_SETTLEMENT_OVERDUE = Gauge("cod_settlement_overdue", "COD cash with couriers for more than 7 days")
SHIPMENTS_STUCK = Gauge("shipments_stuck", "Live shipments without an update for 3+ days")
QUEUE_BACKLOG = Gauge("celery_queue_backlog", "Messages waiting in a Celery queue", ["queue"])
TWIN_SECTION_MAX_AGE = Gauge("twin_section_max_age_seconds", "Oldest Twin section of this kind", ["section"])
PRODUCT_BRAIN_MAX_AGE = Gauge("product_brain_max_age_seconds", "Oldest Product Brain profile")
VARIANTS_WITHOUT_COST_RATIO = Gauge(
    "data_quality_variants_without_cost_ratio", "Active variants without a cost"
)
RECOMMENDATIONS_OPEN = Gauge("recommendations_open", "Open recommendations")
RECOMMENDATIONS_EXPIRED_7D = Gauge(
    "recommendations_expired_unseen_7d", "Recommendations that expired in 7 days"
)
JOB_LAST_SUCCESS = Gauge(
    "job_last_success_timestamp_seconds", "Unix time of a scheduled job's last success", ["job"]
)
OPS_COLLECT_ERRORS = Counter("ops_collect_errors_total", "Failures computing an operational gauge", ["gauge"])
# Worker-side job health (exposed by the worker's metrics server).
JOB_RUNS = Counter("job_runs_total", "Scheduled job runs", ["job", "outcome"])
JOB_DURATION = Histogram(
    "job_duration_seconds",
    "Scheduled job duration",
    ["job"],
    buckets=(0.1, 0.5, 1, 5, 15, 60, 300, 900, 1800),
)
