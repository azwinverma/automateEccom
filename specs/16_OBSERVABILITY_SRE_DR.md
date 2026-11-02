# Observability, SRE & Disaster Recovery

> v1 (2026-11-02). The original 16 was never provided. Authored from the build brief and the
> implementation; owner review required.

## Signals (implemented foundation)
- **Logs:** structured JSON with request_id, trace_id, merchant_id, user_id and error_code. Secrets
  and row values are redacted.
- **Metrics:** Prometheus, bounded labels (route templates):
  - HTTP
  - AI requests, fallbacks, cost and circuit state
  - outbox dispatch and pending count
  - idempotency replays
  - usage blocks
  - integration calls
  - auth events
- **Traces:** OpenTelemetry per request and AI call, with OTLP export.

## Required dashboards & alerts (GAP-ALERTS until staging exists)
| Area | Alert examples |
|---|---|
| API | 5xx rate > 1% (5 min); p95 latency > 1s |
| Outbox | pending > 1,000 or oldest pending > 5 min; any `dead` event |
| Webhooks | verification failures spike; processing lag > 2 min; dead events |
| AI | fallback rate > 20%; circuit open; cost/hour above budget |
| Payments/refunds | verification failures; refund errors (any) |
| Publishing | listing/post failure rate; expired connections count |
| Inventory | ledger/level mismatch (reconciliation); oversell attempt blocked |
| Shipments | creation failures; COD settlement overdue |
| Queues | backlog per queue (default/outbox/ai/media/intelligence) |

## Intelligence monitoring (Phase 6+)
- **Freshness:** age of each Product Brain profile, Twin section and metric family against its SLO
  (e.g. Product Brain < 24h, Twin section < its TTL). Breaches create admin alerts and mark the data
  `stale` in the UI.
- **Job health:** intelligence job success, duration and rows processed; recompute backlog.
- **Data quality:** completeness (e.g. % of products with cost set, % of orders with structured
  address); unknown-category rates.
- **Model drift and calibration:** for COD risk, the outcome rate per level over time; for courier
  ETA, prediction error; alert on calibration breaks.
- **Recommendation health:** acceptance rate; outcome-measurement coverage; recommendations expiring
  unseen.
- **APS sanity:** sudden score jumps (> 15 points/day) are flagged for investigation (often an
  instrumentation change, not real behaviour).

## SLOs (initial targets)
- API availability 99.9%.
- Order and webhook ingestion durability: zero loss (outbox + raw webhook storage).
- Webhook processing p95 < 60s.
- Twin event-driven update p95 < 60s.

## DR
- Managed Postgres with PITR (target RPO ≤ 5 min, RTO ≤ 1h); daily logical backups; quarterly restore
  drills.
- Object storage versioning.
- Intelligence data is recomputable, so its RPO can be looser, but Recommendation, Fact and
  CODRiskAssessment records are decision records and are backed up like Commerce Core.

## Runbooks (to write with staging)
outbox DLQ replay; webhook replay; provider outage (AI/channel/courier/payment); token expiry storm;
intelligence recompute after a method change; restore drill.
