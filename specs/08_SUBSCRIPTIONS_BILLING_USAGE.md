# Subscriptions, Billing, Usage & Entitlements

> v2 (2026-11-02): adds intelligence entitlements and Autopilot-aware upgrade paths.

## Model
**Subscription + included usage + credits + add-ons + optional overage** (implemented: ADR-005).

## Entities
Plan, PlanVersion, Feature, Entitlement, PlanLimit, Subscription, SubscriptionItem, UsageEvent,
UsageAggregate, CreditWallet, CreditTransaction, OverageRule, Invoice, PaymentMethod, Coupon, Trial,
AddOn.

## Tiers
- Starter: Create
- Growth: Sell
- Pro: Automate (hero plan)
- Business: Scale
- Enterprise: custom controls, SLA, SSO, BYOK

## Intelligence entitlements (feature codes; values per plan set in data, not code)
| Feature code | Capability | Indicative tier |
|---|---|---|
| `autopilot.score` | Autopilot Score + breakdown | all plans (visibility drives adoption) |
| `autopilot.improvements` | Coverage improvement recommendations | Growth+ |
| `intelligence.product_brain` | Product Brain profiles | Growth+ |
| `intelligence.profit` | Profit-aware recommendations, product P&L | Pro+ |
| `intelligence.returns` | Return Intelligence | Pro+ |
| `intelligence.courier` | Courier Brain (smart mode) | Pro+ |
| `intelligence.cod` | COD Intelligence | Pro+ |
| `intelligence.creative_genome` | Creative Genome + closed-loop content | Pro+ |
| `intelligence.supplier` | Supplier Intelligence | Business+ |
| `intelligence.simulation` | What-if simulation | Business+ |
| `ai.store_manager` | AI Store Manager (existing code) | Pro+ |
| `network.insights` | Network Intelligence (opt-in, Phase 10) | TBD after legal review |

Tier mapping is **indicative** pending GTM (21). It ships in `feature-entitlements.example.json`
(provisional).

## Metered resources
products, orders, channels, team members, AI text, AI inbox replies, images, Auto Reels, premium video
credits/seconds, storage, automation runs, API usage, **Store Manager questions** and **simulation runs**
(Phase 6/9; metered because they are AI- and compute-heavy).

## Video
Kept separate:
- **Auto Reel:** a lower-cost video assembled from seller media and templates.
- **Premium AI Video:** generative video, charged by credits based on duration, resolution, provider
  and model.

Use monthly quota + daily burst, not only per-day quota.

Example configurable limits:
| Plan | Premium clips / month | Max / day |
|---|---|---|
| Growth | 20 | 4 |
| Pro | 60 | 10 |
| Business | 180 | 30 |

## Entitlement service
check_feature → check_limit → reserve_usage → execute → finalize_usage. Plan names are never
hard-coded in business logic.

## Usage alerts
At 70%, 85% and 100%. At the limit: block, overage, credit purchase or an upgrade path.

## Autopilot-aware upgrade suggestions
Upsell is tied to measurable automation value, never to vague AI claims.
- Example: "Return automation is 72%. Auto-approving low-value exchanges (Pro) would raise it to an
  estimated 88%."
- The estimate comes from the merchant's own AutomationActionLog over the last 30 days, shows its
  assumptions, and is presented once per period (no nagging).
- Suggestions are Recommendations (type `plan_upgrade`) with evidence and are tracked for outcome.

## Gross-margin controls
Admin shows subscription revenue against AI, media, storage, messaging, infra and support cost. It
adds **intelligence compute cost** per merchant (intelligence jobs, Store Manager, simulations).
