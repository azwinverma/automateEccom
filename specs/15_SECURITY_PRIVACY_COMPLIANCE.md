# Security, Privacy & Compliance

> v1 (2026-11-02). The original 15 was never provided. Authored from the build brief, the
> implementation and the strategy update. **Legal review required**, especially for Nepal's
> Individual Privacy Act 2075 and any cross-border transfer.

## Baseline controls (implemented unless noted)
- **Network/crypto:** TLS (at the load balancer); Argon2id password hashing; TOTP MFA; refresh
  rotation with reuse detection.
- **Access:** RBAC (permission strings); ORM-enforced tenant isolation; cross-tenant tests.
- **Abuse:** rate limiting (auth/invites/registration); lockout.
- **Secrets:** secret manager (planned); envelope-encrypted provider credentials; KMS (planned).
- **Webhooks:** signature verification; dedupe; replay protection.
- **Data minimisation:** PII minimisation (no prompts/outputs in the AI ledger; GPS stripped from
  media); payment scope minimisation (no card data stored).
- **Uploads:** secure upload (signed, sniffed, bomb guard, malware scan).
- **Supply chain:** SAST, dependency, secret and container scanning in CI (configured, not yet run).
- **Logging/recovery:** append-only audit; DB errors logged without row values (ADR-010); backup +
  restore testing (planned, needs hosting).

## Intelligence privacy & fairness
1. **Merchant-scoped.** All intelligence tables carry `merchant_id`. Intelligence never crosses tenants
   except through the Network Intelligence aggregation service.
2. **Explainable and auditable.** Facts, assessments and recommendations store their evidence,
   `method_version` and actor of any override.
3. **Correctable.** Merchants can reject facts and override assessments (versioned). Corrections
   persist and are respected by later computations.
4. **No opaque blacklists.** COD risk is per-order, explainable and overridable. There is no
   cross-merchant person-level list.
5. **Protected attributes.** Features never use or infer gender, religion, caste, ethnicity, health or
   similar. Name-derived features are prohibited. Reviewed per model version.
6. **Customer data rights.** Customer records support export and deletion. Derived intelligence about
   a deleted customer is recomputed or anonymised. COD history is kept only as aggregate counts after
   deletion.
7. **Retention.** Raw webhook payloads have limited retention (default 90 days; then a summary is
   kept). Message content follows the merchant setting. Metrics are kept; personal identifiers in
   metrics are avoided (customer ids only where needed).
8. **Opaque LLM memory prohibited** as a source of truth (00).

## Merchant Network Intelligence (Phase 10) gates
- Aggregates only. No raw merchant-level data is shared, and no merchant sees another merchant's
  proprietary data.
- **k-anonymity:** each published cell needs ≥ k contributing merchants (default k = 10) **and** no
  single merchant contributing > 30% of the cell's volume. Otherwise it is suppressed.
- Coarse dimensions only (category, province/district, week). No product-level or customer-level
  cells.
- Merchant **opt-out** (default per legal review); contribution and consumption are controlled
  separately.
- Before launch: a privacy impact assessment, a security review and legal review.

## AI-specific
- Prompt-injection hardening: tools validate arguments; the model cannot call actions without the
  Decision Policy.
- Provider data-retention settings are reviewed per provider. BYOK lets merchants choose.
- Insight narratives are validated so they cannot introduce numbers absent from the evidence.
