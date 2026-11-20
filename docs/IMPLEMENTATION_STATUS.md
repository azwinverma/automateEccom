# Implementation Status

Source of truth for progress. IDs from `specs/23_ENGINEERING_BACKLOG.md`.
Statuses: NOT_STARTED · IN_PROGRESS · BLOCKED · IMPLEMENTED · TESTED · PRODUCTION_READY.

**Nothing is PRODUCTION_READY.** Per `specs/24_DEFINITION_OF_DONE.md` that needs a deployed staging environment, alerts, runbooks and an operational review; none exist yet (see `docs/KNOWN_GAPS.md`). `TESTED` = implemented with automated tests passing locally against real PostgreSQL/Redis.

Phases follow `specs/22_PHASED_ROADMAP.md` (v1, 2026-11-02): **0** Foundation · **1** Product-to-Publish · **2** Conversation-to-Order · **3** Order-to-Delivery · **4** Returns/Refunds/Exchanges · **5** Automation + Exception OS · **6** Commerce Intelligence Foundation · **7** Creative Intelligence · **8** Procurement/Supplier Intelligence · **9** Digital Store Twin + Simulation · **10** Network Intelligence & enterprise scale. Intelligence phases (6+) are gated on trustworthy operational data from 2–5.

_Last updated: 2026-11-20 (Phase 8)._

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

Totals (2026-11-02): backend 165 tests (87% coverage, 10 migrations); web 209 + api-client 25 tests and E2E 8/8 (4 specs × desktop/360px) against the real backend with worker; mobile all tests pass plus one live end-to-end run. The mobile app has never run on a device (GAP-MOBILE-TOOLCHAIN).

## Where development stands (2026-11-02)
- **Phase 0:** engineering complete. Exit is blocked externally: CI needs a git remote (FND-007) and
  staging needs a hosting decision (FND-008).
- **Phase 1:** all unblocked feature work is done, including the CNT-012 pull-forward. Exit is blocked
  externally:
  - publishing to a **real** channel needs a live WooCommerce store, or Meta/TikTok/Shopify app approval
  - live AI quality needs a provider key
  - image AI (MED-005…007) needs a provider decision

  Remaining unblocked Phase 1 hardening: CHN-012 reconciliation, BIL-009 alert notifications, the
  FND-006 S3 path against MinIO, CNT-007 standalone translation, and AIG-008 health-aware ordering.
- **Phase 2 has not started**, per the rule to finish the earliest phase first.

## Phase 8 (Procurement + Supplier Intelligence): built 2026-11-20
- **Built and tested:** suppliers with contact/terms and per-variant terms (price, MOQ, lead time,
  preferred); purchase orders (idempotent, MOQ warnings, share text) with approval above the shop's PO
  limit; partial receiving as lots with good vs defective units; landed cost (freight + duty + other by
  line value) feeding the variant's moving-average cost, so profit uses true cost; supplier performance
  (landed cost, defect rate, returns and quality returns via lot linkage, on-time, lead time ± sd, fill
  rate, contribution per unit with components and "not included"); supplier-switch and reorder
  suggestions on true economics (reorder = lead time + safety + 30 days, MOQ, incoming stock, never for
  loss makers). Reorder replaces the Phase 6 restock suggestion when a supplier is linked.
- **Web:** Inventory → Purchase orders / Suppliers (list, form with live landed cost, detail with
  approval, send text, receiving, lots; supplier terms, products, performance), incoming stock on the
  product page, new suggestion copy. **Mobile:** purchase orders list/detail, approve/return, receive
  sheet, supplier performance card, permission-aware actions, new suggestion copy.
- **Verified in E2E** (desktop + 360px, live API + worker): PO with freight → landed cost → pending
  approval (limit 0) → approve → sent → partial receipt with a defective unit → full receipt → stock up
  by good units only.
- **Totals (2026-11-20):** backend 342 passed (24 migrations); web 310 + api-client 31; E2E 36/36;
  mobile 175 passed + 1 live-only skipped; axe 0 violations and no 360px overflow on 6 purchasing pages
  (light, dark, 360px).
- **Phase 8 exit criterion** ("landed cost + supplier metrics computed; recommendations use true
  economics") is met in code and tests; it still needs real purchasing data to be meaningful.

## Phase 7 (Creative Intelligence): built 2026-11-19, exit BLOCKED
- **Built and tested:** post results from channel insights (adapter capability, sandbox) or typed in by the
  seller from the app's insights; attribution of chats and orders to posts (explicit post reference from
  the channel → 7-day product window with decay, shared between live posts; method stored); Creative
  Genome (≥ 20 measured posts, ≥ 5 per option, shrinkage to the shop average, orders before inquiries,
  likes never recommend a pattern); experiments with a stopping rule set up front; genome guidance in
  Studio captions, Auto Reel settings and the suggested posting time, each recording the genome version;
  observational impact of genome-informed posts; creative tips on Home.
