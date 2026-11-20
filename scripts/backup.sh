#!/usr/bin/env bash
# Logical backup of a Nivaro database (specs/16 DR: daily logical backups next to managed PITR).
#
#   DATABASE_URL=postgresql://user:pass@host:5432/db scripts/backup.sh [backup_dir]
#
# Writes <dir>/nivaro-<db>-<UTC timestamp>.dump (pg_dump custom format, compressed) and a .sha256 next to
# it, then keeps the newest $KEEP (default 14) dumps. Exit code ≠ 0 on any failure — wire it to alerts.
# Production: run against a read replica; encrypt at rest (bucket SSE / KMS) and copy off-site.
set -euo pipefail

: "${DATABASE_URL:?set DATABASE_URL (postgresql://…)}"
DIR="${1:-./backups}"
KEEP="${KEEP:-14}"
URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"   # accept the app's SQLAlchemy URL too
DB="$(basename "${URL%%\?*}")"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DIR"
OUT="$DIR/nivaro-$DB-$TS.dump"

start=$(date +%s)
pg_dump --format=custom --compress=6 --no-owner --no-privileges --file="$OUT.partial" "$URL"
mv "$OUT.partial" "$OUT"
( cd "$DIR" && shasum -a 256 "$(basename "$OUT")" > "$(basename "$OUT").sha256" )
echo "backup ok: $OUT ($(du -h "$OUT" | cut -f1), $(( $(date +%s) - start ))s)"

# retention
ls -1t "$DIR"/nivaro-"$DB"-*.dump 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "$old" "$old.sha256"
done
