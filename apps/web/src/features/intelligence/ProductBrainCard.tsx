"use client";

import type { ProductBrain, StockRisk } from "@commerce-os/api-client";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./intelligence.module.css";
import { reasonLabel, ReturnInsightItem } from "./ReturnInsights";

type T = ReturnType<typeof useI18n>["t"];

export function RiskMeter({ risk }: { risk: StockRisk }) {
  const { t } = useI18n();
  const label = t.dynamic(`intel.brain.risk_${risk}`) ?? risk;
  return (
    <span className={styles.row}>
      <span className={styles.risk} data-risk={risk} role="img" aria-label={t("intel.brain.riskLabel", { risk: label })}>
        <span />
        <span />
        <span />
        <span />
      </span>
      <span>{label}</span>
    </span>
  );
}

/** Each missing section as a plain sentence. */
export function missingSentences(t: T, b: ProductBrain): string[] {
  return Object.entries(b.not_included).map(([section, reason]) => t.dynamic(`intel.brain.missing_${section}_${reason}`) ?? t("intel.brain.missing_other"));
}

/** UX-018 Product Brain card (+ UX-012 stock risk, UX-020 return insights). Hidden without the plan. */
export function ProductBrainCard({ productId }: { productId: string }) {
  const { can } = useAuth();
  const q = useApiQuery(async (a) => {
    if (!can("catalog.read")) throw new Error("no access");
    return a.intelligence.productBrain(productId);
  }, [productId]);
  if (q.state.status !== "success") return null; // not on the plan, no access or still loading: no banner
  return <ProductBrainView brain={q.state.data} />;
}

export function ProductBrainView({ brain: b }: { brain: ProductBrain }) {
  const { t, number, money, relative } = useI18n();
  const pct = (x: number) => number(Math.round(x * 100));
  const missing = missingSentences(t, b);
  const worst = b.by_variant.find((v) => v.returned > 0);
  return (
    <section className={styles.card} aria-labelledby="brain-title" data-testid="product-brain">
      <div className={styles.head}>
        <h2 id="brain-title">{t("intel.brain.title")}</h2>
        <span className={styles.muted}>{t("intel.brain.completeness", { pct: pct(b.completeness) })}</span>
      </div>
      <span className={styles.muted}>{t("intel.brain.hint", { when: relative(b.as_of) })}</span>
      <div className={styles.brainGrid}>
        <div className={styles.brainCell} data-cell="demand">
          <h3>{t("intel.brain.demandLabel")}</h3>
          {b.demand_per_day !== null ? (
            <>
              <span className={styles.figure}>{t("intel.brain.demand", { n: number(b.demand_per_day, { maximumFractionDigits: 1 }) })}</span>
              <span className={styles.muted}>{t("intel.brain.demandFrom", { days: b.in_stock_days_90d })}</span>
            </>
          ) : (
            <span>{t("intel.brain.noDemand")}</span>
          )}
          <span className={styles.muted}>{t("intel.brain.units", { d7: b.units_7d, d30: b.units_30d, d90: b.units_90d })}</span>
        </div>
        <div className={styles.brainCell} data-cell="stock">
          <h3>{t("intel.brain.stockLabel")}</h3>
          {b.available !== null ? (
            <>
              <span className={styles.figure}>{t("intel.brain.stock", { n: number(b.available) })}</span>
              {b.cover_days !== null ? <span className={styles.muted}>{t("intel.brain.cover", { days: number(b.cover_days, { maximumFractionDigits: 0 }) })}</span> : null}
              {b.stock_risk ? <RiskMeter risk={b.stock_risk} /> : null}
              {b.stockouts_90d ? <span className={styles.muted}>{t("intel.brain.stockouts", { n: b.stockouts_90d })}</span> : null}
            </>
          ) : (
            <span>{t("intel.brain.notTracked")}</span>
          )}
        </div>
        <div className={styles.brainCell} data-cell="money">
          <h3>{t("intel.brain.moneyLabel")}</h3>
          {b.margin_pct !== null ? <span className={styles.figure}>{t("intel.brain.margin", { pct: number(b.margin_pct) })}</span> : null}
          {b.contribution_per_unit_minor !== null ? (
            <span className={b.contribution_per_unit_minor < 0 ? styles.negative : undefined}>
              {t(b.contribution_basis === "partial" ? "intel.brain.perUnitPartial" : "intel.brain.perUnit", { amount: money(b.contribution_per_unit_minor, b.currency) })}
            </span>
          ) : null}
          {b.margin_pct === null && b.contribution_per_unit_minor === null ? <span className={styles.muted}>–</span> : null}
        </div>
        <div className={styles.brainCell} data-cell="returns">
          <h3>{t("intel.brain.returnsLabel")}</h3>
          {b.return_rate !== null ? (
            <>
              <span className={styles.figure}>{t("intel.brain.returns", { pct: pct(b.return_rate), returned: b.returned_90d, sold: b.sold_90d_delivered })}</span>
              {b.top_reasons.length ? (
                <span className={styles.muted}>{t("intel.brain.topReasons", { reasons: b.top_reasons.map((r) => `${reasonLabel(t, r.reason)} (${r.units})`).join(", ") })}</span>
              ) : null}
              {worst && b.by_variant.length > 1 ? <span className={styles.muted}>{t("intel.brain.worstVariant", { variant: worst.variant ?? "", pct: pct(worst.rate) })}</span> : null}
            </>
          ) : (
            <span className={styles.muted}>–</span>
          )}
          {b.fit ? <span data-testid="brain-fit">{t(b.fit === "small" ? "intel.brain.fit_small" : "intel.brain.fit_large")}</span> : null}
        </div>
      </div>
      {b.return_insights?.length ? (
        <ul className={styles.facts}>
          {b.return_insights.map((i) => (
            <ReturnInsightItem key={i.id} insight={i} />
          ))}
        </ul>
      ) : null}
      {missing.length ? (
        <div>
          <span className={styles.muted} style={{ fontWeight: "var(--font-weight-medium)" }}>
            {t("intel.brain.missingTitle")}
          </span>
          <ul className={styles.missing} data-testid="brain-missing">
            {missing.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
