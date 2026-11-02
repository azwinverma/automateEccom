# Complete Feature Catalog

> v2 (2026-11-02): adds the Intelligence Core and Autopilot surfaces. Phase per feature: 22_PHASED_ROADMAP.md.

## COMMERCE CORE

### Identity / tenancy
phone/email login; MFA; merchant organizations; multiple stores/brands; warehouses; team invitations;
RBAC; sessions; API keys; enterprise SSO; audit.

### Channel connections
Meta/Instagram; Facebook Pages; TikTok; TikTok Shop where supported; Shopify; WooCommerce; own
storefront; marketplaces where official access exists; WhatsApp Business where supported; OAuth and
API-key connections; token refresh; webhooks; capability matrix; channel performance ingestion
(content metrics, listing views where the API provides them).

### Universal catalog
products; variants; options; categories; bundles; SKU/barcode; costs; prices; dimensions/weight;
attributes with provenance; SEO; multilingual copy; supplier data; channel mapping;
draft/active/archived lifecycle.

### Product Brain *(Commerce Core ↔ Intelligence Core bridge)*
One structured intelligence profile per product. It covers:
- identity, category, media, variants, stock, cost, price and margin
- listings, content and campaign history
- customer questions and FAQs; sales performance and segments
- returns and complaints; reviews; content performance
- stockouts, seasonality and promotion response
- AI recommendations

All agents read product context from here (specs/04 §Product Brain).

### AI Product Studio
capture/upload; bulk media; quality scoring; background removal; resize/crop; AI lifestyle imagery;
attribute extraction; titles; descriptions; SEO; captions; hashtags; translation; channel-specific
copy; confidence review; brand voice; grounding check for commercial claims.

### AI Video Studio
Auto Reels from seller media; generative product clips; showcases; lifestyle; UGC-style concepts;
stories; restock/sale videos; subtitles; logo/price/CTA; 1:1, 4:5, 9:16, 16:9; plan limits; credits;
routing; retries; fidelity checks; templates informed by the Creative Genome (Phase 7).

### Content / publishing
calendar; AI schedules; campaigns; publish now/later; per-channel creatives; approval; autopublish;
retry; rate limit handling; **closed-loop measurement** (views, engagement, clicks, inquiries, orders,
attributed revenue and profit).

### Unified inbox
supported channels; assignment; labels; SLA; AI summary; intent classification; suggested/automatic
replies; escalation; product cards; order status; returns; FAQ mining into Product Brain.

### AI Sales Agent
product Q&A from Product Brain; stock/variant/price checks via tools; delivery estimate; promotions;
order capture; addresses; payment; upsell/cross-sell; language detect.

### CRM
customer graph; addresses; channel identities; order, payment, return and message history; preferences
(sizes, colors, categories); LTV; segmentation; consent; duplicate merge.

### Orders
draft; imported; chat-created; storefront/API; edits; discounts; delivery fees; status machine;
reservation; split fulfillment; partial cancellation/refund; timeline.

### Inventory
on hand; available; reserved; damaged; incoming; multi-location; transfers; adjustments; counts;
reorder; channel sync; oversell protection; immutable ledger; **stockout risk** (days of cover).

### Procurement
suppliers; supplier SKU; PO; receiving; landed cost; lead time; reorder AI; **Supplier Intelligence**
(true economics: landed cost, defects, returns, delays, contribution).

### Payments / COD
provider adapters; payment links; verification; partial payment; refunds; reconciliation;
COD validation, exposure and settlement; **COD Intelligence Engine** (explainable delivery-risk
assessment with recommended action, merchant review, dispute).

### Fulfillment
packing; labels; rate lookup; pickup; tracking; failed delivery recovery; notifications; multiple
courier adapters; reconciliation; **Courier Brain** (route-level learning; modes cheapest / fastest /
smart / preferred only; explainable selection).

### Returns / exchanges / refunds
policy engine; reason/evidence; reverse shipment; inspection; replacement reservation; refund
calculation; partial refund; auto-refund thresholds; audit; abuse signals; **Return Intelligence**
(pattern detection, prevention recommendations, before/after impact).

## INTELLIGENCE CORE
| Feature | Summary | Spec |
|---|---|---|
| Commerce Memory | Merchant-scoped structured operational knowledge: facts and metrics about products, customers, content, logistics and operations. Explainable, auditable, versioned. | 04, 14 |
| Digital Store Twin | Derived, read-optimised live business state for the Store Manager, automation, recommendations and simulation. Transactional systems stay authoritative. | 03, 04 |
| Profit Intelligence | True profit, product P&L, expected contribution model. | 14 |
| Creative Genome | Per-merchant learned content patterns that steer generation and scheduling. | 09 |
| COD / Courier / Return / Supplier Intelligence | Domain learning engines. | 12, 13 |
| Recommendations + Explanation Framework | Evidence-backed recommendations with outcome tracking. | 07, 14 |
| Simulation (what-if) | Estimates with assumptions and confidence; never auto-executes. | 14 |
| Merchant Network Intelligence | Aggregated, anonymised, threshold-protected cross-merchant signals (late phase). | 15 |

## AUTOMATION & AUTOPILOT
### Automation engine
triggers (including intelligence-derived triggers); conditions (including profit-aware conditions);
actions; delays; branches; schedules; versions; templates; dry-run; approvals; retry; pause;
exception inbox; seller workflow builder.

### Autonomous Decision Policy
risk classes; financial impact; confidence; automation mode; entitlements; merchant thresholds for
refunds, discounts, POs, campaign budgets, stock transfers and price changes (06).

### Commerce Autopilot Score
coverage of eligible operations automated successfully, with a breakdown and improvement
recommendations (14).

### Autopilot Control Center *(signature home)*
"Your store is running." Shows orders processed, revenue, AI-handled messages, shipments, returns
resolved, content published, Autopilot Score and active exceptions, with **Needs Your Attention** (18).

### Exception Inbox
payment mismatch; low-confidence AI; refund above threshold; courier failed; expired channel;
inventory mismatch; failed publishing; ambiguous variant; customer escalation; provider failure;
stockout risk; high-risk COD.

## Marketing / retention
campaigns; segments; abandoned checkout; reviews; win-back; restock; price drop; new arrivals; content
autopilot; ad creative; ad integration extension points; profit-aware promotion selection.

## Analytics
sales; channel; product; stock; returns; payment; fulfillment; customer; AI; automation; true profit;
product P&L; cohorts; attribution; Autopilot Score; recommendation impact; hours saved.

## AI Store Manager
An operational intelligence layer over Product Brain, Commerce Memory, Store Twin and the engines.
Answers business questions with tools, evidence and confidence; proposes approval-gated actions; runs
what-if simulations (later phase). Not a generic chat bubble.

## Subscription
plans; versions; features; quotas; credits; overage; add-ons; trials; annual/monthly;
upgrade/downgrade; dunning; invoices; BYOK; gross-margin monitoring; Autopilot-coverage-aware
upgrade suggestions.

## Admin / operations
merchant health; entitlements; usage; provider health; channel health; webhooks; DLQ; retries;
refunds; support; feature flags; plan editor; routing editor; intelligence job health
(staleness, failures, drift).
