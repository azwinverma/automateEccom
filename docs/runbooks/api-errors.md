# API errors & latency

**Alerts:** ApiHighErrorRate (5xx > 1% for 5 min), ApiHighLatency (p95 > 1 s), ApiDown, OpsGaugeErrors.

1. **Scope it.** Grafana *Service health* → "Requests / s by status" and "Slowest routes". One route or all?
2. **Find the errors.** Logs are JSON: filter `status>=500` and group by `error_code` and `route`; follow a
   `request_id`/`trace_id` into the trace (OTLP backend).
3. **Dependencies.** `GET /readyz` reports database and Redis. If Redis is down, rate limiting fails open
   (logins still protected by account lockout); if Postgres is down, everything 5xx's — check the managed
   database status and connection count.
4. **Recent change?** If errors started with a deploy, roll back (see [deploy-rollback](deploy-rollback.md)).
5. **Latency only.** Check the slow route's queries (database CPU, locks: `select * from pg_stat_activity
   where state <> 'idle'`), Celery backlog (`celery_queue_backlog`), and AI provider latency.
6. **OpsGaugeErrors.** A monitoring query keeps failing (`ops_collect_errors_total{gauge=…}`): the scrape
   still works; check the API logs for `ops_gauge_failed` and fix the query or the missing table.

**Done when:** 5xx < 1% and p95 < 1 s for 15 minutes; note the cause in the incident log.
