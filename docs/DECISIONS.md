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
