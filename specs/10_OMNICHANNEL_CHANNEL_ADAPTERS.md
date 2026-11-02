# Omnichannel Channel Adapters

> v1 (2026-11-02). The original 10 was never provided. Authored from the build brief and the
> implementation; owner review required.

## Principles
- Every platform is an adapter (`ChannelAdapter`) with **declared capabilities**:
  product_listing, inventory_sync, content_publish, messages, orders, returns, refunds, fulfillment.
- The UI and automation respect capabilities: they never assume a channel can do something.
- Official APIs only. No browser scraping as a core integration.
- Sandbox adapters exist for development and tests and are refused in production.

## Connection lifecycle (implemented)
- **OAuth:** single-use state bound to merchant + user + provider; tokens envelope-encrypted;
  proactive refresh. A credential rejection sets the connection to `expired`, emits an event and
  creates an exception.
- **API keys (WooCommerce):** verified with a live call before storing; a store whose currency
  differs from the merchant's is refused.
- **Health:** health checks, consecutive-failure tracking, `needs_reconnect`.
- **Disconnect:** crypto-shreds the credentials and removes store webhooks where possible.

## Webhook gateway (implemented)
receive → verify signature → record raw event → dedupe on (provider, event id) → respond fast →
queue → normalise → route to a domain handler → audit.

Per-connection secrets (WooCommerce) are supported. Failing handlers retry with backoff, then the
event is dead-lettered; staff can replay it. Unverified payloads are never stored.

## Listings (implemented, CAT-010)
- `channel_listings` reconciles desired versus actual state per product version.
- Updates are idempotent (no duplicate listings).
- A product change triggers a resync; archiving triggers an unpublish.
- After a reconnect, sync recovers automatically.
- A product deleted on the channel is reflected.

## Adapter status
| Channel | Status |
|---|---|
| Sandbox channel | Implemented (dev/test) |
| WooCommerce | **Implemented**, contract-tested; live verification pending |
| Meta (Instagram, Facebook, Messenger) | Blocked: Meta app + App Review |
| TikTok / TikTok Shop | Blocked: developer approval / eligibility |
| Shopify | Blocked: Partner app |
| WhatsApp Business | Blocked: BSP / approval |
| Own storefront | Planned |
| Marketplaces (e.g. Daraz) | Only where official seller APIs are available |

## Metrics ingestion (closed loop, Phase 7)
Adapters gain optional `fetch_content_metrics(external_ids, since)` and
`fetch_listing_metrics(...)` operations where the platform API provides insights. Metrics land in
CreativePerformanceMetric with source and attribution method. Missing capability means no metric,
never an estimate presented as fact.

## Reconciliation (CHN-012)
Periodic comparison of listings, stock and orders against provider state. Drift creates exceptions,
never silent overwrites.
