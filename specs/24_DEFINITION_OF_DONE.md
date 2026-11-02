# Definition of Done

> v2 (2026-11-02): adds intelligence requirements.

A feature is production ready only when the relevant items below are satisfied.

## Product
requirement; edge cases; loading/error/empty/partial states; entitlement; usage limits;
accessibility; copy.

## Backend
invariants; permissions; tenant isolation; validation; transaction (commit before response);
idempotency where needed; audit (including actor type: user/automation/ai/system); migrations
(round-tripped on data; NOT NULL with defaults); indexes; pagination; rate limits.

## Integrations
retry; timeout; circuit breaker when relevant; token refresh; signature validation; dedupe;
reconciliation; provider-failure UX; DLQ/replay.

## AI
gateway only; schema validation; grounded tools; confidence/approval policy; cost tracking; fallback;
prompt version; eval coverage.

## Intelligence features (Product Brain, Memory, APS, Recommendations, COD/Courier/Return/Supplier, Creative Genome, Twin, Simulation, Network)
- **Measurable inputs:** every input is a defined metric or record with a source and window. Missing
  inputs are surfaced, not zero-filled.
- **Explanation and evidence:** what/why/evidence/confidence/impact/action (07 framework).
- **Confidence:** includes data completeness and sample size. Thin data is labelled.
- **Auditability:** method_version, inputs references and decision records are stored. Merchant
  overrides are versioned.
- **Merchant control:** thresholds, opt-outs, correction/rejection paths. High-risk actions require
  approval.
- **Monitoring:** freshness SLOs, job health, drift/calibration where predictive.
- **Test fixtures:** deterministic Nepal-realistic synthetic histories plus golden-value tests.
- **Offline evaluation:** a backtest with acceptance thresholds before enabling, and before any
  method_version change.
- **No hallucinated commerce facts:** commercial facts come from Commerce Core at execution time.
  Narratives are validated against evidence.
- **Recommendation outcome tracking:** outcomes are measured and reported with their method.
- **Privacy review:** for features touching customer data or cross-tenant aggregation (15).
- **Graceful degradation:** stale or missing intelligence falls back to approval or neutral behaviour,
  never to wrong auto-actions.

## Frontend
responsive; keyboard accessible; screen-reader basics; tokenized styling; loading/degraded states;
stale-data indicators for derived data; no generic AI-template shortcuts.

## Tests
unit; integration (real Postgres/Redis); permissions; tenant isolation; contract; E2E against the real
backend; duplicate/failure/concurrency tests; migration tests for risky changes; offline evals for AI
and intelligence.

## Operations
logs; metrics; traces; alerts; runbook; rollback/feature flag.

## Docs
API; data model; admin notes; user help where needed; IMPLEMENTATION_STATUS updated honestly.

Happy-path-only is not Done. Nothing is PRODUCTION_READY without a deployed staging environment,
alerts and runbooks.
