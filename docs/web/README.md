# Web app (Phase 0 foundation)

`apps/web` (`@commerce-os/web`) is a Next.js 15 App Router app (React 19, strict TypeScript, CSS Modules on top of
`@commerce-os/design-system/tokens.css`). It talks to the FastAPI backend through `packages/api-client`
(`@commerce-os/api-client`).

## Run

```bash
pnpm install
pnpm --filter @commerce-os/design-system build   # regenerate tokens (never hand-edit dist/)
cp apps/web/.env.example apps/web/.env.local      # BACKEND_URL defaults to http://localhost:8000
pnpm --filter @commerce-os/web dev                # http://localhost:3000
```

| Script | What it does |
|---|---|
| `dev` / `build` / `start` | Next.js (build uses `output: "standalone"`) |
| `lint` | `eslint .` with `next/core-web-vitals` + `next/typescript`, zero warnings allowed |
| `typecheck` | `tsc --noEmit` |
| `test` | Vitest + Testing Library (jsdom; BFF route tests run in node) |
| `e2e` | Playwright; the spec is skipped unless `E2E_BASE_URL` is set |

`/dev/components` is a fixtures page showing every state of the signature components. It returns 404 when `NODE_ENV=production`.

Docker image, built from the repo root: `docker build -f apps/web/Dockerfile -t commerce-os-web .` (multi-stage, standalone output, runs as non-root `nextjs`, set `BACKEND_URL` at runtime).

## Architecture

```
browser ──► Next.js (same origin)
             ├─ /api/session/{login,mfa-verify,refresh,logout}   BFF: owns the refresh-token cookie
             ├─ /api/v1/*                                        runtime proxy → BACKEND_URL/api/v1/*
             └─ pages (middleware: no session cookie → /login)
```

### Auth and tokens
- **The refresh token never reaches JavaScript.** BFF route handlers call the backend, put the refresh token in
  `cos_rt` (httpOnly, Secure, SameSite=Lax, **Path=/api/session**, 30 days) and return only
  `{access_token, expires_in, session_id}`.
- Because `cos_rt` is scoped to `/api/session`, page requests can't see it. A second httpOnly marker cookie
  `cos_auth=1` (Path=/, no secret) tells `middleware.ts` that a session exists, so it can redirect anonymous visitors to `/login?next=…`.
- The access token lives only in memory (`AuthProvider` ref). A page reload restores it via `POST /api/session/refresh`.
  It is refreshed 60 s before expiry, and also on any `401 token_expired` through the api-client's single-flight refresh.
- Refresh tokens rotate on every use, and reusing one revokes the whole session family. To stop two tabs refreshing at
  once, `bffRefresh()` holds a Web Locks API lock (`navigator.locks`) across tabs.
- The `/api/v1` proxy **blocks** `auth/login`, `auth/mfa/verify`, `auth/refresh` and `auth/logout`, so token pairs can only pass through the BFF.
- Session routes reject cross-origin `Origin` headers on top of SameSite=Lax. The refresh route clears cookies only on
  a backend `401`. During an outage (503) it keeps them, and the UI shows "Can't reach the server" with a retry button.
- `SESSION_COOKIE_INSECURE=1` drops the `Secure` flag. Use it only for plain-http dev hosts that are not localhost.
- A user who has no active membership is sent to `/onboarding`.

### API client (`packages/api-client`)
`ApiClient` adds `X-Request-ID` to every request. It adds `X-Merchant-Id` on tenant endpoints and refuses to send them
when no merchant is selected. On *(idem)* endpoints it adds an `Idempotency-Key` (`crypto.randomUUID`, or a key the
caller passes). Non-2xx responses are parsed into `ApiError {status, code, message, details, requestId, retryAfter}`.
A `401 token_expired` triggers one shared refresh followed by a single retry with the same idempotency key. Forms use
`useIdempotencyKey()`, which keeps the same key while the body is unchanged, so a double submit or retry replays the
original request instead of creating a duplicate.

### Data states
Every data view goes through `useApiQuery` and renders one of these states:
- loading: a skeleton shaped like the table it replaces
- empty
- error: a localized message, the request ID in small type for support, and a retry button
- permission denied: shown for `403 permission_denied`, naming the missing permission
- partial: a degraded banner when some calls fail. Plan & usage loads three endpoints, and Team still shows members when invitations fail.

