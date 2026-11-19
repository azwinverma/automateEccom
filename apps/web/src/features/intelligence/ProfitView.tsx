"use client";

import { isApiError, type ProfitComponent, type ProfitSettings, type ProfitSummary } from "@commerce-os/api-client";
import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { InlineAlert, Skeleton, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./intelligence.module.css";

type T = ReturnType<typeof useI18n>["t"];
const WINDOWS = [7, 30, 90] as const;

export function isPlanGate(error: unknown): boolean {
  return isApiError(error) && error.status === 403 && error.code === "feature_not_in_plan";
}

/** Why a component isn't fully counted, as a sentence the seller can act on. */
export function reasonSentence(t: T, c: ProfitComponent): string | null {
  if (c.status === "included") return null;
  if (c.reason) return t.dynamic(`intel.profit.reason.${c.reason}`) ?? t("intel.profit.reason.missing_other");
  return t.dynamic(`intel.profit.reason.missing_${c.code}`) ?? t("intel.profit.reason.missing_other");
}

export function statusLabel(t: T, c: ProfitComponent): string {
  if (c.status === "included") return t("intel.profit.included");
  if (c.status === "partial") return t("intel.profit.partial", { n: c.missing });
  return t("intel.profit.notIncluded");
}

/** UX-010 Profit Card + spec 14 waterfall + product P&L + profit settings. */
export function ProfitView() {
  const { t, money, number } = useI18n();
  const [days, setDays] = useState<(typeof WINDOWS)[number]>(30);
  const q = useApiQuery((a) => a.intelligence.profit(days), [days]);

  if (q.state.status === "loading") {
    return (
      <section className={styles.card} aria-busy="true">
        <Skeleton width="40%" height={20} />
        <Skeleton height={120} />
      </section>
    );
  }
  if (q.state.status === "error") {
    if (isPlanGate(q.state.error)) {
      return (
        <InlineAlert tone="info" title={t("intel.profit.upsell")}>
          <LimitActions buyCredits={false} upgrade />
        </InlineAlert>
      );
    }
    return <ErrorAlert error={q.state.error} />;
  }
  const s = q.state.data;
  const shop = s.shop;
  const cur = s.currency;
  const negative = shop.contribution_minor < 0;
  return (
    <>
      <section className={styles.card} aria-labelledby="profit-title" data-testid="profit-card" data-complete={shop.complete}>
        <div className={styles.profitHead}>
          <div className={styles.profitFigure}>
            <h2 id="profit-title" style={{ margin: 0, fontSize: "var(--font-size-md)" }}>
              {t("intel.profit.contribution")}
            </h2>
            <span className={[styles.big, negative ? styles.negative : ""].join(" ")} data-testid="profit-contribution">
              {money(shop.contribution_minor, cur)}
            </span>
            <span className={styles.muted}>
              {t("intel.profit.revenue", { amount: money(shop.revenue_minor, cur) })}
              {shop.margin_pct !== null ? ` · ${t("intel.profit.margin", { pct: number(shop.margin_pct) })}` : ""}
            </span>
          </div>
          <div className={styles.window} role="group" aria-label={t("intel.profit.window")}>
            {WINDOWS.map((d) => (
              <button key={d} type="button" aria-pressed={days === d} onClick={() => setDays(d)}>
                {t(d === 7 ? "intel.profit.days7" : d === 30 ? "intel.profit.days30" : "intel.profit.days90")}
              </button>
            ))}
          </div>
        </div>
        <span className={styles.muted}>{t("intel.profit.hint", { days: s.window_days })}</span>
        {shop.orders === 0 && s.counts.failed === 0 ? (
          <p className={styles.muted} style={{ margin: 0 }}>
            {t("intel.profit.noSales")}
          </p>
        ) : (
          <Waterfall summary={s} />
        )}
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.profit.counts", { sold: s.counts.sold, failed: s.counts.failed, open: s.counts.open })}
          {s.counts.cost_from_current ? ` ${t("intel.profit.costFromCurrent", { n: s.counts.cost_from_current })}` : ""}
        </p>
        <p className={styles.fair} data-testid="profit-completeness">
          {shop.complete ? t("intel.profit.complete") : t("intel.profit.incomplete")}
        </p>
      </section>
      <ProductPnl summary={s} />
      <ProfitSettingsForm settings={s.settings} onSaved={q.reload} />
    </>
  );
}

function Waterfall({ summary }: { summary: ProfitSummary }) {
  const { t, money } = useI18n();
  const shop = summary.shop;
  const cur = summary.currency;
  return (
    <div className={styles.tableWrap}>
      <table className={styles.waterfall} aria-label={t("intel.profit.tableLabel")} data-testid="profit-waterfall">
        <thead>
          <tr>
            <th scope="col">{t("intel.profit.colItem")}</th>
            <th scope="col" className={styles.num}>
              {t("intel.profit.colAmount")}
            </th>
            <th scope="col">{t("intel.profit.colStatus")}</th>
          </tr>
        </thead>
        <tbody>
          {shop.components.map((c) => {
            const why = reasonSentence(t, c);
            return (
              <tr key={c.code} data-component={c.code} data-status={c.status}>
                <th scope="row" style={{ fontWeight: "normal", color: "var(--color-text-primary)" }}>
                  {t.dynamic(`intel.profit.comp.${c.code}`) ?? c.code}
                  {why ? <span className={styles.reasonText}>{why}</span> : null}
                </th>
                <td className={styles.num}>{c.amount_minor === null ? "–" : money(c.amount_minor, cur)}</td>
                <td>
                  <span className={styles.status} data-status={c.status}>
                    {statusLabel(t, c)}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <td>{t("intel.profit.contribution")}</td>
            <td className={[styles.num, shop.contribution_minor < 0 ? styles.negative : ""].join(" ")}>{money(shop.contribution_minor, cur)}</td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function ProductPnl({ summary }: { summary: ProfitSummary }) {
  const { t, money, number } = useI18n();
  const cur = summary.currency;
  if (!summary.products.length) return null;
  return (
    <section className={styles.card} aria-labelledby="pnl-title" data-testid="product-pnl">
      <div className={styles.head}>
        <h2 id="pnl-title">{t("intel.profit.products")}</h2>
      </div>
      <span className={styles.muted}>{t("intel.profit.productsHint")}</span>
      <div className={styles.tableWrap}>
        <table className={styles.waterfall} aria-label={t("intel.profit.productsLabel")}>
          <thead>
            <tr>
              <th scope="col">{t("intel.profit.colProduct")}</th>
              <th scope="col" className={`${styles.num} ${styles.hideNarrow}`}>
                {t("intel.profit.colUnits")}
              </th>
              <th scope="col" className={`${styles.num} ${styles.hideNarrow}`}>
                {t("intel.profit.colRevenue")}
              </th>
              <th scope="col" className={styles.num}>
                {t("intel.profit.colContribution")}
              </th>
              <th scope="col" className={styles.num}>
                {t("intel.profit.colPerUnit")}
              </th>
            </tr>
          </thead>
          <tbody>
            {summary.products.map((p) => {
              const cogs = p.components.find((c) => c.code === "cogs");
              const noCost = cogs?.status === "not_included";
              return (
                <tr key={p.product_id} data-product={p.product_id}>
                  <th scope="row" style={{ fontWeight: "normal" }}>
                    <Link href={`/products/${p.product_id}`}>{p.title ?? p.product_id}</Link>
                    {noCost ? <span className={styles.reasonText}>{t("intel.profit.costNotSet")}</span> : null}
                  </th>
                  <td className={`${styles.num} ${styles.hideNarrow}`}>{number(p.units)}</td>
                  <td className={`${styles.num} ${styles.hideNarrow}`}>{money(p.revenue_minor, cur)}</td>
                  <td className={[styles.num, p.contribution_minor < 0 ? styles.negative : ""].join(" ")}>{noCost ? "–" : money(p.contribution_minor, cur)}</td>
                  <td className={styles.num}>{noCost || p.contribution_per_unit_minor === null ? "–" : money(p.contribution_per_unit_minor, cur)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProfitSettingsForm({ settings, onSaved }: { settings: ProfitSettings; onSaved: () => void }) {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [packaging, setPackaging] = useState(settings.packaging_cost_minor === null ? "" : String(settings.packaging_cost_minor / 100));
  const [margin, setMargin] = useState(String(settings.min_margin_pct));
  const [maxReturn, setMaxReturn] = useState(String(settings.max_return_rate_pct));
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setPackaging(settings.packaging_cost_minor === null ? "" : String(settings.packaging_cost_minor / 100));
    setMargin(String(settings.min_margin_pct));
    setMaxReturn(String(settings.max_return_rate_pct));
  }, [settings]);
  const allowed = can("settings.manage");
  const forbidden = isApiError(action.error) && action.error.status === 403;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    const pct = (v: string) => (v.trim() === "" ? NaN : Number(v));
    const m = pct(margin);
    const r = pct(maxReturn);
    if (![m, r].every((x) => Number.isFinite(x) && x >= 0 && x <= 100)) return setErr(t("intel.profit.invalid"));
    const rupees = packaging.trim() === "" ? null : Number(packaging);
    if (rupees !== null && (!Number.isFinite(rupees) || rupees < 0)) return setErr(t("intel.profit.invalidMoney"));
    const ok = await action.run(() =>
      api.intelligence.updateProfitSettings({
        ...(rupees === null ? { clear_packaging: true } : { packaging_cost_minor: Math.round(rupees * 100) }),
        min_margin_pct: m,
        max_return_rate_pct: r,
      }),
    );
    if (ok) {
      toast(t("intel.profit.saved"));
      onSaved();
    }
  };

  return (
    <section className={styles.card} aria-labelledby="profit-settings-title" data-testid="profit-settings">
      <div className={styles.head}>
        <h2 id="profit-settings-title">{t("intel.profit.settings")}</h2>
      </div>
      <span className={styles.muted}>{t("intel.profit.settingsHint")}</span>
      {!allowed || forbidden ? <p className={styles.muted}>{t("intel.profit.managerOnly")}</p> : <ErrorAlert error={action.error} />}
      <form onSubmit={submit} noValidate>
        <fieldset disabled={!allowed} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
          <div className={styles.formGrid}>
            <TextField
              label={t("intel.profit.packaging")}
              hint={t("intel.profit.packagingHint")}
              inputMode="decimal"
              value={packaging}
              onChange={(e) => setPackaging(e.target.value)}
            />
            <TextField label={t("intel.profit.minMargin")} inputMode="decimal" value={margin} onChange={(e) => setMargin(e.target.value)} />
            <TextField label={t("intel.profit.maxReturn")} inputMode="decimal" value={maxReturn} onChange={(e) => setMaxReturn(e.target.value)} />
          </div>
          {err ? (
            <p role="alert" className={styles.negative} style={{ fontSize: "var(--font-size-sm)" }}>
              {err}
            </p>
          ) : null}
          <div style={{ marginTop: "var(--space-3)" }}>
            <Button type="submit" variant="primary" loading={action.pending}>
              {t("intel.profit.save")}
            </Button>
          </div>
        </fieldset>
      </form>
    </section>
  );
}
