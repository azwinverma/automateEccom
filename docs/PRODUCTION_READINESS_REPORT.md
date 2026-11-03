# Production Readiness Report: Nivaro

> 2026-11-03, after the QA cycle in `docs/QA_TEST_REPORT.md`.

## Overall status: **NOT_READY**

The code that exists is in a verified, stable state:
- All suites are green.
- No BLOCKER, CRITICAL or HIGH issue remains open; the 6 found were fixed and regression-tested.
- Production builds succeed and critical E2E flows pass.

Nivaro is still **not production ready**, for reasons outside the code that exists today:
1. **The core commerce loop isn't built yet.** Orders, inventory, payments/COD, couriers, returns, inbox and the AI sales agent are Phases 2–5. Today's product is Phase 0–1: catalog, AI Studio, media, content, channel publishing and accounts.
2. **No staging or production environment, monitoring, alerting, runbooks or backup regime exists.** These are Definition of Done requirements (24).
3. **No external integration has been exercised live:**
   - AI providers
   - Meta, TikTok and Shopify
   - a live WooCommerce store
   - email delivery
   - object storage (S3/MinIO)
   - payment of plans

No feature is marked PRODUCTION_READY in `docs/IMPLEMENTATION_STATUS.md`.

## Test summary

| | Total | Passed | Failed | Skipped | Blocked |
|---|---|---|---|---|---|
| Backend pytest | 181 | 181 | 0 | 0 | 0 |
| Web unit + API client | 242 | 242 | 0 | 0 | 0 |
| E2E (real backend, 2 viewports) | 16 | 16 | 0 | 0 | 0 |
| Flutter | 102 | 101 | 0 | 1 (live flow; run separately and passed) | 0 |
| Adversarial probe checks | 207 | 207 | 0 | 0 | 0 |
| axe (pages × configurations) | 39 | 39 | 0 | 0 | 0 |
| **Total** | **787** | **786** | **0** | **1** | **0** |

External checks that couldn't run are listed under "External tests pending".

## Critical flows

| Flow | Status |
|---|---|
| Auth (signup, login, sessions, refresh, MFA, reset, verification, lockout) | **PASS** |
| Tenant isolation | **PASS** (after BLOCKER QA-012 fix) |
| RBAC | **PASS** (API-enforced) |
| Catalog | **PASS** |
| AI content (Studio drafts) | **PASS with sandbox provider**; live model BLOCKED_EXTERNAL |
| AI image / video | Auto Reels **PASS**; AI image editing and premium AI video NOT_IMPLEMENTED |
| Subscriptions / quotas | Enforcement **PASS** (after CRITICAL QA-015 fix); plan payment BLOCKED_EXTERNAL |
| Channels / publishing | **PASS (sandbox + WooCommerce contract)**; live platforms BLOCKED_EXTERNAL |
| Inbox / AI Sales Agent | NOT_IMPLEMENTED (Phase 2) |
| Orders / inventory / payments / COD / fulfillment / returns | NOT_IMPLEMENTED (Phases 2–4) |
| Automation / Autopilot | NOT_IMPLEMENTED (Phase 5) |
| Analytics / intelligence | NOT_IMPLEMENTED (Phases 6–10) |
| Admin | API **PASS**; Console UI NOT_IMPLEMENTED |

## Known risks
- **CSP allows inline scripts** (Next.js bootstrap). A nonce-based CSP is a follow-up.
- **Rate limiting fails open if Redis is down.** Account lockout (database-backed) still protects logins.
- **Logo artwork is raster.** A vector master is needed for print (GAP-BRAND-LOGO-VECTOR).
- **Untested at scale.** Throughput and load (webhook floods, flash sales) haven't been measured. Concurrency correctness is covered.
- **One-device testing.** The Flutter app has been tested on emulated and web targets and with a live API flow, but not interactively on a physical device; iOS hasn't been built.

## External tests pending (BLOCKED_EXTERNAL)

| Dependency | Tested with | Still needed | Manual procedure |
|---|---|---|---|
| Anthropic / OpenAI / Gemini keys | Sandbox provider and mocked HTTP failures | Real quality, latency, cost | Set `COS_ANTHROPIC_API_KEY`; run Studio photo → draft; `uv run python -m app.cli run-evals studio` |
| Meta / TikTok / Shopify apps | Sandbox channel (full OAuth shape) | App review, real publishing | Create apps; register redirect URIs; connect in Settings → Channels; publish one product and one post |
| WooCommerce store | Contract tests against recorded API shapes | Live store | Connect a staging store with REST keys; publish a variable product; place a test order and watch the webhook |
| Email provider | Console mailer (`.data/mailbox`) | Deliverability, SPF/DKIM/DMARC | Choose provider and domain (GAP-EMAIL-DOMAIN); send verification, invite and reset emails |
| Object storage | Local storage adapter | S3/MinIO path (FND-006) | `docker compose up` with MinIO; upload and process a photo |
| ClamAV | Scanner adapter unit tests | Real scan | Run clamd in staging; upload the EICAR test file |
| Plan billing / payment provider | Entitlement engine | Charging, upgrade/downgrade, renewal | After pricing (GAP-SPEC-21) and provider choice |

## Security status
- **Strong:**
  - tenant isolation (guessed IDs, header spoofing, body references)
  - RBAC enforced server-side
  - refresh rotation with family revocation
  - single-use TOTP and recovery codes
  - password reset that revokes sessions and avoids enumeration
  - lockout and rate limits
  - CSP, X-Frame-Options and HSTS (on HTTPS)
  - sealed secrets; no secrets in responses or logs
  - dependency audits clean
- **Not done:**
  - SAST, secret and container scans haven't run in CI (no git remote, GAP-CI-RUN)
  - no external penetration test
  - no KMS (GAP-KMS)

## Performance status
Local measurements, single node:
- product list p95 10 ms, detail p95 12 ms, exceptions p95 17 ms, entitlements p95 26 ms
- no N+1 queries on 6 list endpoints

Production-like load testing needs staging.

## Backup / restore status
A local logical backup → restore drill passed: identical schema and row counts. There's **no production backup, PITR, object-storage backup or tested disaster-recovery runbook**. Not DR ready.

## Recommended launch blockers
1. Build the order-to-delivery loop (Phases 2–3), at minimum orders, inventory, COD and a courier, before any paid launch. That's the product promise.
2. Staging environment with CI running (remote plus hosting decision), alerts, dashboards and runbooks.
3. Live AI provider key, with evaluation results above threshold.
4. At least one live channel (WooCommerce store or an approved Meta app).
5. Email provider and domain; object storage; malware scanning in staging.
6. Production database with PITR plus a tested restore runbook; object-storage backup.
7. Pricing and plan billing (GAP-SPEC-21).
8. An external security review of auth, tenancy and uploads.
