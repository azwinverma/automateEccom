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
| GAP-AI-EVALS | Med | No eval harness (AIG-015) or prompt registry service. | Phase 1, alongside the first real prompts. |
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
| GAP-E2E-401 | Low | One unexplained `GET /me 401` immediately after login during an E2E run that coincided with a backend restart. Not reproduced in 8 further runs. Access logs now include `error_code` to diagnose any recurrence. | Watch E2E in CI. |

## Security hardening still to do
- SAST, secret and container scans are configured in CI but have not run (GAP-CI-RUN).
- No malware scanning yet. Uploads arrive in Phase 1 (MED-002), and scanning must ship with them.
- No session/device anomaly notifications to users. A reuse-detection event exists, but nothing notifies the user yet.
- Password breach check uses a small local deny-list, not HIBP k-anonymity.
