# QA Test Report: Nivaro production-readiness cycle

> Cycle: 2026-11-02 → 2026-11-03. Scope: everything implemented (Phases 0–1 plus the public website).
> Method:
> - repo-wide audit
> - every automated suite
> - an adversarial black-box probe against a live, isolated stack (`apps/backend/qa/probe.py`, 207 checks)
> - failure injection
> - performance, N+1, accessibility (axe, WCAG 2.2 AA) and responsive sweeps
> - backup/restore drill
>
> Every bug was reproduced before fixing, fixed at the root, and pinned by a regression test
> (`apps/backend/tests/test_qa_regressions.py` unless stated).

## 1. Final results

| Suite | Result |
|---|---|
| Backend pytest (real Postgres 14 + Redis 7) | **181 passed**, 0 failed, coverage 88% (was 165 / 87%) |
| Backend ruff · format · mypy | clean · clean · clean (113 files) |
| Migrations (fresh DB) | upgrade → downgrade base → upgrade → `alembic check` clean; 12 revisions |
| Web unit (vitest) | **217 passed** (was 214); API client 25 passed |
| Web lint · typecheck · production build | clean · clean · ok |
| E2E Playwright vs real backend + worker (desktop + 360px) | **16/16 passed**, with a CSP-violation guard on every test |
| Adversarial API probe (`qa/probe.py`) | **207/207 passed** |
| Accessibility (axe-core 4.14, WCAG 2.2 A/AA): 13 pages × light/dark × 1280/360 | **0 violations** |
| Responsive: 15 pages × 320 / 768 (ne) / 1024 / 1920 | **0 horizontal overflow** |
| Flutter analyze · test · live flow vs API | clean · **101 passed**, 1 skipped (needs `LIVE_API`) · live flow passed |
| Flutter builds | debug APK, release APK (26.5 MB), web: ok. iOS not built (GAP-MOBILE-TOOLCHAIN) |
| Docker images | backend (with `--build-context contracts=packages/contracts`) and web: ok |
| Dependency audit | `pnpm audit --prod`: none after fix; `pip-audit`: none |
| Logs secret scan (API, worker, web) | 0 hits (passwords, JWTs, refresh tokens, provider keys, hashes, reset tokens) |

## 2. Issues found

Severity:
- **BLOCKER:** cross-tenant data, or nothing works.
- **CRITICAL:** security or billing integrity.
- **HIGH:** core flow broken.
- **MEDIUM:** degraded, or a risk.
- **LOW**, **COSMETIC**.

All issues below are **VERIFIED** (fixed, regression test green, full suite green) unless marked.

### QA-012 · BLOCKER · Cross-tenant references (content, video)

| | |
|---|---|
| Description | A request body could reference another merchant's product. |
| Steps | Merchant A sends `POST /content/posts {"product_id": <B's product>}` and gets 201. Merchant A sends `POST /media/videos/auto-reels {"product_id": <B's product>}` (show_price off) and gets 202. |
| Expected | 404 |
| Actual | The record is stored with a foreign reference. |
| Root cause | `create_post` never checked ownership of `product_id`. The reel service checked only when `show_price` was on. |
| Fix | Ownership is checked whenever a product id is given: `catalog_service.get_product` (tenant 404) and the reel product check. |
| Regression | `test_qa012_no_request_body_can_reference_another_merchants_records` sweeps **13 body-level id references**: post product/media/connection, product and category parent, product media/variant, publish connections, reconnect id, reel media and product, studio media. |
| Files | `content/service.py`, `media/video.py` |
| Remaining risk | New endpoints must be added to the sweep (noted in the test docstring). |

### QA-015 · CRITICAL · Plan limits bypassable by concurrency

| | |
|---|---|
| Description | Gauge limits (products, channels, seats, stores, storage) were count-then-insert. |
| Steps | At 97 of 100 products, send 10 concurrent creates. |
| Expected | 3 succeed. |
| Actual | All 10 succeed; usage reaches 107 of 100. |
| Root cause | No serialisation between the count and the insert. |
| Fix | `check_gauge` takes a transaction-scoped Postgres advisory lock per (merchant, resource) before counting. It is held until commit, so concurrent creates serialise and other merchants never wait. |
| Regression | `test_qa015_gauge_limit_holds_under_concurrency`. The test was proven to fail with the lock removed and pass with it. |
| Files | `billing/service.py` |
| Remaining risk | Consumable quotas already used row-locked reserve/finalize (unchanged, tested). |

### QA-001 · HIGH · No password reset

