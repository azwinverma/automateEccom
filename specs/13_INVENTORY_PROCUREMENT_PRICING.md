# Inventory, Procurement, Pricing & Supplier Intelligence

> v1 (2026-11-02). The original 13 was never provided. Authored from the build brief and the strategy
> update; owner review required.

## Inventory (Phases 2–3)
- **Immutable ledger:** every change is an entry (receive, sale reserve/commit/release, adjust,
  transfer, count, damage, return-to-stock). Levels are derived: on_hand, reserved, available, damaged,
  incoming.
- **Locations:** multiple locations and warehouses; transfers; counts; reorder threshold.
- **Concurrency:** reservation is row-locked (or uses atomic conditional updates). Concurrency tests
  prove there is no oversell (as with the billing counters, ADR-005).
- **Channel sync:** sync to channels with inventory_sync capability. Safety stock per channel to
  absorb sync lag.

## Stockout risk (Phase 6)
`days_of_cover = available / demand_rate`
- `demand_rate` comes from Product Brain: EWMA of daily sales, adjusted for seasonality and in-stock
  days only. Stockout days are excluded so lost demand isn't undercounted.
- `StockoutRiskDetected` fires when `days_of_cover < lead_time_days + safety_days`.
- Explanation example: "Black XL may sell out in 5 days (3.2/day, 16 available; supplier lead time
  7 days)."

## Procurement (Phase 8)
- **Entities:** suppliers, supplier products, MOQ, lead time, purchase orders, approvals (Decision
  Policy thresholds), receiving and partial receiving, landed cost (purchase + freight + duty + other
  allocated), attachments.
- **AI suggestions:** reorder date, quantity, supplier and expected stockout. High-value POs always
  need approval.

## Supplier Intelligence (Phase 8)
**SupplierPerformanceMetric:**
- avg purchase price; landed cost
- defect rate (inspection); return rate attributable to the supplier's batches
- on-time rate; lead-time variance; stock reliability
- complaints
- **contribution per unit**

Recommendations use **true economics**:
`expected contribution per unit = price − landed cost − expected return/defect cost − fees − fulfillment`

Example: Supplier A has a lower purchase price but a higher return rate, so its actual contribution is
lower. Supplier B costs more but has fewer defects, so it is more profitable.

## Pricing
- Prices live in the catalog (paisa). Channel overrides go on listings.
- Price changes are R3 (approval) beyond the merchant's band (06).
- Profit-aware promotion is covered in 14 (expected contribution model).
- Price recommendations require: margin floor, competitor/market data only where legitimately
  available, demand elasticity estimated from the merchant's own promotion history, and a stated
  confidence.
