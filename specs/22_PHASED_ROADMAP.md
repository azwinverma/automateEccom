# Phased Roadmap

> v1 (2026-11-02). The original 22 was never provided. Phases follow the 2026-11-02 strategy update.
> **Gating rule:** intelligence phases start only when the operational phases they depend on produce
> trustworthy data. Exit criteria must be met (24 Definition of Done) before a phase is closed.

**Brand (BRD, cross-phase):** Nivaro brand work runs alongside the current phase and never blocks it
(26, ADR-028). Each phase's new surfaces must meet the brand DoD (24).

| Phase | Name | Scope (backlog groups) | Data it produces for later phases |
|---|---|---|---|
| 0 | Foundation | FND, IAM, BIL, AIG (gateway), CHN-001/002, PAY-001, FUL-001, UX-001…003 | identity, audit (actor types), usage |
| 1 | Product-to-Publish | CAT, MED (001–004, 008–011), CNT, CHN (003/004/009–013), AIG-012/015, UX (Products, Studio, Content) | catalog, media provenance, **creative attributes**, listings, content history |
| 2 | Conversation-to-Order | CRM, inbox, AI Sales Agent, ORD, INV (ledger/reservation), PAY (COD + gateway) | customers, conversations, orders, **structured addresses**, stock movements |
| 3 | Order-to-Delivery | FUL (couriers, shipments, tracking, failed delivery), PAY (COD settlement), INV sync | delivery outcomes by courier/route, COD collection/settlement |
| 4 | Returns/Refunds/Exchanges | RET, PAY-007 refunds | **controlled return reasons**, refund costs |
| 5 | Automation + Exception OS | AUT (engine, builder, Decision Policy, approvals), Exception Inbox v2, **AutomationActionLog**, Autopilot Control Center (operational numbers) | automated/manual action outcomes (APS source) |
| 6 | Commerce Intelligence Foundation | PBR, MEM, APS, REC, profit intelligence (ANA-007/008), RTI, CRI, CODI, basic Store Manager | facts, metrics, recommendations + outcomes |
| 7 | Creative Intelligence | CGN, closed-loop content (CNT-012+), recommendation impact tracking | creative performance, genome |
| 8 | Procurement/Supplier Intelligence | PRO, SPI | supplier economics |
| 9 | Digital Store Twin + Simulation + advanced Store Manager | TWIN, SIM, Store Manager v2 | twin snapshots |
| 10 | Merchant Network Intelligence & enterprise scale | NET, enterprise (SSO, custom roles), scale work | aggregates |

## Exit criteria
- **Phase 0:** auth/tenancy/RBAC/audit, outbox, idempotency, entitlements, AI gateway, adapter
  framework, observability, design systems: **met**. CI executed on the hosting git provider:
  **open**. Staging deployed: **open** (needs a hosting decision).
- **Phase 1:**
  - a seller can create products (manual, CSV, AI from photos)
  - media is processed safely
  - content is drafted and approved per channel with creative attributes recorded
  - products and posts are published to at least one **real** channel
  - failures surface as exceptions
  - web and mobile flows pass E2E against the real backend
- **Phase 2:** DM → order with stock reserved, COD/payment recorded, idempotent imports, Sales Agent
  answers grounded via tools; E2E "message → AI → order".
- **Phase 3:** shipment creation, tracking, failed-delivery recovery, COD settlement reconciliation;
  E2E "order → COD → delivered".
- **Phase 4:** return policy engine, reverse logistics, idempotent refunds within thresholds; E2E
  "delivered → return → refund".
- **Phase 5:** workflows with the Decision Policy; every operational action recorded with
  actor/outcome; Control Center live with real numbers.
- **Phase 6:**
  - ≥ 90 days of Phase 2–5 data for pilot merchants
  - APS matches manual audit within ±2 points on sampled merchants
  - recommendations carry evidence, are outcome-tracked and pass offline backtest thresholds
- **Phase 7:** content metrics ingested from ≥ 1 real channel; genome changes generation with
  measured impact.
- **Phase 8:** landed cost + supplier metrics computed; recommendations use true economics.
- **Phase 9:** Twin freshness SLOs met; simulations show assumptions/ranges and never auto-execute.
- **Phase 10:** privacy impact assessment + legal review passed; k-anonymity enforced and tested.

## Pull-forward rule
Phase 1–5 work **must instrument data that later phases need**:
- creative attributes (Phase 1)
- structured addresses (Phase 2)
- actor/outcome logging (Phase 2+)
- controlled return reasons (Phase 4)

This is required work, not premature intelligence.
