# Implementation Status

Source of truth for progress. IDs from `specs/23_ENGINEERING_BACKLOG.md`.
Statuses: NOT_STARTED · IN_PROGRESS · BLOCKED · IMPLEMENTED · TESTED · PRODUCTION_READY.

**Nothing is PRODUCTION_READY.** Per `specs/24_DEFINITION_OF_DONE.md` that needs a deployed staging environment, alerts, runbooks and an operational review; none exist yet (see `docs/KNOWN_GAPS.md`). `TESTED` = implemented with automated tests passing locally against real PostgreSQL/Redis.

Phases follow `specs/22_PHASED_ROADMAP.md` (v1, 2026-11-02): **0** Foundation · **1** Product-to-Publish · **2** Conversation-to-Order · **3** Order-to-Delivery · **4** Returns/Refunds/Exchanges · **5** Automation + Exception OS · **6** Commerce Intelligence Foundation · **7** Creative Intelligence · **8** Procurement/Supplier Intelligence · **9** Digital Store Twin + Simulation · **10** Network Intelligence & enterprise scale. Intelligence phases (6+) are gated on trustworthy operational data from 2–5.

_Last updated: 2026-11-02. Phase 0 complete (open: CI run, staging target). Phase 1 backend + mobile built; web Studio/Channels/Content/Reels screens in progress._

## Summary

| Area | Result (2026-11-02) |
|---|---|
| Backend | ruff + mypy clean · 151 tests passed (real Postgres 14 + Redis 7) · 87% line coverage · pip-audit: no known vulns · 10 migrations, upgrade/downgrade/check clean |
| Web | typecheck, lint, 95 component tests, 20 api-client tests, production build; Playwright E2E (2 specs × desktop + 360px) passing against the **real** backend |
| Mobile | `flutter analyze` clean · 51 tests · not yet built for a device or run against the real backend |
| Containers | backend image built; compose stack booted (migrate → api → worker/beat) and outbox email dispatch verified |
| CI | workflow written, not yet executed on GitHub (repo has no remote) |

## Phase 1 (Product → Publish) progress

| Area | Backend | Web | Mobile |
|---|---|---|---|
| Catalog (CAT-001…010) | TESTED (incl. add variant, category move, collection membership, variant lock) | Products list, editor, CSV import, categories: TESTED + E2E vs real backend | Product go-live, AI attribute confirmation |
| Media (MED-001…004, 008–011) | TESTED, incl. HEIC, GPS stripping, malware scan path, Auto Reels (Nepali overlays verified in Docker) | In progress | Capture + resumable signed upload: TESTED + live run |
| AI Product Studio (CNT-001…006, AIG-012/015) | TESTED with the sandbox provider. Brand voice and eval harness built. **Not yet called with a live model** | Studio screens TESTED + E2E | Draft review: TESTED + live run |
| Content engine (CNT-008…011) | TESTED | Calendar + post workflow TESTED | Posts: submit/approve/schedule |
| Channels (CHN-003/004/009/010/011/013) | TESTED framework + sandbox; **WooCommerce IMPLEMENTED** (contract-tested incl. per-store webhooks); Meta/TikTok/Shopify BLOCKED on platform approval | Channels settings (OAuth + WooCommerce keys) TESTED + E2E | Publish + reconnect hand-off |
| Exception Inbox | TESTED (derived from live state) | Live on Home TESTED | Live on Home: TESTED |

