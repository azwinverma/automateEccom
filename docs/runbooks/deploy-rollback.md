# Deploy & rollback

Release order (infra/staging/README.md): migrate (one-off) → seed-plans → API → workers → beat → smoke.

**Before:** CI green (backend, web, mobile, security scans, image build); migrations are expand-only for
this release; feature flags ready for anything risky (default off, rollout %).

**Smoke after deploy:** `/readyz` 200 · log in · open Home · `outbox_pending_events` back near 0 within
2 minutes · no new 5xx in Grafana.

**Rollback:** redeploy the previous image tag (API, workers, beat). Migrations are additive-first
(expand → migrate → contract; destructive "contract" ships one release later), so the previous code runs
against the newer schema. Never `alembic downgrade` in production unless the migration notes say it's
safe and data-preserving.

**Feature rollback without a deploy:** feature flag rollout to 0% or kill switch (see README).
