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

## ADR-015 — Resolving missing / conflicting specs
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
