# Known Gaps

Nothing here is silently ignored. Each gap has an owner decision or the next engineering step.
Severity: **High** blocks production, **Med** blocks the related feature, **Low** is quality debt.

## Missing source specifications
| ID | Gap | Impact | Needed |
|---|---|---|---|
| GAP-SPEC-MISSING | Partly resolved | The 21 missing specs were **authored by engineering** on 2026-11-02 (ADR-026) from existing specs, briefs and the implementation. They need **owner review**, and the originals, if they exist, should be reconciled against them. | Owner review of 04–06, 09–17, 19–22, 25. |
| GAP-SPEC-21 | No GTM/pricing doc. | Plan prices are `NULL`. All limits except premium video (spec 08) are **provisional**. | Pricing and limits per plan. |
| ~~GAP-SPEC-22~~ | Resolved | Roadmap authored (Phases 0–10) per the strategy update. | — |
| GAP-SPEC-15 | No security/compliance doc. | Followed the brief's security list. No data-retention periods or Nepal privacy requirements are defined. | Retention rules, legal basis, data residency. |

## Infrastructure & operations
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-INFRA-TARGET | High | No hosting target (AWS / GCP / Fly / Render…). The staging deploy job is gated. | Your decision. Then: IaC, managed Postgres with PITR, managed Redis, bucket, secret manager. |
| GAP-CI-RUN | High | The CI workflow has never run on GitHub (the repo has no remote). Jobs may need small fixes on first run. | Add a remote and push. |
| GAP-KMS | High | Only the local KEK provider is implemented; production refuses to start without KMS. | Choose a KMS, then implement `KmsKeyProvider`. |
| GAP-ALERTS | Med (was High) | Alert rules (26, promtool-tested), dashboards and runbooks now exist (infra/observability, docs/runbooks). Nothing routes alerts to a person yet and no Prometheus runs in a real environment. | Deploy Prometheus/Alertmanager (or a hosted equivalent) with the hosting decision; route page/ticket severities. |
| GAP-EMAIL | High | Only the dev console mailer exists; production refuses to send. | Choose an email provider (SES / Postmark…) and implement the adapter. |
| GAP-SMS | Med | No phone OTP or SMS (Nepal sellers often prefer phone). | SMS provider with Nepal coverage (Sparrow SMS / Aakash SMS…) needs an account. |
| GAP-RLS | Med | Tenant isolation is enforced in the ORM; Postgres RLS is not enabled as a second layer. | Add RLS policies using `SET app.tenant_id`. |
| GAP-RATE-GLOBAL | Med | Rate limits cover auth, invites and verification only; no global per-user/per-tenant API limit. | Middleware limit with per-plan `api_requests` metering. |
| ~~GAP-BACKUP-TEST~~ | Closed 2026-11-20 | Backup + restore drill scripts written and run on QA data (all checks passed, restore 1 s). Production PITR/off-site copies remain under GAP-BACKUP-PROD. | — |
| ~~GAP-S3~~ | Closed 2026-11-20 | boto3 added; S3 backend verified against MinIO in compose (presigned browser upload → worker → derivatives). SSE configurable; public endpoint for presigned URLs. | — |
| GAP-PROXY-IP | Low | The web BFF forwards `X-Forwarded-For`, but the backend trusts it only when `COS_TRUSTED_PROXY_COUNT > 0`. Not set in compose, so session IPs show the web server's IP in dev. | Set per environment topology. |

## AI
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-AI-PROVIDER-VERIFY | Med | OpenAI and Gemini adapters follow documented REST shapes but were never called live. Model IDs and pricing are unverified and pricing is omitted, so their cost is recorded as unknown. The Claude adapter is unit-tested with a mocked SDK client but has not made a live call. | Provide keys for staging; run a live contract test per provider; fill pricing. |
| GAP-AI-MEDIA | Med | Image and video providers are sandbox-only. | Choose providers (fidelity requirements in brief §5–6). |
| GAP-AI-ROUTING-DB | Low | Routing policy is file-based; no admin override or cost/latency-aware ordering yet. | ADM-009 + use health scores in ordering. |
| GAP-AI-EVALS | Med | The eval harness exists, but its cases use synthetic placeholder photos. | Collect consented real seller photos per category, plus a live provider key, and set the CI quality threshold. |
| GAP-AI-BUDGET | Low | No seller AI spend budget separate from plan quotas. | Decide whether quotas suffice. |

