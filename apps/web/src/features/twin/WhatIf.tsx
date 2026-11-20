"use client";

import {
  isApiError,
  type DiscountOutputs,
  type PurchaseOutputs,
  type SimulationAssumption,
  type SimulationKind,
  type SimulationRunView,
  type SimulationWarning,
} from "@commerce-os/api-client";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, Skeleton, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { type PickedVariant, VariantPicker } from "../procurement/VariantPicker";
import styles from "./twin.module.css";

type I18n = ReturnType<typeof useI18n>;
type T = I18n["t"];
const POLL_MS = 1500;
const MAX_POLLS = 80;

const isDiscount = (o: SimulationRunView["outputs"], kind: SimulationKind): o is DiscountOutputs => !!o && kind === "discount";
const isPurchase = (o: SimulationRunView["outputs"], kind: SimulationKind): o is PurchaseOutputs => !!o && kind === "purchase_quantity";

/** Format every amount in a run in the shop's currency (falls back to the formatter's default). */
export function withCurrency(base: I18n, currency: string | undefined): I18n {
  return currency ? { ...base, money: (m: number, c?: string) => base.money(m, c ?? currency) } : base;
}

function fmtNum(i: I18n, v: unknown, digits = 1): string {
  return typeof v === "number" ? i.number(v, { maximumFractionDigits: digits }) : "–";
}

/** Every assumption as a plain sentence with its numbers; unknown codes still show (never hidden). */
export function assumptionSentence(i: I18n, a: SimulationAssumption): string {
  const v = a.vars ?? {};
  const n = (k: string, d = 1) => fmtNum(i, v[k], d);
  const range = Array.isArray(v.range) ? (v.range as number[]) : [];
  switch (a.code) {
    case "baseline_demand":
      return i.t("sim.assume.baseline_demand", { per_day: n("per_day", 2), in_stock_days: n("in_stock_days", 0) });
    case "elasticity_history":
      return i.t("sim.assume.elasticity_history", {
        discount_days: n("discount_days", 0),
        avg_discount_pct: n("avg_discount_pct"),
        value: n("value", 2),
        lo: fmtNum(i, range[0], 2),
        hi: fmtNum(i, range[1], 2),
      });
    case "elasticity_typical_range":
      return i.t("sim.assume.elasticity_typical_range", { lo: fmtNum(i, range[0], 2), hi: fmtNum(i, range[1], 2) });
    case "stock_caps_sales":
      return i.t("sim.assume.stock_caps_sales", { stock: n("stock", 0), incoming: n("incoming", 0) });
    case "stock_not_tracked":
      return i.t("sim.assume.stock_not_tracked");
    case "other_costs_per_unit_unchanged":
      return typeof v.contribution_per_unit_minor === "number"
        ? i.t("sim.assume.other_costs_per_unit_unchanged", { amount: i.money(v.contribution_per_unit_minor) })
        : i.t("sim.assume.other_costs_unknown");
    case "returns_like_recent_sales":
      return typeof v.return_rate === "number" ? i.t("sim.assume.returns_like_recent_sales", { rate: i.percent(v.return_rate) }) : i.t("sim.assume.returns_unknown");
    case "no_seasonality":
      return i.t("sim.assume.no_seasonality");
    case "variant_demand":
      return i.t("sim.assume.variant_demand", { per_day: n("per_day", 2), sold_90d: n("sold_90d", 0) });
    case "lead_time_measured":
    case "lead_time_supplier_terms":
    case "lead_time_default":
      return i.t(`sim.assume.${a.code}`, { days: n("days") });
    case "incoming_arrives_first":
      return i.t("sim.assume.incoming_arrives_first", { incoming: n("incoming", 0) });
    case "poisson_demand":
      return i.t("sim.assume.poisson_demand");
    case "unit_cost_landed":
    case "unit_cost_purchase_price":
      return i.t(`sim.assume.${a.code}`, { amount: typeof v.unit_cost_minor === "number" ? i.money(v.unit_cost_minor) : "–" });
    default:
      return i.t("sim.assume.unknown", { code: a.code });
  }
}

