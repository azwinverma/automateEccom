# Incident response

1. **Acknowledge** the page; open an incident note (time, alert, who's on it).
2. **Stabilise first:** kill switches, roll back, scale — stop the harm before finding the root cause.
3. **Communicate:** if sellers are affected for > 30 minutes, post a status message; update every 30 min.
4. **Fix** using the alert's runbook; keep notes of every command (they're audited anyway).
5. **Close** when the "done when" condition holds for 30 minutes.
6. **Review within 3 days:** timeline, cause, what detected it, what slowed us down; add or fix an alert,
   test or runbook step. No blame.

Data incidents (possible exposure of customer data): follow specs/15 (privacy) — preserve logs, limit
access, and inform the owner immediately; notification duties may apply.