| | |
|---|---|
| Description | There was no way to recover an account. |
| Root cause | Never specified in the backlog. It's required for production login (IAM-002/003). |
| Fix | `POST /auth/password/forgot` always returns 202 (no account enumeration) and is rate-limited per IP and per email. It issues a single-use 30-minute hashed token; issuing a new one voids older ones. `POST /auth/password/reset` enforces password policy, revokes **all** sessions, clears lockout, writes an audit record and sends a "password changed" email. Migration 0011 adds `password_reset_tokens`; two catalogued events were added. |
| UI | Web `/forgot-password` and `/reset-password`, plus a "Forgot password?" link on sign-in. Mobile has a native forgot screen; the emailed link opens the web reset page. All copy in English and Nepali. |
| Regression | Backend tests: end to end, older-token invalidation, expiry, rate limit. Web E2E: forgot → email → reset → sign in. Mobile widget test and route test. |

### QA-008 · HIGH · Email links went to 404

| | |
|---|---|
| Description | Every invitation (`/invite?token=`) and verification (`/verify-email?token=`) email linked to pages that didn't exist, so invited teammates could not join. |
| Root cause | Pages never built. E2E never followed an email link. |
| Fix | Web `/invite` (signed-out visitors get sign-in or create-account with `?next=`; signed-in visitors see Accept and land in the shop) and `/verify-email` (single-use, safe on reload). Middleware treats both as public. Login and register honour `next` for invitees who have no business yet. Error copy added for `invitation_*`, `verification_invalid`, `reset_invalid` and `weak_password`. |
| Regression | `e2e/account-links.spec.ts` reads the real dev mailbox and runs invite → sign up → accept → shop, plus verify-email (desktop and 360px). |

### QA-011 · HIGH · TOTP codes reusable

| | |
|---|---|
| Description | The same 6-digit code, or a replayed `mfa_token` plus code, opened a second session. |
| Root cause | `pyotp.verify` with no replay memory (RFC 6238 §5.2). |
| Fix | `users.mfa_totp_last_step` (migration 0012). A code is accepted only for a newer time-step. The user row is locked during verification, so concurrent replays can't both pass. Codes must be exactly 6 digits. Setting up a new secret resets the step. |
| Regression | `test_qa011_totp_code_is_accepted_only_once`. The existing MFA test now uses consecutive steps, as real authenticators do. |
| Remaining risk | A user who enables MFA and signs in within the same 30 seconds must wait for the next code (standard). |

### QA-013 · HIGH · 500 on concurrent same-title products

| | |
|---|---|
| Description | 8 parallel creates with the same title: 1 created, 7 got HTTP 500. |
| Root cause | The auto-generated handle raced on `uq_catalog_products_merchant_id_handle` outside a savepoint. |
| Fix | Insert inside a savepoint. An auto handle collision retries with a short suffix; a seller-chosen handle gets a clean 409 `handle_taken`. |
| Regression | `test_qa013_concurrent_same_title_products_never_500` and `test_qa013_explicit_handle_collision_is_409`. |

### QA-002 · HIGH · Vulnerable dependency (build-time)

| | |
|---|---|
| Description | `pnpm audit`: postcss < 8.5.23, 2 high and 2 moderate advisories, via `next`. |
| Fix | Root `pnpm.overrides.postcss = ^8.5.23`. |
| Verified | Audit clean; production build and E2E green. |

### QA-009 · MEDIUM · No CSP or HSTS on web pages

| | |
|---|---|
| Fix | Middleware sets the CSP at request time: `default-src 'self'`, API origin allowed only for connect/img/media, `object-src 'none'`, `frame-ancestors 'none'`, `base-uri` and `form-action 'self'`. HSTS is sent only over HTTPS. |
| Regression | `src/lib/security-headers.test.ts`, plus the E2E CSP-violation guard on all 16 tests. |
| Remaining | Scripts still need `'unsafe-inline'` (Next.js bootstrap). A nonce-based CSP is a follow-up. |

### QA-014 · MEDIUM · Upload larger than declared

| | |
|---|---|
| Description | A slot declared at 1 KB accepted up to 20 MB, and the storage quota was checked on the declared size. |
| Fix | `complete` requires stored bytes to equal the declared size; on mismatch it deletes the object and returns `upload_size_mismatch`. |
| Regression | `test_qa014_upload_must_match_declared_size`. |

### QA-016 · MEDIUM · Database outage returned 500

| | |
|---|---|
| Description | With Postgres unreachable, requests returned `internal_error` 500 with stack traces. |
| Fix | Connection-class failures (no SQLSTATE, 08xxx, 57P0x, 53300) return 503 `dependency_unavailable` with `Retry-After: 5`, logged as a single warning. Query bugs remain 500. |
| Regression | `test_qa016_database_outage_is_503_not_500`, plus a live re-injection. |

### QA-017 · MEDIUM · Accessibility

