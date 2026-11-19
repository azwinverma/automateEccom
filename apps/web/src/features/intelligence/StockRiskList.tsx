"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./intelligence.module.css";
import { RiskMeter } from "./ProductBrainCard";

/** UX-012 on Home: products that run out soonest at the current pace. Silent when empty or not on the plan. */
export function StockRiskList() {
  const { t, number } = useI18n();
  const { can, feature } = useAuth();
  const on = feature("intelligence.product_brain") === "yes" && can("catalog.read");
  const q = useApiQuery(async (a) => (on ? a.intelligence.stockRisk() : { items: [] }), [on]);
  const items = q.state.status === "success" ? q.state.data.items.slice(0, 5) : [];
  if (!items.length) return null;
  return (
    <section className={styles.card} aria-labelledby="stock-risk-title" data-testid="stock-risk">
      <div className={styles.head}>
        <h2 id="stock-risk-title">{t("intel.stock.title")}</h2>
        <span className={styles.muted}>{t("intel.stock.hint")}</span>
      </div>
      <ul className={styles.stockList} aria-label={t("intel.stock.listLabel")}>
        {items.map((i) => (
          <li key={i.product_id}>
            <span>
              <Link href={`/products/${i.product_id}`}>{i.title}</Link>
              <span className={styles.muted}>
                {" · "}
                {i.available === 0 || i.stock_risk === "out"
                  ? t("intel.stock.rowOut")
                  : t("intel.stock.row", { n: number(i.available ?? 0), days: number(i.cover_days ?? 0, { maximumFractionDigits: 0 }) })}
              </span>
            </span>
            {i.stock_risk ? <RiskMeter risk={i.stock_risk} /> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
