# Production Readiness Report: Nivaro

> 2026-11-03 QA cycle (`docs/QA_TEST_REPORT.md`); updated 2026-11-19 after Phase 1 completion and Phases 2–8.

## Overall status: **NOT_READY**

The code that exists is in a verified, stable state:
- All suites are green.
- No BLOCKER, CRITICAL or HIGH issue remains open; the 6 found were fixed and regression-tested.
- Production builds succeed and critical E2E flows pass.

Nivaro is still **not production ready**, for reasons outside the code that exists today:
1. **The commerce loop is built up to delivery and cash, but only against sandboxes.** Phases 2–3
   (inbox, AI Sales Agent, chat-to-order, orders, inventory, payments, couriers, tracking,
   failed-delivery recovery, COD settlement) are built and tested end to end. No real Nepal courier
   API is integrated (own-rider/manual deliveries do work). Returns, exchanges and refunds (Phase 4) and automation with the
   Decision Policy and Control Center (Phase 5) are built, as are the Autopilot Score, suggestions,
   Courier Brain and COD risk (Phase 6 part A), which only have sandbox courier data to learn from.
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
| Fulfillment / couriers / returns | **PASS with sandbox/manual couriers** (E2E COD → failed attempt → delivered → settled; return → pickup → inspection → refund). Real Nepal courier API BLOCKED_EXTERNAL |
| Automation / Autopilot | **PASS** (Decision Policy, workflows, Control Center; E2E Assisted → Smart) |
| Analytics / intelligence | Phase 6 **PASS on synthetic data** (Autopilot Score, suggestions, Courier Brain, COD risk, true profit, Product Brain, Return Intelligence, Commerce Memory; E2E). Exit criteria need pilot data. Phase 7 Creative Intelligence **PASS with sandbox/typed-in results** (exit BLOCKED_EXTERNAL on real channel insights); Phase 8 procurement + supplier intelligence **PASS** (E2E PO → approval → lots → stock); Phases 9–10 NOT_IMPLEMENTED |
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
1. A real Nepal courier integration (API access from a courier, GAP-COURIER-NP). Phase 3 flows
   (tracking, failed-delivery recovery, COD settlement) are built and tested against the sandbox
   courier and the own-rider option.
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

## Update 2026-11-04 (Phase 3: order → delivery → COD cash)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 266 | 266 | 0 | 0 |
| Web unit + API client | 276 | 276 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 24 | 24 | 0 | 0 |
| Flutter | 118 | 117 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 3 pages (5 pages × 3 configs) | 15 | 15 | 0 | 0 |

Exit flow verified in E2E: order → COD → courier booked → pickup → failed attempt → reattempt →
delivered → courier statement matched → money confirmed.

Fixed while building: the listings panel stopped refreshing while a listing was "out of sync" (a
resync is always queued then), which made a Phase 1 E2E fail under a busier worker; the CSS print
rule broke the production build (moved to globals); the COD statements table was cut off at 360px.

Overall status remains **NOT_READY** (real courier API, live channels, payment gateway, staging,
backups, pentest).

## Update 2026-11-04 (Phase 4: returns, exchanges, refunds)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 279 | 279 | 0 | 0 |
| Web unit + API client | 284 | 284 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 26 | 26 | 0 | 0 |
| Flutter | 124 | 123 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 4 pages (4 pages × 3 configs) | 12 | 12 | 0 | 0 |

Exit flow verified in E2E: delivered → return → approved → pickup → received → inspected
(restocked) → refunded → order returned.