| | |
|---|---|
| Description | (1) Contrast 4.34:1 for muted text on tinted surfaces (website). (2) White on coral 2.8:1. (3) WCAG 2.5.3 label-in-name on the business switcher and account menu on every app page. |
| Fix | Muted text resolves to Slate 700 on tinted surfaces; ink on coral. Visible text plus a screen-reader-only prefix instead of `aria-label`. |
| Verified | axe: 0 violations across 13 pages × 3 configurations. |

### QA-018 · MEDIUM · Responsive overflow

| | |
|---|---|
| Description | (1) Sign-in, register and forgot pages at 320px: +54px (new theme switch). (2) New-product page at 1024px: +139px. |
| Root cause | (2) Screen-reader-only labels inside table cells were positioned outside the scroll container. |
| Fix | The auth top row wraps. The variant grid is in a focusable, labelled scroll region with `position: relative`. |
| Verified | 0 overflow at 320, 768, 1024 and 1920 px. |

### QA-003 · LOW · Listings ownership

| | |
|---|---|
| Description | `GET /catalog/products/{foreign}/listings` returned 200 `[]` instead of 404 (no data leaked). |
| Fix | Tenant product check. `test_channels` updated to expect 404. |

### QA-004 · LOW · Money coercion

| | |
|---|---|
| Description | `"100"`, `true` or `"1e3"` were accepted as `price_minor` / `cost_minor` / `compare_at_minor`. |
| Fix | Pydantic `strict=True` on all minor-unit fields. Web and mobile already send integers. |

### QA-010 · LOW · Test gap: no test for the per-minute login rate limit

Added `test_qa010_login_is_rate_limited_per_ip_and_per_email`.

### QA-005 / QA-006 / QA-019 · LOW · Warnings

| | |
|---|---|
| QA-005 | Alembic `path_separator` deprecation. Fixed in `alembic.ini`. |
| QA-006 | Expected `DecompressionBombWarning` from the bomb test. Suppressed in that test only. |
| QA-019 | Pydantic `UnsupportedFieldAttributeWarning` on the `X-Merchant-Id` header. Fixed with the `Annotated[..., Header()]` form. |
| Remaining | One third-party warning: FastAPI internals (`alias='body'`) when a test builds a second app instance. Not our code. Documented. |

### QA-020 · LOW · Tooling

- Web ESLint and tsconfig now ignore `.next-*` build folders.
- `NEXT_DIST_DIR` lets a production or QA build run beside `next dev`.
- The backend Docker build needs `--build-context contracts=packages/contracts` outside compose (compose already provides it). Now documented.

### QA-021 · LOW (OPEN, accepted) · Outage log noise

During a database outage, Starlette still logs the re-raised exception after the 503 response is sent. Framework behaviour; it only adds noise during an outage.

### Not bugs: probe expectations corrected

Validation errors are 400 `validation_error` (the documented contract), not 422. Rate limiting and account lockout worked as designed (the probe now respects `Retry-After` and asserts lockout separately). A foreign photo id gets the same `media_not_ready` 409 as a missing one, so there is no existence oracle.

## 3. Coverage by area (spec §2–§45)

