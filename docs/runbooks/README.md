# Runbooks

On-call guides for Nivaro. Every alert in `infra/observability/alerts.yml` links to one of these.
Commands run from `apps/backend` with the environment's `COS_*` settings (`uv run python -m app.cli …`;
in containers `python -m app.cli …`). Every write command is audited (actor `cli`).

| Runbook | Alerts |
|---|---|
| [API errors & latency](api-errors.md) | ApiHighErrorRate, ApiHighLatency, ApiDown, OpsGaugeErrors |
| [Outbox backlog & dead letters](outbox-dlq-replay.md) | OutboxBacklog, OutboxDeadEvents, OutboxDispatcherStalled, QueueBacklog, WorkerDown |
| [Webhook replay](webhook-replay.md) | WebhookSignatureFailures, WebhookProcessingLag, WebhookDeadEvents |
| [Provider outage](provider-outage.md) | AiFallbackRateHigh, AiCircuitOpen, AiCostAboveBudget, RefundErrors, CodSettlementOverdue, ShipmentsStuck, PublishingFailures |
| [Token expiry storm](token-expiry-storm.md) | ExpiredConnections, TokenExpiryStorm |
| [Intelligence recompute](intelligence-recompute.md) | NightlyIntelligenceMissed, IntelligenceJobFailing, ProductBrainStale, TwinSectionStale, TwinUpdateLagSlo |
| [Backup & restore drill](restore-drill.md) | (quarterly drill; backup job failures) |
| [Deploy & rollback](deploy-rollback.md) | (every release) |
| [Incident response](incident-response.md) | (any page) |

**First look, always:** `python -m app.cli ops-status` prints outbox, webhook, queue, freshness and job
heartbeat numbers in one go. Grafana: *Nivaro · Service health* and *Nivaro · Intelligence health*.

**Kill switches** (feature flags, `PUT /api/v1/admin/feature-flags/{key}` with `{"kill_switch": true}`,
staff with MFA; audited): `ops.automation`, `ops.sales_agent_replies`, `ops.content_publishing`,
`ops.intelligence_jobs`, `ops.campaigns` (retention campaigns stop sending; use it first if customers
complain about messages). A merchant override with `enabled=false` stops one shop only. Clearing the switch
resumes work where it stopped (workflow runs continue from their step; scheduled posts publish; campaigns
pick up the customers they hadn't reached).