Fixed while building: abuse signals counted the request being created; refund status and the
"order returned" check read stale data (sessions don't autoflush; explicit flushes added).

Overall status remains **NOT_READY** (real courier API, Nepal payment gateway for online refunds,
live channels, staging, backups, pentest).

## Update 2026-11-05 (Phase 5: automation, Decision Policy, Control Center)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 303 | 303 | 0 | 0 |
| Web unit + API client | 291 | 291 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 28 | 28 | 0 | 0 |
| Flutter | 130 | 129 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 5 pages (5 pages × 3 configs) | 15 | 15 | 0 | 0 |

Exit flow verified in E2E: template workflow → dry run → approval in Assisted → automatic in Smart →
Control Center feed with the reason; all decisions recorded.

Fixed while building: trigger filters matched the record's current status instead of the event's
(double runs); the circuit breaker missed the failure just recorded; "address complete" required the
optional landmark, which would have blocked courier booking for normal orders.

Overall status remains **NOT_READY** (real courier API, Nepal payment gateway, live channels,
production email, staging, backups, pentest).

## Update 2026-11-19 (Phase 6 part A: Autopilot Score, suggestions, Courier Brain, COD risk)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 313 | 313 | 0 | 0 |
| Web unit + API client | 298 | 298 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 30 | 30 | 0 | 0 |
| Flutter | 140 | 139 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 6A pages (3 pages × 3 configs) | 9 | 9 | 0 | 0 |

E2E: 30/30 in the final run. In two earlier runs on a freshly started stack, the phase 2 desktop spec
failed with a client-side "fetch failed" before any server error; it passed alone and in the final
full run (GAP-E2E-COLDSTART).

Fixed while building: after an override the COD card still advised "review before packing"; two notes
on the risk card ran together; the raw `cod_risk` code showed on Home instead of a label.

Fairness: COD risk uses an allow-list of the merchant's own facts, never rejects automatically, and a
static test blocks reading names or adding factors (ADR-064).

Overall status remains **NOT_READY** (real courier API, which Courier Brain needs to be useful; Nepal
payment gateway; live channels; production email; staging; backups; pentest).

## Update 2026-11-19 (Phase 6 part B: profit, Product Brain, Return Intelligence, Commerce Memory)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 327 | 327 | 0 | 0 |
| Web unit + API client | 312 | 312 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 32 | 32 | 0 | 0 |
| Flutter | 150 | 149 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 6B pages (5 views × 3 configs) | 15 | 15 | 0 | 0 |

E2E passed 32/32 on the first run against a fresh stack this time (GAP-E2E-COLDSTART not reproduced).

Fixed while building: a new return insight's numbers weren't saved (status unset before insert); the
weekly metric query failed on PostgreSQL grouping; pending outcome measurements were marked done and would
never be measured again; profit and Product Brain responses lacked the currency.

Profit honesty: missing costs show as Not included / Partial with the reason, never as zero (ADR-065).
The Sales Agent only repeats facts the seller confirmed (ADR-066).

Overall status remains **NOT_READY**. Phase 6 exit criteria need 90 days of pilot-merchant data. Still
missing: real courier API, Nepal payment gateway, live channels, production email, staging, backups, pentest.

## Update 2026-11-19 (Phase 7: Creative Intelligence)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 336 | 336 | 0 | 0 |
| Web unit + API client | 326 | 326 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 34 | 34 | 0 | 0 |
| Flutter | 161 | 160 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 7 pages (4 pages × 3 configs) | 12 | 12 | 0 | 0 |

Found and fixed: a Phase 1 content-calendar chip whose accessible name didn't contain its visible text
(WCAG 2.5.3); Home and order widgets calling plan-gated APIs on plans without the feature (403 noise);
six E2E specs whose post-login URL check also matched the login page (`/login?next=…`), which made
phase 6B flaky at 360px; new experiments had no progress until the next refresh.

Exit BLOCKED_EXTERNAL: real channel insights need Meta/TikTok app approval. Overall status remains
**NOT_READY**.

## Update 2026-11-20 (Phase 8: Procurement + Supplier Intelligence)
| | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Backend pytest | 342 | 342 | 0 | 0 |
| Web unit + API client | 341 | 341 | 0 | 0 |
| E2E (real backend + worker, desktop + 360px) | 36 | 36 | 0 | 0 |
| Flutter | 176 | 175 | 0 | 1 (live flow; needs LIVE_API) |
| axe on Phase 8 pages (6 pages × 3 configs) | 18 | 18 | 0 | 0 |

Found and fixed: the product picker's aria-controls pointed at a list that wasn't rendered (critical);
supplier detail overflowed at 360px because grid children kept min-width:auto and a screen-reader-only
label escaped the table scroller (the shared table wrapper is now position: relative); the login
rate-limit regression test could flake on a minute boundary (fixed-window limiter), which explains the
unexplained 2026-11-04 failure.

One E2E run while the Mac slept timed out on 18 tests; the rerun with sleep prevented passed 36/36.

Overall status remains **NOT_READY** (real courier API, Nepal payment gateway, live channels,
production email/WhatsApp, staging, backups, pentest).
