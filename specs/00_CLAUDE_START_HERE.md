# Claude Start Here

You are implementing a production-grade, multi-tenant AI Commerce OS.

## Mandatory implementation rules
- Keep domain modules separate even if deployed together.
- Every state-changing feature gets validation, permissions, tests and audit records.
- Build entitlements and usage metering into expensive features from day one.
- Use idempotency for payments, refunds, external webhooks, order imports, shipment creation and automation actions.
- Use a transactional outbox for durable side effects.
- Third-party platforms must be accessed through adapters.
- AI outputs that trigger actions must be schema-constrained and validated.
- Inventory, price, payment, shipment, order and refund facts must come from internal tools/services, never model memory.
- Store model/provider/cost/latency metadata for every AI execution.
- Provide graceful fallback when AI or channel providers fail.
- Use realistic incomplete/error/expired/partial states.
- Use realistic Nepal/social-commerce development fixtures.

## Never do
- Direct Claude/OpenAI/Gemini SDK calls throughout business code.
- `if plan == "PRO"` checks scattered across modules.
- Browser scraping as a core channel integration when official APIs exist.
- Raw AI keys in browser/mobile/logs.
- Long-running AI or publish jobs inside synchronous HTTP requests.
- A microservice per domain on day one.
- Fake testimonials, fake numbers or fake partner logos.
- Generic "AI SaaS template" UI.

## Suggested repository
apps/
  backend/
  web/
  mobile/
  worker/
packages/
  design-system/
  api-client/
  contracts/
infra/
docs/

## Backend domains
accounts, merchants, channels, catalog, media, content, customers, inbox,
orders, inventory, procurement, payments, fulfillment, returns, refunds,
marketing, automation, ai, analytics, billing, audit, support, common.

## Feature workflow
For every feature:
1. domain model/invariants
2. permissions/tenant boundary
3. API contract
4. service/use case
5. async/event logic
6. audit trail
7. tests
8. observability
9. UI states
10. entitlement/usage checks
11. documentation

A screen compiling is not Definition of Done.
