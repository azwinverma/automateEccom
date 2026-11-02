# Definition of Done

> v3 (2026-11-02): adds intelligence requirements (v2) and Nivaro brand criteria (v3).

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

## Brand (Nivaro, specs/26)
A feature is **not** done if:
- it uses old product naming ("Commerce OS", "AI Commerce OS") in customer-facing text, or internal
  phase/backlog jargon in seller copy
- hard-coded colours or legacy (indigo) tokens remain; components must use semantic tokens (brand
  guard test passes)
- generic AI visuals are introduced (sparkles, glow, blobs, purple gradients, robot/assistant bubbles)
- unsupported iconography appears (anything outside the in-house line set; sparkle-as-AI)
- illustrations or graphics are inconsistent with the ribbon motif system or the illustration guide
- animation ignores the motion rules (durations, no idle loops, reduced motion)
- app, web and admin use inconsistent logos (only the generated assets / brand components)
- the screen fails responsive (360px) or accessibility rules (contrast, focus, labels)
- the screen exceeds its surface's visual-energy level (26 §14), e.g. accents on payments or admin
- the page looks like a generic AI-generated SaaS template, or could belong unchanged to an
  unrelated CRM, fintech or project tool
- a custom visual has not passed the brand QA list (26 §18)

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
