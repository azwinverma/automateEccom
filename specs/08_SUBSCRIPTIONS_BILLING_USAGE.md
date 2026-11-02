# Subscriptions, Billing, Usage & Entitlements

## Model
**Subscription + included usage + credits + add-ons + optional overage.**

## Entities
Plan, PlanVersion, Feature, Entitlement, PlanLimit, Subscription, SubscriptionItem,
UsageEvent, UsageAggregate, CreditWallet, CreditTransaction, OverageRule,
Invoice, PaymentMethod, Coupon, Trial, AddOn.

## Tiers
Starter — Create
Growth — Sell
Pro — Automate (hero plan)
Business — Scale
Enterprise — custom controls, SLA, SSO, BYOK.

## Metered resources
products, orders, channels, team members, AI text, AI inbox replies, images,
Auto Reels, premium video credits/seconds, storage, automation runs, API usage.

## Video
Separate:
- Auto Reel: lower-cost video assembled from seller media/templates.
- Premium AI Video: generative video, charged by credits based on duration,
  resolution, provider and model.

Use monthly quota + daily burst, not only per-day quota.

Example configurable limits:
Growth: 20 premium clips/month, max 4/day.
Pro: 60/month, max 10/day.
Business: 180/month, max 30/day.

## Entitlement service
check_feature → check_limit → reserve_usage → execute → finalize_usage.

Never hard-code plan names in business logic.

## Usage alerts
70%, 85%, 100%. At limit: block, overage, credit purchase or upgrade path.

## Gross-margin controls
Admin must show subscription revenue vs AI/media/storage/messaging/infra/support cost.