Actions are hidden when `GET /permissions/me` says they aren't allowed. If that call fails, actions are shown and the server still enforces permissions.

## i18n: why a typed dictionary instead of next-intl

We use a small typed dictionary (`src/i18n`) for these reasons:
- `messages/en.ts` is the source of truth, and `ne.ts` is typed `Messages`. A missing or extra key is a **compile
  error**, and `t()` only accepts valid dotted keys (`MessageKey`).
- We need just two locales, `{var}` interpolation and Intl formatters. Locale-prefixed routing, ICU plural syntax and
  the extra middleware composition would add weight without solving a current problem.
- The locale comes from the `cos_locale` cookie, then `Accept-Language`, then the default (`ne`). The root layout reads
  it server-side, so `<html lang>` and fonts are correct on first paint. Switching language sets the cookie and saves
  `PATCH /me {locale}`.

Tests check that `ne` has exactly the keys `en` has, that no string is empty, that both languages use the same
placeholders, and that every contract error code maps to copy.

**Formatting:** money uses `Intl.NumberFormat('ne-NP' | 'en-NP')` with Latin digits, and the currency part is swapped
for the symbol sellers actually write: `रू 1,250` and `Rs 1,250`. `ne-NP` uses lakh grouping (`रू 1,23,456`).
Dates and relative times also use Latin digits. Sellers type Latin digits in chats and receipts, and mixing digit
systems on one screen hurts scanning.

Desktop Chrome ships reduced ICU data for `ne`, so month names can fall back to English there. Values are still correct.

**API errors:** the client maps `error.code` to `errors.<code>` and never shows the API's `message`. `validation_error`
field types map to per-field copy.

## Design notes (spec 18)
- Surfaces are neutral: a cloud sidebar and a white work area. There are no cards. Sections are separated with
  dividers, tables, drawers and whitespace.
- Colour is used only for action (blue), automation (indigo), healthy (teal), attention (sun) and failure (danger).
  **Teal and sun are only ever fills or indicators, never text.** Warning and danger text uses the AA-safe semantic tokens.
- Controls use `radius-md`. There are no pills, gradients, sparkles or icons inside circles.
- Fonts are Inter and Noto Sans Devanagari via `next/font`, with Devanagari at line-height 1.7.
- Motion is 150/220/320 ms through the tokens, and is zeroed under `prefers-reduced-motion`.
- Under 900px the left nav collapses into a Radix Dialog drawer. Layouts were checked at 360px with no horizontal scroll.
- Keyboard: visible focus rings, a skip link, a Cmd/Ctrl+K command palette (combobox/listbox with `aria-activedescendant`),
  and Radix focus trapping in drawers and menus. Async errors use `role="alert"` and toasts use a polite live region.
- Signature components:
  - **Autopilot Status Strip:** a mode track plus automated and needs-you counts. A count that hasn't been measured shows `—`, never a fake 0.
  - **Exception Inbox:** 10 typed exception kinds, sorted by severity, with loading, empty and error states.
  - **Usage meter:** 70/85/100 thresholds. Reserved usage counts toward the limit, and the server's `alert_level` wins when it is more severe.
  - **Video Credit Meter:** the monthly quota as one cell per clip when the limit is 60 or less, the daily burst cap shown separately, the credit balance, and the at-limit options.
- Unbuilt sections show "Arrives in Phase N", one concrete sentence about the section, and links that are useful today. No sample data.

