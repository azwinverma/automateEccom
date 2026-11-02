# Test Strategy & QA

> v1 (2026-11-02). The original 17 was never provided. Authored from the build brief and current
> practice; owner review required.

## Layers (current practice)
- **Unit and integration:** against **real PostgreSQL + Redis** (no SQLite/fakes for locking,
  constraints or tenancy).
- **API and permission tests;** tenant-isolation tests per domain (404 on foreign ids, ORM criteria,
  write guard).
- **Concurrency tests** with real row locks (usage reservations, duplicate apply, registration races).
- **Adapter contract tests** with mocked HTTP following documented provider shapes (OpenAI, Gemini,
  WooCommerce). Stateful sandboxes for OAuth/webhook/publish flows.
- **Structural guards:** every route's DB dependency commits before the response (ADR-021); the event
  catalog validates.
- **Migration round-trips** (upgrade → downgrade → upgrade → check) against a database with data
  (ADR-022).
- **E2E (Playwright)** against the real backend, desktop + 360px, en/ne; run in parallel.
- **Mobile** widget/unit tests at 360dp in en and ne, plus an opt-in live end-to-end test against the
  real backend.

## Critical E2E journeys
| Journey | Phase |
|---|---|
| Product → AI content → publish | 1 |
| Message → AI → order | 2 |
| Order → payment/COD → fulfillment → delivered | 3 |
| Delivered → return → refund | 4 |
| Exception → resolution → Autopilot metric recorded | 5 |
| AI provider failure → fallback | built |
| Channel OAuth expiry → reconnect | built |
| Quota reached → credits/upgrade | built |

## AI evals
Harness implemented (AIG-015). Scorers: schema, grounding, Nepali script, limits, category,
attributes, invented options. Planned suites:
- order extraction; intent; support replies; return decisions
- explanation faithfulness
- Store Manager answers (tool use + grounding)

## Intelligence testing (Phase 6+)
- **Fixtures:** deterministic synthetic merchant histories (Nepal-realistic):
  - seasonal demand (Dashain/Tihar)
  - COD failure clusters by route
  - fit-related return spikes
  - supplier defect batches
  - creative patterns
- **Metric correctness:** golden-value tests per metric definition and method_version.
- **Explanation tests:** every recommendation has evidence, confidence and impact. Narratives
  introduce no numbers absent from the evidence.
- **Offline evaluation:**
  - backtests on historical windows (precision/recall of stockout alerts, COD risk calibration,
    courier ETA error, return-insight hit rate)
  - thresholds gate releases of new method versions
- **Policy tests:** a decision table for each risk class × mode × threshold × confidence × staleness.
- **Fairness tests (COD):** no prohibited features (static check of the feature list); disparity
  report by region.
- **Privacy tests (Network, Phase 10):** k-anonymity and dominance suppression; no cross-tenant leaks.
- **Degradation tests:** stale or missing intelligence leads to approval fallback, not wrong
  auto-actions.

## Non-functional
- Load: webhook bursts, flash-sale reservations, high message volume.
- Failure injection: provider outage, broker loss, DB failover.
- Security: SAST and dependency, secret and container scans.