## Product / UX
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-UX-GAUGE-TONE | Low | Plan & usage was fixed and verified against the real backend (not-in-plan, overage policies, gauges, localized labels). Remaining nit: a gauge at 100% (e.g. "Stores 1 of 1" on a single-store plan) shows danger red + Upgrade; full use of capacity isn't a risk and should be neutral. | Use neutral tone for gauges at limit; reserve danger for consumables that block work. |
| GAP-ADMIN-UI | Med | Admin console is API only. | Separate Next.js app on its own origin. |
| GAP-MOBILE-DEVICE | Med | The Flutter app has not been built for a device or run against the real backend; no MFA setup screens on mobile. | `flutter build` + device smoke test; integration test against compose. |
| GAP-NE-COPY | Med | Nepali copy was written without a native copy editor's review (spec 19 missing). | Native-speaker review pass. |
| GAP-A11Y | Med | No full screen-reader audit (VoiceOver / TalkBack / NVDA). | Audit before the first external users. |
| GAP-CHECKOUT | Med | "Buy credits" / upgrade have no purchase flow (needs PAY + BIL-011). | Phase 2 payments. |
| ~~GAP-E2E-401~~ | Resolved | **Root cause found:** FastAPI ≥0.118 runs `yield` dependency teardown (our DB commit) *after* the response is sent, so a client could call `/me` before its new session was committed (and, worse, could get "success" for a commit that later failed). Fixed with `scope="function"` on every `get_db`; guarded by `test_db_dependency_commits_before_response`; E2E 18/18 in parallel with 0 error responses. | — |


## Phase 1 gaps
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-CHANNEL-APPS | High | No real channel can be connected. Each needs a platform developer app and review:<br>• **Meta:** app + App Review for `instagram_basic`, `instagram_content_publish`, `pages_manage_posts`, `pages_read_engagement`, plus Business verification<br>• **TikTok:** Content Posting API audit<br>• **TikTok Shop:** seller-region eligibility for Nepal unconfirmed<br>• **Shopify:** Partner app<br>• **WooCommerce:** per-store REST keys<br>The framework, OAuth, token refresh, webhooks and publishing are built and tested against a stateful sandbox channel. | Create the developer apps and provide credentials; then write each adapter against `ChannelAdapter`. |
| GAP-AI-LIVE | High | The Product Studio has only run against the sandbox provider. Prompt quality, Nepali copy quality and extraction accuracy are **unmeasured**. | Set `COS_ANTHROPIC_API_KEY` in staging; build the eval set (AIG-015) from real seller photos. |
| GAP-IMAGE-AI | Med | AI background removal (MED-005), AI lifestyle images (MED-006) and the fidelity review flow (MED-007) are not built. Auto Reels are done. | Choose an image-edit provider. |
| GAP-REEL-MUSIC | Low | Auto Reels have no music: there is no licensed track library, and platforms mute or flag unlicensed audio. | License a royalty-free library, or let sellers pick platform sounds at post time. |
| GAP-LIBRAQM-DEV | Low | Local macOS dev has no libraqm, so Nepali reel overlays are refused there. Docker images include it and were verified. | `brew install libraqm` for local dev. |
| GAP-WOO-LIVE | Med | The WooCommerce adapter, including per-store webhook registration, routing and verification, is contract-tested only and has not run against a live store. Order webhooks are recorded but not processed until the Phase 2 orders domain exists. In dev, stores cannot reach `localhost` delivery URLs, so registration retries until `COS_PUBLIC_API_BASE_URL` is a public URL. | Test against a real store with a public API URL (staging). |
| GAP-IMPORT-QUEUE | Low | The CSV import runs inside the outbox handler, which blocks that dispatcher for up to ~5,000 rows. | Move to a Celery task on its own queue, as Studio does. |
| GAP-CLAMAV-COMPOSE | Med | ClamAV is not in docker compose. Dev uses the no-op scanner (assets show `scan_status: skipped`); production refuses to start without clamd. | Add a `clamav` service under a compose profile and a staging deployment. |
| GAP-CHN-RECON | Med | No periodic reconciliation against providers (CHN-012), so drift made directly on a platform isn't detected. | Implement once a real adapter exists. |
| GAP-CATALOG-TAXONOMY | Low | Categories are per-merchant; there is no shared Nepal-relevant base taxonomy or marketplace category mapping. | Seed a base taxonomy; map it per channel when real adapters land. |

