# Engineering Backlog

> v2 (2026-11-02): existing IDs unchanged; added pull-forward tasks and the intelligence groups.
> Phase mapping: 22_PHASED_ROADMAP.md.

Use these IDs in issues and PRs.

## FND Foundation
FND-001 monorepo
FND-002 env config
FND-003 Docker local stack
FND-004 PostgreSQL
FND-005 Redis/Celery
FND-006 object storage abstraction
FND-007 CI
FND-008 staging CD
FND-009 structured logging
FND-010 tracing/metrics
FND-011 feature flags
FND-012 transactional outbox
FND-013 idempotency service
FND-014 audit framework

## IAM
IAM-001 user
IAM-002 login
IAM-003 verification
IAM-004 sessions/token rotation
IAM-005 MFA
IAM-006 merchant tenancy
IAM-007 membership
IAM-008 RBAC
IAM-009 cross-tenant tests
IAM-010 revoke sessions

## BIL
BIL-001 plan
BIL-002 plan version
BIL-003 features
BIL-004 entitlement service
BIL-005 usage event
BIL-006 aggregation
BIL-007 credit wallet
BIL-008 reserve/finalize usage
BIL-009 quota alerts
BIL-010 trials
BIL-011 upgrade/downgrade
BIL-012 overage
BIL-013 admin plan editor

## AIG
AIG-001 gateway
AIG-002 Claude adapter
AIG-003 OpenAI adapter
AIG-004 Gemini adapter
AIG-005 image provider
AIG-006 video provider
AIG-007 routing
AIG-008 health scoring
AIG-009 circuit breaker
AIG-010 retry/timeout
AIG-011 BYOK encryption
AIG-012 prompt registry
AIG-013 schema validation
AIG-014 cost ledger
AIG-015 eval harness

## CAT
CAT-001 Product
CAT-002 Variant
CAT-003 options
CAT-004 taxonomy
CAT-005 pricing
CAT-006 cost
CAT-007 lifecycle
CAT-008 import
CAT-009 SKU rules
CAT-010 listing mapping

## MED
MED-001 signed upload
MED-002 validation
MED-003 EXIF
MED-004 derivatives
MED-005 background removal
MED-006 image generation
MED-007 fidelity review
MED-008 Auto Reel
MED-009 video job state
MED-010 media metering
MED-011 lifecycle cleanup

## CNT
CNT-001 brand voice
CNT-002 titles
CNT-003 descriptions
CNT-004 SEO
CNT-005 captions
CNT-006 hashtags
CNT-007 translation
CNT-008 calendar
CNT-009 approval
CNT-010 scheduler
CNT-011 retry
CNT-012 creative attributes on posts and video jobs (hook, duration, price timing, language mix, CTA, caption length, background, template, posting window) [Phase 1, pull-forward]
CNT-013 content metrics ingestion interface on adapters (fetch_content_metrics) [Phase 7]
CNT-014 inquiry/order attribution to content (explicit ref → window heuristic; method recorded) [Phase 7]

## CHN
CHN-001 adapter interface
CHN-002 capabilities
CHN-003 OAuth
CHN-004 token refresh
CHN-005 Meta/Instagram
CHN-006 TikTok
CHN-007 TikTok Shop where eligible
CHN-008 Shopify
CHN-009 WooCommerce
CHN-010 webhook gateway
CHN-011 dedupe
CHN-012 reconciliation
CHN-013 health UI

## CRM
CRM-001 Customer
CRM-002 identities
CRM-003 addresses
CRM-004 duplicate merge
CRM-005 Conversation
CRM-006 Message
CRM-007 normalization
CRM-008 assignment
CRM-009 intent
CRM-010 AI summary
CRM-011 grounded reply
CRM-012 escalation
CRM-013 segments

## ORD
ORD-001 Order
ORD-002 OrderLine
ORD-003 totals snapshot
ORD-004 state machine
ORD-005 external import
ORD-006 chat-to-order
ORD-007 seller order
ORD-008 idempotency
ORD-009 cancel
ORD-010 partial cancel
ORD-011 timeline
ORD-012 structured Nepal address model (province/district/municipality/ward/area/landmark) + validation [pull-forward for CRI/CODI]

## INV
INV-001 locations
INV-002 ledger
INV-003 reservations
INV-004 reserve/release
INV-005 concurrency tests
INV-006 adjustment
INV-007 transfer
INV-008 low-stock
INV-009 channel sync
INV-010 reconciliation

## PAY
PAY-001 adapter
PAY-002 COD
PAY-003 payment intent
PAY-004 verify
PAY-005 webhook
PAY-006 reconcile
PAY-007 refund
PAY-008 idempotency tests
PAY-009 failed payment
PAY-010 settlement dashboard

## FUL
FUL-001 courier adapter
FUL-002 rates
FUL-003 shipment state
FUL-004 labels
FUL-005 pickup
FUL-006 tracking
FUL-007 notify
FUL-008 delivery failure
FUL-009 smart courier
FUL-010 reconciliation

