# Intelligence recompute (jobs, freshness, method changes)

**Alerts:** NightlyIntelligenceMissed (>26 h), IntelligenceJobFailing, ProductBrainStale, TwinSectionStale,
TwinUpdateLagSlo.

Intelligence is derived and recomputable from Commerce Core; decision records (recommendations, facts,
COD assessments) are kept.

1. `python -m app.cli ops-status` → `job_last_success_timestamp_seconds{job=…}`, `product_brain_max_age_seconds`,
   `twin_section_max_age_seconds{section=…}`. Worker logs: `nightly_intelligence` stats or the exception.
2. **Job failed for one merchant:** each merchant runs in its own savepoint; others continue. Rerun one:
   ```
   python -m app.cli recompute-intelligence --merchant <slug> --part product_brain
   ```
   Parts: courier, returns, product_brain, memory, creative, supplier, aps, recommendations, twin, all.
3. **Method change** (a new `method_version`): deploy, then `recompute-intelligence --part <part>` for all
   merchants (off-peak). Facts from the old method are re-derived on the next run (MEM-008); profiles and
   metrics are overwritten.
4. **Twin stale / lag SLO:** event updates come from the outbox — check
   [outbox-dlq-replay](outbox-dlq-replay.md). Force a rebuild: `python -m app.cli twin-reconcile`.
   Automation already refuses to auto-run on stale Twin data (it asks a person instead).
5. **Pause everything intelligence-related** during an incident: kill switch `ops.intelligence_jobs`
   (nightly jobs skip; UI keeps showing the last values with their "as of").

**Done when:** jobs succeed, Product Brain < 24 h old, Twin sections within their TTLs.
