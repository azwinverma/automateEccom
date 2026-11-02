# Automation Engine & Autonomous Decision Policy

> v1 (2026-11-02). The original 06 was never provided. Authored from the feature catalog, the build
> briefs and the strategy update; owner review required. Phase 5 builds the engine. Profit-aware and
> intelligence-derived parts arrive with Phase 6.

## Model
`TRIGGER → CONDITIONS → ACTIONS → WAIT → BRANCH → APPROVAL → NEXT ACTION`

- **Workflow / WorkflowVersion.** Versions are immutable; edits create a new version; runs pin the
  version they started with.
- **Triggers:**
  - domain events (order.created, shipment.delivery_failed, inventory.low, channels.connection_expired…)
  - schedules
  - **intelligence-derived triggers** (Phase 6+): `StockoutRiskDetected`, `ReturnPatternDetected`,
    `CODRiskAssessed(level≥MEDIUM)`, `RecommendationCreated(type=…)`
- **Conditions:** typed predicates over the trigger payload plus **context providers**:
  - Commerce Core reads (authoritative)
  - Digital Store Twin sections (with max-staleness)
  - Commerce Memory facts and metrics
  - **profit-aware conditions** (Phase 6): `expected_contribution_per_unit > X`, `margin_pct > Y`,
    `return_rate_30d < Z`
- **Actions:** typed Commerce Core commands (reserve stock, confirm order, create shipment, send
  message, publish content, issue refund, create PO draft, apply discount, change price…). Each action
  declares its risk class, financial-impact function, required entitlement and channel capability.
- **Wait / Branch / Approval / Retry / Pause / Dry-run / Templates / Logs.** Every step is recorded in
  WorkflowStepRun and AutomationActionLog.

## Commerce-specific templates (examples)
- **New order, safe COD:** order created → IF COD and COD risk acceptable → reserve stock → confirm
  → create shipment → notify customer.
- **Review request:** delivered → WAIT 3 days → request review.
- **Low stock:** inventory low → notify seller, or create a recommended PO draft.
- **Channel expired:** channel expired → pause affected workflows → notify the merchant (Exception Inbox).
- **Failed delivery:** delivery failed → message customer (where permitted) → collect corrected
  address/time → request reattempt → escalate after N attempts.

## Autonomous Decision Policy
Every automated action (workflow step or accepted recommendation) is evaluated by one policy function:

```
decide(action, context) → AUTO_EXECUTE | REQUIRE_APPROVAL | BLOCK
inputs: risk_class(action), financial_impact(action), confidence(decision),
        merchant.automation_mode, entitlements, merchant thresholds,
        channel/provider capability, data freshness (Twin/Memory as_of)
```

### Risk classes
| Class | Examples | Default |
|---|---|---|
| R0 Informational | notify seller, tag conversation | auto |
| R1 Low | send templated status message, create shipment for a paid order, inventory sync | auto in Smart/Autopilot |
| R2 Medium | auto-approve a low-value exchange, reschedule a delivery, publish AI content, small discount | auto only if the merchant enabled it **and** confidence ≥ threshold |
| R3 High | refund above threshold, price change beyond band, PO above threshold, campaign budget increase, stock transfer above threshold | always requires approval |
| R4 Prohibited | anything violating platform rules or missing entitlement/capability | blocked |

### Rule table (default; merchant-overridable within bounds)
| Mode | R0 | R1 | R2 | R3 |
|---|---|---|---|---|
| Assisted | auto | approval | approval | approval |
| Smart | auto | auto (confidence ≥ 0.8) | approval unless enabled | approval |
| Autopilot | auto | auto | auto if enabled and confidence ≥ threshold | approval |

### Merchant thresholds (DecisionPolicy / RiskThreshold)
Refund amount; discount % and absolute; PO value; campaign budget per day; stock transfer quantity
or value; price change % band; COD order value requiring verification. Thresholds are audited.
Lowering a safety threshold requires `automation.approve` and is logged as a high-risk settings change.

### Safety rules
- **Stale data.** No auto-execution when the required Twin/Memory section is older than the action's
  max staleness. Fall back to approval.
- **Missing data.** Missing data is never treated as a pass: low data-completeness lowers confidence.
- **Facts at execution time.** Price, stock and payment facts are re-read from Commerce Core at
  execution time.
- **Idempotency.** Every action execution carries `workflow_run_id + step_id` (or `recommendation_id`)
  as its idempotency key.
- **Circuit breaker.** Repeated failures of an action type pause that automation for the merchant and
  raise an exception.

## Recommendation → approval → action
1. The recommendation engine creates a `Recommendation` with evidence, confidence, estimated impact
   and a typed `recommended_action`.
2. The Decision Policy classifies it. AUTO_EXECUTE runs it, and the seller is informed in the
   Autopilot feed. REQUIRE_APPROVAL puts it in **Needs Your Attention**.
3. Accept or reject is recorded with the actor. Execution goes through the same idempotent command
   path as workflows.
4. A `RecommendationOutcome` is measured after the evaluation window. It feeds learning and
   recommendation-impact analytics.

## Explainable decisions
Every automated decision stores a decision record:
- inputs (references, not copies)
- policy rule hit
- confidence
- risk class
- financial impact
- outcome

Seller-facing copy follows the Explanation Framework (07). Example: "Auto-approved because the
exchange is under your Rs 1,500 limit and the item is in stock (12 available)."

## Autopilot Score instrumentation
AutomationActionLog records, for every eligible operational action:
- capability
- whether it was eligible for automation
- performed by (automation / ai / user / system)
- outcome (success, failed, reverted)
- whether a human intervened
- exclusion reason

This is the APS denominator and numerator source (14).