## Catalog API gaps reported by the web client (2026-11-02)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| ~~GAP-CAT-VARIANT-LOCK~~ | Resolved | Fixed 2026-11-02 (see test_catalog). | — |
| ~~GAP-CAT-COLLECTIONS~~ | Resolved | Fixed 2026-11-02 (see test_catalog). | — |
| ~~GAP-CAT-CATEGORIES~~ | Resolved | Fixed 2026-11-02 (see test_catalog). | — |
| GAP-IMPORT-I18N | Low | CSV row errors with `invalid_row` carry English text only (e.g. "price: 'abc' is not a number"). | Structured `{field, reason}` codes per row. |
| ~~Add variant after create~~ | Resolved | `POST /catalog/products/{id}/variants` (version-locked, adds new option values). | — |

## Mobile (2026-11-02)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-MOBILE-TOOLCHAIN | Med | The Flutter 3.29.3 iOS simulator build fails with the installed Xcode 27 (`debug_unpack_ios` misreads the architectures), and no Android emulator is installed. The app has passed unit/widget tests and a live end-to-end run against the real backend, but has **never run on a device**. | Upgrade Flutter (and Dart ≥3.9, which unlocks newer plugin versions), or install an Android emulator; then device smoke test. |
| GAP-MOBILE-BG-UPLOAD | Low | Uploads survive app backgrounding but not OS termination; they resume on next launch. | Platform background transfer (URLSession / WorkManager). |
| GAP-MOBILE-RECONNECT | Low | Channel reconnect hands off to the web (link) rather than an in-app OAuth flow. | In-app browser with deep-link callback. |
| GAP-DEV-SIGNED-HOST | Low | Signed URLs use one `COS_PUBLIC_API_BASE_URL`, so a single dev backend can't serve both the Android emulator (10.0.2.2) and the iOS simulator (localhost). | Not an issue in staging/prod (one public host). |
| GAP-EXCEPTION-DISMISS | Low | No server-side dismiss/snooze for exceptions; the `dismiss` action is local to the device. | Add a dismissals table keyed by exception id. |
| GAP-AUTOPILOT-METRIC | Low | There is no "handled automatically" count for the Autopilot strip. | Derive from the audit log (`actor_type in (ai, automation)`) when automations land. |

## Autonomous Commerce OS (strategy update 2026-11-02)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-INTEL-NOT-BUILT | Info | Phases 6–9 intelligence is built and tested (see IMPLEMENTATION_STATUS). Still not built: **Network Intelligence (Phase 10)**, gated on a privacy impact assessment and legal review; and automated **retention campaigns** (win-back, repeat-purchase). Most intelligence runs on sandbox channel/courier data until real integrations exist. | Owner decision on the Phase 10 PIA; build retention campaigns. |
| GAP-INSTRUMENTATION | Med | Creative attributes (CNT-012) are **done** and backfilled. Still to instrument in their phases: structured addresses (ORD-012, Phase 2), action/outcome log (AUT-018, from Phase 2), controlled return reasons (RET-012, Phase 4). Web and mobile post editors don't yet let sellers declare hook, human presence or background (optional fields). | Build with each phase; add the declared fields to the post drawers. |
| GAP-NETWORK-LEGAL | High (Phase 10 gate) | Network Intelligence needs a privacy impact assessment and legal review (Nepal Individual Privacy Act 2075, cross-border). | Before NET work. |
| GAP-ENTITLEMENT-RESEED | Low | The entitlements contract gained intelligence feature codes. Re-seeding creates new plan versions; existing subscribers stay on old versions (grandfathered) until migrated. | Decide the migration policy when Phase 6 features ship. |

