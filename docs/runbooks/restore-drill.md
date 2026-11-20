# Backup & restore drill

**Targets (specs/16):** RPO ≤ 5 min (managed Postgres PITR), RTO ≤ 1 h; daily logical backups; quarterly
restore drills. Object storage has versioning (the compose MinIO bucket is created with it on).

## Daily logical backup
```
DATABASE_URL=postgresql://…/nivaro scripts/backup.sh /backups      # KEEP=14 newest kept
```
Custom-format `pg_dump` + `.sha256`. Run it from a scheduler against a read replica; copy the files to
off-site storage with encryption at rest. Alert on a non-zero exit.

## Quarterly drill (and before risky migrations)
```
SOURCE_URL=postgresql://…/nivaro scripts/restore-drill.sh /backups/nivaro-nivaro-<ts>.dump
```
It verifies the checksum, restores into `nivaro_restore_drill` (never the source), checks the Alembic
revision is head and `alembic check` finds no drift, compares key table row counts with the source,
checks inventory levels against the ledger, prints the restore time, then drops the scratch database
(`--keep` to inspect). Record the result and timing in the ops log.

Last local drill (2026-11-20, QA data): all checks passed, restore 1 s.

## Real restore (production incident)
1. Prefer PITR on the managed database to just before the incident; restore into a NEW instance.
2. Point a staging API at it, run smoke checks (`/readyz`, login, recent orders), then switch the
   production connection string and restart API, workers, beat.
3. Replay webhooks received after the restore point from the providers where possible (channel
   reconciliation imports orders missed); tell affected sellers what was restored.
