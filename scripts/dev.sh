#!/usr/bin/env bash
# Nivaro local stack: API + worker (with scheduler) + web, wired together.
#
#   scripts/dev.sh            # web in dev mode (hot reload)
#   scripts/dev.sh --prod     # production build of the web app (closer to real behaviour)
#
# Needs: PostgreSQL and Redis running locally, uv, pnpm (node). Ctrl+C stops everything.
# Ports: API_PORT (8090), WEB_PORT (3010). Backend settings come from apps/backend/.env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-8090}"
WEB_PORT="${WEB_PORT:-3010}"
WEB_MODE="dev"
[[ "${1:-}" == "--prod" ]] && WEB_MODE="prod"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
ok() { printf '\033[32m✓\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------- preflight
bold "Nivaro · local stack"
command -v uv >/dev/null || fail "uv not found (https://docs.astral.sh/uv/)"
command -v pnpm >/dev/null || fail "pnpm not found (corepack enable)"
[[ -f "$ROOT/apps/backend/.env" ]] || fail "apps/backend/.env missing: copy apps/backend/.env.example and adjust"
[[ -f "$ROOT/apps/web/.env.local" ]] || printf 'BACKEND_URL=http://localhost:%s\n' "$API_PORT" > "$ROOT/apps/web/.env.local"

env_get() { grep -E "^$1=" "$ROOT/apps/backend/.env" | tail -1 | cut -d= -f2-; }
DB_URL="$(env_get COS_DATABASE_URL)"
REDIS_URL="$(env_get COS_REDIS_URL)"
PUBLIC_API="$(env_get COS_PUBLIC_API_BASE_URL)"
[[ "$PUBLIC_API" == "http://localhost:$API_PORT" ]] || fail "COS_PUBLIC_API_BASE_URL in apps/backend/.env must be http://localhost:$API_PORT (uploads go there)"
grep -q "BACKEND_URL=http://localhost:$API_PORT" "$ROOT/apps/web/.env.local" || fail "apps/web/.env.local must contain BACKEND_URL=http://localhost:$API_PORT"

(cd "$ROOT/apps/backend" && uv run python - "$DB_URL" "$REDIS_URL" <<'PY') || fail "PostgreSQL/Redis not reachable (see above). Start them (e.g. brew services start postgresql@14 redis)."
import sys, psycopg, redis
db, rd = sys.argv[1], sys.argv[2]
try:
    psycopg.connect(db.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3).close()
    print("  postgres ok")
except Exception as e:
    print(f"  postgres: {e}"); sys.exit(1)
try:
    redis.Redis.from_url(rd, socket_connect_timeout=3).ping()
    print("  redis ok")
except Exception as e:
    print(f"  redis: {e}"); sys.exit(1)
PY
ok "database and redis reachable"

for port in "$API_PORT" "$WEB_PORT"; do
  pid="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
  if [[ -n "$pid" ]]; then
    cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
    fail "port $port is in use by PID $pid ($(ps -o comm= -p "$pid")) in ${cwd:-?}. Stop it first (or set API_PORT/WEB_PORT)."
  fi
done
ok "ports $API_PORT (API) and $WEB_PORT (web) are free"

(cd "$ROOT/apps/backend" && uv run alembic upgrade head >/dev/null) || fail "migrations failed"
ok "database migrated"
(cd "$ROOT/apps/backend" && uv run python -m app.cli seed-plans >/dev/null) || fail "plan seeding failed"
ok "subscription plans seeded"

if [[ "$WEB_MODE" == "prod" ]]; then
  bold "Building web app (production)…"
  (cd "$ROOT/apps/web" && pnpm -s build >/dev/null) || fail "web build failed (run: pnpm --filter @commerce-os/web build)"
  ok "web built"
fi

# ---------------------------------------------------------------- run
# Everything runs in this script's process group; Ctrl+C (or any child dying) stops all of it.
trap 'trap - INT TERM EXIT; echo; bold "Stopping Nivaro…"; kill 0 2>/dev/null; wait 2>/dev/null' INT TERM EXIT
prefix() { awk -v p="$1" '{ print p " " $0; fflush() }'; }

(cd "$ROOT/apps/backend" && exec uv run uvicorn app.main:app --port "$API_PORT" --reload --reload-dir app) 2>&1 | prefix "$(printf '\033[34m[api]\033[0m')" &
(cd "$ROOT/apps/backend" && exec uv run celery -A app.worker.celery_app:celery worker -B --pool=solo \
  -Q default,outbox,ai,media --loglevel INFO --schedule "$ROOT/.data/celerybeat-schedule") 2>&1 | prefix "$(printf '\033[35m[worker]\033[0m')" &
if [[ "$WEB_MODE" == "prod" ]]; then
  (cd "$ROOT/apps/web" && exec node_modules/.bin/next start -p "$WEB_PORT") 2>&1 | prefix "$(printf '\033[36m[web]\033[0m')" &
else
  (cd "$ROOT/apps/web" && exec node_modules/.bin/next dev -p "$WEB_PORT") 2>&1 | prefix "$(printf '\033[36m[web]\033[0m')" &
fi

for _ in $(seq 1 90); do curl -sf -o /dev/null "http://localhost:$API_PORT/readyz" && break; sleep 1; done
curl -sf -o /dev/null "http://localhost:$API_PORT/readyz" || fail "API did not become ready on :$API_PORT"
for _ in $(seq 1 120); do curl -sf -o /dev/null "http://localhost:$WEB_PORT/" && break; sleep 1; done

echo
bold "Nivaro is running"
echo "  Website        http://localhost:$WEB_PORT"
echo "  Sign up        http://localhost:$WEB_PORT/register"
echo "  Seller app     http://localhost:$WEB_PORT/home"
echo "  API docs       http://localhost:$API_PORT/api/v1/docs"
echo "  Dev emails     $ROOT/.data/mailbox   (verification and invite links land here)"
echo "  Mobile app     scripts/mobile.sh   (in another terminal)"
echo "  Make admin     scripts/make-admin.sh you@example.com"
echo "  Stop           Ctrl+C"
echo
wait
