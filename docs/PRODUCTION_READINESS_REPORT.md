# Production Readiness Report: Nivaro

> 2026-11-03 QA cycle (`docs/QA_TEST_REPORT.md`); updated 2026-11-04 after Phase 1 completion and Phase 2.

## Overall status: **NOT_READY**

The code that exists is in a verified, stable state:
- All suites are green.
- No BLOCKER, CRITICAL or HIGH issue remains open; the 6 found were fixed and regression-tested.
- Production builds succeed and critical E2E flows pass.

Nivaro is still **not production ready**, for reasons outside the code that exists today:
1. **The commerce loop is half built.** Phase 2 (inbox, AI Sales Agent, chat-to-order, orders,
   inventory, payments/COD records) is built and tested end to end. Shipping with couriers, COD
   settlement and failed-delivery recovery (Phase 3), returns/refunds (Phase 4) and automation
   (Phase 5) are not built.
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
| Inbox / AI Sales Agent / chat-to-order | **PASS** (sandbox channel; E2E message → AI → order). Live messaging channels BLOCKED_EXTERNAL; AI replies are grounded templates (ADR-043) |
| Orders / inventory | **PASS** (state machine, no-oversell races, imports, partial cancel) |
| Payments / COD | Verified online payments **PASS with sandbox wallet**; manual payments and COD trail **PASS**; Nepal gateway BLOCKED_EXTERNAL (GAP-PAY-NP); COD settlement Phase 3 |
| Fulfillment / couriers / returns | NOT_IMPLEMENTED (Phases 3–4) |
| Automation / Autopilot | NOT_IMPLEMENTED (Phase 5) |
| Analytics / intelligence | NOT_IMPLEMENTED (Phases 6–10) |
| Admin | API and Nivaro Console UI **PASS** (staff + MFA, E2E); plan/routing editors not built |

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
1. Finish order-to-delivery (Phase 3): a Nepal courier integration, shipment tracking, COD settlement
   and failed-delivery recovery. Phase 2 (chat → order) is done.
2. Staging environment with CI running (remote plus hosting decision), alerts, dashboards and runbooks.
3. Live AI provider key, with evaluation results above threshold.
4. At least one live channel (WooCommerce store or an approved Meta app), and a live messaging channel
   (Messenger/Instagram/WhatsApp) for the Sales Agent.
4b. A Nepal payment gateway (eSewa/Khalti/Fonepay) for prepaid orders (GAP-PAY-NP).
5. Email provider and domain; object storage; malware scanning in staging.
6. Production database with PITR plus a tested restore runbook; object-storage backup.
7. Pricing and plan billing (GAP-SPEC-21).
8. An external security review of auth, tenancy and uploads.

## Update 2026-11-04 (Phase 1 completion + Phase 2)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 246 | 246 | 0 | 0 |
| Web unit + API client | 264 | 264 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 22 | 22 | 0 | 0 |
| Flutter | 112 | 111 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 2 pages (8 pages × 3 configs) | 24 | 24 | 0 | 0 |

Bugs found and fixed while building: re-reserving after release discarded pending changes; same-ms
IDs sorted out of order (uuid7 now monotonic); reconciliation continued after credentials were
rejected; payment webhook path clashed with channel webhooks; order responses carried a stale
version; two identical "Send" buttons in the inbox; message log not keyboard-reachable; order
journey overflowed at 360px. Each has a regression test or E2E/axe coverage.

Overall status remains **NOT_READY** (Phase 3 delivery, live channels, payment gateway, staging,
backups, pentest).