## Nivaro brand migration (2026-11-02)
**The brand migration is incomplete.** Customer-facing naming, tokens, logo, icons and the core motifs
are done. The items below remain.

| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-BRAND-LOGO-VECTOR | Med | The logo masters are cut from the raster concept board (ADR-032): colour mark 384 px, mono marks 114 px. That is fine for UI and app icons, but there is no vector master for print, signage or large-format use. | Designer exports the original vector; drop it into `logo/source` and re-run `render.mjs`. |
| GAP-BRAND-TRADEMARK | Med | "Nivaro" trademark search and filing not done. The ™ from the boards is deliberately omitted. | Legal. |
| GAP-BRAND-CHARACTERS | Med | The character cast and spot illustrations are **not created**. Briefs only (`assets/brand/characters`, `illustrations`). No placeholders ship. | Commission an illustrator (BRD-009/010). |
| GAP-BRAND-MOTION | Low | Only the ribbon trace and token motion exist. Sync pulse, order-step settle, milestone animation and Lottie exports for marketing are pending. | BRD-011, with the Order Journey / Channel Sync work. |
| GAP-BRAND-BANNERS | Low | Only the default OG/social image exists. The campaign, onboarding, AI Video, Autopilot, upgrade and milestone banner set is not built. | BRD-007. |
| GAP-BRAND-ICONS | Low | No Android adaptive icon (foreground/background layers); legacy square mipmaps only. The in-house line icon set is not exported for Flutter, which still uses Material icons. | BRD-012. |
| GAP-MARKETING-SITE | Low | The website is built at `/` (ADR-034). Still missing: real seller photography or product screenshots (a flat illustration stands in, labelled), legal pages (privacy, terms), sitemap/robots, analytics with consent, pricing (GAP-SPEC-21), and a proof section once real customers consent. | BRD-014 follow-ups. |
| ~~GAP-CONSOLE-UI~~ | — | Closed 2026-11-03: Console built (merchants, webhooks, outbox, AI providers, flags, audit). Still missing: plan editor (ADM-008), routing editor (ADM-009), support tickets. | — |
| GAP-EMAIL-DOMAIN | Low | The sender address domain is undecided (`no-reply@nivaro.invalid` placeholder in config). There is no HTML email template. | Owner: domain + DNS (SPF/DKIM/DMARC). |
| GAP-BRAND-LEGACY-DOCS | Low | `docs/Autonomous_Commerce_OS_Business_Partner_Brief.pdf` predates the brand. Technical identifiers keep `commerce-os` (intentional, ADR-028). | Regenerate the partner brief as Nivaro. |
| GAP-NE-TAGLINE | Low | The Nepali tagline "तपाईंको पसल, अटोपाइलटमा।" and module copy need native-speaker review (with GAP-NE-COPY). | Native review. |

## QA cycle 2026-11-03 (see docs/QA_TEST_REPORT.md, docs/PRODUCTION_READINESS_REPORT.md)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-CSP-NONCE | Low | CSP still allows `'unsafe-inline'` scripts (Next.js bootstrap). | Nonce-based CSP via middleware + `headers()` once rendering is per request. |
| GAP-LOAD-TEST | Low (was Med) | Local k6 baseline exists (infra/load/baseline.js: 20 sellers, 0 errors, read p95 248 ms). Not yet run against staging-sized infrastructure, webhook floods or the video queue. | Rerun on staging; add webhook-flood and flash-sale scenarios. |
| GAP-BACKUP-PROD | High (launch) | Only a local pg_dump/restore drill. No PITR, object-storage backup or DR runbook. | With the hosting decision (GAP-INFRA-TARGET). |
| GAP-RATELIMIT-FAILOPEN | Low | Rate limits fail open when Redis is down (DB lockout still applies). | Accepted; revisit with a local fallback bucket if abuse appears. |
| GAP-PENTEST | Med (launch) | No external security review. | Before paid launch: auth, tenancy, uploads. |

