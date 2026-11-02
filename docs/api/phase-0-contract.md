# Phase 0 API Contract (v1)

Base path: `/api/v1`. The FastAPI app also serves the generated OpenAPI document at
`/api/v1/openapi.json` — that is authoritative once the backend runs; this file is the
human-readable contract used by web/mobile clients.

## Conventions

- JSON only. Timestamps are ISO-8601 UTC (`2026-11-02T08:15:00Z`). IDs are UUIDv7 strings.
- Money is never a float: `{ "amount_minor": 125000, "currency": "NPR" }` (NPR 1,250.00).
- Every response carries `X-Request-ID` (echoed if the client sent one, generated otherwise).
- **Tenant scoping:** merchant-owned endpoints require header `X-Merchant-Id: <uuid>`.
  The server verifies the caller has an active membership in that merchant; otherwise `404`
  (not `403`, to avoid leaking existence).
- **Idempotency:** state-changing endpoints marked *(idem)* accept `Idempotency-Key`
  (8–128 chars). Same key + same body → original response replayed with
  `Idempotent-Replayed: true`. Same key + different body → `422 idempotency_key_reused`.
  In-flight duplicate → `409 idempotency_in_progress`.
- **Pagination:** cursor based. Query `?limit=50&cursor=<opaque>`. Response
  `{ "items": [...], "next_cursor": "<opaque>|null" }`. Max limit 200.
- **Errors:** always
  ```json
  { "error": { "code": "snake_case_code", "message": "Human readable", "details": {}, "request_id": "..." } }
  ```
  Clients map `code` to localized copy; `message` is a developer fallback, not UI copy.

| HTTP | code examples |
|------|---------------|
| 400 | `validation_error` (details.fields: `[{loc, msg, type}]`) |
| 401 | `not_authenticated`, `token_expired`, `invalid_credentials`, `mfa_invalid_code` |
| 403 | `permission_denied` (details.permission), `feature_not_in_plan` (details.feature, details.upgrade_options) |
| 404 | `not_found` |
| 409 | `conflict`, `idempotency_in_progress`, `slug_taken`, `email_taken` |
| 402 | `usage_limit_reached` (details: resource, limit, used, period_end, options: [`buy_credits`,`upgrade`,`wait_for_renewal`]) |
| 422 | `idempotency_key_reused`, `invalid_state_transition` |
| 429 | `rate_limited` (header `Retry-After`) |
| 503 | `dependency_unavailable` (details.dependency) |

## Health & ops (no auth, no `/api/v1` prefix)
- `GET /healthz` → `200 {"status":"ok"}` (process alive)
- `GET /readyz` → `200 {"status":"ready","checks":{"database":"ok","redis":"ok"}}` or `503` with failing checks
- `GET /metrics` → Prometheus text (restricted to internal network in deployment)

## Auth

Access token: JWT (HS256 in dev / configurable), 15 min, `Authorization: Bearer <token>`.
Refresh token: opaque, 30 days, **rotated on every use**. Reusing a rotated refresh token revokes
the whole session family (theft detection) → `401 refresh_token_reused`.

