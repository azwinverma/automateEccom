# Engineering Backlog

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