## Phase 2 (2026-11-04)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-NP-MUNICIPALITIES | Med | Municipality is free text; the 753 local levels aren't loaded (no verified source in repo). Province/district lists are embedded and need an owner check. | Load the official local-level list (federal affairs ministry) with Nepali names; validate municipality per district. |
| GAP-PAY-NP | High (launch) | No real Nepal payment gateway (eSewa/Khalti/Fonepay). Online payment links are sandbox-only; production refuses them cleanly. Manual payments work. | Pick a gateway, get merchant credentials, implement the PaymentAdapter + webhook verification. |
| GAP-MSG-CHANNELS | High (launch) | Customer messaging works with the sandbox channel only; Messenger/Instagram DM/WhatsApp need app review/BSP (GAP-CHANNEL-APPS). | Meta app review (pages_messaging, instagram_manage_messages) or a WhatsApp BSP. |
| GAP-AI-REPLY-PHRASING | Med | Sales Agent replies are grounded bilingual templates; no LLM phrasing yet (ADR-043). AI intent classification only runs with a real key. | With a live key: LLM phrasing behind a numbers-must-match grounding guard + evals on real (consented) chats. |
| ~~GAP-DELIVERY-FEE~~ | Closed 2026-11-04 | Merchant delivery-charge table (district > inside valley > default, free over a subtotal) fills chat orders and New order. | — |
| GAP-MOBILE-ORDER-CREATE | Low | Mobile can't create orders, record payments, see draft field values, summarise or assign chats (web can). | Next mobile iteration. |
| ~~GAP-TEST-FLAKE-1104~~ | Closed 2026-11-20 | Likely cause found: the login rate-limit test (fixed-window limiter) failed when its burst straddled a minute boundary. The test now sends up to 2 × limit + 1 attempts (pigeonhole), so one window always exceeds the limit. | — |
| GAP-NE-COPY-REVIEW | Low | New Phase 2 Nepali UI copy and chat templates need a native copy review. | Copy editor pass. |

## Phase 6 part A (2026-11-19)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-APS-AUDIT | Med | No manual-audit comparison tool (APS-006), so the ±2-point accuracy exit criterion isn't verified. | Sample 50 operations per capability, compare with the computed class, report the gap. |
| GAP-APS-TOOL | Low | The score isn't a Store Manager tool yet and there's no plan-upgrade suggestion. | Add with the Store Manager agent. |
| GAP-REC-CAUSAL | Med | Suggestion outcomes are before/after only (other changes in the period also count); courier and restock suggestions aren't measured automatically. | Holdout or difference-in-differences once enough merchants exist. |
| GAP-REC-NARRATIVE | Low | Explanations are deterministic templates; no AI narrative (REC-004). | AI narrative with a no-new-numbers faithfulness check, once a live model key exists. |
| GAP-CRI-DATA | High (value) | Courier Brain has only sandbox courier data; its estimates (NPR 50 handling, 0.05%/day cash cost) are defaults, not merchant settings. ETA calibration (CRI-006) not built. | Real courier API (GAP-COURIER-NP); make the estimates editable. |
| GAP-COD-VERIFY | Med | "Verify the phone" is advice only; no OTP/call verification or partial advance payment (CODI-006). | Build with the payment gateway (GAP-PAY-NP) and an SMS provider. |
| GAP-COD-CALIBRATION-ALERT | Low | The calibration/disparity report exists but nothing alerts on drift or a district disparity. | Weekly check with an ops alert once monitoring exists. |
| GAP-E2E-COLDSTART | Low | On a freshly started QA stack, the first real-backend spec (phase 2, desktop) failed twice with Node "fetch failed"; no server error was logged, and it passed alone and in the next full run (30/30). | Add a warm-up request in the Playwright global setup; capture the cause if it shows up in CI. |

