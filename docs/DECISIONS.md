# Architecture Decision Records

Format: context → decision → consequences. Status is `Accepted` unless noted.

---

## ADR-001 — Modular monolith: FastAPI + SQLAlchemy 2 + Celery
**Context.** specs/03 requires a modular monolith + workers + durable events; Celery is named. Backend language is not specified.
**Decision.** Python 3.12, FastAPI (sync endpoints in the thread pool), SQLAlchemy 2 ORM (sync, psycopg 3), Alembic, Celery on Redis. Domains live in `apps/backend/app/domains/<domain>/` with their own models/service/router. Cross-domain calls go through service functions, never another domain's tables directly. Exception: the billing entitlement service is called by every domain.
**Why sync.** The same service code runs in API and Celery workers, and SQLAlchemy sync sessions give simple, explicit transaction boundaries. That matters more here than raw request concurrency.
**Consequences.** One deployable for API and one for workers. Extract a service only on the triggers in specs/03.

## ADR-002 — Tenant isolation enforced in the ORM, not by convention
**Context.** specs/03 requires a tenant ID on all merchant-owned records plus enforcement and cross-tenant tests.
**Decision.** `TenantScoped` mixin (`merchant_id NOT NULL`, FK, indexed). When a request is bound to a tenant, every ORM SELECT gets `merchant_id = :tenant` automatically via `with_loader_criteria`. A `before_flush` guard rejects writes to another tenant. Foreign-tenant access returns **404**, not 403. Code that must cross tenants (billing internals, admin) opts out explicitly with `execution_options(skip_tenant_filter=True)` and filters by `merchant_id` itself.
**Consequences.** A forgotten filter can't leak data. PostgreSQL row-level security is a planned second layer (GAP-RLS).

## ADR-003 — IDs are UUIDv7
Time-ordered IDs give index locality and allow keyset pagination on the primary key with no extra `created_at` index. They are generated in-app (`app/core/ids.py`), because Python 3.12 has no stdlib `uuid7`.

## ADR-004 — Auth: short JWT access tokens + rotated opaque refresh tokens
**Decision.**
- Access JWT lasts 15 min and carries `sid`. The session row is checked on every request, so revocation takes effect immediately at the cost of one primary-key lookup.
- Refresh tokens are opaque, stored as SHA-256 hashes, and rotated on every use.
- Reusing a rotated refresh token revokes the whole session family and emits `accounts.refresh_token_reuse_detected`.
- MFA uses TOTP with the secret envelope-encrypted, plus 10 Argon2-hashed single-use recovery codes.
- Staff/admin endpoints require a session that passed MFA (`amr=pwd+mfa`).
- Web keeps the refresh token in an httpOnly cookie set by Next.js BFF route handlers. Mobile uses Keychain/Keystore.

**Consequences.** The web client must serialise refreshes across tabs, because a parallel refresh looks like reuse. The web app uses the Web Locks API for this.

