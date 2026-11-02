# Domain Data Model

> v1 (2026-11-02). The original 04 was never provided. This version was authored from the implemented
> schema (migrations 0001–0009) plus planned entities. Owner review required. Authoritative schema:
> `apps/backend/migrations/`.

## Conventions (all tables)
- UUIDv7 primary keys; `created_at`/`updated_at` timestamptz (UTC).
- Every merchant-owned table has `merchant_id NOT NULL` (FK merchants), and the ORM filters it
  automatically (ADR-002). Intelligence tables included.
- Money is `*_minor BIGINT` plus an ISO currency. Never floats.
- Status columns have CHECK constraints; state machines are enforced in services.
- Optimistic locking (`version`) on aggregates edited concurrently by staff (products, content posts).
- Audit rows are append-only (DB trigger). Outbox events are declared in `event-catalog.json`.
- New NOT NULL columns ship with server defaults (ADR-022).

## A. Commerce Core: implemented (Phases 0–1)
| Area | Tables |
|---|---|
| Identity | users, auth_sessions, refresh_tokens, mfa_recovery_codes, email_verification_tokens |
| Tenancy | merchants (incl. automation_mode, brand voice), stores, memberships, invitations |
| Platform | outbox_events, outbox_consumptions, idempotency_records, feature_flags, feature_flag_overrides, audit_logs |
| Billing | billing_features, billing_resources, billing_plans, billing_plan_versions, billing_plan_entitlements, billing_plan_limits, billing_addons, billing_subscriptions, billing_subscription_addons, billing_entitlement_overrides, billing_usage_counters, billing_usage_reservations, billing_usage_events, billing_usage_alerts, billing_credit_wallets, billing_credit_transactions |
| AI | ai_executions (per-attempt cost ledger), ai_provider_credentials (BYOK, sealed), ai_prompt_templates |
| Catalog | catalog_products, catalog_variants, catalog_product_options, catalog_product_option_values, catalog_variant_option_values, catalog_product_attributes (provenance + confidence), catalog_categories, catalog_collections, catalog_collection_products, catalog_bundle_components, catalog_suppliers, catalog_variant_suppliers, catalog_product_media, catalog_import_jobs |
| Media | media_assets (provenance, quality flags, scan status), media_derivatives, media_video_jobs |
| Studio | studio_jobs (AI draft document, issues, prompt version) |
| Channels | channel_connections (sealed tokens, capabilities, per-connection webhook secret), channel_oauth_states, channel_listings, webhook_events |
| Content | content_posts |

## B. Commerce Core: planned (Phases 2–5)
| Phase | Entities (key fields) |
|---|---|
| 2 Conversation→Order | Customer, CustomerIdentity (channel, external_id), CustomerAddress (structured Nepal address: province/district/municipality/ward/area/landmark), Conversation, Message, ConversationAssignment, Order, OrderLine (snapshot of price/sku/title), OrderTotals snapshot, OrderEvent (timeline), InventoryLocation, InventoryLedgerEntry (immutable), InventoryReservation, PaymentIntent, Payment, CODRecord |
| 3 Order→Delivery | Shipment, ShipmentEvent, CourierAccount, CourierRateQuote, Label, PickupRequest, CODSettlement, CODSettlementLine, DeliveryAttempt |
| 4 Returns | ReturnPolicy, ReturnRequest, ReturnLine (reason, condition, evidence media), ReverseShipment, Inspection, Exchange, Refund (idempotent, provider-tracked) |
| 5 Automation | Workflow, WorkflowVersion, WorkflowRun, WorkflowStepRun, DecisionPolicy, RiskThreshold, ApprovalRequest, **AutomationActionLog** (every automated/manual action with outcome; the APS source) |

## C. Intelligence Core (Phases 6–10)
Design rule: **prefer derived metric tables and recomputable profiles** over new "truth" tables. Every
intelligence row carries `computed_at`, `source_window`, `method_version`, and is recomputable from
Commerce Core data. Nothing in this section is authoritative for commercial facts.