| Area | Status | Evidence |
|---|---|---|
| **Auth.** Signup, login, logout, expired and tampered tokens, refresh rotation, reuse detection (whole family revoked), multiple sessions, cross-user revoke, invalid password, no enumeration, lockout, rate limit, MFA (wrong, valid, single-use, recovery codes once), password reset, email verification (invalid, used) | PASS | probe auth (43 checks), pytest auth and regressions, E2E |
| **Tenant isolation.** 2 merchants; 28 guessed-ID attacks across products, variants, categories, collections, media, posts, invitations, members, stores, channels and listings; header spoofing on 10 list endpoints; filters; 13 body references; bulk collection set | PASS (after QA-012) | probe tenancy, `test_qa012`, `test_tenancy_rbac` |
| **RBAC.** Owner, admin, manager, staff, viewer × 12 operations checked against `/permissions/me` (API, not UI); privilege escalation (manager → admin invite, self → owner); admin can't remove owner; removed member loses access | PASS | probe rbac |
| **Catalog.** Variants (shirt 3×2, shoes 7×2, single SKU), duplicate and concurrent SKU, duplicate option combination, invalid, negative, huge and non-integer money, option/variant limits, status transitions, archived edit, optimistic locking, malformed and oversized CSV, pagination bounds | PASS (after QA-004, QA-013) | probe catalog, pytest catalog |
| **Media.** Executable, SVG, 0 B and 200 MB slots, path traversal, corrupted image, size mismatch, tampered signed URL, unknown asset, EXIF/GPS, bomb, derivatives, malware path | PASS (after QA-014) | probe media, pytest media |
| **Video (Auto Reels).** Render, failure, cancel without charge, Nepali shaping guard, cross-tenant media and product | PASS | pytest reels, QA-012 |
| **Premium AI video** | NOT_IMPLEMENTED (no provider; entitlement and quota model tested) | |
| **Subscriptions and quotas.** Feature gates, reserve/finalize/release, monthly and daily burst, gauges, concurrent near-limit | PASS (after QA-015) | pytest entitlements, `test_qa015`, probe quota |
| **Credit purchase, upgrade, downgrade, renewal, payment of plans** | BLOCKED_EXTERNAL (no billing provider; GAP-SPEC-21 pricing) | |
| **AI gateway.** Routing, transient retry, fallback, refusal, schema validation, circuit breaker, cost ledger, grounding guard, evals | PASS with sandbox and mock providers | pytest ai_gateway, studio, evals |
| **Live Claude, OpenAI and Gemini calls** | BLOCKED_EXTERNAL (no keys) | Manual: set `COS_ANTHROPIC_API_KEY`, run the Studio photo → draft flow and `app.cli run-evals` |
| **BYOK.** Envelope encryption, no raw key returned | PASS (unit and API) | pytest ai_gateway; probe "no secrets" |
| **Channels.** Sandbox OAuth (state bound, consent, callback), capabilities, health, reconnect, webhooks (unsigned/oversized rejected, dedupe, replay), WooCommerce contract | PASS | pytest channels and woocommerce, probe platform, E2E |
| **Live Meta, TikTok, Shopify, WooCommerce** | BLOCKED_EXTERNAL (platform app review, live store) | Manual: connect a staging Woo store with keys; publish a product; verify webhook delivery |
| **Publishing.** Draft, schedule, immediate, approval policy, partial channel failure, retry, cancel | PASS (sandbox) | pytest content |
| **Exception Inbox.** Expired channel, failed publish, blocked upload, listing drift | PASS | pytest exceptions |
| **Admin API.** Non-staff 404, staff without MFA 403, flags, DLQ replay, webhooks; no secrets returned | PASS (API only) | probe platform, pytest platform |
| **Admin Console UI** | NOT_IMPLEMENTED (GAP-CONSOLE-UI) | |
| **Inbox, AI Sales Agent, conversation-to-order, CRM, orders, inventory, payments, COD, courier, returns/refunds, automation engine, Autopilot Score, Product Brain, Memory, Creative Genome, profit/COD/courier/return/supplier intelligence, Store Twin, simulation** | NOT_IMPLEMENTED (Phases 2–10, roadmap 22) | No code exists to test. Each needs its own QA cycle when built. |
| **Brand/UI.** Old names, hex colours, legacy indigo | PASS | brand guard tests; screenshot review |
| **Accessibility** | PASS (after QA-017) | axe sweep |
| **Responsive** | PASS (after QA-018) | overflow sweep, E2E at 360px |
| **Flutter.** Analyze, unit, widget, live flow, debug/release/web builds | PASS. iOS and physical-device runs not done here | |
| **Database.** Migrations clean and round-trip; no N+1 (query count constant at 5 vs 50 rows on 6 list endpoints) | PASS | |
| **Performance (local, 95 products × 3 variants).** List p95 10 ms, detail 12 ms, exceptions 17 ms, entitlements 26 ms; 95 creates in 2.2 s at 8-way parallelism | PASS (local only, not load-tested) | |
| **Load.** Webhook floods, flash sale | NOT_TESTED at scale. Concurrency correctness covered (QA-013, QA-015, idempotency); throughput needs staging | |
| **Workers.** Outbox 790/790 dispatched, 0 dead; abandoned-upload cleanup scheduled; idempotent handlers (`outbox_consumptions`) | PASS | |
| **Failure injection.** Redis down: readiness 503, core flows work, rate limit fails open, lockout still in DB. Database down: 503 with `Retry-After` (QA-016) | PASS | |
| **Object storage outage, provider timeouts** | Covered by unit tests with mocks. Live S3/MinIO untested (FND-006) | |
| **Observability.** Request ids on responses and in logs, structured logs without secrets, `/metrics` | PASS (local). Alerts and dashboards don't exist (GAP) | |
| **Backup/restore.** `pg_dump -Fc` → restore → identical schema version and 7 table counts → `alembic check` clean | PASS (local drill). No production backups, PITR or object-storage backup exist | |
| **Clean setup.** `scripts/dev.sh` from a clean checkout; fresh DB migrate and seed; Docker images | PASS | |

## 4. Tools added for repeatable QA

| Tool | What it does |
|---|---|
| `apps/backend/qa/probe.py` | Black-box adversarial probe; run with `QA_API=… uv run python qa/probe.py` |
| `apps/backend/tests/test_qa_regressions.py` | One named test per finding |
| `apps/web/e2e/fixtures.ts` | CSP-violation guard on every E2E test |
| `apps/web/e2e/account-links.spec.ts` | Email-link flows, read from the dev mailbox |