export function warningSentence(i: I18n, w: SimulationWarning): string {
  const p = typeof w.probability === "number" ? i.percent(w.probability) : "–";
  switch (w.code) {
    case "below_min_margin":
      return i.t("sim.warn.below_min_margin", { min: fmtNum(i, w.min_margin_pct, 0) });
    case "earns_less_than_no_discount":
      return i.t("sim.warn.earns_less_than_no_discount", { amount: i.money(Math.abs(Number(w.difference_minor) || 0)) });
    case "loses_money_per_unit":
      return i.t("sim.warn.loses_money_per_unit", { amount: i.money(Math.abs(Number(w.per_unit_minor) || 0)) });
    case "stockout_likely":
      return i.t("sim.warn.stockout_likely", { p });
    case "below_moq":
      return i.t("sim.warn.below_moq", { moq: fmtNum(i, w.moq, 0) });
    case "may_sell_out_before_delivery":
      return i.t("sim.warn.may_sell_out_before_delivery", { p });
    case "slow_to_sell":
      return i.t("sim.warn.slow_to_sell", { n: fmtNum(i, w.leftover_90, 0) });
    default:
      return i.t("sim.warn.other");
  }
}

export function headline(i: I18n, run: SimulationRunView): string | null {
  const o = run.outputs;
  if (isDiscount(o, run.kind)) {
    const vars = {
      pct: fmtNum(i, o.discount_pct, 0),
      days: fmtNum(i, o.days, 0),
      units: fmtNum(i, o.units.expected, 0),
      low: fmtNum(i, o.units.low, 0),
      high: fmtNum(i, o.units.high, 0),
    };
    if (o.difference_minor == null) return i.t("sim.headUnknown", vars);
    const amount = i.money(Math.abs(o.difference_minor));
    return o.difference_minor < 0 ? i.t("sim.headLess", { ...vars, amount }) : i.t("sim.headMore", { ...vars, amount });
  }
  if (isPurchase(o, run.kind)) {
    const title = o.variant ? `${o.title ?? ""} (${o.variant})` : (o.title ?? "");
    return i.t("sim.headPurchase", { qty: fmtNum(i, o.quantity, 0), title, cover: fmtNum(i, o.cover_days_after_arrival, 0), leftover: fmtNum(i, o.leftover_after_90d, 0) });
  }
  return null;
}

function notIncluded(i: I18n, codes: string[]): string | null {
  if (!codes.length) return null;
  const list = codes.map((c) => i.t.dynamic(`sim.ni_${c}`) ?? c).join(", ");
  return i.t("sim.notIncluded", { list });
}