## Phase 6 part B (2026-11-19)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-P6-EXIT | High (phase exit) | Phase 6 exit needs ≥ 90 days of real data from pilot merchants, an APS manual audit and backtests on real data. Everything is tested on synthetic data only. | Recruit pilot merchants; run the audit and backtests after 90 days. |
| GAP-PROFIT-FEES | Med | Online payment provider fees and channel/marketplace fees aren't recorded, so those lines show Partial/Not included when such orders exist. COD fees appear only after the courier statement. | Record provider fees on payments; channel fees from channel order imports. |
| GAP-PROFIT-HISTORY | Low | Order lines placed before 2026-11-19 have no saved cost; profit uses today's cost for them (counted in the response). | None needed once old orders age out of the window. |
| GAP-PROFIT-CURRENCY | Low | Profit and Product Brain responses carry the shop currency; suggestions and profit settings don't (mobile assumes NPR there). All shops are NPR today. | Add currency to recommendation views and settings. |
| GAP-PBR-FAQ | Med | Product FAQs from conversations (PBR-007) and channel/content conversion (PBR-006) aren't built. | FAQ clustering with seller-approved answers; content metrics in Phase 7. |
| GAP-PBR-VARIANT-DEMAND | Low | Demand is per product, not per variant/size; the stock-risk lead time is a fixed 7 days. | Per-variant EWMA; supplier lead times (Phase 8). |
| GAP-STORE-MANAGER | Med | No Store Manager agent, so the get_product_brain / get_memory_facts tools (ANA-009, PBR-009, MEM-007) don't exist. | Build with the Store Manager agent. |
| GAP-RTI-CAUSES | Low | Return causes can't point at the content/image version shown at purchase or a supplier batch: neither is recorded on orders. | Record content version on chat/channel orders (Phase 7) and batch on receiving (Phase 8). |
| GAP-RTI-E2E | Low | Return pattern detection is covered by backend tests, not by E2E (needs 10+ delivered sales per product). | Seed a pattern in a dedicated E2E once a fixtures endpoint exists for QA. |

## Phase 7 (2026-11-19)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-P7-EXIT | High (phase exit) | Phase 7 exit needs content metrics from a real channel and measured genome impact on real posts. Only sandbox insights and seller-typed results exist. | Meta/TikTok app approval (GAP-CHANNEL-APPS), then implement fetch_content_metrics for those adapters. |
| GAP-CGN-EXPERIMENT-ASSIGN | Med | Experiments compare posts the seller made with each option (observational); nothing assigns options at random, so differences can come from other things. | Let Studio/Reels alternate options automatically during a test. |
| GAP-CGN-ATTRIBUTION | Med | Window attribution only works for posts linked to a product; chats count as inquiries only when the channel sends a product/post reference. | Link posts to products in the composer by default; parse post links/UTMs in messages. |
| GAP-CGN-VIDEO | Low | Genome inputs don't reach premium video concepts (premium video isn't built); Auto Reel hook type is suggested but not rendered differently. | With premium video / new reel templates. |
| GAP-CGN-MOBILE | Low | Mobile shows patterns and post results but not experiments, the suggested time or reel settings. | Next mobile iteration. |

## Phase 8 (2026-11-20)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-SPI-LOT | Med | Sales are linked to the latest lot received before the order, not to the actual unit's lot; mixed lots on the shelf blur supplier return rates. | Record lot on pick/pack (FIFO) when fulfilment scanning exists. |
| GAP-PO-SEND | Med | POs aren't emailed or sent on WhatsApp; the seller copies a share text. No PO attachments (invoices, photos). | Production email/WhatsApp provider; reuse media uploads for attachments. |
| GAP-PO-CURRENCY | Low | POs use the shop currency only; no foreign-currency purchases or exchange rates (imports from India/China). | Currency + rate per PO, converted at receipt into landed cost. |
| GAP-PO-PAYMENTS | Low | Supplier payments/advances and payables aren't tracked. | Supplier payments with due dates; cash-flow view. |
| GAP-SPI-COMPLAINTS | Low | "Complaints" are quality-related returns only; there's no separate supplier complaint log. | Add a complaint note on receipts and returns. |
| GAP-AUT-PO-ACTION | Low | Workflows can't create PO drafts yet (low stock → draft PO); suggestions can. | Add create_po_draft as an R3 workflow action. |
| GAP-E2E-SLEEP | Info | An E2E run during which the Mac slept produced 18 timeouts (17-minute files); the rerun with `caffeinate -i` passed 36/36. | Run long suites with caffeinate or in CI. |

