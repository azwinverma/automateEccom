# Outbox backlog & dead letters

**Alerts:** OutboxBacklog (>1,000 pending or oldest >5 min), OutboxDeadEvents, OutboxDispatcherStalled,
QueueBacklog, WorkerDown.

The outbox is how every side effect happens (notifications, workflows, intelligence refreshes, Twin
updates). Events retry with backoff; after `COS_OUTBOX_MAX_ATTEMPTS` they become `dead`.

1. `python -m app.cli ops-status` → `outbox_pending_events`, `outbox_oldest_pending_seconds`,
   `outbox_dead_events`, `celery_queue_backlog{…}`, `job_last_success_timestamp_seconds{job="dispatch_outbox"}`.
2. **Dispatcher stalled / WorkerDown:** beat or workers aren't running. Check the worker and beat processes
   (exactly one beat). Restart them; the backlog drains on its own (it's idempotent per handler).
3. **Backlog but dispatcher alive:** a slow handler. Grafana "Integration calls by outcome" and worker logs
   (`outbox_event_failed` with `event_type`). Scale workers if it's volume.
4. **Dead events:** list them — `GET /api/v1/admin/outbox?status=dead` (staff) or SQL
   `select event_type, count(*), max(last_error) from outbox_events where status='dead' group by 1`.
   Fix the cause first (bad payload, provider down, bug), then replay:
   ```
   python -m app.cli outbox-replay --event-type inbox.send_requested --dry-run
   python -m app.cli outbox-replay --event-type inbox.send_requested
   ```
   One event: `POST /api/v1/admin/outbox/{id}/retry`. Handlers are idempotent per (event, handler), so a
   replay never double-sends what already succeeded.
5. If a handler can never succeed (e.g. deleted merchant), leave it dead and record why.

**Done when:** pending < 100, oldest < 60 s, no new dead events for 30 minutes.