## RET
RET-001 policy
RET-002 eligibility
RET-003 request
RET-004 evidence
RET-005 approval
RET-006 reverse shipment
RET-007 inspection
RET-008 exchange
RET-009 refund calculation
RET-010 auto-refund threshold
RET-011 abuse signals
RET-012 controlled return-reason vocabulary + free text [pull-forward for RTI]

## AUT
AUT-001 workflow schema
AUT-002 triggers
AUT-003 conditions
AUT-004 actions
AUT-005 versions
AUT-006 execution
AUT-007 delay
AUT-008 branch
AUT-009 approval
AUT-010 retry
AUT-011 exceptions
AUT-012 logs
AUT-013 templates
AUT-014 builder UI
AUT-015 dry-run
AUT-016 Autonomous Decision Policy: risk classes R0–R4, mode × class matrix, confidence + staleness gates
AUT-017 merchant thresholds (refund, discount, PO, campaign budget, stock transfer, price-change band) with audit
AUT-018 AutomationActionLog: actor/outcome/eligibility/exclusion for every operational action (APS source)
AUT-019 decision records (inputs refs, rule hit, confidence, impact) + seller-facing explanation
AUT-020 intelligence-derived triggers and profit-aware conditions (Phase 6)
AUT-021 recommendation → policy → approval → idempotent execution path (Phase 6)

## ANA
ANA-001 sales
ANA-002 channels
ANA-003 products
ANA-004 fulfillment
ANA-005 returns
ANA-006 AI/automation
ANA-007 product P&L
ANA-008 profit dashboard
ANA-009 Store Manager tools
ANA-010 recommendations

## PRO
PRO-001 suppliers
PRO-002 supplier products
PRO-003 purchase orders
PRO-004 approvals
PRO-005 receiving
PRO-006 landed cost
PRO-007 reorder recommendations

## ADM
ADM-001 merchant lookup
ADM-002 usage/credits
ADM-003 provider health
ADM-004 channel health
ADM-005 webhook explorer
ADM-006 replay
ADM-007 DLQ
ADM-008 plan editor
ADM-009 routing editor
ADM-010 refund review
ADM-011 feature flags

## UX
UX-001 design tokens
UX-002 web library
UX-003 Flutter theme
UX-004 Product Brain
UX-005 Channel Sync Rail
UX-006 Autopilot Strip
UX-007 Exception Inbox
UX-008 Order Journey
UX-009 AI Timeline
UX-010 Profit Card
UX-011 Video Credit Meter
UX-012 Inventory Risk
UX-013 real states
UX-014 accessibility
UX-015 bilingual review
UX-016 Autopilot Control Center (home): "Your store is running." + Needs Your Attention (Phase 5)
UX-017 Autopilot Score component (breakdown, exclusions, thin-data state) (Phase 6)
UX-018 Product Brain card (Phase 6)
UX-019 Recommendation / Profit Recommendation Card with explanation pattern (Phase 6)
UX-020 Return Insight Card + Courier Recommendation Card (Phase 6)
UX-021 Commerce Memory insight with correction (Phase 6)
UX-022 Creative Genome panel (Phase 7)

## PBR Product Brain (Phase 6)
PBR-001 ProductIntelligenceProfile schema + method_version + as_of + data-completeness
PBR-002 demand rate (EWMA, in-stock days only, seasonality index) per product/variant
PBR-003 margin + expected contribution per unit (uses ANA true-profit components; "not included" handling)
PBR-004 stock cover days + stockout history
PBR-005 return rate + top reasons (from RET-012) per product/variant/size
PBR-006 channel conversion + content performance summary (from CGN metrics when available)
PBR-007 FAQ clustering from conversations + seller-approved answers (ProductFAQ)
PBR-008 incremental refresh on events + nightly full recompute; freshness SLO + metrics
PBR-009 API GET /product-brain/products/{id} (+faqs); Sales Agent + Store Manager tool get_product_brain
PBR-010 golden-value tests + offline backtest of demand rate

## MEM Commerce Memory (Phase 6)
MEM-001 CommerceMemoryMetric registry (named metrics, definitions, periods, method_version) + storage
MEM-002 metric computation jobs (idempotent per period key) for products, customers, logistics, operations
MEM-003 CommerceMemoryFact schema (typed fact_type JSON schemas, confidence, evidence_ref, validity, versions)
MEM-004 fact derivation rules (e.g. fit_runs_small, best_post_window, repeat_cycle_days) with thresholds + min samples
MEM-005 merchant correction (reject/edit fact → new version, respected by derivations), audited
MEM-006 privacy: customer-level facts limited to operational needs; deletion/anonymisation path
MEM-007 API summaries + Store Manager tool get_memory_facts
MEM-008 recompute on method_version change (backfill job)