Totals (2026-11-02): backend 165 tests (87% coverage, 10 migrations); web 206 + api-client 25 tests and E2E 8/8 (4 specs × desktop/360px) against the real backend with worker; mobile all tests pass plus one live end-to-end run. The mobile app has never run on a device (GAP-MOBILE-TOOLCHAIN).

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
| Design tokens + web/Flutter design systems | Met (tested) |

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
| AIG-012 | prompt registry | P1 | TESTED | AIG-001 | apps/backend/app/domains/ai/prompts.py | test_studio | Versioned built-in prompts with DB override; version recorded per execution |
| AIG-013 | schema validation | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/gateway.py | test_ai_gateway::test_schema_violation…, test_low_confidence… | JSON-schema validation, confidence → needs_review |
| AIG-014 | cost ledger | P0 | TESTED | AIG-001 | apps/backend/app/domains/ai/models.py, gateway.py | test_ai_gateway::test_structured_success… | Per-attempt ledger: provider/model/tokens/cost/latency/credits/plan/prompt/trace |
| AIG-015 | eval harness | P1 | IMPLEMENTED | AIG-012 | apps/backend/app/domains/ai/evals/, apps/backend/evals/ | test_evals | Deterministic scorers + gates (schema, grounding), Nepali-script check, invented-size check; CLI writes JSON reports and refuses to call a sandbox run a quality result. **Needs real consented seller photos + a live key to measure quality** |
| CAT-001 | Product | P1 | TESTED | IAM-006 | apps/backend/app/domains/catalog/ | test_catalog | Product with i18n fields, SEO, tags, optimistic lock (version) |
| CAT-002 | Variant | P1 | TESTED | CAT-001 | apps/backend/app/domains/catalog/models.py, service.py | test_catalog | Variants ≤100, unique option combination, dims/weight |
| CAT-003 | options | P1 | TESTED | CAT-002 | apps/backend/app/domains/catalog/service.py | test_catalog | ≤3 options, values case-insensitive, relational links |
| CAT-004 | taxonomy | P1 | TESTED | CAT-001 | apps/backend/app/domains/catalog/service.py | test_catalog::test_categories_and_collections | Merchant taxonomy tree (≤6 levels, materialised path); no shared global taxonomy yet |
| CAT-005 | pricing | P1 | TESTED | CAT-002 | apps/backend/app/domains/catalog/rules.py | test_catalog | Integer paisa; compare-at > price; range guard against unit mistakes |
| CAT-006 | cost | P1 | TESTED | CAT-002 | apps/backend/app/domains/catalog/models.py | test_catalog | Variant cost + supplier cost/MOQ/lead time (VariantSupplier) |
| CAT-007 | lifecycle | P1 | TESTED | CAT-001 | apps/backend/app/domains/catalog/service.py | test_catalog::test_lifecycle… | draft/active/archived machine; publish guards incl. unconfirmed AI attributes |
| CAT-008 | import | P1 | TESTED | CAT-001,FND-012 | apps/backend/app/domains/catalog/imports.py | test_catalog::test_csv_import… | Async CSV (rupee parsing, grouping, per-product savepoints, row errors, dup-file guard). Runs inside outbox handler (GAP-IMPORT-QUEUE) |
| CAT-009 | SKU rules | P1 | TESTED | CAT-002 | apps/backend/app/domains/catalog/rules.py | test_catalog::test_rules_units | SKU format + generation, GTIN checksum, unique per merchant |
| CAT-010 | listing mapping | P1 | TESTED | CHN-001 | apps/backend/app/domains/channels/service.py | test_channels | Listing per connection; desired/actual reconcile per product version |
| MED-001 | signed upload | P1 | TESTED | FND-006 | apps/backend/app/domains/media/ | test_media | Signed PUT (dev object store for local backend; S3 presign untested GAP-S3) |
| MED-002 | validation | P1 | TESTED | MED-001 | apps/backend/app/domains/media/imaging.py, scanner.py | test_media | Byte-sniffed format, bomb guard, clamd INSTREAM; scanner outage retries |
| MED-003 | EXIF | P1 | TESTED | MED-002 | apps/backend/app/domains/media/imaging.py | test_media::test_imaging_applies… | Orientation applied; all metadata incl. GPS stripped from derivatives |
| MED-004 | derivatives | P1 | TESTED | MED-003 | apps/backend/app/domains/media/imaging.py | test_media | thumb/medium/white-square/4:5/9:16; pad never crops or recolours |
| MED-005 | background removal | P1 | NOT_STARTED | AIG-005 | — | — | Background removal needs an image-edit provider + fidelity review (GAP-AI-MEDIA) |
| MED-006 | image generation | P1 | NOT_STARTED | AIG-005 | — | — | AI lifestyle images: provider not chosen (GAP-AI-MEDIA) |
| MED-007 | fidelity review | P1 | NOT_STARTED | MED-006 | — | — | Fidelity review UI/flow for generated images |
| MED-008 | Auto Reel | P1 | TESTED | MED-004 | apps/backend/app/domains/media/reels.py, video.py | test_reels | Templated H.264 reels, 4 aspects, product never cropped/covered, catalog price, usage metered; music not included (no licensed library) |
| MED-009 | video job state | P1 | TESTED | MED-008 | apps/backend/app/domains/media/models.py (VideoJob), video.py | test_reels | queued→generating→post_processing→ready/failed/cancelled; premium provider path uses same states (provider not chosen) |
| MED-010 | media metering | P1 | IMPLEMENTED | BIL-006 | apps/backend/app/domains/media/service.py | test_media::test_upload_request_validation… | storage_mb gauge; image/video generation metering awaits MED-006/008 |
| MED-011 | lifecycle cleanup | P1 | IMPLEMENTED | MED-001 | apps/backend/app/domains/media/service.py, worker/tasks.py | — | Abandoned uploads purged after 24h; deleted assets' objects removed |
| CNT-001 | brand voice | P1 | TESTED | CNT-002 | apps/backend/app/domains/merchants/, studio/service.py | test_studio::test_brand_voice… | Tone/emoji/avoid-words/sample caption on merchant (audited), injected into prompt v2 as style-only guidance |
| CNT-002 | titles | P1 | TESTED | AIG-001 | apps/backend/app/domains/studio/ | test_studio | Titles en/ne via Product Studio extraction |
| CNT-003 | descriptions | P1 | TESTED | CNT-002 | apps/backend/app/domains/studio/ | test_studio | Descriptions + bullets en/ne |
| CNT-004 | SEO | P1 | TESTED | CNT-002 | apps/backend/app/domains/studio/ | test_studio | SEO title/description with length limits |
| CNT-005 | captions | P1 | TESTED | CNT-002 | apps/backend/app/domains/studio/, content/ | test_studio, test_content | Per-platform captions (instagram/facebook/tiktok) + grounding check |
| CNT-006 | hashtags | P1 | TESTED | CNT-002 | apps/backend/app/domains/studio/service.py | test_studio | Hashtags normalised |
| CNT-007 | translation | P1 | IN_PROGRESS | CNT-002 | apps/backend/app/domains/studio/prompts.py | test_studio | Nepali generated with the listing; no standalone translation task yet |
| CNT-008 | calendar | P1 | TESTED | CHN-002 | apps/backend/app/domains/content/ | test_content | Backend + web calendar (week/month, merchant timezone, unscheduled list) + mobile posts |
| CNT-009 | approval | P1 | TESTED | CNT-008 | apps/backend/app/domains/content/service.py | test_content | Approval policy by automation mode + grounding issues |
| CNT-010 | scheduler | P1 | TESTED | CNT-009 | apps/backend/app/domains/content/service.py, worker/ | test_content | 30s beat scheduler, idempotent provider call |
| CNT-011 | retry | P1 | TESTED | CNT-010 | apps/backend/app/domains/content/service.py | test_content::test_transient_failures… | Backoff retry → failed + exception event; reconnect handling |
| CNT-012 | creative attributes on posts and video jobs (hook, duration, price timing, language mix, CTA, caption length, background, template, posting window) [Phase 1, pull-forward] | P1 | TESTED | CNT-008, MED-008 | apps/backend/app/domains/content/creative.py, service.py, migration 0010 | test_creative_attributes | Derived (language mix, CTA, caption bucket, local posting hour, Auto Reel duration/price timing/template) + seller-declared (hook, human presence, background) with CHECK vocabularies; existing posts backfilled. Web/mobile don't yet expose the declared fields (optional) |
| CNT-013 | content metrics ingestion interface on adapters (fetch_content_metrics) [Phase 7] | P7 | NOT_STARTED | — | — | — |  |
| CNT-014 | inquiry/order attribution to content (explicit ref → window heuristic; method recorded) [Phase 7] | P7 | NOT_STARTED | — | — | — |  |
| CHN-001 | adapter interface | P1 | TESTED | — | apps/backend/app/domains/integrations/base.py, registry.py | test_platform::test_registry… | Channel/Payment/Courier/Notification interfaces |
| CHN-002 | capabilities | P1 | TESTED | CHN-001 | apps/backend/app/domains/integrations/base.py | test_platform::test_registry… | Capability enums; sandbox adapters refused in production |
| CHN-003 | OAuth | P1 | TESTED | CHN-001 | apps/backend/app/domains/channels/ | test_channels | OAuth flow + web callback page (state check, single exchange) + E2E studio→channels |
| CHN-004 | token refresh | P1 | TESTED | CHN-003 | apps/backend/app/domains/channels/service.py | test_channels::test_token_refresh… | Proactive refresh; auth failure → expired + event |
| CHN-005 | Meta/Instagram | P1 | BLOCKED | CHN-003 | — | — | Meta/Instagram: needs Meta app + App Review for instagram_content_publish / pages_manage_posts (GAP-CHANNEL-APPS) |
| CHN-006 | TikTok | P1 | BLOCKED | CHN-003 | — | — | TikTok: needs TikTok for Developers app + Content Posting API audit (GAP-CHANNEL-APPS) |
| CHN-007 | TikTok Shop where eligible | P1 | BLOCKED | CHN-003 | — | — | TikTok Shop: seller-region eligibility for Nepal unconfirmed (GAP-CHANNEL-APPS) |
| CHN-008 | Shopify | P1 | BLOCKED | CHN-003 | — | — | Shopify: needs Partner app credentials (GAP-CHANNEL-APPS) |
| CHN-009 | WooCommerce | P1 | IMPLEMENTED | CHN-001 | apps/backend/app/domains/integrations/woocommerce.py | test_woocommerce (REST v3 contract, mocked HTTP) | Real adapter: API-key connect with live verification + currency guard, variable products/variations by SKU, stock, orders fetch, webhook HMAC. **Not yet run against a live store**; per-store webhook registration not built |
| CHN-010 | webhook gateway | P1 | TESTED | CHN-001 | apps/backend/app/domains/channels/ | test_channels::test_webhook… | Verify→record→dedupe→fast 200→async; unverified never stored |
| CHN-011 | dedupe | P1 | TESTED | CHN-010 | apps/backend/app/domains/channels/models.py | test_channels | Unique (provider, event id); duplicate counter |
| CHN-012 | reconciliation | P1 | NOT_STARTED | CHN-008 | — | — | Periodic listing/inventory reconciliation against provider |
| CHN-013 | health UI | P1 | TESTED | CHN-003 | apps/backend/app/domains/channels/ | test_channels | Health API + web Channels settings (status, reconnect, health check, disconnect) |
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
| ORD-012 | structured Nepal address model (province/district/municipality/ward/area/landmark) + validation [pull-forward for CRI/CODI] | P2 | NOT_STARTED | CRM-003 | — | — | Pull-forward (Phase 2): structured Nepal address model |
| INV-001 | locations | P2 | NOT_STARTED | — | — | — |  |
| INV-002 | ledger | P2 | NOT_STARTED | — | — | — |  |
| INV-003 | reservations | P2 | NOT_STARTED | — | — | — |  |
| INV-004 | reserve/release | P2 | NOT_STARTED | — | — | — |  |
| INV-005 | concurrency tests | P2 | NOT_STARTED | — | — | — |  |
| INV-006 | adjustment | P2 | NOT_STARTED | — | — | — |  |
| INV-007 | transfer | P2 | NOT_STARTED | — | — | — |  |
| INV-008 | low-stock | P2 | NOT_STARTED | — | — | — |  |
| INV-009 | channel sync | P3 | NOT_STARTED | — | — | — |  |
| INV-010 | reconciliation | P3 | NOT_STARTED | — | — | — |  |
| PAY-001 | adapter | P0 | IMPLEMENTED | CHN-001 | apps/backend/app/domains/integrations/base.py, sandbox.py | test_platform | Interface + sandbox wallet + COD adapter; no Nepal gateway yet (GAP-PAY-NP) |
| PAY-002 | COD | P2 | NOT_STARTED | — | — | — |  |
| PAY-003 | payment intent | P2 | NOT_STARTED | — | — | — |  |
| PAY-004 | verify | P2 | NOT_STARTED | — | — | — |  |
| PAY-005 | webhook | P2 | NOT_STARTED | — | — | — |  |
| PAY-006 | reconcile | P3 | NOT_STARTED | — | — | — |  |
| PAY-007 | refund | P4 | NOT_STARTED | — | — | — |  |
| PAY-008 | idempotency tests | P2 | NOT_STARTED | — | — | — |  |
| PAY-009 | failed payment | P2 | NOT_STARTED | — | — | — |  |
| PAY-010 | settlement dashboard | P3 | NOT_STARTED | — | — | — |  |
| FUL-001 | courier adapter | P0 | IMPLEMENTED | CHN-001 | apps/backend/app/domains/integrations/base.py, sandbox.py | test_platform | Interface + sandbox courier; no Nepal courier yet (GAP-COURIER-NP) |
| FUL-002 | rates | P3 | NOT_STARTED | — | — | — |  |
| FUL-003 | shipment state | P3 | NOT_STARTED | — | — | — |  |
| FUL-004 | labels | P3 | NOT_STARTED | — | — | — |  |
| FUL-005 | pickup | P3 | NOT_STARTED | — | — | — |  |
| FUL-006 | tracking | P3 | NOT_STARTED | — | — | — |  |
| FUL-007 | notify | P3 | NOT_STARTED | — | — | — |  |
| FUL-008 | delivery failure | P3 | NOT_STARTED | — | — | — |  |
| FUL-009 | smart courier | P6 | NOT_STARTED | — | — | — |  |
| FUL-010 | reconciliation | P3 | NOT_STARTED | — | — | — |  |
| RET-001 | policy | P4 | NOT_STARTED | — | — | — |  |
| RET-002 | eligibility | P4 | NOT_STARTED | — | — | — |  |
| RET-003 | request | P4 | NOT_STARTED | — | — | — |  |
| RET-004 | evidence | P4 | NOT_STARTED | — | — | — |  |
| RET-005 | approval | P4 | NOT_STARTED | — | — | — |  |
| RET-006 | reverse shipment | P4 | NOT_STARTED | — | — | — |  |
| RET-007 | inspection | P4 | NOT_STARTED | — | — | — |  |
| RET-008 | exchange | P4 | NOT_STARTED | — | — | — |  |
| RET-009 | refund calculation | P4 | NOT_STARTED | — | — | — |  |
| RET-010 | auto-refund threshold | P4 | NOT_STARTED | — | — | — |  |
| RET-011 | abuse signals | P4 | NOT_STARTED | — | — | — |  |
| RET-012 | controlled return-reason vocabulary + free text [pull-forward for RTI] | P4 | NOT_STARTED | RET-003 | — | — | Pull-forward (Phase 4): controlled return-reason vocabulary |
| AUT-001 | workflow schema | P5 | NOT_STARTED | — | — | — |  |
| AUT-002 | triggers | P5 | NOT_STARTED | — | — | — |  |
| AUT-003 | conditions | P5 | NOT_STARTED | — | — | — |  |
| AUT-004 | actions | P5 | NOT_STARTED | — | — | — |  |
| AUT-005 | versions | P5 | NOT_STARTED | — | — | — |  |
| AUT-006 | execution | P5 | NOT_STARTED | — | — | — |  |
| AUT-007 | delay | P5 | NOT_STARTED | — | — | — |  |
| AUT-008 | branch | P5 | NOT_STARTED | — | — | — |  |
| AUT-009 | approval | P5 | NOT_STARTED | — | — | — |  |
| AUT-010 | retry | P5 | NOT_STARTED | — | — | — |  |
| AUT-011 | exceptions | P5 | NOT_STARTED | — | — | — |  |
| AUT-012 | logs | P5 | NOT_STARTED | — | — | — |  |
| AUT-013 | templates | P5 | NOT_STARTED | — | — | — |  |
| AUT-014 | builder UI | P5 | NOT_STARTED | — | — | — |  |
| AUT-015 | dry-run | P5 | NOT_STARTED | — | — | — |  |
| AUT-016 | Autonomous Decision Policy: risk classes R0–R4, mode × class matrix, confidence + staleness gates | P5 | NOT_STARTED | — | — | — |  |
| AUT-017 | merchant thresholds (refund, discount, PO, campaign budget, stock transfer, price-change band) with audit | P5 | NOT_STARTED | — | — | — |  |
| AUT-018 | AutomationActionLog: actor/outcome/eligibility/exclusion for every operational action (APS source) | P5 | NOT_STARTED | ORD-001 | — | — | Instrument from Phase 2 onward; APS source |
| AUT-019 | decision records (inputs refs, rule hit, confidence, impact) + seller-facing explanation | P5 | NOT_STARTED | — | — | — |  |
| AUT-020 | intelligence-derived triggers and profit-aware conditions (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| AUT-021 | recommendation → policy → approval → idempotent execution path (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| ANA-001 | sales | P5 | NOT_STARTED | — | — | — |  |
| ANA-002 | channels | P5 | NOT_STARTED | — | — | — |  |
| ANA-003 | products | P5 | NOT_STARTED | — | — | — |  |
| ANA-004 | fulfillment | P5 | NOT_STARTED | — | — | — |  |
| ANA-005 | returns | P5 | NOT_STARTED | — | — | — |  |
| ANA-006 | AI/automation | P5 | NOT_STARTED | — | — | — |  |
| ANA-007 | product P&L | P6 | NOT_STARTED | — | — | — |  |
| ANA-008 | profit dashboard | P6 | NOT_STARTED | — | — | — |  |
| ANA-009 | Store Manager tools | P6 | NOT_STARTED | — | — | — |  |
| ANA-010 | recommendations | P6 | NOT_STARTED | — | — | — |  |
| PRO-001 | suppliers | P8 | NOT_STARTED | — | — | — |  |
| PRO-002 | supplier products | P8 | NOT_STARTED | — | — | — |  |
| PRO-003 | purchase orders | P8 | NOT_STARTED | — | — | — |  |
| PRO-004 | approvals | P8 | NOT_STARTED | — | — | — |  |
| PRO-005 | receiving | P8 | NOT_STARTED | — | — | — |  |
| PRO-006 | landed cost | P8 | NOT_STARTED | — | — | — |  |
| PRO-007 | reorder recommendations | P8 | NOT_STARTED | — | — | — |  |
| ADM-001 | merchant lookup | P0+ | IMPLEMENTED | IAM-005 | apps/backend/app/domains/admin/router.py | test_platform::test_admin_requires_staff_with_mfa | API only; admin UI not built |
| ADM-002 | usage/credits | P0+ | IMPLEMENTED | BIL-006 | apps/backend/app/domains/admin/router.py | — | Usage + credit balance in merchant detail API |
| ADM-003 | provider health | P0+ | IMPLEMENTED | AIG-008 | apps/backend/app/domains/admin/router.py | — | Provider/circuit health API |
| ADM-004 | channel health | P0+ | IMPLEMENTED | CHN-013 | apps/backend/app/domains/channels/router.py | — | Connection health per merchant via API; admin UI pending |
| ADM-005 | webhook explorer | P0+ | TESTED | CHN-010 | apps/backend/app/domains/channels/router.py | test_channels::test_webhook_unknown… | Admin webhook explorer + replay (audited) |
| ADM-006 | replay | P0+ | IMPLEMENTED | FND-012 | apps/backend/app/domains/admin/router.py | test_idempotency_outbox (requeue) | Outbox replay (audited) |
| ADM-007 | DLQ | P0+ | IMPLEMENTED | FND-012 | apps/backend/app/domains/admin/router.py | — | Dead outbox events listing |
| ADM-008 | plan editor | P0+ | NOT_STARTED | — | — | — |  |
| ADM-009 | routing editor | P0+ | NOT_STARTED | — | — | — |  |
| ADM-010 | refund review | P0+ | NOT_STARTED | — | — | — |  |
| ADM-011 | feature flags | P0+ | IMPLEMENTED | FND-011 | apps/backend/app/domains/admin/router.py | test_platform::test_feature_flags… | Upsert flags (audited) |
| UX-001 | design tokens | P0 | TESTED | — | packages/design-system/ | CI diff check of generated outputs | JSON → CSS vars, TS, Dart |
| UX-002 | web library | P0 | TESTED | UX-001 | apps/web/src/components | 95 vitest tests; E2E vs real backend | No 3rd-party visual library; Radix for behaviour only |
| UX-003 | Flutter theme | P0 | TESTED | UX-001 | apps/mobile/lib/design | flutter test (51) | Theme from generated tokens; bundled Inter + Noto Sans Devanagari |
| UX-004 | Product Brain | P1 | NOT_STARTED | — | — | — |  |
| UX-005 | Channel Sync Rail | P1 | NOT_STARTED | — | — | — |  |
| UX-006 | Autopilot Strip | P1 | IMPLEMENTED | UX-002 | apps/web/src/components/commerce, apps/mobile/lib/features/home | widget/component tests | Autopilot Status Strip (no data source until AUT) |
| UX-007 | Exception Inbox | P1 | TESTED | UX-002 | apps/backend/app/domains/exceptions/, apps/web, apps/mobile | test_exceptions | Live Exception Inbox (web Home + mobile Home) from GET /exceptions; actions routed; E2E vs real backend |
| UX-008 | Order Journey | P1 | NOT_STARTED | — | — | — |  |
| UX-009 | AI Timeline | P1 | NOT_STARTED | — | — | — |  |
| UX-010 | Profit Card | P1 | NOT_STARTED | — | — | — |  |
| UX-011 | Video Credit Meter | P1 | TESTED | BIL-006 | apps/web …/settings/plan, apps/mobile …/settings | component tests | Video Credit Meter + plan-aware usage (not-in-plan, overage policy, gauges); verified against real backend |
| UX-012 | Inventory Risk | P1 | NOT_STARTED | — | — | — |  |
| UX-013 | real states | P1 | IN_PROGRESS | — | apps/web, apps/mobile | component tests | Loading/empty/error/offline/permission states for Phase 0 screens |
| UX-014 | accessibility | P1 | IN_PROGRESS | — | apps/web, apps/mobile | — | Keyboard, focus, labels, 48dp; no full screen-reader audit yet |
| UX-015 | bilingual review | P1 | IN_PROGRESS | — | apps/web/src/i18n, apps/mobile/lib/core/l10n/arb | key-parity tests | en/ne complete for Phase 0; Nepali not yet reviewed by a native copy editor |
| UX-016 | Autopilot Control Center (home): "Your store is running." + Needs Your Attention (Phase 5) | P5 | NOT_STARTED | — | — | — |  |
| UX-017 | Autopilot Score component (breakdown, exclusions, thin-data state) (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| UX-018 | Product Brain card (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| UX-019 | Recommendation / Profit Recommendation Card with explanation pattern (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| UX-020 | Return Insight Card + Courier Recommendation Card (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| UX-021 | Commerce Memory insight with correction (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| UX-022 | Creative Genome panel (Phase 7) | P7 | NOT_STARTED | — | — | — |  |
| PBR-001 | ProductIntelligenceProfile schema + method_version + as_of + data-completeness | P6 | NOT_STARTED | — | — | — |  |
| PBR-002 | demand rate (EWMA, in-stock days only, seasonality index) per product/variant | P6 | NOT_STARTED | — | — | — |  |
| PBR-003 | margin + expected contribution per unit (uses ANA true-profit components; "not included" handling) | P6 | NOT_STARTED | — | — | — |  |
| PBR-004 | stock cover days + stockout history | P6 | NOT_STARTED | — | — | — |  |
| PBR-005 | return rate + top reasons (from RET-012) per product/variant/size | P6 | NOT_STARTED | — | — | — |  |
| PBR-006 | channel conversion + content performance summary (from CGN metrics when available) | P6 | NOT_STARTED | — | — | — |  |
| PBR-007 | FAQ clustering from conversations + seller-approved answers (ProductFAQ) | P6 | NOT_STARTED | — | — | — |  |
| PBR-008 | incremental refresh on events + nightly full recompute; freshness SLO + metrics | P6 | NOT_STARTED | — | — | — |  |
| PBR-009 | API GET /product-brain/products/{id} (+faqs); Sales Agent + Store Manager tool get_product_brain | P6 | NOT_STARTED | — | — | — |  |
| PBR-010 | golden-value tests + offline backtest of demand rate | P6 | NOT_STARTED | — | — | — |  |
| MEM-001 | CommerceMemoryMetric registry (named metrics, definitions, periods, method_version) + storage | P6 | NOT_STARTED | — | — | — |  |
| MEM-002 | metric computation jobs (idempotent per period key) for products, customers, logistics, operations | P6 | NOT_STARTED | — | — | — |  |
| MEM-003 | CommerceMemoryFact schema (typed fact_type JSON schemas, confidence, evidence_ref, validity, versions) | P6 | NOT_STARTED | — | — | — |  |
| MEM-004 | fact derivation rules (e.g. fit_runs_small, best_post_window, repeat_cycle_days) with thresholds + min samples | P6 | NOT_STARTED | — | — | — |  |
| MEM-005 | merchant correction (reject/edit fact → new version, respected by derivations), audited | P6 | NOT_STARTED | — | — | — |  |
| MEM-006 | privacy: customer-level facts limited to operational needs; deletion/anonymisation path | P6 | NOT_STARTED | — | — | — |  |
| MEM-007 | API summaries + Store Manager tool get_memory_facts | P6 | NOT_STARTED | — | — | — |  |
| MEM-008 | recompute on method_version change (backfill job) | P6 | NOT_STARTED | — | — | — |  |
| APS-001 | capability registry (eligibility rules per capability, steps-per-operation constants) | P6 | NOT_STARTED | — | — | — |  |
| APS-002 | daily AutopilotMetric aggregation from AutomationActionLog (A/F/M/X with reasons) | P6 | NOT_STARTED | — | — | — |  |
| APS-003 | AutopilotScoreSnapshot (volume-weighted overall; thin-data handling) | P6 | NOT_STARTED | — | — | — |  |
| APS-004 | improvement recommendations (largest gap with config lever; estimated coverage from last 30 days) | P6 | NOT_STARTED | — | — | — |  |
| APS-005 | API + Control Center + Store Manager tool; upsell hook via REC (plan_upgrade) | P6 | NOT_STARTED | — | — | — |  |
| APS-006 | audit sampling: manual-audit comparison tool (±2 points exit criterion) | P6 | NOT_STARTED | — | — | — |  |
| APS-007 | anomaly flag on sudden score jumps | P6 | NOT_STARTED | — | — | — |  |
| REC-001 | Recommendation + RecommendationEvidence + RecommendationOutcome models | P6 | NOT_STARTED | — | — | — |  |
| REC-002 | typed recommended_action commands (mapped to automation actions) | P6 | NOT_STARTED | — | — | — |  |
| REC-003 | explanation object builder (what/why/evidence/confidence/impact/action) — deterministic | P6 | NOT_STARTED | — | — | — |  |
| REC-004 | insight-narrative AI task with faithfulness validation (no new numbers) | P6 | NOT_STARTED | — | — | — |  |
| REC-005 | policy routing (AUT-016) → auto / approval (Needs Your Attention) / blocked | P6 | NOT_STARTED | — | — | — |  |
| REC-006 | accept/reject APIs (idempotent; reasons) + expiry | P6 | NOT_STARTED | — | — | — |  |
| REC-007 | outcome measurement jobs (pre/post, holdout/DiD where possible) + impact analytics | P6 | NOT_STARTED | — | — | — |  |
| REC-008 | dedupe + rate limiting of recommendations per merchant (no spam) | P6 | NOT_STARTED | — | — | — |  |
| RTI-001 | return-reason metrics by product/variant/size/content version/supplier/campaign | P6 | NOT_STARTED | — | — | — |  |
| RTI-002 | pattern detection (share vs baseline, min sample, significance) → ReturnInsight | P6 | NOT_STARTED | — | — | — |  |
| RTI-003 | suspected-cause linking (content/image version shown at purchase, supplier batch) | P6 | NOT_STARTED | — | — | — |  |
| RTI-004 | recommendations (size guide, fit warning, description, image, stop creative, size-up hint, supplier flag) | P6 | NOT_STARTED | — | — | — |  |
| RTI-005 | before/after impact measurement | P6 | NOT_STARTED | — | — | — |  |
| RTI-006 | Return Insight Card + Sales Agent fit hint | P6 | NOT_STARTED | — | — | — |  |
| CRI-001 | CourierPerformanceMetric by courier × route × weight band × COD | P6 | NOT_STARTED | — | — | — |  |
| CRI-002 | expected-cost model (price + failure cost × failure prob + settlement delay cost) | P6 | NOT_STARTED | — | — | — |  |
| CRI-003 | selection modes cheapest/fastest/smart/preferred-only with policy integration | P6 | NOT_STARTED | — | — | — |  |
| CRI-004 | explanation ("selected because …") + alternatives | P6 | NOT_STARTED | — | — | — |  |
| CRI-005 | cold-start fallback (merchant preference/rules) with explicit low-confidence label | P6 | NOT_STARTED | — | — | — |  |
| CRI-006 | ETA calibration monitoring | P6 | NOT_STARTED | — | — | — |  |
| CODI-001 | feature set (allowed inputs only) + static prohibited-feature check | P6 | NOT_STARTED | — | — | — |  |
| CODI-002 | CODRiskAssessment (level, score, factors with evidence, recommended action, model_version) | P6 | NOT_STARTED | — | — | — |  |
| CODI-003 | decision-policy integration (LOW auto, MEDIUM per policy, HIGHER review/advance) | P6 | NOT_STARTED | — | — | — |  |
| CODI-004 | merchant override + dispute workflow (audited) | P6 | NOT_STARTED | — | — | — |  |
| CODI-005 | outcome capture + calibration monitoring + regional disparity report | P6 | NOT_STARTED | — | — | — |  |
| CODI-006 | phone verification + partial-advance flows (with PAY) | P6 | NOT_STARTED | — | — | — |  |
| CGN-001 | CreativePerformanceMetric (views, engagement, clicks, inquiries, orders, attributed contribution) | P7 | NOT_STARTED | — | — | — |  |
| CGN-002 | genome computation (outcome-weighted effects, min sample, shrinkage) → CreativeGenomeProfile | P7 | NOT_STARTED | — | — | — |  |
| CGN-003 | CreativeExperiment (hypothesis, variants, stopping rule) | P7 | NOT_STARTED | — | — | — |  |
| CGN-004 | genome inputs to Studio prompts, Auto Reel template choice, video concepts, schedule suggestions (genome_version recorded) | P7 | NOT_STARTED | — | — | — |  |
| CGN-005 | Creative Genome panel + Store Manager tool | P7 | NOT_STARTED | — | — | — |  |
| CGN-006 | impact measurement of genome-informed content vs baseline | P7 | NOT_STARTED | — | — | — |  |
| SPI-001 | SupplierPerformanceMetric (landed cost, defect, return, on-time, lead-time variance, contribution/unit) | P8 | NOT_STARTED | — | — | — |  |
| SPI-002 | batch/lot linkage receiving → returns/defects | P8 | NOT_STARTED | — | — | — |  |
| SPI-003 | true-economics supplier recommendation with explanation | P8 | NOT_STARTED | — | — | — |  |
| SPI-004 | reorder recommendation using true economics + lead time | P8 | NOT_STARTED | — | — | — |  |
| TWIN-001 | section registry (owner domain, TTL, max staleness per consumer) | P9 | NOT_STARTED | — | — | — |  |
| TWIN-002 | event-driven incremental updaters (monotonic source_version) | P9 | NOT_STARTED | — | — | — |  |
| TWIN-003 | periodic reconciliation + on-read freshness check + stale flag | P9 | NOT_STARTED | — | — | — |  |
| TWIN-004 | StoreTwinSnapshot daily | P9 | NOT_STARTED | — | — | — |  |
| TWIN-005 | API /twin/summary + Store Manager tool get_twin_section | P9 | NOT_STARTED | — | — | — |  |
| TWIN-006 | freshness SLO monitoring | P9 | NOT_STARTED | — | — | — |  |
| SIM-001 | SimulationRun model + async execution | P9 | NOT_STARTED | — | — | — |  |
| SIM-002 | discount scenario (elasticity from own history, margin, stock duration, return impact) | P9 | NOT_STARTED | — | — | — |  |
| SIM-003 | purchase-quantity scenario (stockout probability, cash tied up) | P9 | NOT_STARTED | — | — | — |  |
| SIM-004 | ad-budget shift scenario (requires connected ad spend) | P9 | NOT_STARTED | — | — | — |  |
| SIM-005 | assumptions/confidence/range presentation; no execution without separate approval | P9 | NOT_STARTED | — | — | — |  |
| SIM-006 | backtest calibration of simulation estimates | P9 | NOT_STARTED | — | — | — |  |
| NET-001 | privacy impact assessment + legal review (gate) | P10 | NOT_STARTED | — | — | — |  |
| NET-002 | aggregation service (k ≥ 10, dominance ≤ 30%, suppression) — only cross-tenant reader | P10 | NOT_STARTED | — | — | — |  |
| NET-003 | opt-out/opt-in controls (contribute vs consume) | P10 | NOT_STARTED | — | — | — |  |
| NET-004 | aggregates: category demand trends, regional demand, price bands, return trends, courier route success, seasonality | P10 | NOT_STARTED | — | — | — |  |
| NET-005 | priors for cold start (courier, creative) with clear "network-based" labelling | P10 | NOT_STARTED | — | — | — |  |
| NET-006 | privacy tests (no cross-tenant leakage, threshold enforcement) | P10 | NOT_STARTED | — | — | — |  |

Status counts: BLOCKED 4, IMPLEMENTED 23, IN_PROGRESS 9, NOT_STARTED 207, TESTED 74. **PRODUCTION_READY: 0** (no staging/alerts/runbooks yet).
