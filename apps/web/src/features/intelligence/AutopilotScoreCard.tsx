"use client";

import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import styles from "./intelligence.module.css";

const ORDER = ["customer_replies", "order_capture", "shipment_creation", "pickup_requests", "delivery_notifications", "delivery_recovery", "returns", "refunds", "marketing"];

/** UX-017: the score, each capability, what wasn't counted and why. Thin data is shown as thin. */
export function AutopilotScoreCard() {
  const { t, number } = useI18n();
  const q = useApiQuery((a) => a.intelligence.autopilotScore(30));
  if (q.state.status !== "success") return null;
  const s = q.state.data;
  const caps = ORDER.filter((c) => s.capabilities[c]).map((c) => [c, s.capabilities[c]!] as const);
  if (!caps.length) return null;
  const pct = (v: number) => `${Math.round(v * 100)}%`;
  return (
    <section className={styles.card} aria-labelledby="aps-title" data-testid="autopilot-score">
      <div className={styles.head}>
        <h2 id="aps-title">{t("intel.aps.title")}</h2>
        <span className={styles.big} data-testid="aps-overall">
          {s.overall === null ? <span style={{ fontSize: "var(--font-size-sm)" }}>{t("intel.aps.notEnough")}</span> : pct(s.overall)}
        </span>
      </div>
      <span className={styles.muted}>
        {t("intel.aps.hint", { days: s.window_days })}
        {s.overall === null ? ` ${t("intel.aps.notEnoughHint", { n: s.min_eligible })}` : ""}
      </span>
      <ul className={styles.caps}>
        {caps.map(([code, c]) => {
          const name = t.dynamic(`intel.aps.capability.${code}`) ?? code;
          const excluded = Object.entries(c.excluded)
            .map(([k, n]) => `${t.dynamic(`intel.aps.exclusion.${k}`) ?? k} (${n})`)
            .join(", ");
          return (
            <li key={code} className={styles.cap} data-capability={code}>
              <span>{name}</span>
              <span className={[styles.meter, c.score === null ? styles.meterThin : ""].join(" ")} role="img" aria-label={t("intel.aps.rowLabel", { name, score: c.score === null ? t("intel.aps.notEnough") : pct(c.score) })}>
                {c.score !== null ? <span style={{ width: pct(c.score) }} /> : null}
              </span>
              <span className={styles.pct}>{c.score === null ? "–" : pct(c.score)}</span>
              <span className={styles.muted} style={{ gridColumn: "1 / -1" }}>
                {t("intel.aps.auto")} {number(c.A)} · {t("intel.aps.failed")} {number(c.F)} · {t("intel.aps.manual")} {number(c.M)}
                {c.X ? ` · ${t("intel.aps.excluded", { n: c.X })}: ${excluded}` : ""}
              </span>
            </li>
          );
        })}
      </ul>
      {s.hours_saved_estimate > 0 ? <span className={styles.muted}>{t("intel.aps.hours", { hours: s.hours_saved_estimate })}</span> : null}
    </section>
  );
}