## Phase 9 (2026-11-20)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-ADS | Med | No ad-account connector, so ad-budget simulation (SIM-004) and ad spend in true profit are unavailable. | Meta/TikTok ads APIs after app approval. |
| GAP-SIM-MODEL | Med | Discount model has no seasonality (needs a year of data) and a constant elasticity; purchase model assumes incoming stock arrives first and Poisson demand. | Seasonality index once 12 months exist; per-category elasticity priors from network data (Phase 10). |
| GAP-TWIN-SLO | Med | The 60 s p95 freshness target is measured (report + histogram) but not alerted on or proven under real load. | Alerting with the monitoring stack (GAP-OBS). |
| GAP-SIM-MOBILE | Low | Mobile shows simulation results but can't start one. | Add a "What if I order N?" action on PO/variant screens. |

## Production readiness round (2026-11-20)
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-OBS | Med | Monitoring is code (rules, dashboards, runbooks) but not deployed; worker metrics need `COS_WORKER_METRICS_PORT` and, for prefork, `PROMETHEUS_MULTIPROC_DIR` in each environment. | Deploy with the hosting target; verify alerts fire end to end. |
| GAP-RUNBOOK-DRILL | Low | Runbooks are written and their commands tested, but no game-day has exercised them with a real incident. | Run a game-day on staging (kill a worker, dead-letter events, expire tokens). |
| GAP-MINIO-IMAGE | Info | Official MinIO images aren't pullable anonymously any more; compose uses Bitnami's legacy MinIO build (pinned). | Switch to the production bucket provider's local emulator or an internal registry mirror. |

## Security hardening still to do
- SAST, secret and container scans are configured in CI but have not run there (GAP-CI-RUN). Run locally on 2026-11-20: pip-audit (1 fixed), pnpm audit (Next.js patched), bandit (0 medium/high), gitleaks (test fixtures only).
- No malware scanning yet. Uploads arrive in Phase 1 (MED-002), and scanning must ship with them.
- No session/device anomaly notifications to users. A reuse-detection event exists, but nothing notifies the user yet.
- Password breach check uses a small local deny-list, not HIBP k-anonymity.
| GAP-COD-BANK | Med | "Money received" on a COD statement is the seller's confirmation; Nivaro doesn't see the bank or wallet credit. | Bank/wallet statement import or a payout API from the courier. |
| GAP-LABEL-BARCODE | Low | Nivaro's printable label shows the tracking number as text; no barcode/QR. Couriers that supply their own label link to it. | Add Code-128/QR rendering once a courier confirms which format its scanners read. |
| GAP-SETTLEMENT-XLSX | Low | Courier statements are imported as CSV; Excel files must be saved as CSV first. | Parse .xlsx server-side (with a vetted library) if sellers ask for it. |
| GAP-COURIER-RATES-REAL | Med | Rates and ETAs come from the sandbox courier; own-rider bookings have no rate. Courier Brain (built in Phase 6A) has only sandbox data (GAP-CRI-DATA). | Integrate a Nepal courier API (GAP-COURIER-NP). |
| GAP-RETURN-SELF-SERVE | Med | Returns are created by the seller (or prompted by the Sales Agent's hand-over); customers have no return link/portal. | A signed customer return link once a storefront/portal exists. |
| GAP-RETURN-EVIDENCE-UI | Low | Return lines store evidence media ids and the policy checks them, but the web/mobile forms don't upload photos yet. | Reuse the media upload flow in the Start-a-return form. |
| GAP-EXCHANGE-PRICE | Low | Exchanges are limited to the same product at the same price (no top-up or partial refund). | Price-difference exchanges with a payment link or partial refund. |
| GAP-AUT-SCHEDULE | Low | Workflows start from events only; no time-of-day/schedule triggers yet. | Schedule trigger (daily/weekly in the merchant's timezone) on the existing resume worker. |
| GAP-AUT-ACTIONS | Med | Workflow actions cover messaging, courier booking/pickup, reattempts and return approval. Refunds, discounts, price changes and purchase orders aren't workflow actions yet (the policy thresholds for them exist). | Add as R2/R3 actions when the pricing/procurement domains exist (Phase 6/8). |
| ~~GAP-AUT-STALENESS~~ | Closed 2026-11-20 | Twin sections exist; the Decision Policy refuses to auto-run on sections older than their automation max staleness (ADR-079). | — |

