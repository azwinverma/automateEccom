# Admin, Operations & Support

> v1 (2026-11-02). The original 20 was never provided. Authored from the build brief and the
> implementation; owner review required.

## Access
Staff only, with an MFA-verified session (implemented). Every staff action is audited. Secret values
are never shown.

## Console capabilities
| Capability | Status |
|---|---|
| Merchant search/detail, usage, credits | API implemented |
| Subscription, entitlement override, plan editor | Overrides model implemented; editor UI planned |
| AI provider health, routing editor | Health API implemented; routing editor planned |
| Outbox DLQ + replay | Implemented (API) |
| Webhook explorer + replay | Implemented (API) |
| Feature flags | Implemented (API) |
| Channel health per merchant | API implemented |
| Orders / payments / shipments / returns / refunds review | Phases 2–4 |
| Support tickets | Planned |
| **Intelligence job health** (freshness, failures, recompute) | Phase 6 |
| **Recommendation audit** (why a recommendation or automated action happened, its evidence and outcome) | Phase 6 |
| **COD assessment disputes** queue | Phase 6 |
| **Network Intelligence aggregation review** (suppression stats, k thresholds) | Phase 10 |
| Gross margin incl. intelligence compute | Phase 6 |

## Support playbooks (to write)
- channel reconnect
- payment mismatch
- COD settlement dispute
- courier failure
- refund above threshold
- AI wrong answer (eval feedback loop)
- merchant asks why an automated action happened (decision record lookup)