/** SIM-005: the estimate, its range, its warnings, and every assumption; nothing is executed. */
export function SimulationResult({ run }: { run: SimulationRunView }) {
  const i = withCurrency(useI18n(), run.currency);
  const { t, money, percent } = i;
  if (run.status === "queued" || run.status === "running") {
    return (
      <div className={styles.card} aria-busy="true" role="status" data-testid="sim-pending">
        <p className={styles.muted}>{run.status === "queued" ? t("sim.queued") : t("sim.running")}</p>
        <Skeleton height={80} />
      </div>
    );
  }
  if (run.status === "failed") {
    return (
      <InlineAlert tone="warning" title={t("sim.statusFailed")}>
        {t.dynamic(`sim.failed_${run.error_code ?? ""}`) ?? t("sim.failed_other")}
      </InlineAlert>
    );
  }
  const o = run.outputs;
  const conf = run.confidence === "high" ? t("sim.confHigh") : run.confidence === "medium" ? t("sim.confMedium") : t("sim.confLow");
  const ni = o ? notIncluded(i, o.not_included) : null;
  return (
    <article className={styles.card} data-testid="sim-result" data-kind={run.kind} aria-labelledby={`sim-h-${run.id}`}>
      <div className={styles.head}>
        <span className={styles.estimateLabel}>{t("sim.estimate")}</span>
        <Badge tone={run.confidence === "low" ? "warning" : "info"} dot={false}>
          {conf}
        </Badge>
      </div>
      <p className={styles.headline} id={`sim-h-${run.id}`}>
        {headline(i, run)}
      </p>
      {o && o.warnings.length ? (
        <div role="group" aria-label={t("sim.warningsLabel")} style={{ display: "grid", gap: "var(--space-2)" }}>
          {o.warnings.map((w, k) => (
            <InlineAlert key={`${w.code}-${k}`} tone={w.code === "loses_money_per_unit" || w.code === "earns_less_than_no_discount" ? "danger" : "warning"} live={false}>
              {warningSentence(i, w)}
            </InlineAlert>
          ))}
        </div>
      ) : null}
      {isDiscount(o, run.kind) ? (
        <dl className={styles.facts}>
          <div>
            <dt>{t("sim.units")}</dt>
            <dd>{t("sim.unitsValue", { units: fmtNum(i, o.units.expected, 0), low: fmtNum(i, o.units.low, 0), high: fmtNum(i, o.units.high, 0) })}</dd>
            <dd className={styles.meta}>{t("sim.withoutDiscount", { units: fmtNum(i, o.units.baseline, 0) })}</dd>
            <dd className={styles.meta}>{t("sim.perDay", { n: fmtNum(i, o.demand_per_day.expected, 1), base: fmtNum(i, o.demand_per_day.baseline, 1) })}</dd>
          </div>
          <div>
            <dt>{t("sim.margin")}</dt>
            <dd>
              {t("sim.marginValue", {
                before: o.margin_pct.before == null ? "–" : `${fmtNum(i, o.margin_pct.before)}%`,
                after: o.margin_pct.after == null ? "–" : `${fmtNum(i, o.margin_pct.after)}%`,
              })}
            </dd>
          </div>
          <div>
            <dt>{t("sim.contribution")}</dt>
            <dd>
              {o.contribution_minor.with_discount && o.contribution_minor.without_discount != null
                ? t("sim.contribValue", {
                    with: money(o.contribution_minor.with_discount.expected),
                    low: money(o.contribution_minor.with_discount.low),
                    high: money(o.contribution_minor.with_discount.high),
                    without: money(o.contribution_minor.without_discount),
                  })
                : "–"}
            </dd>
          </div>
          <div>
            <dt>{t("sim.stock")}</dt>
            <dd>{o.stock == null ? t("sim.stockUntracked") : t("sim.stockDays", { n: fmtNum(i, o.stock_days, 0) })}</dd>
            {o.stockout_probability != null ? (
              <dd className={styles.meta}>
                {t("sim.stockout")}: {percent(o.stockout_probability)}
              </dd>
            ) : null}
          </div>
        </dl>
      ) : null}
      {isPurchase(o, run.kind) ? (
        <dl className={styles.facts}>
          <div>
            <dt>{t("sim.perDayDemand", { n: fmtNum(i, o.per_day, 2) })}</dt>
            <dd>{t("sim.lead", { n: fmtNum(i, o.lead_days, 0) })}</dd>
          </div>
          <div>
            <dt>{t("sim.stockoutBefore")}</dt>
            <dd>{percent(o.stockout_before_arrival_probability)}</dd>
          </div>
          <div>
            <dt>{t("sim.cover")}</dt>
            <dd>{fmtNum(i, o.cover_days_after_arrival, 0)}</dd>
          </div>
          <div>
            <dt>{t("sim.sellOut60")}</dt>
            <dd>{percent(o.sell_out_within_60d_probability)}</dd>
          </div>
          <div>
            <dt>{t("sim.leftover90")}</dt>
            <dd>{fmtNum(i, o.leftover_after_90d, 0)}</dd>
          </div>
          <div>
            <dt>{t("sim.cash")}</dt>
            <dd>{o.cash_tied_up_minor == null ? "–" : money(o.cash_tied_up_minor)}</dd>
          </div>
          <div>
            <dt>{t("sim.contrib90")}</dt>
            <dd>{o.contribution_90d_minor == null ? "–" : money(o.contribution_90d_minor)}</dd>
          </div>
        </dl>
      ) : null}
      {ni ? <p className={styles.muted}>{ni}</p> : null}
      <div>
        <h3 className={styles.glanceTitle} style={{ margin: "0 0 var(--space-2)" }}>
          {t("sim.assumptionsTitle")}
        </h3>
        <ul className={styles.assumptions} data-testid="sim-assumptions">
          {run.assumptions.map((a, k) => (
            <li key={`${a.code}-${k}`} data-code={a.code}>
              {assumptionSentence(i, a)}
            </li>
          ))}
        </ul>
      </div>
      <p className={styles.note}>{t("sim.nothingChanges")}</p>
    </article>
  );
}

