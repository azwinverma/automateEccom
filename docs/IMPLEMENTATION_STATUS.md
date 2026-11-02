# Implementation Status

Source of truth for progress. IDs from `specs/23_ENGINEERING_BACKLOG.md`.
Statuses: NOT_STARTED · IN_PROGRESS · BLOCKED · IMPLEMENTED · TESTED · PRODUCTION_READY.

**Nothing is PRODUCTION_READY.** Per `specs/24_DEFINITION_OF_DONE.md` that needs a deployed staging environment, alerts, runbooks and an operational review; none exist yet (see `docs/KNOWN_GAPS.md`). `TESTED` = implemented with automated tests passing locally against real PostgreSQL/Redis.

Phases are provisional because `22_PHASED_ROADMAP.md` is not in the repository (GAP-SPEC-22): **P0** Foundation · **P1** Product → Publish · **P2** Conversation → Order (CRM, orders, inventory, payments) · **P3** Fulfil & return · **P4** Automation · **P5** Analytics, procurement, growth. ADM/UX items ship alongside the phase they support.

_Last updated: 2026-11-02 — Phase 0 foundation._

## Summary

| Area | Result (2026-11-02) |
|---|---|
| Backend | ruff + mypy clean · 65 tests passed (real Postgres 14 + Redis 7) · 84% line coverage · pip-audit: no known vulns · alembic upgrade/downgrade/check clean |
| Web | typecheck, lint, 77 component tests, 20 api-client tests, production build; Playwright E2E 8/8 against the **real** backend (desktop + 360px) |
| Mobile | `flutter analyze` clean · 51 tests · not yet built for a device or run against the real backend |
| Containers | backend image built; compose stack booted (migrate → api → worker/beat) and outbox email dispatch verified |
| CI | workflow written, not yet executed on GitHub (repo has no remote) |

## Phase 0 exit criteria

| Criterion | State |
|---|---|
| Auth, sessions, MFA, tenancy, RBAC, audit | Met (tested) |
| Outbox, idempotency, feature flags | Met (tested) |
| Entitlements + usage metering before any expensive AI | Met (tested) |
| AI Gateway with failover, circuit breaker, cost ledger, BYOK | Met for text/structured (tested); image/video providers sandbox-only |
| Integration adapter framework | Met (interfaces + sandbox; no real providers by design in P0) |
| Logging, metrics, tracing, health | Met; dashboards/alerts not yet |
| CI baseline | Written; **not yet run on GitHub** |
| Staging deployment | **Not met** — hosting target undecided (GAP-INFRA-TARGET) |
| Design tokens + web/Flutter design systems | Met (tested); Plan & usage UX fixes in progress |

Phase 1 can start in parallel with closing the two open items above, which need decisions from you rather than engineering work.

## Task table

