"use client";

import { isApiError } from "@commerce-os/api-client";
import { SectionHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import styles from "./intelligence.module.css";

/** CRI analytics: success / first attempt / time per courier and route, with sample size. Pro+. */
export function CourierPerformance() {
  const { t, number } = useI18n();
  const q = useApiQuery((a) => a.intelligence.courierPerformance(true));
  if (q.state.status === "error" && isApiError(q.state.error) && q.state.error.status === 403) return null;
  if (q.state.status !== "success") return null;
  const d = q.state.data;
  const pct = (v: number | null) => (v === null ? "–" : `${Math.round(v * 100)}%`);
  return (
    <section aria-labelledby="cp-title" data-testid="courier-performance">
      <SectionHeader title={t("intel.courier.performance")} id="cp-title" />
      <p className={styles.muted} style={{ marginTop: 0 }}>
        {t("intel.courier.performanceHint", { days: d.period_days, n: d.min_sample })}
      </p>
      {d.items.length === 0 ? (
        <p className={styles.muted}>{t("intel.courier.empty")}</p>
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} aria-labelledby="cp-title">
            <thead>
              <tr>
                <th scope="col">{t("intel.courier.colRoute")}</th>
                <th scope="col">{t("intel.courier.colCourier")}</th>
                <th scope="col" className={table.num}>
                  {t("intel.courier.colSuccess")}
                </th>
                <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                  {t("intel.courier.colFirst")}
                </th>
                <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                  {t("intel.courier.colDays")}
                </th>
                <th scope="col" className={table.num}>
                  {t("intel.courier.colN")}
                </th>
              </tr>
            </thead>
            <tbody>
              {d.items.map((r) => (
                <tr key={`${r.courier_account_id}-${r.origin}-${r.destination}-${r.weight_band}-${r.cod}`}>
                  <td>
                    {r.origin} → {r.destination}
                    {r.cod ? " · COD" : ""}
                  </td>
                  <td>{r.courier_name}</td>
                  <td className={table.num}>{pct(r.delivery_success)}</td>
                  <td className={[table.num, table.hideSm].join(" ")}>{pct(r.first_attempt_success)}</td>
                  <td className={[table.num, table.hideSm].join(" ")}>{r.eta_p50_days ?? "–"}</td>
                  <td className={table.num}>
                    {number(r.n)}
                    {!r.enough_data ? <div className={styles.muted}>{t("intel.courier.fewData")}</div> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
