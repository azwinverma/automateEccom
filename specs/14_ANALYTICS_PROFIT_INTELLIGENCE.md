# Analytics & Profit Intelligence

> v1 (2026-11-02). The original 14 was never provided. Authored from the build brief and the strategy
> update; owner review required. Definitions here are normative: UI, Store Manager and marketing must
> use them.

## True profit (Phase 6)
```
Revenue
 − discounts
 − COGS (landed cost at time of sale)
 − payment fees
 − marketplace/channel fees
 − courier cost
 − delivery subsidy
 − packaging
 − returns (reverse shipping + unrecoverable value)
 − refunds
 − COD failure cost (outbound + return shipping + handling)
 − ad allocation (where ad spend is connected; else shown as "not included")
 = Contribution (profit before fixed costs)
```

- Product-level P&L follows the same waterfall with allocation rules shown.
- A component with **missing data is labelled "not included"**, never silently zero.
- Cost of goods uses the landed cost at the time of sale. If no cost is set, it shows "cost not set".

## Expected contribution model (profit-aware decisions)
For a product or action, over a horizon H:

```
E[contribution] = E[units] × (price − landed_cost − fees − fulfillment_cost)
                − E[returns] × return_cost
                − E[COD failures] × failure_cost
                − promotion_cost
```

| Input | Source |
|---|---|
| E[units] | Product Brain demand rate (seasonality-adjusted), capped by stock position |
| return rate, COD failure rate | Product Brain / COD Intelligence |
| promotion response | the merchant's own history; otherwise flagged as low confidence |

**Profitability thresholds (merchant policy):**
- minimum margin %
- minimum contribution per unit
- maximum return rate for promotion eligibility

**Rule:** high revenue with poor margin and high returns must **not** automatically trigger more
promotion. Recommendations rank by expected contribution, explain the trade-off, and allow merchant
overrides (recorded).

## Commerce Autopilot Score (APS, Phase 6; instrumentation from Phase 2/5)
A measure of **eligible operations automated successfully**, never a vanity metric.

**Capabilities:**
- customer replies
- order capture
- inventory sync
- shipment creation
- delivery notifications
- returns
- marketing
- content generation

New capabilities are added as they ship.

Per capability c and window W:
- **Eligible E_c:** operations of type c that occurred in W and *could* have been automated given the
  merchant's plan, channel capability and configuration.
- **Automated success A_c:** handled by automation/AI end-to-end, with no human intervention and a
  successful outcome (not reverted within the reversal window).
- **Automated failed F_c:** attempted automatically but failed, was reverted or escalated.
- **Manual M_c:** a human performed the operation.
- **Excluded X_c** (not in the denominator, reported separately), with a reason:
  - merchant-disabled automation
  - capability unavailable on the channel
  - not in the plan
  - policy requires approval (R3)

  High-risk approvals are excluded by design. They are not failures.

`score_c = A_c / E_c` (E_c = A_c + F_c + M_c)

Overall = Σ(w_c × score_c) / Σ w_c, with `w_c = E_c` (volume-weighted). Capabilities with
E_c < 10 in W are shown as "not enough activity", not as 0% or 100%.

**Report fields:** score, A, F, M, X with reasons, data completeness, window.

**Improvement recommendations:** the largest gap `E_c × (1 − score_c)` where a *config* change exists,
for example "Enable automatic low-value exchange approval to increase return automation". Each carries
an estimated coverage change computed from the last 30 days.

**Surfaces:** seller dashboard (Autopilot Control Center), Store Manager, analytics, and upsell where a
plan feature is the lever (08).

## Automation coverage & time saved
- Manual steps saved = A_c × steps_per_operation_c, using a documented constant table per capability.
- Hours saved = steps × median handling time per step. Medians are measured from manual operations
  where timestamps allow, otherwise documented constants marked "estimated".

## Intelligence analytics
| Area | Metrics |
|---|---|
| Stockout risk | products at risk, days of cover, lost-sales estimate (labelled estimate) |
| Courier intelligence | success / first-attempt / COD settlement by courier × route |
| COD risk | assessments by level, outcome by level (calibration), override rate |
| Return prevention | return rate by product/reason; insights raised; before/after per accepted recommendation |
| Content conversion | orders, inquiries and contribution per post; attribution method mix |
| Creative Genome | learned preferences with effect size, sample size and confidence |
| Supplier economics | contribution per unit by supplier |

## Recommendation impact
For each recommendation type: created, accepted, rejected (with reasons), executed, and the **measured
outcome** vs baseline.
- **Method:** pre/post with equal windows and seasonality adjustment. Where possible, a holdout
  (products not acted on) gives difference-in-differences.
- Results are reported with confidence intervals and never as guaranteed causal effects.

## Simulation (Phase 9)
What-if inputs: discount %, purchase quantity, ad budget shift.

Outputs:
- margin impact
- expected demand (with range)
- inventory duration
- contribution
- stockout probability
- return impact

Rules:
- Every assumption is listed. Confidence and ranges are shown.
- Outputs are labelled "estimate".
- No action is taken without a separate approval.

## Commerce analytics (Phases 2–5)
sales; channel; product; stock; returns; payment; fulfillment; customer cohorts; AI and automation
usage; attribution extension.