| ID | Title | Phase | Status | Depends on | Implementation | Tests | Notes |
|---|---|---|---|---|---|---|---|
| FND-001 | monorepo | P0 | TESTED | — | package.json, pnpm-workspace.yaml, apps/*, packages/* | CI workflow | pnpm workspace (web+packages), uv (backend), Flutter app |
| FND-002 | env config | P0 | TESTED | — | apps/backend/app/core/config.py, apps/*/.env.example | test_platform (prod guards via registry test) | Typed settings; refuses weak JWT secret / dev KEK / sandbox AI in staging+prod |
| FND-003 | Docker local stack | P0 | TESTED | FND-004,005 | docker-compose.yml, apps/backend/Dockerfile, apps/web/Dockerfile | Manual: stack booted, register→worker email dispatch verified | Ports overridable (PG_PORT, REDIS_PORT, API_PORT); web behind `--profile web` |
| FND-004 | PostgreSQL | P0 | TESTED | — | apps/backend/app/core/db.py, apps/backend/migrations/ | alembic upgrade/downgrade/check in CI | UUIDv7 PKs, naming convention, hide_parameters, statement timeout |
| FND-005 | Redis/Celery | P0 | TESTED | FND-004 | apps/backend/app/worker/ | test_idempotency_outbox; container run | Celery acks_late, prefetch 1, beat schedule (outbox 2s, usage expiry 60s, idempotency purge 1h) |
| FND-006 | object storage abstraction | P0 | IMPLEMENTED | — | apps/backend/app/domains/integrations/storage.py | test_platform::test_local_storage… | Local backend tested; S3 backend (boto3) not exercised — boto3 not yet a dependency |
| FND-007 | CI | P0 | IMPLEMENTED | — | .github/workflows/ci.yml | — | Not yet run on GitHub (no remote). Jobs: backend, web, mobile, security, images |
| FND-008 | staging CD | P0 | IN_PROGRESS | FND-007 | .github/workflows/deploy-staging.yml, infra/staging/README.md | — | Builds/pushes images; deploy gated: hosting target undecided (GAP-INFRA-TARGET) |
| FND-009 | structured logging | P0 | TESTED | — | apps/backend/app/core/logging.py, core/middleware.py, core/errors.py | test_platform::test_log_redaction, test_auth::test_unhandled_db_error_log… | JSON logs; request_id/trace_id/merchant/user/error_code; key redaction; DB errors logged without row values |
| FND-010 | tracing/metrics | P0 | IMPLEMENTED | — | apps/backend/app/core/tracing.py, core/metrics.py | test_platform::test_health_readiness_metrics | OTel spans per request + AI call; OTLP export when configured; Prometheus metrics. No dashboards/alerts yet |
| FND-011 | feature flags | P0 | TESTED | — | apps/backend/app/domains/platform/flags.py, admin/router.py | test_platform::test_feature_flags… | Kill switch > override > rollout % > default |
| FND-012 | transactional outbox | P0 | TESTED | FND-004 | apps/backend/app/domains/platform/outbox.py | test_idempotency_outbox (retry, DLQ, exactly-once per handler, rollback) | Event catalog contract + JSON-schema validation at publish |
| FND-013 | idempotency service | P0 | TESTED | FND-004 | apps/backend/app/domains/platform/idempotency.py, api/idempotent.py | test_idempotency_outbox | HTTP replay/422/409 + worker run_once |
| FND-014 | audit framework | P0 | TESTED | FND-004 | apps/backend/app/domains/audit/ | test_tenancy_rbac::test_audit_log_is_append_only… | Same-transaction audit; DB trigger blocks UPDATE/DELETE/TRUNCATE |
| IAM-001 | user | P0 | TESTED | — | apps/backend/app/domains/accounts/ | test_auth | Case-insensitive unique email; concurrent duplicate → 409 |
| IAM-002 | login | P0 | TESTED | IAM-001 | apps/backend/app/domains/accounts/service.py | test_auth | Argon2id, generic failure, IP/email rate limits, lockout |
| IAM-003 | verification | P0 | TESTED | FND-012 | apps/backend/app/domains/accounts/, domains/handlers.py | test_auth::test_email_verification_via_outbox | Email via outbox → dev mailer. Phone/SMS OTP not built (GAP-SMS) |
| IAM-004 | sessions/token rotation | P0 | TESTED | IAM-002 | apps/backend/app/domains/accounts/service.py | test_auth::test_refresh_rotation… | Rotation every use; reuse revokes family; session checked per request |
| IAM-005 | MFA | P0 | TESTED | IAM-004 | apps/backend/app/domains/accounts/service.py | test_auth::test_mfa_totp_flow… | TOTP (sealed secret) + 10 single-use recovery codes; staff routes require MFA |
| IAM-006 | merchant tenancy | P0 | TESTED | — | apps/backend/app/core/db.py, domains/merchants/ | test_tenancy_rbac | ORM auto tenant criteria + write guard; 404 on foreign tenant |
| IAM-007 | membership | P0 | TESTED | IAM-006,BIL-004 | apps/backend/app/domains/merchants/ | test_tenancy_rbac::test_invitation_flow… | Invites bound to email, sealed token purged on accept, seat limit |
| IAM-008 | RBAC | P0 | TESTED | IAM-007 | apps/backend/app/domains/merchants/rbac.py, api/deps.py | test_tenancy_rbac | Permission strings; system roles; escalation guard; last-owner guard. Custom roles not built |
| IAM-009 | cross-tenant tests | P0 | TESTED | IAM-006 | apps/backend/tests/test_tenancy_rbac.py | — | Endpoint, ORM and write-guard cross-tenant tests |
| IAM-010 | revoke sessions | P0 | TESTED | IAM-004 | apps/backend/app/domains/accounts/ | test_auth::test_logout_and_revoke_all… | Revoke one / all others; immediate effect |
| BIL-001 | plan | P0 | TESTED | — | apps/backend/app/domains/billing/models.py, plans.py | conftest seeds; test_entitlements | Plans as data |
| BIL-002 | plan version | P0 | TESTED | BIL-001 | apps/backend/app/domains/billing/plans.py | — | Content-hash versioning; one active version per plan; grandfathering |
| BIL-003 | features | P0 | TESTED | BIL-001 | packages/contracts/feature-entitlements.example.json | test_entitlements::test_feature_gating… | 22 features, 14 metered resources |
| BIL-004 | entitlement service | P0 | TESTED | BIL-003 | apps/backend/app/domains/billing/service.py | test_entitlements | No plan-name checks in business code; admin overrides; add-ons |
| BIL-005 | usage event | P0 | TESTED | BIL-004 | apps/backend/app/domains/billing/models.py | test_entitlements | Immutable UsageEvent with idempotency key |
| BIL-006 | aggregation | P0 | TESTED | BIL-005 | apps/backend/app/domains/billing/service.py | test_entitlements | Row-locked counters per window (billing month / merchant-local day); gauge counter registry |
| BIL-007 | credit wallet | P0 | TESTED | BIL-004 | apps/backend/app/domains/billing/service.py | test_entitlements::test_monthly_overrun_uses_credits… | Wallet + ledger (hold/release/consume). No purchase flow (needs PAY) |
| BIL-008 | reserve/finalize usage | P0 | TESTED | BIL-006 | apps/backend/app/domains/billing/service.py | test_entitlements::test_concurrent_reservations… | 12 concurrent reservations vs limit 4 → exactly 4 |
| BIL-009 | quota alerts | P0 | IMPLEMENTED | FND-012 | apps/backend/app/domains/billing/service.py | test_entitlements::test_usage_alerts… | 70/85/100 events emitted once; no notification handler yet |
| BIL-010 | trials | P0 | IMPLEMENTED | BIL-002 | apps/backend/app/domains/billing/plans.py | test_tenancy_rbac (trialing on signup) | Trial start only; trial expiry/conversion job not built |
| BIL-011 | upgrade/downgrade | P0 | NOT_STARTED | PAY-001 | — | — | Upgrade/downgrade needs payment provider + proration rules (GAP-SPEC-21) |
| BIL-012 | overage | P0 | IN_PROGRESS | BIL-011 | apps/backend/app/domains/billing/service.py | test_entitlements | 'overage' funding recorded; invoicing not built |
| BIL-013 | admin plan editor | P0 | NOT_STARTED | ADM | — | — | Admin plan editor UI; seed_from_file is the write path it will reuse |
| AIG-001 | gateway | P0 | TESTED | BIL-008 | apps/backend/app/domains/ai/gateway.py | test_ai_gateway | Single entry point; entitlement + reserve/finalize built in |
| AIG-002 | Claude adapter | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/providers/anthropic_adapter.py | test_ai_gateway (mocked SDK client) | Official SDK, retries off, output_config json_schema, refusal handling. Not called live (no key here) |
| AIG-003 | OpenAI adapter | P0 | IMPLEMENTED | AIG-001 | apps/backend/app/domains/ai/providers/openai_adapter.py | test_platform::test_openai_adapter_contract (respx) | Model IDs/pricing unverified (GAP-AI-PROVIDER-VERIFY) |
| AIG-004 | Gemini adapter | P0 | IMPLEMENTED | AIG-001 | apps/backend/app/domains/ai/providers/gemini_adapter.py | test_platform::test_gemini_adapter_contract (respx) | Key in header, never URL. Unverified live |
| AIG-005 | image provider | P0 | IN_PROGRESS | AIG-001 | apps/backend/app/domains/ai/providers/sandbox.py | test_ai_gateway::test_feature_not_in_plan… | Interface + sandbox only; real image provider not chosen |
| AIG-006 | video provider | P0 | IN_PROGRESS | AIG-001 | apps/backend/app/domains/ai/providers/sandbox.py | test_ai_gateway | Interface + sandbox only; real video provider not chosen |
| AIG-007 | routing | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/policy.py, gateway.py | test_ai_gateway | Policy contract: capability, BYOK, configured keys, circuit. Cost/latency-aware ordering not yet |
| AIG-008 | health scoring | P0 | IMPLEMENTED | AIG-009 | apps/backend/app/domains/ai/circuit.py | — | Success rate + last latency in Redis; exposed to admin; not yet used for ordering |
| AIG-009 | circuit breaker | P0 | TESTED | — | apps/backend/app/domains/ai/circuit.py | test_ai_gateway::test_circuit_opens… | Shared Redis breaker, half-open single probe, event on open |
| AIG-010 | retry/timeout | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/gateway.py | test_ai_gateway::test_transient_errors… | Bounded attempts, full jitter, Retry-After |
| AIG-011 | BYOK encryption | P0 | TESTED | BIL-004 | apps/backend/app/core/crypto.py, domains/ai/credentials.py | test_ai_gateway::test_byok… | Envelope AES-GCM, AAD-bound, crypto-shred on revoke. KMS provider stub only (GAP-KMS) |
| AIG-012 | prompt registry | P0 | IN_PROGRESS | AIG-001 | apps/backend/app/domains/ai/models.py | — | PromptTemplate table + version recorded per execution; no registry service/rollout yet |
| AIG-013 | schema validation | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/gateway.py | test_ai_gateway::test_schema_violation…, test_low_confidence… | JSON-schema validation, confidence → needs_review |
| AIG-014 | cost ledger | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/models.py, gateway.py | test_ai_gateway::test_structured_success… | Per-attempt ledger: provider/model/tokens/cost/latency/credits/plan/prompt/trace |
| AIG-015 | eval harness | P0 | NOT_STARTED | AIG-012 | — | — | Eval harness needs real prompts (Phase 1) |
| CAT-001 | Product | P1 | NOT_STARTED | — | — | — |  |
| CAT-002 | Variant | P1 | NOT_STARTED | — | — | — |  |
| CAT-003 | options | P1 | NOT_STARTED | — | — | — |  |
| CAT-004 | taxonomy | P1 | NOT_STARTED | — | — | — |  |
| CAT-005 | pricing | P1 | NOT_STARTED | — | — | — |  |
| CAT-006 | cost | P1 | NOT_STARTED | — | — | — |  |
| CAT-007 | lifecycle | P1 | NOT_STARTED | — | — | — |  |
| CAT-008 | import | P1 | NOT_STARTED | — | — | — |  |
| CAT-009 | SKU rules | P1 | NOT_STARTED | — | — | — |  |
| CAT-010 | listing mapping | P1 | NOT_STARTED | — | — | — |  |
| MED-001 | signed upload | P1 | NOT_STARTED | — | — | — |  |
| MED-002 | validation | P1 | NOT_STARTED | — | — | — |  |
| MED-003 | EXIF | P1 | NOT_STARTED | — | — | — |  |
| MED-004 | derivatives | P1 | NOT_STARTED | — | — | — |  |
| MED-005 | background removal | P1 | NOT_STARTED | — | — | — |  |
| MED-006 | image generation | P1 | NOT_STARTED | — | — | — |  |
| MED-007 | fidelity review | P1 | NOT_STARTED | — | — | — |  |
| MED-008 | Auto Reel | P1 | NOT_STARTED | — | — | — |  |
| MED-009 | video job state | P1 | NOT_STARTED | — | — | — |  |
| MED-010 | media metering | P1 | NOT_STARTED | — | — | — |  |
| MED-011 | lifecycle cleanup | P1 | NOT_STARTED | — | — | — |  |
| CNT-001 | brand voice | P1 | NOT_STARTED | — | — | — |  |
| CNT-002 | titles | P1 | NOT_STARTED | — | — | — |  |
| CNT-003 | descriptions | P1 | NOT_STARTED | — | — | — |  |
| CNT-004 | SEO | P1 | NOT_STARTED | — | — | — |  |
| CNT-005 | captions | P1 | NOT_STARTED | — | — | — |  |
| CNT-006 | hashtags | P1 | NOT_STARTED | — | — | — |  |
| CNT-007 | translation | P1 | NOT_STARTED | — | — | — |  |
| CNT-008 | calendar | P1 | NOT_STARTED | — | — | — |  |
| CNT-009 | approval | P1 | NOT_STARTED | — | — | — |  |
| CNT-010 | scheduler | P1 | NOT_STARTED | — | — | — |  |
| CNT-011 | retry | P1 | NOT_STARTED | — | — | — |  |
| CHN-001 | adapter interface | P1 | TESTED | — | apps/backend/app/domains/integrations/base.py, registry.py | test_platform::test_registry… | Channel/Payment/Courier/Notification interfaces |
| CHN-002 | capabilities | P1 | TESTED | CHN-001 | apps/backend/app/domains/integrations/base.py | test_platform::test_registry… | Capability enums; sandbox adapters refused in production |
| CHN-003 | OAuth | P1 | NOT_STARTED | — | — | — |  |
| CHN-004 | token refresh | P1 | NOT_STARTED | — | — | — |  |
| CHN-005 | Meta/Instagram | P1 | NOT_STARTED | — | — | — |  |
| CHN-006 | TikTok | P1 | NOT_STARTED | — | — | — |  |
| CHN-007 | TikTok Shop where eligible | P1 | NOT_STARTED | — | — | — |  |
| CHN-008 | Shopify | P1 | NOT_STARTED | — | — | — |  |
| CHN-009 | WooCommerce | P1 | NOT_STARTED | — | — | — |  |
| CHN-010 | webhook gateway | P1 | NOT_STARTED | — | — | — |  |
| CHN-011 | dedupe | P1 | NOT_STARTED | — | — | — |  |
| CHN-012 | reconciliation | P1 | NOT_STARTED | — | — | — |  |
| CHN-013 | health UI | P1 | NOT_STARTED | — | — | — |  |
| CRM-001 | Customer | P2 | NOT_STARTED | — | — | — |  |
| CRM-002 | identities | P2 | NOT_STARTED | — | — | — |  |
| CRM-003 | addresses | P2 | NOT_STARTED | — | — | — |  |
| CRM-004 | duplicate merge | P2 | NOT_STARTED | — | — | — |  |
| CRM-005 | Conversation | P2 | NOT_STARTED | — | — | — |  |
| CRM-006 | Message | P2 | NOT_STARTED | — | — | — |  |
| CRM-007 | normalization | P2 | NOT_STARTED | — | — | — |  |
| CRM-008 | assignment | P2 | NOT_STARTED | — | — | — |  |
| CRM-009 | intent | P2 | NOT_STARTED | — | — | — |  |
| CRM-010 | AI summary | P2 | NOT_STARTED | — | — | — |  |
| CRM-011 | grounded reply | P2 | NOT_STARTED | — | — | — |  |
| CRM-012 | escalation | P2 | NOT_STARTED | — | — | — |  |
| CRM-013 | segments | P2 | NOT_STARTED | — | — | — |  |
| ORD-001 | Order | P2 | NOT_STARTED | — | — | — |  |
| ORD-002 | OrderLine | P2 | NOT_STARTED | — | — | — |  |
| ORD-003 | totals snapshot | P2 | NOT_STARTED | — | — | — |  |
| ORD-004 | state machine | P2 | NOT_STARTED | — | — | — |  |
| ORD-005 | external import | P2 | NOT_STARTED | — | — | — |  |
| ORD-006 | chat-to-order | P2 | NOT_STARTED | — | — | — |  |
| ORD-007 | seller order | P2 | NOT_STARTED | — | — | — |  |
| ORD-008 | idempotency | P2 | NOT_STARTED | — | — | — |  |
| ORD-009 | cancel | P2 | NOT_STARTED | — | — | — |  |
| ORD-010 | partial cancel | P2 | NOT_STARTED | — | — | — |  |
| ORD-011 | timeline | P2 | NOT_STARTED | — | — | — |  |
| INV-001 | locations | P2 | NOT_STARTED | — | — | — |  |
| INV-002 | ledger | P2 | NOT_STARTED | — | — | — |  |
| INV-003 | reservations | P2 | NOT_STARTED | — | — | — |  |
| INV-004 | reserve/release | P2 | NOT_STARTED | — | — | — |  |
| INV-005 | concurrency tests | P2 | NOT_STARTED | — | — | — |  |
| INV-006 | adjustment | P2 | NOT_STARTED | — | — | — |  |
| INV-007 | transfer | P2 | NOT_STARTED | — | — | — |  |
| INV-008 | low-stock | P2 | NOT_STARTED | — | — | — |  |
| INV-009 | channel sync | P2 | NOT_STARTED | — | — | — |  |
| INV-010 | reconciliation | P2 | NOT_STARTED | — | — | — |  |
| PAY-001 | adapter | P2 | IMPLEMENTED | CHN-001 | apps/backend/app/domains/integrations/base.py, sandbox.py | test_platform | Interface + sandbox wallet + COD adapter; no Nepal gateway yet (GAP-PAY-NP) |
| PAY-002 | COD | P2 | NOT_STARTED | — | — | — |  |
| PAY-003 | payment intent | P2 | NOT_STARTED | — | — | — |  |
| PAY-004 | verify | P2 | NOT_STARTED | — | — | — |  |
| PAY-005 | webhook | P2 | NOT_STARTED | — | — | — |  |
| PAY-006 | reconcile | P2 | NOT_STARTED | — | — | — |  |
| PAY-007 | refund | P2 | NOT_STARTED | — | — | — |  |
| PAY-008 | idempotency tests | P2 | NOT_STARTED | — | — | — |  |
| PAY-009 | failed payment | P2 | NOT_STARTED | — | — | — |  |
| PAY-010 | settlement dashboard | P2 | NOT_STARTED | — | — | — |  |
| FUL-001 | courier adapter | P3 | IMPLEMENTED | CHN-001 | apps/backend/app/domains/integrations/base.py, sandbox.py | test_platform | Interface + sandbox courier; no Nepal courier yet (GAP-COURIER-NP) |
| FUL-002 | rates | P3 | NOT_STARTED | — | — | — |  |
| FUL-003 | shipment state | P3 | NOT_STARTED | — | — | — |  |
| FUL-004 | labels | P3 | NOT_STARTED | — | — | — |  |
| FUL-005 | pickup | P3 | NOT_STARTED | — | — | — |  |
| FUL-006 | tracking | P3 | NOT_STARTED | — | — | — |  |
| FUL-007 | notify | P3 | NOT_STARTED | — | — | — |  |
| FUL-008 | delivery failure | P3 | NOT_STARTED | — | — | — |  |
| FUL-009 | smart courier | P3 | NOT_STARTED | — | — | — |  |
| FUL-010 | reconciliation | P3 | NOT_STARTED | — | — | — |  |
| RET-001 | policy | P3 | NOT_STARTED | — | — | — |  |
| RET-002 | eligibility | P3 | NOT_STARTED | — | — | — |  |
| RET-003 | request | P3 | NOT_STARTED | — | — | — |  |
| RET-004 | evidence | P3 | NOT_STARTED | — | — | — |  |
| RET-005 | approval | P3 | NOT_STARTED | — | — | — |  |
| RET-006 | reverse shipment | P3 | NOT_STARTED | — | — | — |  |
| RET-007 | inspection | P3 | NOT_STARTED | — | — | — |  |
| RET-008 | exchange | P3 | NOT_STARTED | — | — | — |  |
| RET-009 | refund calculation | P3 | NOT_STARTED | — | — | — |  |
| RET-010 | auto-refund threshold | P3 | NOT_STARTED | — | — | — |  |
| RET-011 | abuse signals | P3 | NOT_STARTED | — | — | — |  |
| AUT-001 | workflow schema | P4 | NOT_STARTED | — | — | — |  |
| AUT-002 | triggers | P4 | NOT_STARTED | — | — | — |  |
| AUT-003 | conditions | P4 | NOT_STARTED | — | — | — |  |
| AUT-004 | actions | P4 | NOT_STARTED | — | — | — |  |
| AUT-005 | versions | P4 | NOT_STARTED | — | — | — |  |
| AUT-006 | execution | P4 | NOT_STARTED | — | — | — |  |
| AUT-007 | delay | P4 | NOT_STARTED | — | — | — |  |
| AUT-008 | branch | P4 | NOT_STARTED | — | — | — |  |
| AUT-009 | approval | P4 | NOT_STARTED | — | — | — |  |
| AUT-010 | retry | P4 | NOT_STARTED | — | — | — |  |
| AUT-011 | exceptions | P4 | NOT_STARTED | — | — | — |  |
| AUT-012 | logs | P4 | NOT_STARTED | — | — | — |  |
| AUT-013 | templates | P4 | NOT_STARTED | — | — | — |  |
| AUT-014 | builder UI | P4 | NOT_STARTED | — | — | — |  |
| AUT-015 | dry-run | P4 | NOT_STARTED | — | — | — |  |
| ANA-001 | sales | P5 | NOT_STARTED | — | — | — |  |
| ANA-002 | channels | P5 | NOT_STARTED | — | — | — |  |
| ANA-003 | products | P5 | NOT_STARTED | — | — | — |  |
| ANA-004 | fulfillment | P5 | NOT_STARTED | — | — | — |  |
| ANA-005 | returns | P5 | NOT_STARTED | — | — | — |  |
| ANA-006 | AI/automation | P5 | NOT_STARTED | — | — | — |  |
| ANA-007 | product P&L | P5 | NOT_STARTED | — | — | — |  |
| ANA-008 | profit dashboard | P5 | NOT_STARTED | — | — | — |  |
| ANA-009 | Store Manager tools | P5 | NOT_STARTED | — | — | — |  |
| ANA-010 | recommendations | P5 | NOT_STARTED | — | — | — |  |
| PRO-001 | suppliers | P5 | NOT_STARTED | — | — | — |  |
| PRO-002 | supplier products | P5 | NOT_STARTED | — | — | — |  |
| PRO-003 | purchase orders | P5 | NOT_STARTED | — | — | — |  |
| PRO-004 | approvals | P5 | NOT_STARTED | — | — | — |  |
| PRO-005 | receiving | P5 | NOT_STARTED | — | — | — |  |
| PRO-006 | landed cost | P5 | NOT_STARTED | — | — | — |  |
| PRO-007 | reorder recommendations | P5 | NOT_STARTED | — | — | — |  |
| ADM-001 | merchant lookup | P0+ | IMPLEMENTED | IAM-005 | apps/backend/app/domains/admin/router.py | test_platform::test_admin_requires_staff_with_mfa | API only; admin UI not built |
| ADM-002 | usage/credits | P0+ | IMPLEMENTED | BIL-006 | apps/backend/app/domains/admin/router.py | — | Usage + credit balance in merchant detail API |
| ADM-003 | provider health | P0+ | IMPLEMENTED | AIG-008 | apps/backend/app/domains/admin/router.py | — | Provider/circuit health API |
| ADM-004 | channel health | P0+ | NOT_STARTED | — | — | — |  |
| ADM-005 | webhook explorer | P0+ | NOT_STARTED | — | — | — |  |
| ADM-006 | replay | P0+ | IMPLEMENTED | FND-012 | apps/backend/app/domains/admin/router.py | test_idempotency_outbox (requeue) | Outbox replay (audited) |
| ADM-007 | DLQ | P0+ | IMPLEMENTED | FND-012 | apps/backend/app/domains/admin/router.py | — | Dead outbox events listing |
| ADM-008 | plan editor | P0+ | NOT_STARTED | — | — | — |  |
| ADM-009 | routing editor | P0+ | NOT_STARTED | — | — | — |  |
| ADM-010 | refund review | P0+ | NOT_STARTED | — | — | — |  |
| ADM-011 | feature flags | P0+ | IMPLEMENTED | FND-011 | apps/backend/app/domains/admin/router.py | test_platform::test_feature_flags… | Upsert flags (audited) |
| UX-001 | design tokens | P0 | TESTED | — | packages/design-system/ | CI diff check of generated outputs | JSON → CSS vars, TS, Dart |
| UX-002 | web library | P0 | TESTED | UX-001 | apps/web/src/components | 77 vitest tests; E2E vs real backend | No 3rd-party visual library; Radix for behaviour only |
| UX-003 | Flutter theme | P0 | TESTED | UX-001 | apps/mobile/lib/design | flutter test (51) | Theme from generated tokens; bundled Inter + Noto Sans Devanagari |
| UX-004 | Product Brain | P0 | NOT_STARTED | — | — | — |  |
| UX-005 | Channel Sync Rail | P0 | NOT_STARTED | — | — | — |  |
| UX-006 | Autopilot Strip | P0 | IMPLEMENTED | UX-002 | apps/web/src/components/commerce, apps/mobile/lib/features/home | widget/component tests | Autopilot Status Strip (no data source until AUT) |
| UX-007 | Exception Inbox | P0 | IMPLEMENTED | UX-002 | apps/web/src/components/commerce, apps/mobile/lib/features/home | widget/component tests | Exception Inbox (10 types; empty until domains emit exceptions) |
| UX-008 | Order Journey | P0 | NOT_STARTED | — | — | — |  |
| UX-009 | AI Timeline | P0 | NOT_STARTED | — | — | — |  |
| UX-010 | Profit Card | P0 | NOT_STARTED | — | — | — |  |
| UX-011 | Video Credit Meter | P0 | IN_PROGRESS | BIL-006 | apps/web …/settings/plan, apps/mobile …/settings | component tests | Video Credit Meter; plan-page UX fixes in progress (see KNOWN_GAPS GAP-UX-PLAN) |
| UX-012 | Inventory Risk | P0 | NOT_STARTED | — | — | — |  |
| UX-013 | real states | P0 | IN_PROGRESS | — | apps/web, apps/mobile | component tests | Loading/empty/error/offline/permission states for Phase 0 screens |
| UX-014 | accessibility | P0 | IN_PROGRESS | — | apps/web, apps/mobile | — | Keyboard, focus, labels, 48dp; no full screen-reader audit yet |
| UX-015 | bilingual review | P0 | IN_PROGRESS | — | apps/web/src/i18n, apps/mobile/lib/core/l10n/arb | key-parity tests | en/ne complete for Phase 0; Nepali not yet reviewed by a native copy editor |
