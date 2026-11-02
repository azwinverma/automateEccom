# Commerce OS

The operating system for online and social-commerce sellers in Nepal: from product photo to delivered order.
Product and engineering specs are in [`specs/`](specs/). Start with `specs/00_CLAUDE_START_HERE.md`.

**Status:** Phase 0 (platform foundation). See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md),
[`docs/KNOWN_GAPS.md`](docs/KNOWN_GAPS.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Repository
| Path | What |
|---|---|
| `apps/backend` | FastAPI modular monolith + Celery workers (Python 3.12, uv) |
| `apps/web` | Next.js seller web app with BFF auth ([docs/web/README.md](docs/web/README.md)) |
| `apps/mobile` | Flutter seller app ([docs/mobile/README.md](docs/mobile/README.md)) |
| `packages/design-system` | Design tokens → CSS / TS / Dart |
| `packages/api-client` | Typed TS client for the API |
| `packages/contracts` | Event catalog, plan entitlements, AI routing policy |
| `infra/` | Deployment notes / IaC (staging skeleton) |
| `docs/api/phase-0-contract.md` | API contract (OpenAPI served at `/api/v1/openapi.json`) |

## Run locally

**Everything in Docker** (Postgres, Redis, MinIO, migrations, API, worker, beat):
```bash
docker compose up --build          # API → http://localhost:8000
docker compose --profile web up    # + web → http://localhost:3000
# Ports in use? PG_PORT=55432 REDIS_PORT=56379 API_PORT=58000 docker compose up
```

**Backend on the host** (needs Postgres and Redis running):
```bash
cd apps/backend
cp .env.example .env               # edit COS_DATABASE_URL
uv sync
uv run alembic upgrade head
uv run python -m app.cli seed-plans
uv run uvicorn app.main:app --reload
uv run celery -A app.worker.celery_app:celery worker -B -Q default,outbox   # dev: worker + beat
```
Dev emails (verification, invites) are written to `.data/mailbox/`.

**Web:** `pnpm install && pnpm tokens && BACKEND_URL=http://localhost:8000 pnpm web:dev` (port 3010)
**Mobile:** `cd apps/mobile && flutter run --dart-define=API_BASE_URL=http://localhost:8000`

## Quality gates
```bash
cd apps/backend && uv run ruff check app tests && uv run mypy app && uv run pytest   # needs Postgres + Redis
pnpm -r lint && pnpm -r typecheck && pnpm -r test && pnpm --filter @commerce-os/web build
cd apps/mobile && flutter analyze && flutter test
E2E_BASE_URL=http://localhost:3010 pnpm --filter @commerce-os/web e2e    # live stack
```
CI runs all of these plus migration checks, dependency audits, SAST, secret and container scanning (`.github/workflows/ci.yml`).

## Platform rules
- Business code never calls AI SDKs. It calls `app.domains.ai.gateway`.
- Business code never checks plan names. It asks `entitlements` for a feature or resource.
- Every state change writes an audit row in the same transaction.
- Durable side effects go through the outbox; events must be declared in `packages/contracts/event-catalog.json`.
- Merchant-owned tables use `TenantScoped`. Tenant filtering is automatic, and cross-tenant tests are required.
