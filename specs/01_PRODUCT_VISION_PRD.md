# Product Vision & PRD

> v2 (2026-11-02): repositioned as an Autonomous Commerce OS (see 25_COMPETITIVE_POSITIONING_AND_USP.md).

> v3 (2026-11-02): the product is named **Nivaro** (26_NIVARO_BRAND_SYSTEM.md).

## Product
**Nivaro**: *Your store, on autopilot.*
Nivaro helps online sellers create, publish, sell, fulfill, support and optimize commerce from one place.
Create once. Sell everywhere. Let Nivaro handle the routine work.

## Category
**Autonomous Commerce OS**

## Core promise
**From product photo to delivered order — automatically.**

## USP
**Your store runs itself. You handle exceptions.**

## Vision
The operating system that runs an online and social-commerce seller's business: it captures and
publishes products, sells through conversations, takes and delivers orders, handles returns, and keeps
learning how to make the merchant more profitable. The merchant increasingly works on strategy:
product, sourcing, merchandising, relationships and growth. Repetitive operations are not their job.

## The seller experience we are building toward
The seller opens one app and sees **"Your store is running."**
- 27 orders handled overnight; 23 progressing normally
- 2 need stock confirmation · 1 exchange request · 1 refund approval
- Black XL may sell out in 5 days (3.2/day demand, 16 available)
- Yesterday's Reel generated 11 orders
- Two optimised creatives are prepared for today

Every line above must be computed from verified data, with evidence one tap away.

## Primary users
- **Seller-founder**: 1–5 staff, 50–2,000 SKUs, social DMs, spreadsheets, COD and couriers.
- **Ecommerce operator**: catalog, stock, messages, promotions, shipments, returns, reports.
- **Multi-store owner**: multiple stores, warehouses, users, permissions, analytics, APIs.
- **Operations staff**: clear queues for messages, packing, courier exceptions, returns, refunds.

## Jobs to be done
Operational (Commerce Core):
- turn photos into sellable content; publish once across channels; sync product, price and inventory
- auto-answer repetitive questions; turn chats into orders; collect and record payment
- create shipments; track delivery and COD settlement; handle returns, exchanges and refunds
- create images, Reels and premium AI video; re-engage customers; surface only exceptions

Intelligence (Intelligence Core):
- know true profit per product and order, not revenue alone
- know what will sell out, and when
- know which courier will actually deliver (and settle COD) on each route
- know which COD orders are risky, and why
- know why returns happen and how to prevent them
- know what content sells for *this* audience
- know which supplier is actually more profitable

## Product modes (merchant-controlled; see 06 §Autonomous Decision Policy)
- **Assisted**: AI prepares; the merchant approves.
- **Smart**: low-risk, high-confidence actions auto-run; important actions need approval.
- **Autopilot**: maximum automation within merchant policies, thresholds, budgets and platform rules.

## Operational learning loop
**OBSERVE → UNDERSTAND → DECIDE → ACT → MEASURE → LEARN → IMPROVE** (architecture: 03).

## Metrics
North star: **Automated order lifecycle completion rate**. These are eligible orders completed from
inquiry or order creation through delivery without merchant manual intervention.

Headline merchant-facing metric: **Commerce Autopilot Score** (definition: 14 §Autopilot Score).
It is never a vanity metric: an explicit denominator, exclusions and failure accounting are required.

Supporting:
- product upload → publish time; publish success
- AI customer resolution rate; chat-to-order conversion
- stock sync accuracy; fulfillment automation; return automation; exception rate
- recommendation acceptance rate and **measured impact**
- return-rate change after Return Insights; COD delivery success; courier first-attempt success
- content → order attribution
- merchant weekly active usage; GMV processed; provider cost as % of subscription revenue

## Principles for intelligence
1. **Structured, not opaque.** Intelligence is stored as structured facts, metrics and derived state.
   It is never LLM chat history. LLMs may phrase explanations; they never invent the facts.
2. **Explainable.** Every recommendation states what happened, why, the evidence, the confidence, the
   estimated impact and the recommended action (07 §Explanation Framework).
3. **Earned data first.** Intelligence features ship only after the operational phases produce
   trustworthy data (22 roadmap gating).
4. **Merchant control.** Risk classes and thresholds are merchant-set; high-risk actions always need
   approval (06).
5. **Profit over vanity.** Optimise expected contribution, not likes or raw revenue (14).
6. **Fair and private.** No opaque blacklists, no inference of protected attributes, network data only
   aggregated above minimum thresholds (15).

## Non-goals initially
- consumer marketplace; lending/banking
- proprietary frontier model training
- every global channel on day one; full enterprise ERP
- Network Intelligence before Phase 10 and legal/privacy review
