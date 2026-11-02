# API Contracts & Integrations

> v1 (2026-11-02). The original 05 was never provided. Authored from the implemented API plus planned
> surfaces; owner review required. The authoritative machine contract is `/api/v1/openapi.json`.
> Conventions are detailed in `docs/api/phase-0-contract.md`.

## Conventions
- Base `/api/v1`. JSON. UTC ISO-8601 timestamps. UUIDv7 ids. Money `{amount_minor, currency}` or
  `*_minor` fields.
- Tenant header `X-Merchant-Id`; a foreign tenant gets **404** (never 403).
- `Idempotency-Key` on creates and side-effecting POSTs. A replay returns the original response with
  `Idempotent-Replayed: true`.
- Errors use `{error:{code,message,details,request_id}}`. Clients localise by `code`.
- Keyset pagination: `?limit&cursor` → `{items,next_cursor}`.
- Optimistic locking: a `version` field; a stale write returns `409 version_conflict`.
- Async work returns `202` and a resource to poll (studio jobs, video jobs, imports, listings).

## Implemented API groups (Phases 0–1)
| Group | Paths |
|---|---|
| Health/ops | `/healthz`, `/readyz`, `/metrics` |
| Auth & me | `/auth/*` (register, login, MFA, refresh rotation, sessions), `/me` |
| Tenancy | `/merchants`, `/merchant` (incl. automation mode, brand voice), `/stores`, `/members`, `/invitations`, `/permissions/me` |
| Billing | `/billing/subscription`, `/billing/entitlements` (limits with `included`, gauges), `/billing/credits` |
| Catalog | `/catalog/products` (+variants, attributes, media, status, publish, listings), `/catalog/categories`, `/catalog/collections`, `/catalog/imports` |
| Media | `/media/uploads` (signed PUT), `/media/{id}`, `/media/videos/auto-reels` |
| Studio | `/studio/jobs` (create, poll, apply, discard, retry) |
| Channels | `/channels/providers`, `/channels`, `/channels/connect` (OAuth), `/channels/oauth/callback`, `/channels/connect-with-keys`, `/channels/{id}/health` |
| Content | `/content/posts` (calendar, from-studio, submit/approve/reject/schedule/unschedule/cancel) |
| Exceptions | `/exceptions` |
| AI | `/ai/credentials` (BYOK) |
| Webhooks (public, signed) | `/webhooks/{provider}`, `/webhooks/{provider}/{connection_id}` |
| Admin (staff + MFA) | `/admin/merchants`, `/admin/ai/providers`, `/admin/outbox`, `/admin/feature-flags`, `/admin/webhooks` |

## Planned operational APIs (Phases 2–5)
- **Customers/CRM:** `/customers` (search, merge with evidence), `/customers/{id}/timeline`.
- **Inbox:** `/conversations`, `/conversations/{id}/messages`, assignment, `/conversations/{id}/order-draft`.
- **Orders:** `/orders` (create from chat/seller/API; idempotent), state transitions, `/orders/{id}/timeline`.
- **Inventory:** `/inventory/levels`, `/inventory/adjustments`, `/inventory/transfers`, `/inventory/ledger`.
- **Payments:** `/payments/intents`, `/payments/{id}/verify`, `/cod/exposure`, `/cod/settlements`.
- **Fulfillment:** `/shipments`, `/shipments/{id}/label`, `/couriers/rates`, `/couriers/recommendation` (Phase 3 rules; Courier Brain in Phase 6).
- **Returns:** `/returns`, eligibility check, inspection, `/refunds` (idempotent, threshold policy).
- **Automation:** `/automation/workflows` (+versions, dry-run, runs), `/automation/policy` (Decision Policy and thresholds), `/approvals`.

## Planned intelligence APIs (Phases 6–10)
Exposure rules:
- Merchant-scoped only.
- Return **explanations and evidence summaries**, never raw model internals, other merchants' data,
  or personal data beyond what the caller can already see.
- COD risk factors are shown as human-readable reasons.

| API | Purpose | Phase |
|---|---|---|
| `GET /product-brain/products/{id}` | Product intelligence profile + `as_of` + data-completeness | 6 |
| `GET /product-brain/products/{id}/faqs`, `PUT` | Curated FAQs | 6 |
| `GET /autopilot/score?window=7d` | Overall + per-capability score, denominator, exclusions, failures | 6 |
| `GET /autopilot/score/improvements` | Ranked recommendations to raise coverage | 6 |
| `GET /memory/summary?subject_type=&subject_id=` | Active facts + key metrics with evidence | 6 |
| `POST /memory/facts/{id}/reject` | Merchant correction (versioned, audited) | 6 |
| `GET /recommendations?status=` | Recommendation inbox | 6 |
| `GET /recommendations/{id}` | Includes explanation + evidence + estimated impact + confidence | 6 |
| `POST /recommendations/{id}/accept` | Idempotent; routes through the Decision Policy/approval | 6 |
| `POST /recommendations/{id}/reject` | With reason (feeds learning) | 6 |
| `GET /intelligence/returns/insights` | Return patterns + recommendations + before/after | 6 |
| `GET /intelligence/couriers/recommendation?order_id=` | Ranked couriers with explanation | 6 |
| `GET /intelligence/cod/assessments/{order_id}` + `POST …/override` | COD risk + dispute/override | 6 |
| `GET /intelligence/suppliers` | Supplier true economics | 8 |
| `GET /creative-genome` | Learned content patterns with effect sizes | 7 |
| `GET /twin/summary` | Store Twin sections with `as_of` / `stale` | 9 |
| `POST /simulations` → `GET /simulations/{id}` | What-if runs (async), assumptions + ranges | 9 |
| `POST /store-manager/ask` | Tool-using Q&A over the layers above, with evidence | 6 (basic) → 9 (full) |

## External integrations required
| Integration | Purpose | Status / needs |
|---|---|---|
| Anthropic / OpenAI / Gemini | AI Gateway providers | Adapters built; need production keys + live verification |
| Image-edit / image-gen provider | Background removal, lifestyle images | Not chosen |
| Video-gen provider | Premium AI video | Not chosen |
| Meta Graph API (Instagram, Facebook, Messenger) | Publish, messages, insights (closed loop) | Needs Meta app + App Review |
| TikTok Content Posting API / TikTok Shop | Publish, metrics, shop | Needs developer approval; Nepal eligibility unconfirmed |
| WhatsApp Business Platform | Messages | Needs BSP / Meta approval |
| Shopify Admin API | Listings, orders | Partner app |
| WooCommerce REST v3 | Listings, stock, orders, webhooks | **Adapter built** (contract-tested) |
| Nepal payment gateways (e.g. eSewa, Khalti, Fonepay) | Payments, verification, refunds | Merchant accounts + API credentials |
| Nepal couriers (various) | Rates, shipments, tracking, COD settlement | Per-courier API access |
| Email (SES/Postmark) and SMS (Nepal SMS provider) | Notifications, OTP | Accounts needed |
| KMS (cloud) | Envelope encryption KEK | Hosting decision |
| ClamAV | Upload scanning | Deploy in staging/prod |
| Content/insights APIs (Meta Insights, TikTok analytics) | Closed-loop content metrics (Phase 7) | Same app approvals as publishing |