/** Poll a queued run until it finishes (the worker runs it; usually a second or two). */
export function useSimulationPoll(onDone: (r: SimulationRunView) => void) {
  const { api } = useAuth();
  const [run, setRun] = useState<SimulationRunView | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stop = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  }, []);
  useEffect(() => stop, [stop]);
  const track = useCallback(
    (first: SimulationRunView) => {
      stop();
      setRun(first);
      let polls = 0;
      const tick = async (r: SimulationRunView) => {
        if (r.status === "completed" || r.status === "failed" || polls >= MAX_POLLS) {
          onDone(r);
          return;
        }
        polls += 1;
        timer.current = setTimeout(async () => {
          try {
            const next = await api.simulations.get(r.id);
            setRun(next);
            void tick(next);
          } catch {
            /* transient: try again on the next tick */
            void tick(r);
          }
        }, POLL_MS);
      };
      void tick(first);
    },
    [api, onDone, stop],
  );
  return { run, track };
}

/** Analytics → What if (SIM-001…005). */
export function WhatIf() {
  const i = useI18n();
  const { t } = i;
  const { api, feature, can } = useAuth();
  const toast = useToast();
  const on = feature("intelligence.simulation");
  const runs = useApiQuery((a) => (on === "yes" && can("analytics.read") ? a.simulations.list() : Promise.resolve({ items: [] as SimulationRunView[] })), [on]);
  const action = useAction();
  const [kind, setKind] = useState<SimulationKind>("discount");
  const [picked, setPicked] = useState<PickedVariant | null>(null);
  const [pct, setPct] = useState("15");
  const [days, setDays] = useState("14");
  const [qty, setQty] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [open, setOpen] = useState<SimulationRunView | null>(null);
  const reload = runs.reload;
  const onDone = useCallback(
    (r: SimulationRunView) => {
      setOpen(r);
      reload();
    },
    [reload],
  );
  const poll = useSimulationPoll(onDone);
  const shown = poll.run && (!open || open.id === poll.run.id) ? poll.run : open;

  if (on === "pending") return <Skeleton height={160} />;
  if (on === "no" || (runs.state.status === "error" && isApiError(runs.state.error) && runs.state.error.status === 403 && runs.state.error.code === "feature_not_in_plan")) {
    return (
      <InlineAlert tone="info" title={t("sim.upsell")} live={false}>
        <LimitActions buyCredits={false} upgrade />
      </InlineAlert>
    );
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!picked) errs.pick = kind === "discount" ? t("sim.pickProduct") : t("sim.pickItem");
    if (kind === "discount") {
      const p = Number(pct);
      const d = Number(days);
      if (!Number.isFinite(p) || p < 1 || p > 70) errs.pct = t("sim.validPct");
      if (!Number.isInteger(d) || d < 3 || d > 60) errs.days = t("sim.validDays");
    } else {
      const q = Number(qty);
      if (!Number.isInteger(q) || q < 1) errs.qty = t("sim.validQty");
    }
    setErrors(errs);
    if (Object.keys(errs).length || !picked) return;
    const body =
      kind === "discount"
        ? { kind, discount: { product_id: picked.product_id, discount_pct: Number(pct), days: Number(days) } }
        : { kind, purchase: { variant_id: picked.variant_id, quantity: Number(qty) } };
    const r = await action.run(() => api.simulations.create(body));
    if (r) {
      setOpen(null);
      poll.track(r);
      toast(t("sim.queued"));
    }
  };

  const items = runs.state.status === "success" ? runs.state.data.items : [];
  return (
    <div data-testid="what-if">
      <form className={styles.card} onSubmit={submit} noValidate aria-labelledby="whatif-title">
        <div className={styles.head}>
          <h2 id="whatif-title">{t("intel.analytics.tabWhatIf")}</h2>
        </div>
        <p className={styles.muted}>{t("sim.intro")}</p>
        <fieldset className={styles.kinds}>
          <legend>{t("sim.kindLabel")}</legend>
          {(["discount", "purchase_quantity", "ad_budget"] as const).map((k) => (
            <label key={k} className={styles.kind}>
              <input
                type="radio"
                name="sim-kind"
                value={k}
                checked={kind === k}
                disabled={k === "ad_budget"}
                aria-describedby={k === "ad_budget" ? "sim-ad-note" : undefined}
                onChange={() => {
                  setKind(k);
                  setPicked(null);
                  setErrors({});
                }}
              />
              {k === "discount" ? t("sim.kindDiscount") : k === "purchase_quantity" ? t("sim.kindPurchase") : t("sim.kindAd")}
            </label>
          ))}
        </fieldset>
        <p className={styles.muted} id="sim-ad-note">
          {t("sim.adNeedsAccount")}
        </p>
        {picked ? (
          <div className={styles.picked}>
            <span>{t("sim.picked", { title: kind === "discount" || !picked.variant ? picked.title : `${picked.title} (${picked.variant})` })}</span>
            <Button size="sm" variant="ghost" type="button" onClick={() => setPicked(null)}>
              {t("sim.change")}
            </Button>
          </div>
        ) : (
          <VariantPicker onPick={(v) => setPicked(v)} />
        )}
        {errors.pick ? (
          <span className={styles.stale} role="alert">
            {errors.pick}
          </span>
        ) : null}
        {kind === "discount" ? (
          <div className={styles.grid}>
            <TextField label={t("sim.discountPct")} inputMode="decimal" value={pct} onChange={(e) => setPct(e.target.value)} error={errors.pct} />
            <TextField label={t("sim.days")} inputMode="numeric" value={days} onChange={(e) => setDays(e.target.value)} error={errors.days} />
          </div>
        ) : (
          <div className={styles.grid}>
            <TextField label={t("sim.quantity")} inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value)} error={errors.qty} />
          </div>
        )}
        {action.error ? <InlineAlert tone="danger">{errorMessage(t, action.error)}</InlineAlert> : null}
        <div>
          <Button type="submit" variant="primary" loading={action.pending}>
            {t("sim.run")}
          </Button>
        </div>
      </form>

      {shown ? <SimulationResult run={shown} /> : null}

      <section className={styles.card} aria-labelledby="sim-recent">
        <div className={styles.head}>
          <h2 id="sim-recent">{t("sim.recent")}</h2>
        </div>
        {items.length === 0 ? (
          <p className={styles.muted}>{t("sim.recentEmpty")}</p>
        ) : (
          <ul className={styles.runs}>
            {items.slice(0, 10).map((r) => (
              <li key={r.id}>
                <span>
                  {r.kind === "discount"
                    ? `${(r.outputs as DiscountOutputs | null)?.title ?? ""} · ${t("sim.shortDiscount", { pct: fmtNum(i, r.inputs.discount_pct, 0), days: fmtNum(i, r.inputs.days, 0) })}`
                    : r.kind === "purchase_quantity"
                      ? `${(r.outputs as PurchaseOutputs | null)?.title ?? ""} · ${t("sim.shortPurchase", { qty: fmtNum(i, r.inputs.quantity, 0) })}`
                      : t("sim.shortAd")}
                  {" · "}
                  <span className={styles.meta}>{r.created_at ? i.relative(r.created_at) : ""}</span>
                </span>
                {r.status === "completed" ? (
                  <Button size="sm" variant="ghost" onClick={() => setOpen(r)}>
                    {t("sim.open")}
                  </Button>
                ) : (
                  <span className={styles.meta}>{r.status === "failed" ? t("sim.statusFailed") : t("sim.statusPending")}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <Calibration />
    </div>
  );
}

/** SIM-006: how far off past estimates were, said plainly. */
export function Calibration() {
  const i = useI18n();
  const { t } = i;
  const q = useApiQuery((a) => a.simulations.calibration());
  if (q.state.status !== "success") return null;
  const c = q.state.data;
  const bt = c.demand_backtest;
  return (
    <section className={styles.card} aria-labelledby="sim-cal" data-testid="sim-calibration">
      <div className={styles.head}>
        <h2 id="sim-cal">{t("sim.calTitle")}</h2>
      </div>
      <p className={styles.muted}>
        {bt.mape == null ? t("sim.calBacktestNone") : t("sim.calBacktest", { days: fmtNum(i, bt.holdout_days, 0), n: fmtNum(i, bt.products, 0), mape: i.percent(bt.mape) })}
      </p>
      <p className={styles.muted}>
        {c.discount_runs_mape == null ? t("sim.calRunsNone") : t("sim.calRuns", { n: fmtNum(i, c.discount_runs_compared, 0), mape: i.percent(c.discount_runs_mape) })}
      </p>
      <p className={styles.note}>{t("sim.calNote")}</p>
    </section>
  );
}

function seconds(t: T, s: number | null): string {
  if (s == null) return "–";
  return s >= 120 ? t("twin.minutes", { n: Math.round(s / 60) }) : t("twin.seconds", { n: Math.round(s) });
}

/** TWIN-006: how fresh each part of the store summary is, for owners and managers. */
export function Freshness() {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const allowed = can("analytics.read");
  const q = useApiQuery((a) => (allowed ? a.twin.freshness() : Promise.resolve(null)), [allowed]);
  if (!allowed || q.state.status !== "success" || !q.state.data) return null;
  const f = q.state.data;
  return (
    <section className={styles.card} aria-labelledby="twin-fresh" data-testid="twin-freshness">
      <div className={styles.head}>
        <h2 id="twin-fresh">{t("twin.freshTitle")}</h2>
        <Button
          size="sm"
          variant="ghost"
          loading={action.pending}
          onClick={async () => {
            if (await action.run(() => api.twin.reconcile())) {
              toast(t("twin.refreshed"));
              q.reload();
            }
          }}
        >
          {t("twin.refresh")}
        </Button>
      </div>
      <p className={styles.muted}>{t("twin.freshIntro")}</p>
      <p className={styles.muted}>
        {f.p95_lag_s == null
          ? t("twin.freshNone")
          : f.meets_target
            ? t("twin.freshMet", { s: Math.round(f.p95_lag_s), target: f.target_p95_s })
            : t("twin.freshMissed", { s: Math.round(f.p95_lag_s), target: f.target_p95_s })}
      </p>
      {/* A scrollable region must be reachable by keyboard (WCAG 2.1.1): focusable and named. */}
      <div className={styles.tableWrap} tabIndex={0} role="region" aria-labelledby="twin-fresh">
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">{t("twin.colSection")}</th>
              <th scope="col">{t("twin.colAge")}</th>
              <th scope="col">{t("twin.colTtl")}</th>
              <th scope="col">{t("twin.colLag")}</th>
            </tr>
          </thead>
          <tbody>
            {f.sections.map((s) => (
              <tr key={s.section}>
                <th scope="row">{t.dynamic(`twin.section.${s.section}`) ?? s.section}</th>
                <td>{seconds(t, s.age_s)}</td>
                <td>{seconds(t, s.ttl_s)}</td>
                <td>{s.last_lag_ms == null ? "–" : seconds(t, s.last_lag_ms / 1000)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