| Entity | Kind | Purpose / key fields | Phase |
|---|---|---|---|
| **ProductIntelligenceProfile** (Product Brain) | Derived profile, 1 row per product, recomputed | demand rate (7/30/90d), stock cover days, margin & expected contribution per unit, return rate + top reasons, conversion by channel, content performance summary, seasonality index, promotion response, stockout history count, FAQ ids, `as_of` | 6 |
| ProductFAQ | Stored (curated) | question cluster, answer (seller-approved), source conversations count | 6 |
| **CommerceMemoryFact** | Stored, versioned | `subject_type/id` (product, customer, courier_route, supplier, content_pattern…), `fact_type` (e.g. `fit_runs_small`, `best_post_window`), `value` JSONB (typed by fact_type schema), `confidence`, `evidence_ref` (metric ids / query spec), `valid_from/valid_to`, `status` (active/superseded/rejected_by_merchant), `version` | 6 |
| **CommerceMemoryMetric** | Derived time series | `subject_type/id`, `metric` (registered name), `period` (day/week/month), `period_start`, `value`, `n` (sample size), `method_version`; unique per key | 6 |
| AutopilotMetric | Derived | per day × capability: eligible, automated_success, automated_failed, manual, excluded (with reason counts) | 6 |
| **AutopilotScoreSnapshot** | Derived | daily overall + per-capability score, coverage and data-completeness | 6 |
| StoreTwin (sections) | Derived read model | `merchant_id`, `section`, `state` JSONB (typed per section), `source_version`, `as_of`, `computed_at` | 9 (sections for exceptions/automation earlier) |
| StoreTwinSnapshot | Derived, daily | compact copy of key sections for trends/simulation baselines | 9 |
| **CODRiskAssessment** | Stored (decision record) | order_id, level (LOW/MEDIUM/HIGHER), score, factors[] (name, contribution, evidence), recommended_action, model_version, merchant_override, override_reason, disputed | 6 |
| **CourierPerformanceMetric** | Derived | courier × route (origin district → destination district) × weight band × cod flag × period: price, eta_p50/p90, delivery_success, first_attempt_success, failed_rate, cod_settlement_days, loss_damage_rate, n | 6 |
| **ReturnInsight** | Stored (detected pattern) | product/variant, pattern (e.g. reason=size_small 61%), sample size, window, suspected causes (image/content version, supplier, campaign), recommendation ids, status, baseline_rate, post_change_rate | 6 |
| **SupplierPerformanceMetric** | Derived | supplier × period: avg landed cost, defect rate, return rate, on-time rate, lead-time variance, contribution per unit | 8 |
| **CreativeExperiment** | Stored | content variants compared (hook, duration, price timing…), hypothesis, start/end, status | 7 |
| **CreativePerformanceMetric** | Derived | content_post × period: views, engagement, clicks, inquiries, orders, attributed revenue, attributed contribution, attribution method | 7 |
| **CreativeGenomeProfile** | Derived profile, 1 per merchant(+channel) | learned preferences with effect size & confidence: duration band, price timing, language mix, hook type, human presence, posting window | 7 |
| **Recommendation** | Stored | type, subject, title, explanation (what/why), estimated_impact {metric, value, range}, confidence, risk_class, recommended_action (typed command), status (proposed/accepted/rejected/expired/executed/failed), decided_by, decided_at | 6 |
| **RecommendationEvidence** | Stored | recommendation_id, evidence_type (metric/fact/record_ref), reference, value, window, description | 6 |
| RecommendationOutcome | Stored | recommendation_id, metric, baseline, observed, window, method, measured_at | 6 |
| **SimulationRun** | Stored | question, scenario inputs, assumptions[], outputs with ranges, confidence, model_version, status; never linked to execution without a separate approval | 9 |
| NetworkAggregate | Stored, cross-tenant aggregate only | dimension keys (category, region, period), metric, value, contributor_count (≥ k), suppression flag | 10 |

### Why these choices
- Metrics are time series with sample size `n`, so confidence can be computed and thin data shown as
  thin.
- Facts are **versioned** and can be rejected by the merchant, so merchant corrections persist and are
  auditable.
- Profiles are recomputable caches. Losing them loses no truth, and they are rebuilt from metrics.
- Recommendations store their evidence and outcomes, which makes impact measurable and auditable.

## D. Migration implications
- Intelligence tables are additive (new tables) and need no backfill of Commerce Core.
- Metrics need historical recompute jobs (idempotent per period key) when a `method_version` changes.
- Commerce Core needs **actor/outcome recording** on every operational action from Phase 2 onwards.
  `audit_logs.actor_type` exists today; Phase 5 adds AutomationActionLog for structured outcomes.
- Address data must be structured from Phase 2, because Courier/COD intelligence depends on route keys.
- Return reasons must be a controlled vocabulary (plus free text) from Phase 4.
- Content posts must keep the creative attributes (hook, duration, price timing, language, CTA) from
  Phase 1 onward, so the Creative Genome has data to learn from.
