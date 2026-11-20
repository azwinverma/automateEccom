#!/usr/bin/env bash
# Restore drill (specs/16 DR: quarterly restore drills; RTO target ≤ 1h).
#
#   SOURCE_URL=postgresql://…/db [DRILL_DB=nivaro_restore_drill] scripts/restore-drill.sh <dump file> [--keep]
#
# 1. verifies the dump's checksum, 2. restores it into a scratch database (never the source),
# 3. checks the Alembic revision equals the code's head and `alembic check` finds no drift,
# 4. compares row counts of key tables with the source (when SOURCE_URL is given),
# 5. checks ledger/level consistency, 6. prints the measured restore time, then drops the scratch DB
#    unless --keep. Exit code ≠ 0 on any failed check.
set -euo pipefail

DUMP="${1:?usage: restore-drill.sh <dump> [--keep]}"
KEEP="${2:-}"
DRILL_DB="${DRILL_DB:-nivaro_restore_drill}"
PGHOST_URL="${PGHOST_URL:-postgresql://localhost:5432}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${SOURCE_URL:-}"; SRC="${SRC/postgresql+psycopg:/postgresql:}"

[[ "$DRILL_DB" == nivaro_restore_* ]] || { echo "DRILL_DB must start with nivaro_restore_ (safety)"; exit 2; }
if [[ -n "$SRC" && "$(basename "${SRC%%\?*}")" == "$DRILL_DB" ]]; then echo "refusing: drill DB = source"; exit 2; fi

( cd "$(dirname "$DUMP")" && shasum -a 256 -c "$(basename "$DUMP").sha256" ) || { echo "CHECKSUM FAILED"; exit 1; }

start=$(date +%s)
psql "$PGHOST_URL/postgres" -qc "DROP DATABASE IF EXISTS $DRILL_DB WITH (FORCE)" -c "CREATE DATABASE $DRILL_DB"
pg_restore --no-owner --no-privileges --exit-on-error --jobs=4 --dbname="$PGHOST_URL/$DRILL_DB" "$DUMP"
restored=$(date +%s)

fail=0
cd "$ROOT/apps/backend"
export COS_DATABASE_URL="postgresql+psycopg://${PGHOST_URL#postgresql://}/$DRILL_DB"
head_rev=$(uv run alembic heads 2>/dev/null | awk '{print $1}' | head -1)
cur_rev=$(psql "$PGHOST_URL/$DRILL_DB" -Atc "select version_num from alembic_version")
if [[ "$head_rev" == "$cur_rev" ]]; then echo "ok   alembic revision $cur_rev = head"; else echo "FAIL alembic revision $cur_rev ≠ head $head_rev"; fail=1; fi
if uv run alembic check >/dev/null 2>&1; then echo "ok   schema matches the models (alembic check)"; else echo "FAIL alembic check reports drift"; fail=1; fi

TABLES="merchants users orders order_lines inventory_ledger inventory_levels payments refunds return_requests shipments outbox_events audit_logs decision_records recommendations purchase_orders"
for t in $TABLES; do
  got=$(psql "$PGHOST_URL/$DRILL_DB" -Atc "select count(*) from $t" 2>/dev/null || echo "missing")
  if [[ -n "$SRC" ]]; then
    want=$(psql "$SRC" -Atc "select count(*) from $t" 2>/dev/null || echo "missing")
    if [[ "$got" == "$want" ]]; then echo "ok   $t $got rows"; else echo "WARN $t restored $got vs source now $want (source changed since the dump?)"; fi
  else
    echo "info $t $got rows"
  fi
done

# Inventory invariant: each level's on_hand equals the latest ledger on_hand_after for it.
bad=$(psql "$PGHOST_URL/$DRILL_DB" -Atc "
  with last as (
    select distinct on (variant_id, location_id) variant_id, location_id, on_hand_after
    from inventory_ledger order by variant_id, location_id, created_at desc, id desc)
  select count(*) from inventory_levels l join last using (variant_id, location_id)
  where l.on_hand <> last.on_hand_after")
if [[ "$bad" == "0" ]]; then echo "ok   inventory levels match the ledger"; else echo "FAIL $bad inventory levels differ from the ledger"; fail=1; fi

echo "restore time: $(( restored - start ))s (target RTO ≤ 3600s)"
if [[ "$KEEP" != "--keep" ]]; then psql "$PGHOST_URL/postgres" -qc "DROP DATABASE IF EXISTS $DRILL_DB WITH (FORCE)"; fi
[[ $fail == 0 ]] && echo "RESTORE DRILL PASSED" || { echo "RESTORE DRILL FAILED"; exit 1; }