## ADR-005 — Entitlements are data; one pipeline for metered work
**Context.** specs/08: never hard-code plan names; `check_feature → check_limit → reserve_usage → execute → finalize_usage`.
**Decision.**
- Plans, versions, features, limits, add-ons and overrides live in the database, seeded from `packages/contracts/feature-entitlements.example.json`. A changed plan definition creates a new `PlanVersion`; existing subscribers stay on theirs.
- Usage counters are per window (subscription month; merchant-local day for burst). They are row-locked during reserve, with a stable lock order.
- Resources missing from a plan are denied. Unlimited must be explicit (`NULL`).
- Daily burst limits are always hard. Monthly overage follows policy: `block`, `credits` (credit-funded usage doesn't consume quota) or `overage`.
- Gauge resources (seats, stores, products) are counted by counters each domain registers. The enforced number and the displayed number come from the same query.

**Consequences.** Expensive work must reserve in a short transaction *before* the provider call (the AI gateway does this). Abandoned reservations expire via a Celery beat task.

## ADR-006 — AI Gateway owns retries, failover and cost; provider SDKs only inside adapters
**Decision.**
- Business code calls `gateway.run(task=…)` with a provider-neutral `AIRequest`.
- Routing comes from a versioned policy contract (`packages/contracts/ai-routing-policy.example.json`). A database override (ADM-009) comes later.
- The Claude adapter uses the official `anthropic` SDK with `max_retries=0`, so the gateway counts and costs every attempt in one place. Structured output uses `output_config.format` (json_schema), and the gateway validates again.
- A `refusal` stop reason is non-retryable and doesn't count toward the circuit breaker; the gateway falls through to the next candidate.
- OpenAI and Gemini use plain HTTP adapters.
- A shared Redis circuit breaker (half-open single probe) protects providers.
- Every attempt writes an `AIExecution` ledger row. Prompts and outputs are never stored there (PII).
- Default model: `claude-opus-5-5` at `medium` effort for copy, `claude-haiku-5-5` at `low` for classification/summaries, `claude-sonnet-5-5` for customer replies. All are configurable, not code.
- Server-side refusal fallback (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`) is on for Opus/Sonnet 5.5 via policy.

**Consequences.** The gateway must run in workers, never in synchronous HTTP handlers. BYOK test (`/ai/credentials/{id}/test`) is the one sync exception: it is a bounded 10s health check.

## ADR-007 — Envelope encryption for stored secrets
AES-256-GCM data keys wrapped by a key-encryption key (KEK). Associated data binds each ciphertext to its owner, e.g. `byok:<merchant>:<provider>:<id>`. The `local` KEK provider is dev/test only, and production settings refuse it. Used for BYOK keys, TOTP secrets and invitation tokens awaiting email. Revoke deletes the ciphertext (crypto-shred).

## ADR-008 — Transactional outbox with per-handler exactly-once
Events are declared in `packages/contracts/event-catalog.json` and their payloads validated with JSON Schema at publish time; undeclared events are refused. The dispatcher claims rows with `SKIP LOCKED`. Each handler commits its side effects together with an `outbox_consumptions` row, so a retry after a partial failure never re-runs a handler that already succeeded. Backoff is exponential with jitter. After `outbox_max_attempts` an event becomes `dead` (the DLQ), and admin can replay it (audited).

## ADR-009 — Audit is append-only at the database level
Audit rows are written in the same transaction as the change. A trigger blocks `UPDATE`, `DELETE` and `TRUNCATE` on `audit_logs`. Changes and metadata are redacted by key before storing.

## ADR-010 — Error envelope and log hygiene
- All errors use `{error: {code, message, details, request_id}}`. Clients localise by `code`; `message` is never shown as UI copy.
- SQLAlchemy runs with `hide_parameters=True`.
- Unhandled database errors are logged as SQLSTATE, constraint and stack *locations* only, because Postgres echoes row values (emails, hashes) in error text. This was found while testing.

## ADR-011 — Monorepo layout
`apps/{backend,web,mobile}`, `packages/{design-system,api-client,contracts}`, `infra/`, `docs/`, `specs/` (the spec documents, moved from the repo root unchanged). pnpm workspaces for JS, uv for Python, standalone Flutter project. The admin console is served from the backend API (`/api/v1/admin/*`), and its UI is not built yet. When built, it ships as a separate Next.js app on a separate origin (GAP-ADMIN-UI).

## ADR-012 — Design tokens: one JSON source, generated per platform
`packages/design-system/design-tokens.json` is the source. `scripts/build-tokens.mjs` emits CSS custom properties, TypeScript and Dart. CI fails if generated files drift. Brand teal and sun fail WCAG contrast as text on white, so they are used only as fills and indicators.

## ADR-013 — Web i18n via typed dictionaries (made by the web workstream)
Typed `en`/`ne` dictionaries instead of next-intl, so a missing Nepali key is a compile error. Reasoning is in `docs/web/README.md`.

## ADR-014 — Dependency versions: lower bounds in manifests, exact pins in lockfiles
The initial exact pins in `pyproject.toml` were stale, and `pip-audit` found known CVEs, including in PyJWT. Manifests now declare minimums; `uv.lock` / `pnpm-lock.yaml` pin exact versions. CI audits the lockfile. Upgrades are deliberate PRs that run the full gate.

## ADR-015 — Resolving missing / conflicting specs (superseded in part by ADR-026)
21 of the 30 referenced spec files are not in the repository (see KNOWN_GAPS). Where they are missing:
- Derive from the 9 present docs and the build brief.
- Prefer security and data integrity.
- Mark derived values **provisional**. Plan limits other than the video numbers in spec 08 are provisional. Prices are `NULL` (not configured) rather than invented.

## ADR-016: AI output is a draft document; commercial facts stay with the seller
The Product Studio stores the model output as a JSONB draft on `studio_jobs`. It is review material, not commerce data.
- **Schema:** the extraction schema has no price, stock, delivery or discount fields.
- **Seller-entered facts:** `apply` requires seller-entered variants and prices.
- **Grounding check:** a deterministic check (English and Nepali patterns) flags such claims in generated copy unless the seller's own notes contain them.
- **Attribute confidence:** attributes become `confirmed` automatically only above the routing policy's `min_confidence` (0.75). Below that, the product cannot go live until the seller confirms them.

## ADR-017: Slow AI work runs on Celery behind the outbox
The flow is: HTTP creates a job → outbox event → handler enqueues a Celery task on the `ai` queue → the task calls the gateway without holding a DB transaction.
- **Recovery:** a beat sweeper re-enqueues jobs stuck in queued/running, which covers broker loss.
- **Retries:** at most 3 attempts.
- **No charge on failure:** provider outages leave the usage reservation released.

## ADR-018: Channel listings reconcile desired vs actual state per product version
`channel_listings` stores `desired_state` and the `published_product_version`.
- **Idempotency:** each sync uses the key `listing:{id}:v{product.version}`. A redelivered event is a no-op, and updates reuse the provider's `external_id`, so there are no duplicate listings.
- **Credential rejection** marks the connection `expired` (with an event and an exception). Listings wait and re-sync automatically on reconnect.
- **Transient errors** back off through delayed outbox events.

## ADR-019: Content approval follows automation mode
- **Seller-written posts:** never need approval.
- **AI-written posts:** need approval in Assisted mode, or in any mode when the grounding check flagged issues. Otherwise they are auto-approved.
- **Edits:** any edit after approval sends the post back to draft.

## ADR-020: The Exception Inbox is derived, not stored
`GET /exceptions` computes open exceptions from authoritative domain state: expired connections, failed listings and posts, pending approvals, drafts needing review, unconfirmed AI attributes, and quarantined uploads. Fixing the underlying problem removes the item, so there's no separate ack/resolve state to drift. Dismiss and snooze, and exceptions from future domains (orders, payments, couriers), plug into the same function.

## ADR-021: DB unit of work commits before the response (dependency scope)
FastAPI 0.118+ runs `yield` dependency teardown after the response is sent by default (`scope="request"`). Our `get_db` commits in teardown. That allowed clients to act on uncommitted data (an intermittent `session_revoked` right after login) and to receive success for commits that could still fail.
- **Fix:** every `get_db` dependency declares `scope="function"`, used uniformly so that tenant binding and the endpoint share one session.
- **Guard:** a structural test walks every route's dependency tree and fails on any other scope.
- **Lesson:** this regression arrived with a security-driven dependency upgrade (ADR-014). Upgrades must run the full E2E suite against a real stack, not only unit tests.

## ADR-022: Migrations that add NOT NULL columns ship with a server default
Adding a NOT NULL column without a server default fails on a populated table. The brand-voice migration hit this locally, against 56 merchants. Rules:
- New NOT NULL columns get a `server_default`, mirrored in the model so `alembic check` stays clean.
- Every migration is round-tripped (upgrade → downgrade → upgrade) against a database with data before merge, not only an empty one.
- Changes to existing CHECK constraints are not detected by autogenerate and are written by hand, using `op.f()` for the full constraint name (see 0007).

## ADR-023: Autonomous Commerce OS architecture (Commerce Core / Intelligence Core / Digital Store Twin)
The product is repositioned as an Autonomous Commerce OS (specs/25, 01, 03).
- **Decision:** two cores inside the modular monolith. Commerce Core (authoritative, transactional)
  and Intelligence Core (derived, explainable, recomputable). The Digital Store Twin is a **derived
  read model**, never a second source of truth.
- **Rules:** intelligence never supplies commercial facts at execution time; every recommendation
  carries structured evidence; LLMs may only phrase explanations, validated against evidence.
- **Consequences:**
  - intelligence tables are additive and carry method_version/as_of
  - automation enforces max-staleness per action
  - a new `intelligence` worker queue arrives in Phase 6

## ADR-024: Event naming for new intelligence events
The strategy brief names events in PascalCase (`ProductPerformanceUpdated`…). The implemented catalog
uses `<domain>.<past_tense_snake_case>` (e.g. `catalog.product_created`), and the backend validates
against it.
- **Decision:** keep one convention. New events are declared as `productbrain.performance_updated`
  etc., with `maps_to` holding the brief's name and `status: planned` until their phase ships.

## ADR-025: Roadmap renumbering (Phases 0–10) and pull-forward instrumentation
`specs/22` (authored 2026-11-02) supersedes the provisional phase grouping (old P2 included
inventory/payments; old P5 analytics/procurement).
- **Decision:** Phases 0–10 as in the strategy update. Intelligence starts at Phase 6, gated on ≥90
  days of operational data for pilot merchants.
- **Pull-forward:** data that intelligence needs is instrumented in the operational phases as
  required work:
  - CNT-012 creative attributes (Phase 1)
  - ORD-012 structured addresses (Phase 2)
  - AUT-018 action/outcome log (from Phase 2)
  - RET-012 controlled return reasons (Phase 4)

## ADR-026: Specification set authored by engineering
21 of the 30 referenced specs were never supplied. On 2026-11-02 they were authored from the existing
specs, the build briefs, the strategy update and the implemented system.
- 04–06, 09–17, 19–22 and 25 are marked "authored; owner review required".
- Business decisions are left explicitly TBD rather than invented (prices, most limits, brand
  adoption, legal positions).

## ADR-027: COD Intelligence fairness constraints
COD risk is a per-order, explainable assessment with merchant override and dispute (specs/12, 15).
- **Prohibited:** name-derived features, protected-attribute inference, cross-merchant person-level
  lists.
- **Process:** a static prohibited-feature check is part of CI for CODI. Calibration and regional
  disparity reports are required before enabling auto-actions on MEDIUM/HIGHER.

## ADR-028: Nivaro brand migration and safe rename plan
The owner adopted **Nivaro** (category Autonomous Commerce OS, tagline "Your store, on autopilot.").
- **Decision:** rename everything customer-facing; keep technical identifiers that would break
  integrations, data, tokens or installs.
- **Renamed (customer-facing):**
  - web titles/description/OG/Twitter/PWA manifest
  - favicon, apple icon and PWA icons
  - logo in the app shell and sign-in
  - i18n copy (en/ne), email subjects/sign-off, email sender display name (`COS_EMAIL_FROM_NAME`)
  - OpenAPI title "Nivaro API"
  - TOTP issuer "Nivaro" (new enrolments only; existing authenticator entries keep their old label, the
    secret is unaffected)
  - WooCommerce webhook display name (webhooks are tracked by id, not name)
  - Flutter display name (iOS `CFBundleDisplayName`, Android `android:label`), launcher icons, app
    title; README and specs
- **Kept, documented as legacy:**

  | Identifier | Why it stays |
  |---|---|
  | npm scope `@commerce-os/*` | imports in every package |
  | Dart package `commerce_os_seller`, bundle/application ID `np.commerceos.commerce_os_seller` | a new ID is a new store app; rename only before first store submission |
  | `COS_` env prefix and `cos_` cookies | deployed config and live sessions |
  | `jwt_issuer = "commerce-os"` | issued tokens would fail validation |
  | DB names `commerce_os*`, bucket `commerce-os-private`, service name `commerce-os-api` | data, IAM and telemetry continuity |
  | Docker image/compose names, CI job names | infra continuity |
  | `docs/Autonomous_Commerce_OS_Business_Partner_Brief.pdf` | binary partner brief; needs regeneration (GAP-BRAND-LEGACY-DOCS) |

- **Future rename:** possible behind a migration plan (dual-issuer JWT window, env alias, DB rename at
  a maintenance window). Not scheduled.

## ADR-029: Brand palette authority
The concept boards (`assets/brand/reference/`) show Blue #185CFF, Teal #00D7B2 and Navy #0B1B3D. The
brand brief specifies #2563EB, #14B8A6 and #0F172A.
- **Decision:** the brief wins. These values were already the token primitives, so no screen changes
  colour. They also have known contrast behaviour; the board values are more saturated and #00D7B2
  fails contrast for any text use.
- **The boards are reference only.** Their ™ marks wait for trademark filing (GAP-BRAND-TRADEMARK).

## ADR-030: Logo built as code-generated geometry; navy app icon (logo part superseded by ADR-032)
The concept boards are raster images and cannot be used as production assets.
- **Decision:** redraw the mark and wordmark as geometry (`packages/design-system/brand/geometry.mjs`).
  - **Mark:** a ribbon N in three overlapping strokes with fold shading.
  - **Wordmark:** stroked geometric lowercase letters, so there is no font dependency or licence issue.
  - `assets/brand/scripts/render.mjs` generates every SVG and PNG (logo variants, motifs, favicon,
    PWA/apple icons, OG image, Android mipmaps, iOS AppIcon set) from it.
  - Web (`components/brand`) and Flutter (`nivaro_brand.dart`, from generated `brand_geometry.g.dart`)
    draw from the same geometry.
- **Primary app icon:** the colour mark on Deep Navy. It is the more ownable on home screens, and a
  light variant is kept.
- **Status:** this is an engineering redraw of the approved concept. A designer review of curves and
  optical balance is recommended before trademark filing (BRD-002 note).

## ADR-031: Semantic token layer; indigo retired
Tokens v1.0 add `semantic.light` and `semantic.dark` (brand, text, surface, border, action, focus,
status, flow, scrim), emitted as `--color-*` CSS variables, TS and Dart `AppColorsLight/Dark`.
- **Dark mode** is now generated, both for the media query and for `[data-theme="dark"]`. The
  hand-written dark overrides in `globals.css` are removed.
- **Legacy aliases** (`--surface-page`, `--text-secondary`, …) point at the semantic layer, so existing
  components keep working while new code uses `--color-*`.
- **Indigo (#4F46E5) is not in the Nivaro palette and is removed.** Automation and AI markers use
  brand blue (`text-brand` on `surface-brand-tint`).
- **Enforcement:** the web brand guard test fails on hex colours outside an allowlist, on indigo, and
  on the pre-Nivaro name in UI copy.

## ADR-032: The logo is the owner's artwork (supersedes the logo part of ADR-030)
The owner asked for the concept-board artwork itself to be the logo everywhere.
- **Decision:** `assets/brand/scripts/extract_logo.py` cuts the mark and the wordmark out of the
  reference board.
  - It unmixes each pixel against the sampled background (colour-to-alpha), so edges stay clean on
    light and navy.
  - The ™ is removed until the trademark is filed.
  - The outputs in `assets/brand/logo/source/` are the masters. `render.mjs` composes every lockup,
    app icon, favicon (incl. `.ico`), PWA/apple icon and OG image from them.
- **Where it is used:**
  - **Web:** the mark as an image; the wordmark as a CSS mask filled with `--color-brand-ink`, so one
    asset serves light and dark.
  - **Flutter:** `Image.asset`, with the wordmark tinted by theme.
- **Geometry kept for motifs only.** The geometry-drawn mark and wordmark are removed;
  `geometry.mjs` now holds only the ribbon motifs (trail, loop, empty state).
- **Limits:**
  - The colour mark master is 384×263 px. That is enough for UI and app icons (scaled up about 1.7×
    for 1024 px icons), but print and large-format use need a vector master (GAP-BRAND-LOGO-VECTOR).
  - The monochrome marks come from the board's small monochrome panel (114 px). Use them only small.

## ADR-033: Light theme by default; dark is opt-in
- **Decision:** light for everyone by default, regardless of OS setting.
- **How:**
  - Web: `data-theme` is set on `<html>` on the server from the `cos_theme` cookie (light | dark |
    system), so the page never flashes the wrong theme.
  - Generated tokens apply dark under `[data-theme="dark"]`, or under `[data-theme="system"]` with a
    dark OS.
  - Web switches: the user menu (app) and a three-way switch (Light · Dark · Device) on the website
    and sign-in.
  - Flutter: `ThemeController` defaults to `ThemeMode.light`; Settings → Theme offers Light, Dark or
    Same as phone (stored on the device).
- **Dark mode also overrides the `*-soft` status colours,** so badges and alerts need no
  per-component dark CSS.

## ADR-034: Public website lives in the web app at "/"
- **Decision:** the website is a public route (`/`) of `apps/web`, not a separate site.
- **Why:** it shares tokens, brand components, i18n (en/ne), the theme switch and the auth entry
  points (`/register`, `/login`); signed-in visitors see "Open Nivaro". The middleware treats `/` as
  public; the app stays under `/home` and the section routes.
- **Honesty rules, enforced by `features/site/site.test.tsx`:**
  - Every capability carries its real build status (Available now / In development).
  - The Control Center and intelligence examples are labelled illustrative.
  - No prices until GTM decides (GAP-SPEC-21), and no testimonials, customer logos or invented
    adoption numbers.
  - Product imagery is a flat illustration, labelled as a stand-in for real seller photography.
- **Content source:** the partner brief PDF, plus specs 01/21/25/26.

## ADR-035: Password reset (QA-001)
- **Decision:** `POST /auth/password/forgot` always answers 202 (no account enumeration) and is
  rate-limited per IP (10/h) and per email (3/h).
- **Token:** issued when the email is sent. Single-use, 30 minutes, stored only as a hash. Issuing a new
  token voids older ones.
- **Reset:** `POST /auth/password/reset` enforces password policy, revokes every session, clears
  lockout, audits the change and emails a "password changed" notice.
- **Where it appears:** the web reset page is the landing page for emailed links. Mobile requests the
  link natively.

## ADR-036: Gauge limits serialised with advisory locks (QA-015)
- **Decision:** `check_gauge` takes `pg_advisory_xact_lock(hash(merchant, resource))` before counting,
  held until commit.
- **Why:** count-then-insert can't be made atomic with a CHECK constraint, and a counter table would
  duplicate the source of truth.
- **Cost:** contention is per merchant per resource only.

## ADR-037: TOTP replay protection (QA-011)
- **Decision:** `users.mfa_totp_last_step`. A code is valid once, for a time-step newer than the last
  accepted one (±1 step of skew), checked under a row lock.

## ADR-038: Runtime CSP from middleware (QA-009)
- **Decision:** the CSP is built per request from `PUBLIC_API_ORIGIN` / `BACKEND_URL`, because the
  browser uploads to and loads media from the API origin, which differs per environment.
- **Allowed:** inline scripts, for the Next.js bootstrap. Nonces are a follow-up.
- **HSTS:** sent only over HTTPS.

## ADR-039: Database outage is 503, not 500 (QA-016)
- **Decision:** connection-class `OperationalError` (no SQLSTATE, 08xxx, 57P0x, 53300) maps to 503
  `dependency_unavailable` with `Retry-After`. Query bugs stay 500 so they still alert as bugs.

## ADR-040: Nivaro Console is English-only and lives in the web app (2026-11-03)
- **Context:** the Console is an internal staff tool; seller surfaces must be bilingual (specs/19).
- **Decision:** the Console ships at `/console` inside the web app (same BFF/session), English copy in
  `features/console/copy.ts`, not the seller dictionaries. Access: platform staff + MFA-verified
  session (API-enforced); non-staff see a plain not-found page.
- **Consequences:** one deployment, no second auth surface. If non-English-speaking support staff join,
  move the copy into the typed dictionaries.

## ADR-041: Listing reconciliation reports drift, the seller decides (CHN-012, 2026-11-03)
- **Decision:** reconciliation only reads the channel. Drift is stored on the listing and shown in the
  Exception Inbox; the seller chooses "use Nivaro's version" (republish, recreate if deleted) or "keep the
  channel's version". Drift that disappears on the channel clears itself. A credential failure expires
  the connection instead of recording drift.
- **Why:** spec 10 ("drift creates exceptions, never silent overwrites"); sellers edit directly in their
  stores, and overwriting would destroy their work.

## ADR-042: A variant is stock-tracked once stock is first recorded (INV, 2026-11-04)
- **Decision:** a variant has no inventory level row until the seller records stock. Untracked variants
  never block orders or reservations, and the Sales Agent says "the shop will confirm stock" instead
  of guessing. Recording any stock makes it tracked; from then on reservations can't oversell.
- **Why:** existing shops have no stock data; blocking every order on day one would stop sales.
  Made-to-order items stay untracked on purpose.

## ADR-043: Sales Agent replies are grounded templates; AI enriches understanding (CRM-011, 2026-11-04)
- **Decision:** understanding is rules-first (Nepal phones, districts, wards, quantities, COD/online,
  yes/no in English, Romanized Nepali and Devanagari) plus the gateway intent model when confidence
  ≥ 0.7. Replies are bilingual templates filled only with tool results, and each reply stores what was
  looked up. Free-form LLM phrasing is deferred until a live model can be evaluated with a guard that
  rejects any number not present in the tool results.
- **Why:** spec 11 forbids model-generated transactional facts; no live key is available to evaluate
  phrasing quality; templates make chat-to-order work and stay correct without a key.

## ADR-044: A sale is never refused for a plan limit (BIL × ORD, 2026-11-04)
- **Decision:** orders past the monthly allowance are recorded as `overage` funding (the plans'
  `overage_policy`), and channel imports are always imported. Only stock can refuse an order.
- **Why:** refusing a customer's order because of the seller's plan loses real revenue and trust.

## ADR-045: Payments count only after server verification of the amount (PAY, 2026-11-04)
- **Decision:** online payments are marked paid only when the provider's `verify_payment` confirms
  capture *and* the amount equals the order total; webhooks only trigger verification. A different
  amount is held for the seller (`payment_mismatch`). Sellers may record outside payments
  (bank/eSewa/Khalti to their own account) for the exact total with an Idempotency-Key. A paid order
  moves to ready-to-ship automatically (R1).

## ADR-046: Order reservation happens at confirmation; channel imports keep short orders (ORD, 2026-11-04)
- **Decision:** stock is reserved when an order is confirmed, released on cancel, committed on ship.
  A channel order that can't be reserved is still imported (the sale happened on the channel) and
  flagged `stock_short` in the Exception Inbox.

## ADR-047: The order follows the parcel; parcel status is newest-event-wins (FUL-003/006, 2026-11-04)
- **Decision:** every parcel update (courier webhook, poll, or seller for own-rider deliveries) goes
  through one function: deduped per courier event, applied only if newer than the last applied event,
  and terminal states (delivered, returned, cancelled, lost) are final. Late events are stored with
  `applied=false`. The order is moved through the normal order state machine (picked up → shipped,
  failed → delivery_failed, returned → returned), never written directly.
- **Why:** couriers retry and reorder webhooks; a late "in transit" must never undo "out for
  delivery", and the order's history must stay explainable.

## ADR-048: Booking holds the order row lock across the courier call (FUL-003, 2026-11-04)
- **Decision:** booking locks the order row, checks there's no live shipment, then calls the courier
  with the Idempotency-Key. A partial unique index enforces one live shipment per order.
- **Why:** a double tap or two staff booking at once must not create two courier consignments (and
  two COD collections). A short lock during one HTTP call is cheaper than reconciling a duplicate.

## ADR-049: Shipping messages are transactional, sent only into the customer's own chat (FUL-007/008, 2026-11-04)
- **Decision:** on-its-way, out-for-delivery, delivered and failed-delivery messages are fixed en/ne
  templates, sent only to a conversation the customer started, when the merchant's toggle is on (default
  on), once per parcel and kind. A reply to the failed-delivery question is captured on the attempt
  before the Sales Agent sees it. Reattempts are requested automatically only in smart/autopilot mode
  (Decision Policy); in assisted mode the seller gets a "customer replied" exception.
- **Why:** customers expect delivery updates; templates can't promise anything the data doesn't
  support; asking the courier to go again costs money, so the merchant's automation mode decides.

## ADR-050: COD is settled only when a statement line matches or is accepted (FUL-010, 2026-11-04)
- **Decision:** courier statements (API, CSV, or seller-recorded own-rider cash) are matched line by
  line: matched, amount differs, not our parcel, not delivered, already paid, listed twice, not COD.
  Confirming "money received" requires every line matched or accepted with a reason (audited), and
  only then marks those COD records settled. Re-importing a reference returns the first import.
- **Why:** COD leakage is the top cash risk for Nepal social sellers; the seller must see exactly
  which parcels a courier paid and decide consciously about every difference.

## ADR-051: Fulfillment is on every plan (2026-11-04)
- **Decision:** couriers, shipments, recovery and COD settlement need no feature entitlement.
  Courier Brain (`intelligence.courier`) and COD Intelligence (`intelligence.cod`) stay Pro+ (Phase 6).
- **Why:** delivering and getting paid is core to every seller; intelligence on top is the upsell.

## ADR-052: Return eligibility is recorded; soft failures need an audited override (RET-002, 2026-11-04)
- **Decision:** each request stores the checks against the policy at that moment. Not delivered,
  nothing left to return, or a bad exchange choice refuse the request. Outside the window, final sale
  or missing evidence can be approved by someone with returns.approve, with a reason in the audit log.
- **Why:** sellers make goodwill exceptions every day; the exception must be visible and attributable.

## ADR-053: Abuse signals are merchant-scoped facts that only switch automation off (RET-011, 2026-11-04)
- **Decision:** frequent returns, high return rate and unusually high value are computed from this
  merchant's own records, shown as neutral facts, and stop auto-approve/auto-refund. They never reject.
  No personal attributes or cross-merchant data (same rule as COD Intelligence).
- **Why:** fairness and privacy (spec 12); a human decides when something looks unusual.

## ADR-054: Refunds never exceed what was paid; above the threshold a manager approves (PAY-007, RET-010, 2026-11-04)
- **Decision:** refunds are idempotent, serialised per order and capped at paid minus earlier refunds.
  Original-payment refunds go through the provider with the refund id as idempotency key; COD refunds
  are recorded transfers with a reference. Amounts above the policy threshold (default 0) wait for
  refunds.approve. Staff gained refunds.create so they can raise (not approve) refunds.
- **Why:** money leaving the business must be bounded, attributable and approved per merchant policy.

## ADR-055: Return pickups are shipments with direction=return (RET-006, 2026-11-04)
- **Decision:** the courier layer books, tracks and dedupes return pickups like deliveries, but they
  drive the return (in transit → received) and never the order status, COD record or customer
  shipping messages.
- **Why:** one tracking pipeline; no risk of a return parcel marking an order "delivered" or "failed".

## ADR-056: Exchanges reserve the replacement at approval and ship it after inspection (RET-008, 2026-11-04)
- **Decision:** same product, same price. Approval reserves the replacement (reference = the return);
  after inspection the reservation moves to a zero-total replacement order that ships normally.
- **Why:** the customer shouldn't lose their size while the parcel travels back, and the shop
  shouldn't send the replacement before the original is back.

## ADR-057: One Decision Policy for every automated action (AUT-016, 2026-11-05)
- **Decision:** workflows, the Sales Agent's auto-send, delivery reattempts and return auto-approve /
  auto-refund all call `policy.decide()` and store a DecisionRecord (rule, risk, mode, confidence,
  impact, inputs). Feature-specific opt-ins (the returns policy's auto-approve) count as the R2
  enablement, but the shop's mode still applies: Assisted never auto-executes anything above R0.
- **Why:** spec 06 requires a single, explainable policy; sellers need one mental model for "what
  runs on its own". Behaviour change: return auto-approve no longer runs in Assisted mode.

## ADR-058: Workflow triggers filter on the event's own status; facts are read live (AUT-002/003, 2026-11-05)
- **Decision:** a status filter matches the status the event announced, not the record's current
  status. Conditions and actions read facts from Commerce Core at each step and again at approval.
- **Why:** queued events can be processed after the record moved on; acting on the current state
  avoids double runs and stale decisions (found by tests: a "confirmed" event matched "packed").

## ADR-059: Workflows can't loop; edits are new versions; new workflows start off (AUT-001/005, 2026-11-05)
- **Decision:** jumps go forward only (max 20 steps), editing creates an immutable version that new
  runs use, and turning a workflow on needs automation.approve.
- **Why:** predictable, auditable automation; a draft can be built and dry-run safely.

## ADR-060: The action log is the Autopilot Score source (AUT-018, 2026-11-05)
- **Decision:** order capture/processing, courier booking/pickup, reattempts, customer messages,
  return decisions, refunds, settlement confirmations and workflow actions log performer
  (automation/ai/user/system), outcome and human intervention, idempotently.
- **Why:** APS (Phase 6) needs a trustworthy numerator/denominator from Phase 5 onward.

## ADR-061: Recommendations are always R3 and change only settings (REC-005, AUT-021, 2026-11-19)
- **Decision:** applying a suggestion goes through `policy.decide()` as R3 in every mode, needs
  automation.approve, is idempotent and stores a DecisionRecord. Suggestions only turn on a template
  workflow, change courier selection or create a restock task; they never move money or stock.
- **Why:** a suggestion is Nivaro's opinion about the seller's business; the seller decides. Settings
  changes are reversible, which keeps the before/after measurement honest.

## ADR-062: Score and suggestions are computed from the action log, not new metric tables (APS-002, REC-001, 2026-11-19)
- **Decision:** the Autopilot Score is computed from AutomationActionLog for a 30-day window; only the
  daily snapshot is stored. Recommendation evidence, baseline and outcome are JSON on the
  recommendation row.
- **Why:** one source of truth with Phase 5 and no aggregate that can drift. Revisit if computing it
  gets slow at real volume (index on merchant + created_at exists).

## ADR-063: Courier Brain ranks by expected cost with documented estimates (CRI-002, 2026-11-19)
- **Decision:** expected cost = price + failure probability × (2 × price for return and wasted outbound
  + NPR 50 handling) + COD cash held × 0.05%/day. Only couriers with 20+ finished parcels on the route
  are ranked, preferring those at 80%+ success; with none, the seller's rules apply, with a note saying so.
- **Why:** sellers need a reason they can check ("delivered 46 of 50 to Dhanusha"). The two estimates are
  shown as estimates and become merchant settings if sellers disagree with them.

## ADR-064: COD risk never rejects and never uses personal attributes (CODI-001/003, 2026-11-19)
- **Decision:** only this merchant's facts: the customer's delivery/return history with the shop, new
  vs repeat, address completeness, order value against the shop's usual orders and the shop's failure
  rate to the district. HIGHER holds the order for review (`needs_review="cod_risk"`); MEDIUM suggests
  verifying the phone; nothing is cancelled automatically. A static test fails the build if the module
  reads a name or adds a factor outside the allow-list. Overrides need a reason and are audited.
- **Why:** spec 12 fairness rules. A wrong "risky" label must cost the seller one phone call, not a
  lost customer, and must be possible to challenge.

## ADR-065: True profit counts only finished orders and never fills gaps with zero (ANA-007/008, 2026-11-19)
- **Decision:** the waterfall covers orders placed in the window that reached the customer (delivered,
  completed, or returned by the customer after delivery). Undelivered parcels count only their cost
  (both trips + NPR 50 handling); open orders are listed, not counted. Cost of goods uses the cost saved
  on the order line when it was placed (new column), falling back to today's cost for older lines.
  Restocked returns carry no cost; damaged ones keep it. Shared order costs are split across lines by
  value. Each component is Included / Partial (with a count) / Not included (with a reason).
- **Why:** spec 14: a missing cost must never look like profit. Sellers need to see what's missing and
  how to fix it.

## ADR-066: The Sales Agent uses only facts the seller confirmed (RTI-006, MEM-005, 2026-11-19)
- **Decision:** a derived fact such as "runs small" is shown to the seller first; it reaches customers
  only after the seller confirms it (directly or by applying the suggestion). Seller corrections become
  a new version that derivations never overwrite; a rejected fact isn't suggested again until the method
  version changes.
- **Why:** telling customers something wrong about a product costs sales and trust; the seller knows the
  product. Versioning keeps an audit trail of what Nivaro believed and when.

## ADR-067: Commerce Memory holds no personal facts (MEM-006, 2026-11-19)
- **Decision:** facts and metrics are about the shop, products, districts or couriers, never about one
  customer. Customer behaviour appears only as shop-level aggregates (e.g. reorder cycle). A test fails if
  a fact type or metric with a customer subject is added.
- **Why:** customer deletion/anonymisation then needs no extra step here, and memory can't become a
  profile of individuals.

## ADR-068: Return patterns are judged against the shop's own baseline with minimum samples (RTI-002, 2026-11-19)
- **Decision:** 10+ delivered units and 3+ returns; flagged when the rate is at or above the seller's
  limit or significantly above the shop's rate (exact binomial, p < 0.05, baseline needs 30+ units). A
  reason holding 50%+ of returns becomes the pattern. Dismissed patterns stay quiet for 90 days.
- **Why:** small shops have small numbers; without minimums every second return would raise an alert.

## ADR-069: Post results come from the channel or the seller, never estimated (CNT-013, 2026-11-19)
- **Decision:** channels report insights through an adapter capability (CONTENT_METRICS). Until Meta/TikTok
  approve the apps, the seller can type the numbers from the app's insights; every snapshot keeps its source
  (channel / manual) and the UI says which. Chats and orders always come from Nivaro's own records.
- **Why:** the learning loop can start before platform approval without inventing data.

## ADR-070: Attribution and the genome favour orders, with honest uncertainty (CNT-014, CGN-002, 2026-11-19)
- **Decision:** explicit post references win; otherwise orders for the post's product within 7 days get
  exp(-days/3) credit, shared between posts of that product live at the time (one order never counts as
  more than one). The genome needs 20 measured posts and 5 per option, shrinks each option towards the
  shop average (k = 5) and marks a pattern recommended only with ≥ 10% lift and z ≥ 1.5. Engagement is
  shown but cannot make a pattern recommended. With fewer than 5 attributed orders the outcome is chats.
- **Why:** spec 09: optimise for commerce, not likes; small shops have small samples, so the shop average
  is the safe default until the evidence is strong.

## ADR-071: Genome guidance is recorded, optional and never overrides the prompt rules (CGN-004, 2026-11-19)
- **Decision:** Studio adds the shop's caption patterns to the brand-voice input as guidance (the grounding
  rules stay above it) and stores the genome version on the job; posts inherit it. Auto Reel settings and
  the suggested time are applied only when the seller chooses them, and send the genome version. The
  suggested time falls back to when customers order (Commerce Memory), labelled differently, without a
  genome version.
- **Why:** sellers stay in control, and genome-informed posts can be compared with the rest (CGN-006).

## ADR-072: The web asks the plan before calling plan-gated APIs (2026-11-19)
- **Decision:** the auth context loads the plan's features (when the user can read billing) and widgets
  that hide quietly without a feature (stock risk, Product Brain, COD risk, creative suggestions) don't call
  their API at all when the plan lacks it. Pages whose job is the feature still show the upsell on 403.
- **Why:** avoids pointless 403s (noise in logs and alerts) found by the settings E2E's failed-request check.

## ADR-073: PO approval uses the shop's PO limit and the approver permission (PRO-004, 2026-11-20)
- **Decision:** above `po_minor` (Rules & limits; default 0) a PO always waits for an explicit approval
  by someone with procurement.approve, even its creator. Below it, an approver's PO is approved on submit;
  others wait. Reorder suggestions only create drafts, which go through the same path.
- **Why:** spec 06 makes POs above the threshold R3; a separate approve click keeps buying deliberate and
  audited without slowing small, routine orders once the seller raises the limit.

## ADR-074: Landed cost becomes the product's moving-average cost (PRO-006, 2026-11-20)
- **Decision:** freight, duty and other costs are allocated to lines by ordered value; each receipt stores
  the landed unit cost per lot; the variant's cost becomes the weighted average of stock on hand and the
  new good units at landed cost. Defective units aren't stocked; their cost shows up as the supplier's
  defect cost. Every cost change is audited.
- **Why:** true profit (ADR-065) needs the cost actually paid per sellable unit; order lines snapshot it.

## ADR-075: No supplier email/WhatsApp sending yet; a share text instead (PRO-003, 2026-11-20)
- **Decision:** "Mark sent" records the date; the PO offers a plain message to paste into WhatsApp,
  Viber or email. No prices or terms are added that the seller didn't enter.
- **Why:** sellers in Nepal order from suppliers by chat; sending needs a production email/WhatsApp
  provider (not configured) and the seller's consent per supplier.

## ADR-076: Supplier attribution by the lot on the shelf; true economics per unit (SPI-001/002, 2026-11-20)
- **Decision:** a sold unit belongs to the latest lot of that variant received before the order. Contribution
  per unit = selling price − landed − defect cost (defect_rate/(1−defect_rate) × landed) − return cost
  (unrestockable value + average return shipping, per unit sold) − fees & fulfilment (shop P&L, "not
  included" when missing). Switch suggestions need 20+ received units per supplier and a gain of at least
  5% of the price (min NPR 20 per unit).
- **Why:** spec 13's example: the cheaper supplier can be the less profitable one. Per-unit lot tracking
  isn't recorded at sale time, so the shelf-lot rule is the honest approximation (GAP-SPI-LOT).

## ADR-077: The Twin is recomputed per section from Commerce Core, never patched (TWIN-001…003, 2026-11-20)
- **Decision:** each section is a cheap aggregate query recomputed whole when one of its events arrives;
  `source_version` is the event's creation time in µs and an older event never overwrites a newer
  section. Reads past the TTL recompute synchronously; reconciliation runs every 6 h. Shop totals in the
  Twin need analytics.read. "Open orders" excludes delivered orders.
- **Why:** incremental patching of aggregates drifts; whole-section recompute is simple, correct and fast
  at SMB volumes. Exact values (stock for an order, refund amounts) still come from Commerce Core.

## ADR-078: Simulations are estimates from the shop's own history, with stated assumptions (SIM-002/003/005, 2026-11-20)
- **Decision:** discount demand = baseline (Product Brain EWMA over in-stock days) × (1 − discount)^elasticity.
  Elasticity comes from the shop's own discounted vs full-price days (≥ 5 and ≥ 10 days); otherwise a
  typical range (−0.5 to −3, central −1.5) with low confidence. Demand is Poisson; sales are capped by
  stock. Results list every assumption, give low/expected/high and never execute anything.
- **Why:** spec 14 rules; sellers must see why a number is what it is and how sure Nivaro is.

## ADR-079: The Decision Policy checks Twin freshness (spec 06 stale-data rule, 2026-11-20)
- **Decision:** a Proposal may name the Twin sections it relies on; if any is older than its automation
  max staleness the decision becomes REQUIRE_APPROVAL with rule `stale_data` and the stale sections.
- **Why:** automation must not act on old state; a person can still decide.

## ADR-080: Operational gauges are computed from the database when /metrics is scraped (2026-11-20)
- **Decision:** the API computes platform-wide operational gauges (outbox, webhooks, queues, failures,
  freshness, job heartbeats via Redis) on scrape, cached 15 s, each gauge isolated so one failing query
  never breaks the scrape. Workers expose their own metrics endpoint (multiprocess mode for prefork).
  Labels are bounded (queue, section, job) — never merchant ids.
- **Why:** gauges set inside workers were invisible to the API scrape (the outbox backlog always read 0);
  the database is the source of truth for backlogs and failures.

## ADR-081: Kill switches are feature flags read by the risky subsystems (2026-11-20)
- **Decision:** `ops.automation`, `ops.sales_agent_replies`, `ops.content_publishing`,
  `ops.intelligence_jobs`: a flag's kill switch stops the subsystem globally; a merchant override with
  enabled=false stops one shop. Stopped work waits (runs pause at their step, posts stay scheduled,
  messages stay in the inbox) and resumes when cleared. A missing flag means "on".
- **Why:** incident response needs a stop button that doesn't require a deploy and loses nothing.

## ADR-082: S3 encryption and presigned endpoints are configuration (2026-11-20)
- **Decision:** `COS_S3_SSE` = AES256 (default) | aws:kms (+ key id) | none (bucket default encryption);
  `COS_S3_PUBLIC_ENDPOINT_URL` signs browser URLs with a reachable host. boto3 is a runtime dependency.
- **Why:** the hard-coded SSE header failed on S3-compatible stores without KMS, and presigned browser
  uploads can't carry server-chosen SSE headers anyway; production buckets should enforce default
  encryption.


## ADR-083: Sellers connect payment gateways and messaging channels with their own credentials (2026-11-20)

**Context.** Khalti/eSewa pay out to a merchant account, and Messenger/Instagram need Meta App Review for Nivaro's app. Waiting on platform-level approvals would keep Pay and Converse unusable.
**Decision.** Each seller connects their own Khalti/eSewa merchant keys, Telegram bot token, or their own WhatsApp Business Cloud app (token, app secret, phone number id). Credentials are sealed with the existing envelope encryption (per-record data key, AAD bound to merchant + provider + row), opened only in memory for a call, never returned, never logged, and destroyed on disconnect. Payments are confirmed server-side with the gateway; redirects are never trusted.
**Consequences.** No Nivaro app review is needed for these channels; sellers do a little setup (copying a callback URL and verify token for WhatsApp). Platform-level OAuth channels (Meta, TikTok) remain blocked on review.

## ADR-084: Retention campaigns only reach customers who chatted, with opt-out and caps (2026-11-20)

**Decision.** Campaigns are sent only through a channel the customer already used to message the shop; every message carries an opt-out line and a STOP reply is honoured permanently; at most one campaign message per customer per 7 days, only 09:00–20:00 shop time, with a daily limit and a kill switch. WhatsApp customers outside the 24-hour window are deferred (templates not built).
**Why.** Unsolicited marketing harms sellers' channel standing and customers' trust; Nepal sellers mostly sell over chat already.
