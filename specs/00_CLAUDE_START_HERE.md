# Claude Start Here

You are implementing a production-grade, multi-tenant **Autonomous Commerce OS**.
Promise: **From product photo to delivered order — automatically.**
USP: **Your store runs itself. You handle exceptions.** (25_COMPETITIVE_POSITIONING_AND_USP.md)

## Mandatory implementation rules
- Keep domain modules separate even if deployed together.
- Every state-changing feature gets validation, permissions, tests and audit records.
- Every operational action records **who or what performed it** (user, automation, ai, system) and its
  outcome. This feeds the Autopilot Score and recommendation outcome tracking.
- Build entitlements and usage metering into expensive features from day one.
- Use idempotency for payments, refunds, external webhooks, order imports, shipment creation,
  automation actions and execution of accepted recommendations.
- Use a transactional outbox for durable side effects.
- Third-party platforms must be accessed through adapters.
- AI outputs that trigger actions must be schema-constrained and validated.
- Inventory, price, payment, shipment, order and refund facts must come from internal tools/services,
  never model memory, and never from the derived Intelligence Core at execution time.
- Store model/provider/cost/latency metadata for every AI execution.
- Provide graceful fallback when AI or channel providers fail.
- Use realistic incomplete/error/expired/partial states.
- Use realistic Nepal/social-commerce development fixtures.

## Intelligence rules
- Intelligence is **structured data and derived metrics**, never opaque LLM memory or chat history.
- Every recommendation follows the Explanation Framework: what happened, why, evidence, confidence,
  impact, recommended action (07).
- Every automated decision passes the Autonomous Decision Policy (06).
- Build intelligence only on trustworthy operational data. Follow the phase gating in 22.
- Optimise for profit (expected contribution), not engagement or revenue alone (14).

## Never do
- Direct Claude/OpenAI/Gemini SDK calls throughout business code.
- `if plan == "PRO"` checks scattered across modules.
- Browser scraping as a core channel integration when official APIs exist.
- Raw AI keys in browser/mobile/logs.
- Long-running AI or publish jobs inside synchronous HTTP requests.
- A microservice per domain on day one.
- Fake testimonials, fake numbers or fake partner logos.
- Generic "AI SaaS template" UI, AI sparkles, or a chat bubble as the primary UX.
- Opaque blacklists, or inference of protected/sensitive attributes (COD risk included).
- Cross-merchant data exposure; Network Intelligence only via thresholded aggregates (15).
- Building Phase 6+ intelligence before the operational phases produce the data it needs.

## Repository
```
apps/{backend,web,mobile}   packages/{design-system,api-client,contracts}
infra/   docs/   specs/  (this specification set)
```

## Backend domains
Commerce Core: accounts, merchants, channels, catalog, media, content, studio, customers, inbox,
orders, inventory, procurement, payments, fulfillment, returns, marketing, automation, ai, analytics,
billing, audit, support, exceptions, platform.
Intelligence Core: productbrain, memory, twin, autopilot, recommendations, intelligence/*, simulation,
network.

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

For intelligence features, also:

12. evidence, confidence, outcome tracking
13. offline evaluation

A screen compiling is not Definition of Done.