- **Web:** Content → What sells (patterns, post results with "Add results", tests), suggested time in the
  post drawer, "Use your best settings" for Auto Reels, a note on genome-informed Studio drafts. **Mobile:**
  What sells card/screen, post results + Add results, tip copy. Gated widgets no longer call plan-gated
  APIs when the plan lacks the feature (auth context now knows the plan's features).
- **Verified in E2E** (desktop + 360px, live API + worker): publish a post → type in results → shown as
  "You typed it" → What sells shows the learning state → a test is created and collecting.
- **Totals (2026-11-19):** backend 336 passed (23 migrations); web 297 + api-client 29; E2E 34/34;
  mobile 160 passed + 1 live-only skipped; axe 0 violations and no 360px overflow on Home, Content,
  What sells and Reels (light, dark, 360px), after fixing a Phase 1 calendar chip label (WCAG 2.5.3).
- **Exit BLOCKED (external):** needs content metrics from ≥ 1 real channel and measured impact on real
  posts. Meta/TikTok insights need app approval (GAP-CHANNEL-APPS); typed-in results work meanwhile.

## Phase 6 part B (profit, Product Brain, Return Intelligence, Commerce Memory): built 2026-11-19
- **Built and tested:** true profit waterfall and product P&L per spec 14 (cost recorded on each order
  line at sale; returns, refunds and failed deliveries costed; every missing input labelled "Not included"
  or "Partial"), profit settings (packaging cost, margin and return-rate limits), Product Brain profiles
  (EWMA demand over in-stock days, cover days, stockouts, margin, contribution, return rate and reasons,
  stock risk; refreshed on delivery and nightly), Return Intelligence (min-sample + binomial test against
  the shop's own baseline, reason patterns, likely causes, dismiss, 30-day before/after), Commerce Memory
  (5 registered metrics, versioned facts, seller confirm/correct/reject, method-version backfill) and
  profit-aware suggestions (restock ranked by contribution; loss makers and missing costs flagged). The
  Sales Agent gives a fit hint only when the seller has confirmed the fact.
- **Web:** /analytics (Profit, What Nivaro learned, Return patterns), Product Brain card on the product
  page, "Running out" on Home, new suggestion types. **Mobile:** Product Brain card, Profit card, new
  suggestion types, "What Nivaro has learned" screen.
- **Verified in E2E** (desktop + 360px, live API + worker): delivered orders + a size return → /analytics
  shows packaging Not included → seller sets it → included and contribution updates → product page shows
  the Product Brain card.
- **Totals (2026-11-19):** backend 327 passed (22 migrations); web 285 + api-client 27; E2E 32/32 (first
  run); mobile 149 passed + 1 live-only skipped; axe 0 violations and no 360px overflow on Home, the
  three Analytics tabs and a product page (light, dark, 360px).
- **Phase 6 exit criteria not met:** they need ≥ 90 days of real data from pilot merchants, an APS manual
  audit and offline backtests on real data. There are no pilot merchants yet.
- **Not built:** product FAQs (PBR-007), channel/content conversion (PBR-006, needs Phase 7 metrics),
  Store Manager tools (ANA-009, PBR-009/MEM-007 tool parts), profit-aware workflow conditions (AUT-020),
  APS-006, REC-004, CRI-006, CODI-006.

## Phase 6 part A (Commerce Intelligence foundation): built 2026-11-19
- **Built and tested:** Autopilot Score (A/F/M/X per capability from the action log, thin-data state,
  volume-weighted overall, daily snapshots with jump flags), recommendations (deterministic
  explanations, dedupe, at most 10 open, 30-day expiry, always R3: a manager applies them, 14-day
  before/after measurement), Courier Brain (90-day performance per courier × district × weight × COD,
  expected-cost ranking, 5 selection modes, "not enough data" fallback under 20 parcels) and COD
  Intelligence (allowed factors only, LOW/MEDIUM/HIGHER with reasons, HIGHER holds the order for review
  and never rejects, audited override and dispute, calibration report). Web: score + suggestions on
  Home, COD risk on the order, courier performance and selection in settings. Mobile: score,
  suggestions, COD risk card.
- **Verified in E2E** (desktop + 360px, live API + worker): manual courier bookings show as a 0% gap →
  suggestion applied from Home → workflow active; a customer with two failed COD parcels is held with
  reasons → override with a reason clears the hold.
- **Totals (2026-11-19):** backend 313 passed (21 migrations); web 273 + api-client 25; E2E 30/30;
  mobile 139 passed + 1 live-only skipped; axe 0 violations and no 360px overflow on Home, an order with COD risk and courier
  settings (light, dark, 360px).
- **Not built (Part B and later):** Product Brain, Return Intelligence, Commerce Memory, profit
  analytics, AI narratives for suggestions (REC-004), the score audit tool (APS-006), ETA calibration
  (CRI-006), phone verification and COD advance (CODI-006).

## Phase 5 (Automation + Control Center): built 2026-11-05
- **Built and tested:** one Decision Policy for every automated action (workflows, Sales Agent auto-send,
  delivery reattempts, return auto-approve/refund), merchant thresholds with audited loosening,
  decision records, the operational action log (APS source), the workflow engine (versions, triggers,
  conditions, waits, branches, approvals, retries, circuit breaker, dry-run, 6 templates), and the
  Control Center with real numbers. Web: Home Control Center, Automation (workflows, templates, rules &
  limits, activity), builder. Mobile: Control Center, approvals, feed, workflows on/off.
- **Exit criterion met in E2E** (desktop + 360px, live API + worker): template workflow → approval in
  Assisted → automatic in Smart → Control Center feed explains why; every decision on record.
- **Totals (2026-11-05):** backend 303 passed (20 migrations); web 266 + api-client 25; E2E 28/28;
  mobile 129 passed + 1 live-only skipped; axe 0 violations on 5 Phase 5 pages (light, dark, 360px).
- **Not production-ready:** scheduled triggers and higher-risk actions (refunds, discounts, price
  changes, POs) aren't workflow actions yet; seller email notices need a production email provider.

## Phase 4 (Returns, exchanges, refunds): built 2026-11-04
- **Built and tested:** return policy, eligibility with audited overrides, abuse signals, return
  pickups through the courier layer, inspection with restock, exchanges with reserved stock,
  idempotent threshold-controlled refunds (original payment or recorded transfer), Sales Agent
  return answers, customer return messages. Web: Returns list, return detail, order Returns panel,
  Settings → Returns, final-sale flag. Mobile: returns on orders, return detail, returns list.
- **Exit criterion met in E2E** (desktop + 360px, live API + worker): delivered → return requested →
  approved → pickup → received → inspected (restocked) → refunded → order returned.
- **Totals (2026-11-04):** backend 279 passed (19 migrations); web 259 + api-client 25; E2E 26/26;
  mobile 123 passed + 1 live-only skipped; axe 0 violations on the 4 Phase 4 pages (light, dark, 360px).
- **Not production-ready:** online refunds need a Nepal gateway (GAP-PAY-NP); no customer self-service
  return link; no photo upload for evidence in the forms; exchanges only at the same price.

## Phase 3 (Order → Delivery): built 2026-11-04
- **Built and tested:** couriers (sandbox courier + "own rider / other courier"), merchant delivery
  charges (used by chat orders and New order), rule-based courier options, idempotent booking,
  labels, pickup, tracking by signed webhooks and polling, customer shipping messages, failed-delivery
  recovery with the customer's reply, return to sender with restock, COD settlement (courier API,
  CSV, own-rider cash) with line-by-line reconciliation. Web: Deliveries, COD cash, Settings →
  Couriers, order Delivery panel, printable label. Mobile: order Delivery section, COD screen.
- **Exit criterion met in E2E** (desktop + 360px, live API + worker): order → COD → courier booked →
  pickup → failed attempt → reattempt → delivered → courier statement matched → money confirmed.
- **Totals (2026-11-04):** backend 266 passed (88% coverage, 18 migrations); web 251 + api-client 25;
  E2E 24/24 (desktop + 360px); mobile 117 passed + 1 live-only skipped; axe 0 violations on the 5
  Phase 3 pages (light, dark, 360px).
- **Not production-ready:** no Nepal courier API is integrated (GAP-COURIER-NP: needs courier API
  access); shipping messages only reach customers on real channels after Meta/WhatsApp approval
  (GAP-MSG-CHANNELS); settlement confirmation relies on the seller (no bank feed, GAP-COD-BANK).

## Phase 2 (Conversation → Order): built 2026-11-04
- **Built and tested:** customers (identity by phone, Nepal addresses, merge, segments), inventory
  (ledger, reservations, transfers, low stock, channel stock sync), orders (state machine, imports,
  partial cancel, timeline), payments (verified online, manual, COD trail), unified inbox and the
  grounded AI Sales Agent with chat-to-order and escalation. Web: Inbox, Orders, Customers, Inventory.
  Mobile: Orders, Inbox, stock.
- **Exit criterion met in E2E** (desktop + 360px, live API + worker): customer message → AI answer
  from real price/stock → details collected → YES → order with stock reserved → packed → shipped.
- **Totals (2026-11-04):** backend 246 passed (88% coverage, 17 migrations); web 239 + api-client 25;
  E2E 22/22; mobile 111 passed + 1 live-only skipped; axe 0 violations on Phase 2 pages.
- **Not production-ready:** real messaging channels (Meta/WhatsApp) and a Nepal payment gateway are
  blocked externally; AI replies use templates (LLM phrasing deferred); municipality list unverified;
  delivery charges are manual until courier rates (Phase 3).

## Phase 1 completion (2026-11-03)
- **CHN-012 reconciliation, BIL-009 alert notifications, Nivaro Console UI** built and tested
  (backend, web unit, real-backend E2E desktop + 360px).
- Phase 1 exit is still externally blocked (live channel, live AI key, image AI provider). Phase 2
  proceeds per the owner's instruction (2026-11-03).

## QA cycle (2026-11-03): verified stable, NOT production ready
- **Found and fixed:** 1 BLOCKER, 1 CRITICAL, 5 HIGH, 6 MEDIUM and the LOW items, each with a
  regression test.
- **Final results:**
  - backend 181 passed, 88% coverage
  - web 217 + 25 passed
  - E2E 16/16, with a CSP guard on every test
  - probe 207/207
  - axe 0 violations
  - no responsive overflow
  - Flutter 101 passed plus the live flow
- **Added for IAM:** password reset (QA-001); the email-link pages /invite and /verify-email
  (QA-008); TOTP replay protection (QA-011).
- Full detail: `docs/QA_TEST_REPORT.md`. Launch status: `docs/PRODUCTION_READINESS_REPORT.md`
  (NOT_READY).

## Nivaro brand migration (2026-11-02): INCOMPLETE
**Done:**
- Customer-facing naming: web, mobile, email, OpenAPI, TOTP issuer, WooCommerce webhook label, specs,
  README.
- Tokens v1.0 with a light/dark semantic layer; indigo retired.
- Logo: the owner's artwork, extracted from the concept board (ADR-032). Lockups, icons, favicon and
  OG are generated from it, and web and Flutter render it in light and dark.
- Light theme by default with an opt-in dark theme (web and Flutter, ADR-033).
- Public website at `/` with sign-up and sign-in entry points (ADR-034).
- Icons: favicon, PWA, apple, Android, iOS.
- OG image.
- Brand primitives in web and Flutter.
- Sign-in brand panel, logo in nav, active ribbon, outlined-trail empty states, Studio drop target,
  neutral at-capacity meter.
- Brand guard test.
- Brand spec (26), product UI spec (18 v3), layout directions for 7 surfaces.

**Remaining (not complete, see KNOWN_GAPS "Nivaro brand migration"):**
- Vector logo master; trademark.
- Character cast and illustrations: none exist, and no placeholders are used.
- Motion assets beyond the ribbon trace.
- Campaign banners.
- Android adaptive icon; Flutter export of the icon set.
- Website follow-ups: photography, legal pages, pricing. Nivaro Console UI.
- Email domain and HTML template.
- Partner brief PDF regeneration.

**Legacy references remaining (intentional, ADR-028):**
- `@commerce-os/*` npm scope
- Dart package / bundle ID `np.commerceos.commerce_os_seller`
- `COS_` env and `cos_` cookies
- `jwt_issuer`
- DB, bucket and service names
- Docker and CI names

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
| IAM-002 | login | P0 | TESTED | IAM-001 | apps/backend/app/domains/accounts/service.py | test_auth | Argon2id, generic failure, IP/email rate limits, lockout QA-001: password reset (API, web, mobile). |
| IAM-003 | verification | P0 | TESTED | FND-012 | apps/backend/app/domains/accounts/, domains/handlers.py | test_auth::test_email_verification_via_outbox | Email via outbox → dev mailer. Phone/SMS OTP not built (GAP-SMS) QA-008: web /verify-email page. |
| IAM-004 | sessions/token rotation | P0 | TESTED | IAM-002 | apps/backend/app/domains/accounts/service.py | test_auth::test_refresh_rotation… | Rotation every use; reuse revokes family; session checked per request |
| IAM-005 | MFA | P0 | TESTED | IAM-004 | apps/backend/app/domains/accounts/service.py | test_auth::test_mfa_totp_flow… | TOTP (sealed secret) + 10 single-use recovery codes; staff routes require MFA QA-011: TOTP single-use (replay protection). |
| IAM-006 | merchant tenancy | P0 | TESTED | — | apps/backend/app/core/db.py, domains/merchants/ | test_tenancy_rbac | ORM auto tenant criteria + write guard; 404 on foreign tenant |
| IAM-007 | membership | P0 | TESTED | IAM-006,BIL-004 | apps/backend/app/domains/merchants/ | test_tenancy_rbac::test_invitation_flow… | Invites bound to email, sealed token purged on accept, seat limit QA-008: web /invite accept page. |
| IAM-008 | RBAC | P0 | TESTED | IAM-007 | apps/backend/app/domains/merchants/rbac.py, api/deps.py | test_tenancy_rbac | Permission strings; system roles; escalation guard; last-owner guard. Custom roles not built |
| IAM-009 | cross-tenant tests | P0 | TESTED | IAM-006 | apps/backend/tests/test_tenancy_rbac.py | — | Endpoint, ORM and write-guard cross-tenant tests QA-012: body-reference sweep test. |
| IAM-010 | revoke sessions | P0 | TESTED | IAM-004 | apps/backend/app/domains/accounts/ | test_auth::test_logout_and_revoke_all… | Revoke one / all others; immediate effect |
| BIL-001 | plan | P0 | TESTED | — | apps/backend/app/domains/billing/models.py, plans.py | conftest seeds; test_entitlements | Plans as data |
| BIL-002 | plan version | P0 | TESTED | BIL-001 | apps/backend/app/domains/billing/plans.py | — | Content-hash versioning; one active version per plan; grandfathering |
| BIL-003 | features | P0 | TESTED | BIL-001 | packages/contracts/feature-entitlements.example.json | test_entitlements::test_feature_gating… | 22 features, 14 metered resources QA-015: gauges serialised (advisory lock). |
| BIL-004 | entitlement service | P0 | TESTED | BIL-003 | apps/backend/app/domains/billing/service.py | test_entitlements | No plan-name checks in business code; admin overrides; add-ons |
| BIL-005 | usage event | P0 | TESTED | BIL-004 | apps/backend/app/domains/billing/models.py | test_entitlements | Immutable UsageEvent with idempotency key |
| BIL-006 | aggregation | P0 | TESTED | BIL-005 | apps/backend/app/domains/billing/service.py | test_entitlements | Row-locked counters per window (billing month / merchant-local day); gauge counter registry |
| BIL-007 | credit wallet | P0 | TESTED | BIL-004 | apps/backend/app/domains/billing/service.py | test_entitlements::test_monthly_overrun_uses_credits… | Wallet + ledger (hold/release/consume). No purchase flow (needs PAY) |
| BIL-008 | reserve/finalize usage | P0 | TESTED | BIL-006 | apps/backend/app/domains/billing/service.py | test_entitlements::test_concurrent_reservations… | 12 concurrent reservations vs limit 4 → exactly 4 |
| BIL-009 | quota alerts | P0 | TESTED | FND-012 | apps/backend/app/domains/billing/service.py, domains/handlers.py, exceptions/service.py | test_entitlements::test_usage_alerts… (2) | 70/85/100 emitted once; owners/admins emailed in their language; Exception Inbox usage_limit (≥85%, billing roles only) on web + mobile |
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
| CNT-013 | content metrics ingestion interface on adapters (fetch_content_metrics) [Phase 7] | P7 | IMPLEMENTED | CHN-001 | integrations/base.py ChannelCapability.CONTENT_METRICS + fetch_content_metrics; sandbox adapter; apps/backend/app/domains/intelligence/creative.py::ingest_channel_metrics, record_manual | apps/backend/tests/test_creative.py::test_channel_insights_and_typed_in_results_keep_their_source | Sandbox + seller-typed results only; Meta/TikTok insights BLOCKED with their app approval (GAP-CHANNEL-APPS) |
| CNT-014 | inquiry/order attribution to content (explicit ref → window heuristic; method recorded) [Phase 7] | P7 | TESTED | CNT-013 | apps/backend/app/domains/intelligence/creative.py::attribute_post (explicit post ref → 7-day window with decay, shared credit); inbox post_ref → conversation.content_post_id | apps/backend/tests/test_creative.py::test_explicit_beats_window_and_shared_credit_never_exceeds_one_order | Method recorded per metric |
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
| CHN-012 | reconciliation | P1 | TESTED | CHN-009 | apps/backend/app/domains/channels/service.py, integrations/woocommerce.py | test_reconciliation (8), test_woocommerce::test_fetch_listings… | Every 6h + on demand (Channels → Check). Drift (missing/hidden/price/variants) reported, never auto-overwritten; seller pushes Nivaro's or keeps channel's version; self-clears. Stock and order drift wait for INV/ORD (Phase 2). WooCommerce path not yet run against a live store |
| CHN-013 | health UI | P1 | TESTED | CHN-003 | apps/backend/app/domains/channels/ | test_channels | Health API + web Channels settings (status, reconnect, health check, disconnect) |
| CRM-001 | Customer | P2 | TESTED | — | apps/backend/app/domains/customers/ | test_customers | Customer with normalised Nepal mobile; one live customer per phone |
| CRM-002 | identities | P2 | TESTED | — | apps/backend/app/domains/customers/service.py | test_customers, test_inbox | Channel identities; a phone typed in chat joins the existing customer |
| CRM-003 | addresses | P2 | TESTED | — | apps/backend/app/domains/customers/ | test_customers | Structured addresses with completeness; default address |
| CRM-004 | duplicate merge | P2 | TESTED | — | apps/backend/app/domains/customers/service.py | test_customers, test_orders | Audited merge; orders, chats, identities, addresses move via merge hooks |
| CRM-005 | Conversation | P2 | TESTED | — | apps/backend/app/domains/inbox/ | test_inbox | Conversations per channel thread; open/snoozed/closed, labels, unread, first-response SLA |
| CRM-006 | Message | P2 | TESTED | — | apps/backend/app/domains/inbox/ | test_inbox | Messages deduped on channel id; outbound queued and sent by worker with idempotency key |
| CRM-007 | normalization | P2 | TESTED | — | apps/backend/app/domains/integrations/sandbox.py, inbox/service.py | test_inbox | ChannelAdapter.normalize_message; sandbox implemented. Meta/WhatsApp blocked (GAP-CHANNEL-APPS) |
| CRM-008 | assignment | P2 | TESTED | — | apps/backend/app/domains/inbox/service.py | test_inbox (API) | Assign to team member (audited); seller reply auto-assigns |
| CRM-009 | intent | P2 | TESTED | — | apps/backend/app/domains/inbox/extract.py, agent.py | test_inbox | Rules-first intent (en, Romanized ne, Devanagari) + AI gateway INTENT_CLASSIFICATION when confident (≥0.7). Live model unverified |
| CRM-010 | AI summary | P2 | TESTED | — | apps/backend/app/domains/inbox/agent.py | test_inbox | Factual summary from conversation data; AI phrasing only with a real model |
| CRM-011 | grounded reply | P2 | TESTED | — | apps/backend/app/domains/inbox/agent.py | test_inbox (10) + e2e phase2 | Replies are bilingual templates filled from tools (get_product/price/inventory/order); grounding recorded per reply. LLM phrasing deferred (ADR-043) |
| CRM-012 | escalation | P2 | TESTED | — | apps/backend/app/domains/inbox/agent.py | test_inbox | Complaint/return/refund/exchange/cancel/person/unknown order escalate with holding message; seller reply takes over; hand back |
| CRM-013 | segments | P2 | TESTED | — | apps/backend/app/domains/customers/service.py | test_orders::test_customer_segments… | new / repeat / inactive (90d) from real orders |
| ORD-001 | Order | P2 | TESTED | — | apps/backend/app/domains/orders/ | test_orders (16) | One Order for chat/seller/channel/API; per-merchant numbers |
| ORD-002 | OrderLine | P2 | TESTED | — | apps/backend/app/domains/orders/models.py | test_orders | Line snapshots: price, SKU, title, variant title |
| ORD-003 | totals snapshot | P2 | TESTED | — | apps/backend/app/domains/orders/service.py | test_orders | Totals snapshot recomputed on partial cancel |
| ORD-004 | state machine | P2 | TESTED | — | apps/backend/app/domains/orders/service.py | test_orders | Strict transitions; stock reserve on confirm, release on cancel, commit on ship; optimistic version |
| ORD-005 | external import | P2 | TESTED | — | apps/backend/app/domains/orders/service.py, integrations/woocommerce.py | test_orders (import, catch-up, Woo mapping) | Webhooks + reconciliation catch-up; unmatched SKUs / stock gaps imported and flagged. WooCommerce not run against a live store |
| ORD-006 | chat-to-order | P2 | TESTED | — | apps/backend/app/domains/inbox/agent.py | test_inbox::test_message_to_ai_to_order_end_to_end + e2e phase2 | Slot filling, sellable options only, summary + explicit YES, idempotent on (conversation, draft version) |
| ORD-007 | seller order | P2 | TESTED | — | apps/backend/app/domains/orders/router.py, apps/web/src/features/orders | test_orders, OrderDetail.test, e2e | Seller order with variant picker and live stock (web) |
| ORD-008 | idempotency | P2 | TESTED | — | apps/backend/app/domains/orders/service.py | test_orders | Idempotency-Key, source_key, (connection, external id) |
| ORD-009 | cancel | P2 | TESTED | — | apps/backend/app/domains/orders/service.py | test_orders | Cancel with reason; needs orders.cancel |
| ORD-010 | partial cancel | P2 | TESTED | — | apps/backend/app/domains/orders/service.py | test_orders | Partial cancel releases matching stock |
| ORD-011 | timeline | P2 | TESTED | — | apps/backend/app/domains/orders/models.py | test_orders | Timeline: actor, automated, source, provider |
| ORD-012 | structured Nepal address model (province/district/municipality/ward/area/landmark) + validation [pull-forward for CRI/CODI] | P2 | TESTED | — | apps/backend/app/domains/customers/nepal.py | test_customers | 7 provinces, 77 districts, ward 1-35; municipality free text (GAP-NP-MUNICIPALITIES) |
| INV-001 | locations | P2 | TESTED | — | apps/backend/app/domains/inventory/ | test_inventory | Default location; more locations need inventory.multi_location |
| INV-002 | ledger | P2 | TESTED | — | apps/backend/app/domains/inventory/ | test_inventory | Append-only ledger (DB trigger); levels equal ledger sums |
| INV-003 | reservations | P2 | TESTED | — | apps/backend/app/domains/inventory/ | test_inventory | Reservations per order line, idempotent; expiry task |
| INV-004 | reserve/release | P2 | TESTED | — | apps/backend/app/domains/inventory/service.py | test_inventory | Reserve / release / commit / return to stock |
| INV-005 | concurrency tests | P2 | TESTED | — | tests/test_inventory.py, test_orders.py | 12-thread and 6-request races | No oversell |
| INV-006 | adjustment | P2 | TESTED | — | apps/backend/app/domains/inventory/ | test_inventory | Adjust, count, damage |
| INV-007 | transfer | P2 | TESTED | — | apps/backend/app/domains/inventory/service.py | test_inventory | Transfer with deadlock-safe lock order |
| INV-008 | low-stock | P2 | TESTED | — | apps/backend/app/domains/inventory/ | test_inventory | Threshold; flagged once per crossing; low-stock page |
| INV-009 | channel sync | P3 | TESTED | — | apps/backend/app/domains/channels/service.py | test_inventory::test_stock_syncs… | Pushes available - per-channel safety stock to inventory-sync channels |
| INV-010 | reconciliation | P3 | NOT_STARTED | — | — | — |  |
| PAY-001 | adapter | P0 | IMPLEMENTED | CHN-001 | apps/backend/app/domains/integrations/base.py, sandbox.py | test_platform | Interface + sandbox wallet + COD adapter; no Nepal gateway yet (GAP-PAY-NP) |
| PAY-002 | COD | P2 | TESTED | — | apps/backend/app/domains/payments/, fulfillment/settlement.py | test_payments, test_fulfillment | COD record follows the order and the parcel; settled only when a courier statement (or own-rider cash) is confirmed |
| PAY-003 | payment intent | P2 | TESTED | — | apps/backend/app/domains/payments/service.py | test_payments | Payment intents via adapter; sandbox only (GAP-PAY-NP) |
| PAY-004 | verify | P2 | TESTED | — | apps/backend/app/domains/payments/service.py | test_payments | Server-side verify + amount must equal total; mismatch held for seller |
| PAY-005 | webhook | P2 | TESTED | — | apps/backend/app/domains/payments/ | test_payments | Signed payment webhooks, deduped, only trigger verify |
| PAY-006 | reconcile | P3 | NOT_STARTED | — | — | — |  |
| PAY-007 | refund | P4 | TESTED | PAY-001 | apps/backend/app/domains/returns/service.py | test_returns | Idempotent; never above paid minus earlier refunds; original payment via provider refund (provider id stored) or recorded manual transfer; failed refunds retry with the same provider key. No Nepal gateway yet (GAP-PAY-NP) |
| PAY-008 | idempotency tests | P2 | TESTED | — | tests/test_payments.py | test_payments | Manual payment idempotent; link reuse; webhook dedupe |
| PAY-009 | failed payment | P2 | TESTED | — | apps/backend/app/domains/payments/service.py | test_payments | Failed payment recorded; retry; switch to COD |
| PAY-010 | settlement dashboard | P3 | TESTED | — | apps/backend/app/domains/fulfillment/settlement.py; apps/web/src/features/fulfillment/CodView.tsx | test_fulfillment::test_courier_statement…, Fulfillment.test (CodView), e2e phase3 | Cash with couriers by age and by courier, statements to review, received in 30 days; awaiting list; mobile COD screen |
| FUL-001 | courier adapter | P0 | TESTED | CHN-001 | apps/backend/app/domains/integrations/base.py, sandbox.py | test_fulfillment | Normalised tracking, pickup, reattempt, return, COD statements; sandbox courier + real 'own rider / other courier' adapter. No Nepal courier API yet (GAP-COURIER-NP) |
| FUL-002 | rates | P3 | TESTED | FUL-001 | apps/backend/app/domains/fulfillment/couriers.py | test_fulfillment::test_rates… | Options per courier, COD-capable only for COD; rule recommendation (default → cheapest → only), method=rules; merchant delivery-fee table (district > valley > default, free-over) |
| FUL-003 | shipment state | P3 | TESTED | FUL-001 | apps/backend/app/domains/fulfillment/service.py, models.py | test_fulfillment | 12 normalised statuses; one live shipment per order; idempotent booking under an order lock; order follows the parcel through the order state machine |
| FUL-004 | labels | P3 | TESTED | FUL-003 | fulfillment/service.py::label; apps/web/src/features/fulfillment/LabelView.tsx | test_fulfillment::test_booking…, e2e phase3 | Courier label when provided, else Nivaro printable label (tracking, COD to collect, addresses, contents). No barcode yet (GAP-LABEL-BARCODE) |
| FUL-005 | pickup | P3 | TESTED | FUL-003 | fulfillment/service.py::request_pickup | test_fulfillment::test_cannot_book…, e2e phase3 | One pickup request per courier for selected booked parcels; bulk from the Deliveries list |
| FUL-006 | tracking | P3 | TESTED | FUL-003 | fulfillment/service.py (webhooks + poll_due) | test_fulfillment::test_courier_webhooks…, test_late_webhook…, test_polling… | Signed per-account webhooks through the webhook inbox (dedupe, retry, dead-letter); polling every 30 min (6 h with webhooks); newest-event-wins, late events kept as history |
| FUL-007 | notify | P3 | TESTED | FUL-006 | fulfillment/service.py::_notify_customer, notify.py | test_fulfillment::test_failed_delivery_asks… | en/ne templates into the customer's own chat only, once per parcel and kind, merchant toggle. Meta 24 h window applies on real channels (GAP-MSG-CHANNELS) |
| FUL-008 | delivery failure | P3 | TESTED | FUL-006 | fulfillment/service.py (attempts, capture_customer_reply, escalate_stale) | test_fulfillment (3 recovery tests), e2e phase3 | Attempt record → customer asked → reply captured before the Sales Agent → auto reattempt only in smart/autopilot → escalation after the wait window; return to sender; restock on receipt |
| FUL-009 | smart courier | P6 | TESTED | CRI-003 | Courier Brain (CRI-001…005); settings/CouriersView | apps/backend/tests/test_intelligence.py::test_courier_selection_recommendation_switches_to_smart | Only sandbox courier data until a real Nepal courier API exists (GAP-COURIER-NP) |
| FUL-010 | reconciliation | P3 | TESTED | FUL-006 | apps/backend/app/domains/fulfillment/settlement.py | test_fulfillment (4 settlement tests) | Statements from courier API, CSV import or own-rider cash; per-line matching (7 outcomes); accept with reason (audited); confirm settles COD records; idempotent per reference |
| RET-001 | policy | P4 | TESTED | — | apps/backend/app/domains/returns/models.py, service.py; web Settings > Returns | test_returns::test_final_sale…, test_shop_fault… | Window, refund/exchange, evidence reasons, customer-pays return shipping, auto-approve, auto-refund threshold; final-sale products |
| RET-002 | eligibility | P4 | TESTED | RET-001 | apps/backend/app/domains/returns/service.py::check_eligibility | test_returns::test_outside_window… | Recorded per request; hard checks refuse; soft checks need an audited override reason; live check in the web/mobile form |
| RET-003 | request | P4 | TESTED | RET-002 | apps/backend/app/domains/returns/router.py | test_returns, e2e phase4 | Seller-created from the order (Idempotency-Key, order lock); Sales Agent answers return questions from the policy and hands over. No customer self-service link (GAP-RETURN-SELF-SERVE) |
| RET-004 | evidence | P4 | IMPLEMENTED | RET-003 | apps/backend/app/domains/returns/models.py (evidence_asset_ids) | test_returns::test_final_sale… | Evidence media ids per line + policy check; the web/mobile forms don't upload photos yet (GAP-RETURN-EVIDENCE-UI) |
| RET-005 | approval | P4 | TESTED | RET-002 | apps/backend/app/domains/returns/service.py | test_returns::test_refund_above_threshold…, test_frequent_returner… | returns.approve (manager+); auto-approve only within policy and with no abuse signal |
| RET-006 | reverse shipment | P4 | TESTED | FUL-003 | apps/backend/app/domains/fulfillment/service.py::book_return | test_returns::test_delivered_cod…, e2e phase4 | Return pickups reuse couriers/tracking/webhooks (direction=return); never move the order or COD; or mark received for drop-offs |
| RET-007 | inspection | P4 | TESTED | RET-006 | apps/backend/app/domains/returns/service.py::inspect | test_returns (inspection tests), e2e phase4 | Condition per line; only resellable items restock (idempotent ledger key); missing items aren't refunded |
| RET-008 | exchange | P4 | TESTED | RET-005 | apps/backend/app/domains/returns/service.py::_create_exchange | test_returns::test_exchange…, test_cancelling… | Same product and price; replacement reserved at approval; free replacement order after inspection; cancel releases it. Price-difference exchanges not supported (GAP-EXCHANGE-PRICE) |
| RET-009 | refund calculation | P4 | TESTED | — | apps/backend/app/domains/returns/service.py::_unit_refund, _compute_due | test_returns::test_shop_fault… | Paid per unit net of line and order discounts; delivery charge back when the shop's fault covers the whole order; customer-fault return shipping deducted |
| RET-010 | auto-refund threshold | P4 | TESTED | PAY-007 | apps/backend/app/domains/returns/service.py | test_returns::test_prepaid_auto_refund…, test_refund_above_threshold… | Auto-refund only to the original online payment, within the threshold, without abuse signals; above it a manager approves (staff may raise refunds) |
| RET-011 | abuse signals | P4 | TESTED | — | apps/backend/app/domains/returns/service.py::abuse_signals | test_returns::test_frequent_returner… | Merchant-scoped facts only (frequent returns, high return rate, high value vs usual order); shown neutrally; turn automation off. Never names/gender/caste/location traits or cross-merchant data |
| RET-012 | controlled return-reason vocabulary + free text [pull-forward for RTI] | P4 | TESTED | RET-003 | apps/backend/app/domains/returns/models.py | test_returns | 10 controlled reasons (DB check) + customer's words; conditions at inspection |
| AUT-001 | workflow schema | P5 | TESTED | — | apps/backend/app/domains/automation/models.py, engine.py::validate | test_automation::test_workflows_need… | Trigger + steps (condition, branch, wait, action, approval), forward-only jumps, ≤20 steps, validated per subject |
| AUT-002 | triggers | P5 | TESTED | — | apps/backend/app/domains/automation/facts.py::TRIGGERS | test_automation | Order created/status, parcel status, return status, low stock, channel expired; filter on the event's own status. Schedules not built (GAP-AUT-SCHEDULE) |
| AUT-003 | conditions | P5 | TESTED | — | apps/backend/app/domains/automation/facts.py | test_automation | Typed fields per subject; all/any; facts re-read at every step; missing data never passes |
| AUT-004 | actions | P5 | TESTED | — | apps/backend/app/domains/automation/actions.py | test_automation | 8 typed actions (notify, note, customer message, review request, book courier, pickup, reattempt, approve return) with risk class, impact, capability; idempotency key run+step |
| AUT-005 | versions | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py | test_automation::test_editing_creates… | Immutable versions; runs pin theirs |
| AUT-006 | execution | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py | test_automation, e2e phase5 | Outbox-triggered, one run per workflow per event |
| AUT-007 | delay | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py::resume_due | test_automation::test_failed_delivery_followup… | Waits 1–720 h; worker resumes every minute |
| AUT-008 | branch | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py | test_automation::test_failed_delivery_followup… | If/otherwise to forward steps or stop |
| AUT-009 | approval | P5 | TESTED | AUT-016 | apps/backend/app/domains/automation/engine.py::resolve_approval | test_automation::test_assisted_mode…, e2e phase5 | Policy or explicit approval steps; automation.approve; facts re-checked at approval |
| AUT-010 | retry | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py::_execute | test_automation::test_retries… | Retryable provider errors: 3 attempts with backoff, same idempotency key |
| AUT-011 | exceptions | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py::_maybe_trip_breaker; exceptions/service.py | test_automation::test_retries… | Circuit breaker pauses workflows using a failing action and raises an urgent exception; approvals in the Exception Inbox |
| AUT-012 | logs | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py::run_view | test_automation | Run + step trace with decisions in the builder |
| AUT-013 | templates | P5 | TESTED | — | apps/backend/app/domains/automation/templates.py | test_automation | 6 commerce templates (en/ne messages) |
| AUT-014 | builder UI | P5 | TESTED | — | apps/web/src/features/automation/WorkflowBuilder.tsx | Automation.test, e2e phase5 | Form-based builder: trigger + filters, step editor with conditions, branches, waits, actions, approvals |
| AUT-015 | dry-run | P5 | TESTED | — | apps/backend/app/domains/automation/engine.py::dry_run | test_automation::test_dry_run…, e2e phase5 | Real facts, real policy decision, nothing recorded or executed |
| AUT-016 | Autonomous Decision Policy: risk classes R0–R4, mode × class matrix, confidence + staleness gates | P5 | TESTED | — | apps/backend/app/domains/automation/policy.py::decide | test_automation::test_decision_matrix (9 cases) | One function for workflows, Sales Agent, delivery recovery and returns automation. Staleness gate waits for the Digital Twin (Phase 9) |
| AUT-017 | merchant thresholds (refund, discount, PO, campaign budget, stock transfer, price-change band) with audit | P5 | TESTED | — | apps/backend/app/domains/automation/policy.py | test_automation::test_loosening… | Loosening needs automation.approve and is audited as high risk |
| AUT-018 | AutomationActionLog: actor/outcome/eligibility/exclusion for every operational action (APS source) | P5 | TESTED | ORD-001 | apps/backend/app/domains/automation/policy.py::log_action (+ orders, inbox, fulfillment, returns, settlement) | test_automation | Idempotent per action; performed by automation/ai/user/system; human intervention flag |
| AUT-019 | decision records (inputs refs, rule hit, confidence, impact) + seller-facing explanation | P5 | TESTED | — | apps/backend/app/domains/automation/models.py::DecisionRecord | test_automation | Rule → plain-words explanation in Control Center, approvals and Activity |
| AUT-020 | intelligence-derived triggers and profit-aware conditions (Phase 6) | P6 | NOT_STARTED | — | — | — |  |
| AUT-021 | recommendation → policy → approval → idempotent execution path (Phase 6) | P6 | TESTED | REC-005 | apps/backend/app/domains/intelligence/recommendations.py::accept/_execute | apps/backend/tests/test_intelligence.py::test_autopilot_recommendation_is_r3_accepted_by_a_manager_and_measured; e2e phase6a | Recommendation → policy → approval → idempotent execution, decision on record |
| ANA-001 | sales | P5 | NOT_STARTED | — | — | — |  |
| ANA-002 | channels | P5 | NOT_STARTED | — | — | — |  |
| ANA-003 | products | P5 | NOT_STARTED | — | — | — |  |
| ANA-004 | fulfillment | P5 | NOT_STARTED | — | — | — |  |
| ANA-005 | returns | P5 | NOT_STARTED | — | — | — |  |
| ANA-006 | AI/automation | P5 | NOT_STARTED | — | — | — |  |
| ANA-007 | product P&L | P6 | TESTED | ANA | apps/backend/app/domains/intelligence/profit.py::compute (per-product waterfall, order costs split by line value) | apps/backend/tests/test_intelligence_b.py::test_true_profit_waterfall_counts_returns_failures_and_labels_missing_data | Cost snapshot on order lines from 2026-11-19; older lines use today's cost (counted) |
| ANA-008 | profit dashboard | P6 | TESTED | ANA-007 | apps/backend/app/domains/intelligence/profit.py; web /analytics Profit tab; mobile profit_card | apps/backend/tests/test_intelligence_b.py; web Analytics tests; e2e phase6b | Missing data shown as Not included / Partial, never 0 (ADR-065) |
| ANA-009 | Store Manager tools | P6 | NOT_STARTED | — | — | — |  |
| ANA-010 | recommendations | P6 | TESTED | ANA-007 | apps/backend/app/domains/intelligence/recommendations.py::_profit, profit-aware _restock | apps/backend/tests/test_intelligence_b.py::test_suggestions_rank_by_profit_and_never_push_loss_makers | Ranks restock by 30-day contribution; never restocks loss makers or high-return items; informational only (no price changes) |
| PRO-001 | suppliers | P8 | TESTED | CAT | catalog Supplier (contact, terms, status); apps/backend/app/domains/procurement/service.py create/update_supplier | apps/backend/tests/test_procurement.py::test_suppliers_and_their_products |  |
| PRO-002 | supplier products | P8 | TESTED | PRO-001 | apps/backend/app/domains/procurement/service.py set_supplier_product / set_preferred (catalog_variant_suppliers) | apps/backend/tests/test_procurement.py::test_suppliers_and_their_products | First supplier for a variant becomes preferred |
| PRO-003 | purchase orders | P8 | TESTED | PRO-002 | apps/backend/app/domains/procurement/models.py PurchaseOrder/Line; service create/update/submit/send/cancel | apps/backend/tests/test_procurement.py::test_po_approval_receiving_lots_and_landed_cost | Idempotent create; MOQ warning; share text instead of email (ADR-075) |
| PRO-004 | approvals | P8 | TESTED | AUT-016 | apps/backend/app/domains/procurement/service.py::submit/approve/reject (po_minor threshold) | apps/backend/tests/test_procurement.py::test_staff_create_but_only_approvers_approve | Above the threshold always needs explicit approval (ADR-073) |
| PRO-005 | receiving | P8 | TESTED | INV | apps/backend/app/domains/procurement/service.py::receive (receipts = lots, good vs defective, inventory ledger) | apps/backend/tests/test_procurement.py::test_po_approval_receiving_lots_and_landed_cost | Partial receiving; over-receipt refused; idempotent |
| PRO-006 | landed cost | P8 | TESTED | PRO-005 | apps/backend/app/domains/procurement/service.py::landed_unit_costs + moving-average variant cost | apps/backend/tests/test_procurement.py::test_po_approval_receiving_lots_and_landed_cost | Freight/duty/other allocated by line value; order lines then snapshot landed cost (ADR-074) |
| PRO-007 | reorder recommendations | P8 | TESTED | PBR-002 | apps/backend/app/domains/procurement/supplier_intel.py::reorder_proposals; recommendations create_po_draft | apps/backend/tests/test_procurement.py::test_reorder_suggestion_uses_lead_time_moq_and_creates_a_draft_for_approval | Creates a draft only; the PO still needs submit + approval |
| ADM-001 | merchant lookup | P0+ | TESTED | IAM-005 | apps/backend/app/domains/admin/router.py, apps/web/src/features/console | test_admin_console, Console.test.tsx, e2e console-real-backend | Console UI: search + detail drawer (team, usage, channels, overrides, credits); suspend/reactivate with reason |
| ADM-002 | usage/credits | P0+ | TESTED | BIL-006 | apps/backend/app/domains/admin/router.py | test_admin_console | Usage + balance; idempotent goodwill credit grants; limit overrides (validated, end keeps record) |
| ADM-003 | provider health | P0+ | TESTED | AIG-008 | apps/backend/app/domains/admin/router.py, features/console/OpsViews.tsx | e2e console-real-backend | Console AI providers: key configured, circuit state, 1h success, latency |
| ADM-004 | channel health | P0+ | TESTED | CHN-013 | apps/backend/app/domains/admin/router.py | test_admin_console | Per-merchant connection health in Console merchant drawer |
| ADM-005 | webhook explorer | P0+ | TESTED | CHN-010 | apps/backend/app/domains/channels/router.py, features/console/OpsViews.tsx | test_channels::test_webhook_unknown… | API + Console screen with status/provider filters and replay (audited) |
| ADM-006 | replay | P0+ | TESTED | FND-012 | apps/backend/app/domains/admin/router.py, features/console/OpsViews.tsx | test_idempotency_outbox (requeue) | Outbox retry from the Console (audited) |
| ADM-007 | DLQ | P0+ | TESTED | FND-012 | apps/backend/app/domains/admin/router.py, features/console/OpsViews.tsx | e2e console-real-backend | Console Outbox: dead/pending/dispatched |
| ADM-008 | plan editor | P0+ | NOT_STARTED | — | — | — |  |
| ADM-009 | routing editor | P0+ | NOT_STARTED | — | — | — |  |
| ADM-010 | refund review | P0+ | NOT_STARTED | — | — | — |  |
| ADM-011 | feature flags | P0+ | TESTED | FND-011 | apps/backend/app/domains/admin/router.py, features/console/OpsViews.tsx | test_platform::test_feature_flags… | API + Console editor (audited) |
| UX-001 | design tokens | P0 | TESTED | — | packages/design-system/ | CI diff check of generated outputs | JSON → CSS vars, TS, Dart |
| UX-002 | web library | P0 | TESTED | UX-001 | apps/web/src/components | 95 vitest tests; E2E vs real backend | No 3rd-party visual library; Radix for behaviour only |
| UX-003 | Flutter theme | P0 | TESTED | UX-001 | apps/mobile/lib/design | flutter test (51) | Theme from generated tokens; bundled Inter + Noto Sans Devanagari |
| UX-004 | Product Brain | P6 | TESTED | PBR-009 | apps/web/src/features/products Product Brain card; mobile product_brain_card | web + mobile component tests; e2e phase6b | See UX-018 |
| UX-005 | Channel Sync Rail | P1 | IMPLEMENTED | — | — | — | Web product listings panel = per-channel sync state (status, error, polling); not yet a standalone reusable rail component |
| UX-006 | Autopilot Strip | P1 | IMPLEMENTED | UX-002 | apps/web/src/components/commerce, apps/mobile/lib/features/home | widget/component tests | Autopilot Status Strip (no data source until AUT) |
| UX-007 | Exception Inbox | P1 | TESTED | UX-002 | apps/backend/app/domains/exceptions/, apps/web, apps/mobile | test_exceptions | Live Exception Inbox (web Home + mobile Home) from GET /exceptions; actions routed; E2E vs real backend |
| UX-008 | Order Journey | P2 | TESTED | — | apps/web/src/features/orders/OrderDetail.tsx | OrderDetail.test, e2e phase2 | Order Journey on web; mobile order detail shows status + timeline |
| UX-009 | AI Timeline | P5 | NOT_STARTED | — | — | — | AI Action Timeline: needs AutomationActionLog (Phase 5) |
| UX-010 | Profit Card | P6 | TESTED | ANA-008 | apps/web/src/features/analytics Profit card; mobile profit_card | web + mobile tests; e2e phase6b; axe |  |
| UX-011 | Video Credit Meter | P1 | TESTED | BIL-006 | apps/web …/settings/plan, apps/mobile …/settings | component tests | Video Credit Meter + plan-aware usage (not-in-plan, overage policy, gauges); verified against real backend |
| UX-012 | Inventory Risk | P6 | TESTED | PBR-004 | apps/backend/app/domains/intelligence/product_brain.py::stock_risk; /intelligence/stock-risk; web Home 'Running out' + product meter | web tests; apps/backend/tests/test_intelligence_b.py | Lead time fixed at 7 days until supplier lead times are used (Phase 8) |
| UX-013 | real states | P1 | IN_PROGRESS | — | apps/web, apps/mobile | component tests | Loading/empty/error/offline/permission states for Phase 0 screens |
| UX-014 | accessibility | P1 | IN_PROGRESS | — | apps/web, apps/mobile | — | Keyboard, focus, labels, 48dp; no full screen-reader audit yet |
| UX-015 | bilingual review | P1 | IN_PROGRESS | — | apps/web/src/i18n, apps/mobile/lib/core/l10n/arb | key-parity tests | en/ne complete for Phase 0; Nepali not yet reviewed by a native copy editor |
| UX-016 | Autopilot Control Center (home): "Your store is running." + Needs Your Attention (Phase 5) | P5 | TESTED | AUT-018 | apps/backend/app/domains/automation/control.py; apps/web/src/features/automation/ControlCenter.tsx; mobile control_center.dart | Automation.test, mobile tests, e2e phase5 | Real 7-day numbers, automatic vs team share, approvals, autopilot feed |
| UX-017 | Autopilot Score component (breakdown, exclusions, thin-data state) (Phase 6) | P6 | TESTED | APS-005 | apps/web/src/features/intelligence/AutopilotScoreCard.tsx; mobile autopilot_score_card.dart | Intelligence.test.tsx; mobile tests; e2e phase6a; axe | Breakdown, exclusions, thin-data state |
| UX-018 | Product Brain card (Phase 6) | P6 | TESTED | PBR-009 | apps/web/src/features/products Product Brain card; mobile product_brain_card | web + mobile tests; e2e phase6b; axe |  |
| UX-019 | Recommendation / Profit Recommendation Card with explanation pattern (Phase 6) | P6 | TESTED | REC-003 | apps/web/src/features/intelligence/Recommendations.tsx; mobile recommendations_section.dart | Intelligence.test.tsx; mobile tests; e2e phase6a; axe | Profit recommendation variant waits for profit analytics (Part B) |
| UX-020 | Return Insight Card + Courier Recommendation Card (Phase 6) | P6 | IMPLEMENTED | RTI-002 | apps/web/src/features/analytics Return patterns tab; product card insights | web component tests | Return Insight Card done; Courier Recommendation Card is the Phase 6A courier panel. Not covered by E2E (needs 10+ delivered sales) |
| UX-021 | Commerce Memory insight with correction (Phase 6) | P6 | TESTED | MEM-005 | apps/web/src/features/analytics What Nivaro learned; mobile memory_screen | web + mobile tests; axe | Mobile has confirm/reject, not correct |
| UX-022 | Creative Genome panel (Phase 7) | P7 | TESTED | CGN-005 | apps/web/src/features/intelligence/CreativeView.tsx; mobile creative_genome_card.dart | web + mobile tests; e2e phase7; axe |  |
| PBR-001 | ProductIntelligenceProfile schema + method_version + as_of + data-completeness | P6 | TESTED | — | apps/backend/app/domains/intelligence/models.py::ProductIntelligenceProfile | apps/backend/tests/test_intelligence_b.py::test_product_brain_uses_in_stock_days_and_lists_what_it_cant_know | completeness + not_included reasons |
| PBR-002 | demand rate (EWMA, in-stock days only, seasonality index) per product/variant | P6 | TESTED | PBR-001 | apps/backend/app/domains/intelligence/product_brain.py::ewma, _in_stock_days | apps/backend/tests/test_intelligence_b.py::test_product_brain_uses_in_stock_days_and_lists_what_it_cant_know | Per product (not per variant); seasonality index needs 12 months → listed as not included |
| PBR-003 | margin + expected contribution per unit (uses ANA true-profit components; "not included" handling) | P6 | TESTED | ANA-007 | apps/backend/app/domains/intelligence/product_brain.py (margin, contribution from 90-day P&L) | apps/backend/tests/test_intelligence_b.py | Contribution needs 5+ delivered units |
| PBR-004 | stock cover days + stockout history | P6 | TESTED | PBR-002 | apps/backend/app/domains/intelligence/product_brain.py (cover_days, stockouts_90d) | apps/backend/tests/test_intelligence_b.py::test_product_brain_uses_in_stock_days_and_lists_what_it_cant_know |  |
| PBR-005 | return rate + top reasons (from RET-012) per product/variant/size | P6 | TESTED | RTI-001 | apps/backend/app/domains/intelligence/product_brain.py (return_rate, top_reasons, by_variant) | apps/backend/tests/test_intelligence_b.py |  |
| PBR-006 | channel conversion + content performance summary (from CGN metrics when available) | P6 | NOT_STARTED | — | — | — |  |
| PBR-007 | FAQ clustering from conversations + seller-approved answers (ProductFAQ) | P6 | NOT_STARTED | — | — | — |  |
| PBR-008 | incremental refresh on events + nightly full recompute; freshness SLO + metrics | P6 | TESTED | PBR-001 | apps/backend/app/domains/intelligence/product_brain.py (_on_status handler, recompute_all nightly, 26h freshness) | apps/backend/tests/test_intelligence_b.py::test_product_brain_refreshes_when_an_order_is_delivered | Event refresh debounced 10 min; no freshness metric exported yet |
| PBR-009 | API GET /product-brain/products/{id} (+faqs); Sales Agent + Store Manager tool get_product_brain | P6 | IMPLEMENTED | PBR-008 | apps/backend/app/domains/intelligence/router.py GET /intelligence/products/{id}/brain; Sales Agent fit hint | apps/backend/tests/test_intelligence_b.py | FAQs (PBR-007) and Store Manager tool not built; path is /intelligence/products/{id}/brain |
| PBR-010 | golden-value tests + offline backtest of demand rate | P6 | TESTED | PBR-002 | apps/backend/tests/test_intelligence_b.py::test_ewma_golden_values_and_backtest | apps/backend/tests/test_intelligence_b.py | Synthetic backtest only; real backtest needs pilot data |
| MEM-001 | CommerceMemoryMetric registry (named metrics, definitions, periods, method_version) + storage | P6 | TESTED | — | apps/backend/app/domains/intelligence/memory.py::METRICS; models.CommerceMemoryMetric | apps/backend/tests/test_intelligence_b.py::test_memory_facts_are_versioned_and_the_seller_has_the_last_word | 5 metrics: units_sold, return_rate, orders, repeat_share, delivery_success |
| MEM-002 | metric computation jobs (idempotent per period key) for products, customers, logistics, operations | P6 | TESTED | MEM-001 | apps/backend/app/domains/intelligence/memory.py::compute_metrics (upsert per period key) | apps/backend/tests/test_intelligence_b.py::test_memory_facts_are_versioned_and_the_seller_has_the_last_word | Idempotency asserted |
| MEM-003 | CommerceMemoryFact schema (typed fact_type JSON schemas, confidence, evidence_ref, validity, versions) | P6 | TESTED | — | apps/backend/app/domains/intelligence/memory.py::FACT_TYPES, _validate; models.CommerceMemoryFact | apps/backend/tests/test_intelligence_b.py |  |
| MEM-004 | fact derivation rules (e.g. fit_runs_small, best_post_window, repeat_cycle_days) with thresholds + min samples | P6 | TESTED | MEM-003 | apps/backend/app/domains/intelligence/memory.py (fit_runs_small/large, repeat_cycle_days, peak_order_hours, best_courier_route) | apps/backend/tests/test_intelligence_b.py | best_post_window needs content metrics (Phase 7) |
| MEM-005 | merchant correction (reject/edit fact → new version, respected by derivations), audited | P6 | TESTED | MEM-004 | apps/backend/app/domains/intelligence/memory.py::confirm/correct/reject (audited) | apps/backend/tests/test_intelligence_b.py::test_rejected_fact_is_not_derived_again_until_the_method_changes |  |
| MEM-006 | privacy: customer-level facts limited to operational needs; deletion/anonymisation path | P6 | TESTED | MEM-003 | apps/backend/app/domains/intelligence/memory.py (no customer-subject facts/metrics) | apps/backend/tests/test_intelligence_b.py::test_memory_holds_no_personal_facts_and_is_tenant_isolated | ADR-067 |
| MEM-007 | API summaries + Store Manager tool get_memory_facts | P6 | IMPLEMENTED | MEM-005 | apps/backend/app/domains/intelligence/router.py /intelligence/memory/* | apps/backend/tests/test_intelligence_b.py | Store Manager tool not built (no Store Manager agent yet) |
| MEM-008 | recompute on method_version change (backfill job) | P6 | TESTED | MEM-004 | apps/backend/app/domains/intelligence/memory.py::put_fact (method_version), compute_all nightly | apps/backend/tests/test_intelligence_b.py::test_rejected_fact_is_not_derived_again_until_the_method_changes |  |
| APS-001 | capability registry (eligibility rules per capability, steps-per-operation constants) | P6 | TESTED | AUT-018 | apps/backend/app/domains/intelligence/aps.py (CAPABILITY_OF, ACTION_CAPABILITY, STEPS) | apps/backend/tests/test_intelligence.py::test_score_counts_automated_failed_manual_and_excluded_with_thin_data | 8 capabilities from the Phase 5 action log |
| APS-002 | daily AutopilotMetric aggregation from AutomationActionLog (A/F/M/X with reasons) | P6 | TESTED | APS-001 | apps/backend/app/domains/intelligence/aps.py::compute | apps/backend/tests/test_intelligence.py::test_score_counts_automated_failed_manual_and_excluded_with_thin_data | Computed live from AutomationActionLog over a 30-day window (no separate daily metric table); A/F/M/X with exclusion reasons |
| APS-003 | AutopilotScoreSnapshot (volume-weighted overall; thin-data handling) | P6 | TESTED | APS-002 | apps/backend/app/domains/intelligence/aps.py::snapshot; models.AutopilotScoreSnapshot | apps/backend/tests/test_intelligence.py::test_score_api_levers_need_the_plan_and_snapshots_flag_jumps | Volume-weighted; capabilities under 10 eligible operations show 'not enough data' and don't count |
| APS-004 | improvement recommendations (largest gap with config lever; estimated coverage from last 30 days) | P6 | TESTED | APS-003 | apps/backend/app/domains/intelligence/aps.py::levers | apps/backend/tests/test_intelligence.py::test_score_api_levers_need_the_plan_and_snapshots_flag_jumps | Largest manual gap with a config lever (template workflow); coverage estimated from the last 30 days |
| APS-005 | API + Control Center + Store Manager tool; upsell hook via REC (plan_upgrade) | P6 | TESTED | APS-004 | apps/backend/app/domains/intelligence/router.py; web AutopilotScoreCard; mobile autopilot_score_card | Intelligence.test.tsx; mobile intelligence_test; e2e phase6a | Store Manager tool and plan_upgrade recommendation not built (GAP-APS-TOOL) |
| APS-006 | audit sampling: manual-audit comparison tool (±2 points exit criterion) | P6 | NOT_STARTED | — | — | — |  |
| APS-007 | anomaly flag on sudden score jumps | P6 | TESTED | APS-003 | apps/backend/app/domains/intelligence/aps.py::snapshot (anomaly) | apps/backend/tests/test_intelligence.py::test_score_api_levers_need_the_plan_and_snapshots_flag_jumps | Flags jumps of 25+ points against the previous snapshot |
| REC-001 | Recommendation + RecommendationEvidence + RecommendationOutcome models | P6 | TESTED | — | apps/backend/app/domains/intelligence/models.py::Recommendation (evidence, baseline, outcome inline) | apps/backend/tests/test_intelligence.py::test_autopilot_recommendation_is_r3_accepted_by_a_manager_and_measured | Evidence and outcome are JSON columns on the recommendation, not separate tables (ADR-062) |
| REC-002 | typed recommended_action commands (mapped to automation actions) | P6 | TESTED | REC-001 | apps/backend/app/domains/intelligence/recommendations.py::_execute | apps/backend/tests/test_intelligence.py::test_courier_selection_recommendation_switches_to_smart | enable_template, set_courier_selection, create_restock_task |
| REC-003 | explanation object builder (what/why/evidence/confidence/impact/action) — deterministic | P6 | TESTED | REC-001 | apps/backend/app/domains/intelligence/recommendations.py generators + view | Intelligence.test.tsx | Deterministic what/why/evidence/confidence/impact/action; no AI narrative (REC-004) |
| REC-004 | insight-narrative AI task with faithfulness validation (no new numbers) | P6 | NOT_STARTED | — | — | — |  |
| REC-005 | policy routing (AUT-016) → auto / approval (Needs Your Attention) / blocked | P6 | TESTED | AUT-016 | apps/backend/app/domains/intelligence/recommendations.py::accept → policy.decide (R3) | apps/backend/tests/test_intelligence.py::test_autopilot_recommendation_is_r3_accepted_by_a_manager_and_measured | Always R3: needs a person with automation.approve, in every mode (ADR-061) |
| REC-006 | accept/reject APIs (idempotent; reasons) + expiry | P6 | TESTED | REC-005 | apps/backend/app/domains/intelligence/router.py accept/reject (Idempotency-Key); 30-day expiry | apps/backend/tests/test_intelligence.py::test_rejected_recommendations_dont_come_back_and_restock_uses_real_sales |  |
| REC-007 | outcome measurement jobs (pre/post, holdout/DiD where possible) + impact analytics | P6 | IMPLEMENTED | REC-006 | apps/backend/app/domains/intelligence/recommendations.py::measure | apps/backend/tests/test_intelligence.py::test_autopilot_recommendation_is_r3_accepted_by_a_manager_and_measured | Pre/post after 14 days for score suggestions only; no holdout/DiD yet (GAP-REC-CAUSAL) |
| REC-008 | dedupe + rate limiting of recommendations per merchant (no spam) | P6 | TESTED | REC-001 | apps/backend/app/domains/intelligence/recommendations.py::generate (dedupe key, MAX_OPEN=10, rejected stay rejected) | apps/backend/tests/test_intelligence.py::test_rejected_recommendations_dont_come_back_and_restock_uses_real_sales |  |
| RTI-001 | return-reason metrics by product/variant/size/content version/supplier/campaign | P6 | TESTED | RET | apps/backend/app/domains/intelligence/return_intel.py::stats | apps/backend/tests/test_intelligence_b.py | By product/variant/reason; content version, supplier batch and campaign aren't recorded yet |
| RTI-002 | pattern detection (share vs baseline, min sample, significance) → ReturnInsight | P6 | TESTED | RTI-001 | apps/backend/app/domains/intelligence/return_intel.py::detect (min sample, exact binomial vs baseline) | apps/backend/tests/test_intelligence_b.py::test_return_pattern_becomes_a_fit_fact_used_in_chat_only_after_the_seller_confirms; test_small_samples_raise_nothing |  |
| RTI-003 | suspected-cause linking (content/image version shown at purchase, supplier batch) | P6 | IMPLEMENTED | RTI-002 | apps/backend/app/domains/intelligence/return_intel.py::_causes | apps/backend/tests/test_intelligence_b.py | Variant concentration + preferred supplier; content version shown as not tracked (Phase 7) |
| RTI-004 | recommendations (size guide, fit warning, description, image, stop creative, size-up hint, supplier flag) | P6 | TESTED | RTI-002 | apps/backend/app/domains/intelligence/recommendations.py::_returns | apps/backend/tests/test_intelligence_b.py | Fit note (confirm fact) or 'I've fixed it' (starts measurement) |
| RTI-005 | before/after impact measurement | P6 | TESTED | RTI-004 | apps/backend/app/domains/intelligence/return_intel.py::measure; recommendations outcome | apps/backend/tests/test_intelligence_b.py::test_return_pattern_becomes_a_fit_fact_used_in_chat_only_after_the_seller_confirms | Pre/post after 30 days and 10 sales |
| RTI-006 | Return Insight Card + Sales Agent fit hint | P6 | TESTED | RTI-004 | apps/backend/app/domains/intelligence/memory.py::confirmed_fit; inbox/agent.py fit hint; web/mobile cards | apps/backend/tests/test_intelligence_b.py::test_return_pattern_becomes_a_fit_fact_used_in_chat_only_after_the_seller_confirms | Agent uses only seller-confirmed facts (ADR-066) |
| CRI-001 | CourierPerformanceMetric by courier × route × weight band × COD | P6 | TESTED | FUL | apps/backend/app/domains/intelligence/courier_brain.py::recompute; models.CourierPerformanceMetric | apps/backend/tests/test_intelligence.py::test_courier_brain_picks_the_courier_that_delivers_on_this_route | 90 days, courier × district × weight band × COD; nightly |
| CRI-002 | expected-cost model (price + failure cost × failure prob + settlement delay cost) | P6 | TESTED | CRI-001 | apps/backend/app/domains/intelligence/courier_brain.py::rank | apps/backend/tests/test_intelligence.py::test_courier_brain_picks_the_courier_that_delivers_on_this_route | Handling cost (NPR 50) and cash-holding cost are documented estimates (ADR-063) |
| CRI-003 | selection modes cheapest/fastest/smart/preferred-only with policy integration | P6 | TESTED | CRI-002 | apps/backend/app/domains/intelligence/courier_brain.py MODES; fulfillment courier_selection | apps/backend/tests/test_intelligence.py::test_courier_selection_recommendation_switches_to_smart | rules / cheapest / fastest / smart / preferred |
| CRI-004 | explanation ("selected because …") + alternatives | P6 | TESTED | CRI-003 | apps/backend/app/domains/intelligence/courier_brain.py::_result; web DeliveryPanel | apps/backend/tests/test_intelligence.py::test_courier_brain_picks_the_courier_that_delivers_on_this_route |  |
| CRI-005 | cold-start fallback (merchant preference/rules) with explicit low-confidence label | P6 | TESTED | CRI-003 | apps/backend/app/domains/intelligence/courier_brain.py (MIN_SAMPLE=20) | apps/backend/tests/test_intelligence.py::test_courier_brain_picks_the_courier_that_delivers_on_this_route | Under 20 finished parcels: falls back to rules with a 'not enough data' note |
| CRI-006 | ETA calibration monitoring | P6 | NOT_STARTED | — | — | — |  |
| CODI-001 | feature set (allowed inputs only) + static prohibited-feature check | P6 | TESTED | — | apps/backend/app/domains/intelligence/cod_risk.py::ALLOWED_FACTORS | apps/backend/tests/test_intelligence.py::test_cod_model_reads_no_personal_attributes | Static test: factor allow-list and the module never reads names |
| CODI-002 | CODRiskAssessment (level, score, factors with evidence, recommended action, model_version) | P6 | TESTED | CODI-001 | apps/backend/app/domains/intelligence/cod_risk.py::assess; models.CODRiskAssessment | apps/backend/tests/test_intelligence.py::test_cod_risk_uses_allowed_inputs_only_and_never_rejects | codi-1.0 transparent weighted score |
| CODI-003 | decision-policy integration (LOW auto, MEDIUM per policy, HIGHER review/advance) | P6 | TESTED | CODI-002 | apps/backend/app/domains/intelligence/cod_risk.py (LOW ok, MEDIUM verify phone, HIGHER needs_review) | apps/backend/tests/test_intelligence.py::test_cod_risk_uses_allowed_inputs_only_and_never_rejects; e2e phase6a | Never auto-rejects (ADR-064) |
| CODI-004 | merchant override + dispute workflow (audited) | P6 | TESTED | CODI-003 | apps/backend/app/domains/intelligence/cod_risk.py::override/dispute (audited) | apps/backend/tests/test_intelligence.py::test_cod_risk_uses_allowed_inputs_only_and_never_rejects; e2e phase6a | Override with reason clears the hold and changes the advice |
| CODI-005 | outcome capture + calibration monitoring + regional disparity report | P6 | IMPLEMENTED | CODI-002 | apps/backend/app/domains/intelligence/cod_risk.py::calibration (outcome by level, per district) | apps/backend/tests/test_intelligence.py::test_cod_risk_uses_allowed_inputs_only_and_never_rejects | Ops endpoint only; no alerting on drift yet |
| CODI-006 | phone verification + partial-advance flows (with PAY) | P6 | NOT_STARTED | — | — | — |  |
| CGN-001 | CreativePerformanceMetric (views, engagement, clicks, inquiries, orders, attributed contribution) | P7 | TESTED | CNT-014 | apps/backend/app/domains/intelligence/creative.py; models.CreativePerformanceMetric, ContentChannelMetric | apps/backend/tests/test_creative.py | One row per post over its 7-day window; contribution = margin of attributed lines (None when cost unknown) |
| CGN-002 | genome computation (outcome-weighted effects, min sample, shrinkage) → CreativeGenomeProfile | P7 | TESTED | CGN-001 | apps/backend/app/domains/intelligence/creative.py::compute_genome (min 20 posts, 5 per value, shrinkage k=5, z vs rest) | apps/backend/tests/test_creative.py::test_genome_recommends_what_sells_with_shrinkage | Orders first; inquiries when < 5 orders; likes never recommend (ADR-070) |
| CGN-003 | CreativeExperiment (hypothesis, variants, stopping rule) | P7 | TESTED | CGN-001 | apps/backend/app/domains/intelligence/creative.py::create_experiment/evaluate/stop | apps/backend/tests/test_creative.py::test_experiment_follows_its_stopping_rule | Observational assignment (the seller makes the posts); no randomisation |
| CGN-004 | genome inputs to Studio prompts, Auto Reel template choice, video concepts, schedule suggestions (genome_version recorded) | P7 | TESTED | CGN-002 | apps/backend/app/domains/intelligence/creative.py::suggestions/studio_guidance; studio run_job; media auto-reels + content schedule accept genome_version | apps/backend/tests/test_creative.py::test_genome_version_is_recorded_on_studio_drafts_reels_and_scheduled_posts | Video concepts not built (premium video not built) |
| CGN-005 | Creative Genome panel + Store Manager tool | P7 | IMPLEMENTED | CGN-002 | web Content → What sells; mobile What sells card; creative_tip suggestion | web Creative.test.tsx; mobile creative_test; e2e phase7; axe | Store Manager tool not built (GAP-STORE-MANAGER) |
| CGN-006 | impact measurement of genome-informed content vs baseline | P7 | TESTED | CGN-004 | apps/backend/app/domains/intelligence/creative.py::impact | apps/backend/tests/test_creative.py::test_impact_compares_genome_informed_posts_with_the_rest | Observational comparison, labelled as such |
| SPI-001 | SupplierPerformanceMetric (landed cost, defect, return, on-time, lead-time variance, contribution/unit) | P8 | TESTED | PRO-005 | apps/backend/app/domains/procurement/supplier_intel.py::compute; models.SupplierPerformanceMetric | apps/backend/tests/test_procurement.py::test_true_economics_prefer_the_supplier_with_fewer_defects_and_returns | Complaints = quality returns; no separate complaints log |
| SPI-002 | batch/lot linkage receiving → returns/defects | P8 | IMPLEMENTED | PRO-005 | apps/backend/app/domains/procurement/supplier_intel.py::_attribution (latest lot received before the order) | apps/backend/tests/test_procurement.py::test_true_economics_prefer_the_supplier_with_fewer_defects_and_returns | Approximation: lots aren't tracked per unit (GAP-SPI-LOT) |
| SPI-003 | true-economics supplier recommendation with explanation | P8 | TESTED | SPI-001 | apps/backend/app/domains/procurement/supplier_intel.py::switch_proposals; set_preferred_supplier action | apps/backend/tests/test_procurement.py::test_true_economics_prefer_the_supplier_with_fewer_defects_and_returns |  |
| SPI-004 | reorder recommendation using true economics + lead time | P8 | TESTED | SPI-001 | apps/backend/app/domains/procurement/supplier_intel.py::reorder_proposals (true economics, lead time ± sd, MOQ, incoming, profit limits) | apps/backend/tests/test_procurement.py::test_reorder_suggestion_uses_lead_time_moq_and_creates_a_draft_for_approval; test_loss_makers_are_not_reordered |  |
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
| BRD-001 | Nivaro brand migration audit | BRD | IMPLEMENTED | — | ADR-028; "Nivaro brand migration" section above; before/after screenshots reviewed | Brand guard test (no legacy name in UI copy) | Legacy technical identifiers kept by design |
| BRD-002 | logo asset integration | BRD | TESTED | BRD-006 | Owner artwork extracted (extract_logo.py) → render.mjs; web NivaroMark/NivaroLogo (mask wordmark); Flutter Image.asset logo | Flutter widget test (light+dark); visual check web light/dark | Raster masters; vector master pending (GAP-BRAND-LOGO-VECTOR) |
| BRD-003 | web metadata + theme | BRD | IMPLEMENTED | BRD-002 | app/layout.tsx (title, OG, Twitter, theme from cookie), app/manifest.ts, favicon.ico, icon.png, apple-icon.png, opengraph-image.png; light default (ADR-033) | Manifest + icon served 200 on the dev server (manual) | `NEXT_PUBLIC_SITE_URL` needed for absolute OG URLs in prod |
| BRD-004 | Flutter branding | BRD | TESTED | BRD-002 | Display name, launcher icons (Android + iOS), NivaroMark/NivaroLogo, automation colour → brand blue | flutter analyze; nivaro_brand_test (2) + full suite | Never run on a device (GAP-MOBILE-TOOLCHAIN) |
| BRD-005 | Nivaro Console branding | BRD | TESTED | ADM | apps/web/src/features/console | e2e console-real-backend (desktop + 360) | Navy top bar, white lockup + Console suffix, environment badge, dense tables, no accents (26 §14) |
| BRD-006 | design-token migration | BRD | TESTED | — | design-tokens.json v1.0 semantic layer; generator emits light/dark CSS, TS, Dart AppColorsLight/Dark | Brand guard (no hex/indigo); all CSS vars resolve (checked) | Legacy aliases kept |
| BRD-007 | banner system | BRD | IN_PROGRESS | BRD-008 | Grammar + variants in specs/26 §10; og-default; sign-in panel | — | Campaign set pending (GAP-BRAND-BANNERS) |
| BRD-008 | graphic motif library | BRD | IN_PROGRESS | BRD-002 | N-trail, commerce loop, outlined-trail empty state, active ribbon, 4 hand accents | Visual review | Sync stream + order route motifs pending |
| BRD-009 | character system | BRD | BLOCKED | — | Brief in assets/brand/characters | — | Needs an illustrator; no placeholders (GAP-BRAND-CHARACTERS) |
| BRD-010 | illustration guide | BRD | IMPLEMENTED | — | specs/26 §11 | — | Spot illustrations pending with BRD-009 |
| BRD-011 | motion system | BRD | IN_PROGRESS | BRD-006 | Motion tokens incl. flow; reduced-motion zeroing; ribbon trace (`NTrail animate`) | — | Sync pulse, step settle, milestone pending (GAP-BRAND-MOTION) |
| BRD-012 | app icon / favicon | BRD | IMPLEMENTED | BRD-002 | Generated favicon, apple, PWA (incl. maskable), Android mipmaps, iOS AppIcon | Visual check | Adaptive Android icon + Flutter icon set pending (GAP-BRAND-ICONS) |
| BRD-013 | dark/light logo variants | BRD | IMPLEMENTED | BRD-002 | assets/brand/logo/{primary,dark,light,monochrome} | Visual check | |
| BRD-014 | marketing-site art direction + build | BRD | TESTED | GTM | Public site at `/` (features/site): en/ne, light default + theme switch, ribbon lifecycle, illustrative fragments, hand accents, scroll reveal/trace/count-up (reduced-motion safe) | site.test.tsx (5); e2e/site.spec.ts (desktop + 360px); visual review light/dark/ne/mobile | No prices/photos/legal pages yet (GAP-MARKETING-SITE) |
| BRD-015 | UX copy migration | BRD | TESTED | — | en/ne meta + brand keys, sign-in copy, "Soon" instead of phase codes, email subject/sign-off/sender, OpenAPI title | i18n parity tests; brand guard; backend suite | Nepali tagline needs native review |
| BRD-016 | visual QA | BRD | IN_PROGRESS | — | brand-guard.test.ts; desktop + 390px screenshot review of auth, home, products, studio, content, channels, plan | 3 guard tests | Per-surface QA continues as surfaces are built |

Status counts: BLOCKED 5, IMPLEMENTED 29, IN_PROGRESS 12, NOT_STARTED 43, TESTED 244. **PRODUCTION_READY: 0** (no staging/alerts/runbooks yet).