## APS Autopilot Score (Phase 6; instrumentation AUT-018 earlier)
APS-001 capability registry (eligibility rules per capability, steps-per-operation constants)
APS-002 daily AutopilotMetric aggregation from AutomationActionLog (A/F/M/X with reasons)
APS-003 AutopilotScoreSnapshot (volume-weighted overall; thin-data handling)
APS-004 improvement recommendations (largest gap with config lever; estimated coverage from last 30 days)
APS-005 API + Control Center + Store Manager tool; upsell hook via REC (plan_upgrade)
APS-006 audit sampling: manual-audit comparison tool (±2 points exit criterion)
APS-007 anomaly flag on sudden score jumps

## REC Recommendations & Explanation Framework (Phase 6)
REC-001 Recommendation + RecommendationEvidence + RecommendationOutcome models
REC-002 typed recommended_action commands (mapped to automation actions)
REC-003 explanation object builder (what/why/evidence/confidence/impact/action) — deterministic
REC-004 insight-narrative AI task with faithfulness validation (no new numbers)
REC-005 policy routing (AUT-016) → auto / approval (Needs Your Attention) / blocked
REC-006 accept/reject APIs (idempotent; reasons) + expiry
REC-007 outcome measurement jobs (pre/post, holdout/DiD where possible) + impact analytics
REC-008 dedupe + rate limiting of recommendations per merchant (no spam)

## RTI Return Intelligence (Phase 6)
RTI-001 return-reason metrics by product/variant/size/content version/supplier/campaign
RTI-002 pattern detection (share vs baseline, min sample, significance) → ReturnInsight
RTI-003 suspected-cause linking (content/image version shown at purchase, supplier batch)
RTI-004 recommendations (size guide, fit warning, description, image, stop creative, size-up hint, supplier flag)
RTI-005 before/after impact measurement
RTI-006 Return Insight Card + Sales Agent fit hint

## CRI Courier Intelligence / Courier Brain (Phase 6)
CRI-001 CourierPerformanceMetric by courier × route × weight band × COD
CRI-002 expected-cost model (price + failure cost × failure prob + settlement delay cost)
CRI-003 selection modes cheapest/fastest/smart/preferred-only with policy integration
CRI-004 explanation ("selected because …") + alternatives
CRI-005 cold-start fallback (merchant preference/rules) with explicit low-confidence label
CRI-006 ETA calibration monitoring

## CODI COD Intelligence (Phase 6)
CODI-001 feature set (allowed inputs only) + static prohibited-feature check
CODI-002 CODRiskAssessment (level, score, factors with evidence, recommended action, model_version)
CODI-003 decision-policy integration (LOW auto, MEDIUM per policy, HIGHER review/advance)
CODI-004 merchant override + dispute workflow (audited)
CODI-005 outcome capture + calibration monitoring + regional disparity report
CODI-006 phone verification + partial-advance flows (with PAY)

## CGN Creative Genome (Phase 7)
CGN-001 CreativePerformanceMetric (views, engagement, clicks, inquiries, orders, attributed contribution)
CGN-002 genome computation (outcome-weighted effects, min sample, shrinkage) → CreativeGenomeProfile
CGN-003 CreativeExperiment (hypothesis, variants, stopping rule)
CGN-004 genome inputs to Studio prompts, Auto Reel template choice, video concepts, schedule suggestions (genome_version recorded)
CGN-005 Creative Genome panel + Store Manager tool
CGN-006 impact measurement of genome-informed content vs baseline

## SPI Supplier Intelligence (Phase 8)
SPI-001 SupplierPerformanceMetric (landed cost, defect, return, on-time, lead-time variance, contribution/unit)
SPI-002 batch/lot linkage receiving → returns/defects
SPI-003 true-economics supplier recommendation with explanation
SPI-004 reorder recommendation using true economics + lead time

## TWIN Digital Store Twin (Phase 9; exception/automation sections may start Phase 5)
TWIN-001 section registry (owner domain, TTL, max staleness per consumer)
TWIN-002 event-driven incremental updaters (monotonic source_version)
TWIN-003 periodic reconciliation + on-read freshness check + stale flag
TWIN-004 StoreTwinSnapshot daily
TWIN-005 API /twin/summary + Store Manager tool get_twin_section
TWIN-006 freshness SLO monitoring

## SIM Simulation (Phase 9)
SIM-001 SimulationRun model + async execution
SIM-002 discount scenario (elasticity from own history, margin, stock duration, return impact)
SIM-003 purchase-quantity scenario (stockout probability, cash tied up)
SIM-004 ad-budget shift scenario (requires connected ad spend)
SIM-005 assumptions/confidence/range presentation; no execution without separate approval
SIM-006 backtest calibration of simulation estimates

## NET Merchant Network Intelligence (Phase 10)
NET-001 privacy impact assessment + legal review (gate)
NET-002 aggregation service (k ≥ 10, dominance ≤ 30%, suppression) — only cross-tenant reader
NET-003 opt-out/opt-in controls (contribute vs consume)
NET-004 aggregates: category demand trends, regional demand, price bands, return trends, courier route success, seasonality
NET-005 priors for cold start (courier, creative) with clear "network-based" labelling
NET-006 privacy tests (no cross-tenant leakage, threshold enforcement)
