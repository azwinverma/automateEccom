# Staging deployment

Status: **skeleton** — images build and push from CI; no hosting target is provisioned yet
(see `docs/KNOWN_GAPS.md` → GAP-INFRA-TARGET).

## Required topology (specs/03 "Initial production")
| Component | Requirement |
|---|---|
| API | ≥2 instances behind a load balancer, `/readyz` health check, TLS terminated at LB |
| Workers | ≥2 Celery workers (`-Q default,outbox`), separate media queue later |
| Scheduler | exactly 1 Celery beat |
| PostgreSQL | managed, PITR enabled, separate DB per environment |
| Redis | managed, persistence on (Celery broker + rate limits + circuit breaker) |
| Object storage | private bucket, SSE, `COS_STORAGE_BACKEND=s3` |
| Secrets | secret manager → env; `COS_KEK_PROVIDER=kms` in production |
| Telemetry | `COS_OTEL_EXPORTER_OTLP_ENDPOINT`, Prometheus scrape of `/metrics` on private network |

## Release order
1. `alembic upgrade head` as a one-off job (migrations must be backward compatible with the running version).
2. `python -m app.cli seed-plans` (idempotent; new plan content → new PlanVersion).
3. Roll API, then workers, then beat.
4. Smoke: `/readyz`, register/login against staging, outbox lag metric `outbox_pending_events` back to ~0.

## Rollback
Redeploy the previous image tag. Migrations are additive-first (expand → migrate → contract), so the
previous version keeps working against the newer schema. Destructive "contract" migrations ship one
release after the code that stopped using the column.