Web clients must keep the refresh token in an httpOnly, Secure, SameSite=Lax cookie managed by
the Next.js server (BFF route handlers) — never in `localStorage`. Mobile stores it in
platform secure storage (Keychain / Android Keystore).

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, full_name, phone?, locale?: "en"\|"ne"}` | `201 {user}` |
| POST | `/auth/login` | `{email, password, device_name?}` | `200 TokenPair` or `200 {"mfa_required": true, "mfa_token": "..."}` |
| POST | `/auth/mfa/verify` | `{mfa_token, code}` (TOTP or recovery code) | `200 TokenPair` |
| POST | `/auth/refresh` | `{refresh_token}` | `200 TokenPair` |
| POST | `/auth/logout` | `{refresh_token}` | `204` |
| GET | `/auth/sessions` | — | `{items: [{id, device_name, ip, user_agent, created_at, last_used_at, current}]}` |
| DELETE | `/auth/sessions/{id}` | — | `204` |
| POST | `/auth/sessions/revoke-all` | — | `204` (revokes all other sessions) |
| POST | `/auth/mfa/totp/setup` | — | `{secret, otpauth_uri}` |
| POST | `/auth/mfa/totp/enable` | `{code}` | `{recovery_codes: [10 strings]}` (shown once) |
| POST | `/auth/mfa/totp/disable` | `{code, password}` | `204` |
| POST | `/auth/verify-email/request` | — | `202` |
| POST | `/auth/verify-email/confirm` | `{token}` | `204` |

`TokenPair = {access_token, refresh_token, token_type: "bearer", expires_in: 900, session_id}`

Password policy: ≥ 10 chars, not in common-password list, not equal to email. Login is rate
limited per IP and per account; repeated failures lock the account for 15 minutes
(`429 rate_limited`, same message as invalid credentials to avoid enumeration).

## Me
- `GET /me` → `{user: {id, email, full_name, phone, locale, email_verified, mfa_enabled}, memberships: [{merchant: {id, name, slug}, role, status}]}`
- `PATCH /me` → `{full_name?, phone?, locale?}`

## Merchants (tenancy)
- `POST /merchants` *(idem)* `{name, slug?, country: "NP", currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "ne"|"en"}`
  → `201 {merchant}`. Creates owner membership, a default store and a trial subscription on the
  default plan version.
- `GET /merchant` *(tenant)* → current merchant.
- `PATCH /merchant` *(tenant, `merchant.update`)*.

## Stores *(tenant)*
- `GET /stores` → paginated `{id, name, slug, status, default_currency, created_at}`
- `POST /stores` *(idem, `store.create`, limit `stores`)* `{name, slug?}`
- `PATCH /stores/{id}` *(`store.update`)* `{name?, status?: "active"|"archived"}`

## Team *(tenant)*
- `GET /members` → `{items: [{id, user: {id, email, full_name}, role, status, joined_at}]}`
- `PATCH /members/{id}` *(`team.manage`)* `{role}` — cannot demote the last owner (`409 last_owner`)
- `DELETE /members/{id}` *(`team.manage`)*
- `GET /invitations` *(`team.manage`)*
- `POST /invitations` *(idem, `team.manage`, limit `team_members`)* `{email, role}` → `201 {invitation}`
- `DELETE /invitations/{id}` *(`team.manage`)*
- `POST /invitations/accept` (auth, no tenant) `{token}` → `{membership}`

Roles (system): `owner`, `admin`, `manager`, `staff`, `viewer`. Permissions are strings like
`orders.read`; role → permission map lives server-side (`GET /permissions/me` returns the
effective list so UIs can hide actions, but the server always enforces).

## Billing / entitlements *(tenant)*
- `GET /billing/subscription` → `{plan: {code, name, tagline}, plan_version, status, trial_ends_at, current_period_start, current_period_end}`
- `GET /billing/entitlements` →
  ```json
  { "features": {"ai.product_studio": true, "video.premium": false, ...},
    "limits": [{"resource": "ai_text_generations", "period": "month", "limit": 500, "used": 120, "reserved": 3,
                "burst": {"period": "day", "limit": null, "used": 0}, "alert_level": null|"70"|"85"|"100"}] }
  ```
  Each limit entry also carries `kind` (`consumable` | `gauge`), `unit`, `overage_policy`
  (`block` | `credits` | `overage`), `period_end` (consumables) and `included` (false when the plan
  limit is 0, meaning the resource is not part of the plan; show "not in plan", never "limit reached").
  For gauges, `used` is the current count, or `null` when the owning domain does not exist yet
  ("not counted"; never display it as 0).
- `GET /billing/credits` → `{balance, transactions: [{id, amount, balance_after, kind, reference_type, created_at}], next_cursor}`
  where `kind` ∈ `grant|purchase|hold|release|consume|refund|expire|adjustment`.

## Audit *(tenant, `audit.read`)*
- `GET /audit-logs?action=&actor_id=&resource_type=&resource_id=&limit=&cursor=` →
  `{items: [{id, occurred_at, actor: {type: "user"|"system"|"automation"|"ai", id, display}, action, resource_type, resource_id, source, request_id, ip, changes, metadata}], next_cursor}`

## Feature flags *(tenant)*
- `GET /feature-flags` → `{flags: {"inbox.beta": false, ...}}` (evaluated for this merchant/user)

## AI (tenant)
- `GET /ai/credentials` *(ai.credentials.manage)*: BYOK keys, shown only as `key_last4`
- `POST /ai/credentials` *(feature `ai.byok`)* `{provider, api_key, fallback_to_platform}`
- `POST /ai/credentials/{id}/rotate` · `POST /ai/credentials/{id}/test` · `DELETE /ai/credentials/{id}`

## Admin (staff only, MFA-verified session required)
- `GET /admin/merchants?q=` · `GET /admin/merchants/{id}`
- `GET /admin/ai/providers` → provider health/circuit state (never secrets)
- `GET /admin/outbox?status=failed` · `POST /admin/outbox/{id}/retry`
- `GET /admin/feature-flags` · `PUT /admin/feature-flags/{key}`
