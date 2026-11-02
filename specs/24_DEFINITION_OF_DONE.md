# Definition of Done

A feature is production ready only when relevant items are satisfied.

## Product
requirement; edge cases; loading/error/empty/partial states; entitlement;
usage limits; accessibility; copy.

## Backend
invariants; permissions; tenant isolation; validation; transaction;
idempotency where needed; audit; migrations; indexes; pagination; rate limits.

## Integrations
retry; timeout; circuit breaker when relevant; token refresh; signature validation;
dedupe; reconciliation; provider-failure UX; DLQ/replay.

## AI
gateway only; schema validation; grounded tools; confidence/approval policy;
cost tracking; fallback; prompt version; eval coverage.

## Frontend
responsive; keyboard accessible; screen-reader basics; tokenized styling;
loading/degraded states; no generic AI-template shortcuts.

## Tests
unit; integration; permissions; contract; E2E; duplicate/failure tests;
migration tests for risky changes.

## Operations
logs; metrics; traces; alerts; runbook; rollback/feature flag.

## Docs
API; data model; admin notes; user help where needed.

Happy-path-only is not Done.
