# Orders, Payments, COD, Fulfillment & Returns (+ COD / Courier / Return Intelligence)

> v1 (2026-11-02). The original 12 was never provided. Authored from the build brief and the strategy
> update; owner review required. Operational flows ship in Phases 2–4; intelligence engines in Phase 6.

## Orders (Phase 2)
- **Sources:** AI conversation, seller entry, storefront, marketplace and API all normalise to one
  `Order`.
- **State machine (no arbitrary status writes):**
  draft → pending_confirmation → confirmed → (payment_pending | cod_pending) → ready_to_ship → shipped
  → delivered → completed.
  Branches: cancelled, partially_cancelled, delivery_failed, returned.
- **Snapshots and idempotency:** line and totals snapshots (price, SKU, title, tax, discount, delivery
  fee) are kept. External imports are idempotent on (channel, external_order_id).
- **Timeline:** actor, time, event, source, automated/manual, related provider.
- **Reservation:** at the configured stage; concurrency-safe (no oversell); released on cancel/expiry.

## Payments & COD (Phases 2–3)
- **Provider interface:** create_payment, verify_payment, capture, refund, get_status. A client
  redirect is never trusted; verification is server-side or by webhook. Refunds are idempotent and
  provider-tracked.
- **COD subsystem states:** requested → approved → handed_to_courier → delivered → cash_collected →
  settlement_pending → settled. Also failed_delivery and returned_to_origin.
- **COD dashboard:** outstanding, collected, pending settlement, settled, failed delivery, return
  exposure.

## COD Intelligence Engine (Phase 6)
Output per COD order: `CODRiskAssessment`.
- **level:** LOW / MEDIUM / HIGHER DELIVERY RISK
- score
- factors[] with contribution and evidence
- **recommended_action:** `cod_ok`, `verify_phone`, `request_partial_advance`, `manual_review`

**Allowed inputs** (operational and merchant-specific only):
- customer's own delivery history with this merchant (successful/failed)
- address completeness and validity
- phone verification status
- order value relative to merchant norms
- new vs repeat customer
- destination route performance (Courier Brain)
- product category return/failed-delivery rates
- the customer's prior return history with this merchant

**Prohibited:**
- name-, gender-, religion-, caste- or ethnicity-derived features
- inference of any protected or sensitive attribute
- cross-merchant personal blacklists (Network Intelligence uses route/category aggregates only,
  never person-level data)

**Controls:**
- explainable factors shown to the merchant
- merchant override with reason (audited)
- customer dispute/correction path via the merchant
- every assessment logged
- outcomes (delivered/failed) recorded for calibration
- periodic fairness review: disparity checks by region

**Decision Policy:** auto-accept LOW; MEDIUM follows merchant policy (e.g. verify phone); HIGHER always
goes to manual review or an advance request. Never an automatic silent rejection.

## Fulfillment & couriers (Phase 3)
- **Courier adapters:** rates, shipment creation, label, pickup, tracking, cancellation, delivery
  events, COD settlement reports.
- **Failed delivery automation:** detect → message the customer where permitted → collect a corrected
  address/time → request reattempt → update → escalate.

## Courier Brain (Phase 6)
**CourierPerformanceMetric** per courier × route (origin district → destination district) × weight
band × COD flag:
- price; ETA p50/p90
- delivery success; first-attempt success; failed-delivery rate
- COD settlement delay; loss/damage rate
- sample size

**Selection modes:**
- **cheapest:** lowest price meeting minimum success
- **fastest:** lowest ETA p50
- **smart:** maximises expected contribution, i.e. price + failure cost (return shipping, re-delivery,
  lost margin) weighted by success probability, settlement delay and merchant preference
- **preferred only**

**Explainability:** "Courier B selected because it has 97% successful COD delivery on Kathmandu →
Biratnagar (n=212, last 90 days) at Rs 20 more than the cheapest."

**Cold start:** with too little data on a route, fall back to merchant preference or rules (and later
the network prior), and say so.

## Returns, exchanges & refunds (Phase 4)
- **Policy engine:** delivery date, return window, product, reason, condition, final-sale rules,
  merchant policy.
- **Flow:** REQUESTED → ELIGIBILITY → APPROVAL → REVERSE SHIPMENT → RECEIVED → INSPECTION →
  REFUND/EXCHANGE → CLOSED.
- **Exchanges** reserve replacement stock. **Refunds** are idempotent, auditable, threshold-controlled
  and provider-tracked; auto-refund only under merchant policy.
- **Reason vocabulary (controlled, plus free text):** size_small, size_large, colour_different,
  quality_defect, damaged_in_transit, not_as_described, changed_mind, late_delivery, wrong_item, other.

## Return Intelligence (Phase 6)
**Tracks:**
- reason by product/variant/size
- the image/content version shown at purchase
- customer segment; supplier; delivery condition; campaign

**Detection:** a ReturnInsight is raised when a reason share or return rate exceeds the baseline, with
a minimum sample and significance (e.g. "61% of Product X returns are 'fit small' (n=33, 60 days)").

**Recommendations (typed actions):**
- update the size guide; add a fit warning
- edit the description; replace an image
- stop a misleading creative
- suggest one size up in the Sales Agent
- flag a supplier quality issue

**Impact:** baseline vs post-change return rate over an equal window, with the measurement method
shown (RecommendationOutcome).
