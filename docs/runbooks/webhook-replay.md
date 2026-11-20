# Webhook replay

**Alerts:** WebhookSignatureFailures, WebhookProcessingLag (>2 min), WebhookDeadEvents.

Webhooks are stored raw before processing (zero-loss SLO), then processed via the outbox.

1. **Signature failures:** `integration_calls_total{operation="webhook",outcome="bad_signature"}` by
   provider. A burst right after a secret rotation means the stored secret is stale → update the channel
   connection's webhook secret (WooCommerce: per store) or the provider's env secret. A burst with no
   change can be probing: confirm the source IPs and that nothing was processed (bad signatures are
   rejected before storage).
2. **Lag:** `webhook_oldest_unprocessed_seconds`. Usually the outbox backlog — see
   [outbox-dlq-replay](outbox-dlq-replay.md).
3. **Dead webhooks:** fix the cause (often a mapping bug for a new provider event), then:
   ```
   python -m app.cli webhook-replay --status dead --provider woocommerce --dry-run
   python -m app.cli webhook-replay --status dead --provider woocommerce
   ```
   Processing is deduplicated by provider event id, so replays are safe.
4. **Missed webhooks** (provider outage on their side): channel reconciliation runs every 6 h and imports
   anything missed; trigger it sooner for one connection with "Check" on the Channels screen (or `POST /api/v1/channels/{id}/reconcile`).

**Done when:** no unprocessed webhook older than 60 s and no new dead events.
