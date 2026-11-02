# Known Gaps

Nothing here is silently ignored. Each gap has an owner decision or the next engineering step.
Severity: **High** blocks production, **Med** blocks the related feature, **Low** is quality debt.

## Missing source specifications
| ID | Gap | Impact | Needed |
|---|---|---|---|
| GAP-SPEC-MISSING | 21 of 30 referenced files are absent: 04, 05, 06, 09–17, 19–22 and all 4 JSON files (`design-tokens.json`, `feature-entitlements.example.json`, `event-catalog.json`, `ai-routing-policy.example.json`). | The 4 JSON files were **created** from the present docs (in `packages/`). Everything else was derived from specs 00/01/02/03/07/08/18/23/24 plus the build brief. | Add the missing files; I will reconcile and log any conflicts in DECISIONS.md. |
| GAP-SPEC-21 | No GTM/pricing doc. | Plan prices are `NULL`. All limits except premium video (spec 08) are **provisional**. | Pricing and limits per plan. |
| GAP-SPEC-22 | No phased roadmap. | Phase grouping in IMPLEMENTATION_STATUS is provisional. | Roadmap. |
| GAP-SPEC-15 | No security/compliance doc. | Followed the brief's security list. No data-retention periods or Nepal privacy requirements are defined. | Retention rules, legal basis, data residency. |

## Infrastructure & operations
| ID | Sev | Gap | Next step |
|---|---|---|---|
| GAP-INFRA-TARGET | High | No hosting target (AWS / GCP / Fly / Render…). The staging deploy job is gated. | Your decision. Then: IaC, managed Postgres with PITR, managed Redis, bucket, secret manager. |
| GAP-CI-RUN | High | The CI workflow has never run on GitHub (the repo has no remote). Jobs may need small fixes on first run. | Add a remote and push. |
| GAP-KMS | High | Only the local KEK provider is implemented; production refuses to start without KMS. | Choose a KMS, then implement `KmsKeyProvider`. |
| GAP-ALERTS | High | Metrics exist, but there are no dashboards, alert rules, SLOs or runbooks beyond `infra/staging/README.md`. | Define SLOs; alerts for outbox backlog/dead events, AI fallback rate, 5xx rate, login failure spikes. |
| GAP-EMAIL | High | Only the dev console mailer exists; production refuses to send. | Choose an email provider (SES / Postmark…) and implement the adapter. |
| GAP-SMS | Med | No phone OTP or SMS (Nepal sellers often prefer phone). | SMS provider with Nepal coverage (Sparrow SMS / Aakash SMS…) needs an account. |
| GAP-RLS | Med | Tenant isolation is enforced in the ORM; Postgres RLS is not enabled as a second layer. | Add RLS policies using `SET app.tenant_id`. |
| GAP-RATE-GLOBAL | Med | Rate limits cover auth, invites and verification only; no global per-user/per-tenant API limit. | Middleware limit with per-plan `api_requests` metering. |
| GAP-BACKUP-TEST | High | No backup/restore drill (needs a hosting target). | Run after GAP-INFRA-TARGET. |
| GAP-S3 | Med | The S3 storage backend is written but untested; boto3 is not a dependency yet. | Add boto3 and test against MinIO in compose. |
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

## Security hardening still to do
- SAST, secret and container scans are configured in CI but have not run (GAP-CI-RUN).
- No malware scanning yet. Uploads arrive in Phase 1 (MED-002), and scanning must ship with them.
- No session/device anomaly notifications to users. A reuse-detection event exists, but nothing notifies the user yet.
- Password breach check uses a small local deny-list, not HIBP k-anonymity.
