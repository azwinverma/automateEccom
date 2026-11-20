# Provider outage (AI, channel, courier, payment)

**Alerts:** AiFallbackRateHigh, AiCircuitOpen, AiCostAboveBudget, RefundErrors, CodSettlementOverdue,
ShipmentsStuck, PublishingFailures.

1. **Confirm it's the provider:** Grafana "Integration calls by outcome" / "AI requests" by provider; the
   provider's status page. Our circuit breakers open automatically (AI: per provider:model).
2. **AI:** fallbacks route to the next candidate model automatically. If all candidates fail, Studio jobs
   requeue and fail without charging; the Sales Agent escalates to a person. To stop AI replies entirely:
   kill switch `ops.sales_agent_replies`. Cost alert: check `ai_cost_usd_total` by task for a runaway loop;
   kill the feature's switch if needed.
3. **Channels:** publishing failures retry with backoff, then surface as exceptions to sellers. If a
   platform is down for long, set `ops.content_publishing` so posts stay scheduled instead of failing, and
   clear it afterwards (they publish then).
4. **Couriers:** bookings fail visibly on the order; sellers can use another courier or own rider.
   ShipmentsStuck usually means tracking polling fails — check `integration_calls_total{provider=…}`.
   CodSettlementOverdue: contact the courier with the statement list from Deliveries → Settlements.
5. **Payments/refunds:** RefundErrors — look at failed refunds (Returns → refund status) and the provider
   error; retry from the return once the provider recovers. Never re-issue a refund outside Nivaro (it
   would double-pay; refunds are capped at what was paid).
6. Tell affected sellers (status banner / message) when an outage lasts more than 30 minutes.

**Done when:** error rates back to baseline, circuits closed, stuck work drained.