## Assumptions about the API contract
These are recorded here so the backend team can confirm them:
1. `GET /permissions/me` → `{permissions: string[]}`. The shape isn't specified.
2. `GET /invitations` → `{items: Invitation[]}` with `{id, email, role, status?, created_at?, expires_at?}`.
3. `POST /merchants` and `POST /invitations` may return the object bare or wrapped (`{merchant}` / `{invitation}`). The client accepts both.
4. `POST /auth/register` returns `201 {user}` and does not sign the user in. The web app logs in right after.
5. Audit `changes` format isn't pinned. We accept `{before:{}, after:{}}`, `{field:{old,new}}`, `{field:[old,new]}` or `{field: value}`.
6. `credits.transactions[]` → `{id, amount, reason?, created_at?}`.
7. Premium video limits are any `resource` that contains `video` and not `reel` (e.g. `premium_video_clips`, `video_seconds`).
8. `last_owner` is listed under `PATCH /members` only. We also handle it on `DELETE /members/{id}`.
9. Phase numbers for unbuilt sections (Orders, Products, Customers, Inventory → P1; Inbox, Content, Fulfillment → P2; Returns, Automation, Analytics → P3) are a working plan. The specs don't define them. They live in `src/lib/sections.ts`.
10. Onboarding sends `country: "NP"` and `currency: "NPR"`, as the contract literal requires. The currency select only offers NPR for now.
11. "Buy credits" and "Compare plans" link to the Plan page anchors. The contract has no checkout endpoint yet.
12. The backend is assumed to read `X-Forwarded-For` and `User-Agent`, which the BFF forwards, to record session IP and device.
13. Phase 0 has no endpoint for exceptions or automation counts. Home passes real empty values: `items=[]` and counts of `0` with honest copy.

## Products (Phase 1 catalog)

Routes: `/products` (list), `/products/new`, `/products/[id]` (editor). The API wrapper is `api.catalog.*` in
`packages/api-client`. Logic that can be tested without the UI lives in `apps/web/src/lib/catalog`:

| File | What it does |
|---|---|
| `lib/money.ts` | Rupees ↔ paisa using string math. Accepts `1,250.50`, `Rs 1250`, `रू १२५०`. Allows at most 2 decimals and caps at NPR 100M, matching the backend guard. |
| `catalog/variants.ts` | Builds option combinations (cartesian product). Grid rows are keyed by option values, so renaming an option keeps prices already typed in. Removed combinations stay excluded. |
| `catalog/editor.ts` | Maps the form to and from the API, validates on the client, and builds per-field diffs for PATCH. |
| `catalog/status.ts` | Lifecycle transitions mirrored from the backend, and the map from each `not_publishable` problem to its editor section. |
| `catalog/codes.ts` | SKU normalisation and GTIN check digits, mirroring `rules.py`, so a typo is caught before the request. |
| `catalog/csv.ts` | Import template, error export, formula-injection guard, and a UTF-8 BOM so Excel shows Devanagari. |
| `catalog/useImportJob.ts` | Polls an import with backoff (1s ×1.5, capped at 5s). Stops on a terminal status, on unmount, or after 3 failures in a row. |

How saving works in the editor:
1. `PATCH /products/{id}` is sent first, always with `version`. An empty patch still checks for concurrent edits.
2. Then one `PATCH` per changed variant.
3. Then the variant archives the seller queued with Remove.
4. Finally a fresh `GET`.

If something fails partway, the rows that saved become clean. Failed cells keep the seller's values and show the
error, and a banner says what happened. A `version_conflict` shows a banner and keeps the edits; Reload throws them
away, and the banner says so. Attribute review (confirm, edit, add) saves immediately and never touches `version`.

Status changes are separate from Save. They are disabled while there are unsaved edits, and disabled for anyone
without `catalog.publish`.

`lib/navigationGuard.ts` blocks leaving the page with unsaved changes in three ways: `beforeunload`, a capture-phase
click handler on same-origin links, and `confirmLeave()`, which the command palette calls.

### Catalog API gaps (reported to the backend team)
- **Options and variants are fixed after create.** There is no endpoint to add an option, value or variant to an
  existing product. The editor shows existing variants, which can be edited or archived, and explains the limit.
- **Variant PATCH has no `version`.** The editor works around this by sending an empty product PATCH with `version`
  first.
- **Collection membership can't be edited safely.** `PUT /collections/{id}/products` replaces the whole list, and no
  endpoint lists a collection's products. Collections are therefore shown read-only.
- **Categories are create-only.** There is no rename, move or delete.
- **Import row errors with `code: invalid_row` carry English text** (e.g. `price: 'abc' is not a number`) and no
  structured field, so they can't be localized. Known catalog codes are localized.
