"use client";

import { isApiError, type MemoryFact } from "@commerce-os/api-client";
import Link from "next/link";
import { Fragment, useState, type ReactNode } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, Skeleton, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./intelligence.module.css";
import { isPlanGate } from "./ProfitView";

type I18n = ReturnType<typeof useI18n>;
const MARK = "\u0000";
const num = (v: unknown) => (typeof v === "number" ? v : Number(v ?? 0));
const titleCase = (s: string) => s.replace(/(^|[\s-])(\w)/g, (_m, a: string, b: string) => a + b.toUpperCase());

function hourLabel(locale: string, h: number): string {
  return new Intl.DateTimeFormat(locale === "ne" ? "ne-NP" : "en-NP", { hour: "numeric", timeZone: "UTC" }).format(Date.UTC(2026, 0, 1, ((h % 24) + 24) % 24));
}

/** One fact as a sentence; the subject (product) becomes a link when there is one. */
export function factSentence(i18n: I18n, f: MemoryFact): ReactNode {
  const { t, locale } = i18n;
  const v = f.value;
  const subject = f.subject_type === "district" ? titleCase(f.subject_id) : (f.subject_label ?? "");
  const vars: Record<string, string | number> = {
    subject: MARK,
    pct: Math.round(num(v.share) * 100) || Math.round(num(v.success) * 100),
    returns: num(v.returns),
    sold: num(v.sold),
    days: num(v.days),
    customers: num(v.customers),
    from: hourLabel(locale, num(v.start_hour)),
    to: hourLabel(locale, num(v.end_hour)),
    courier: String(v.courier ?? ""),
    n: num(v.n),
  };
  const text = t.dynamic(`intel.mem.${f.fact_type}`, vars) ?? t("intel.mem.unknownFact");
  const parts = text.split(MARK);
  const subjectNode = f.subject_type === "product" ? <Link href={`/products/${f.subject_id}`}>{subject || f.subject_id}</Link> : subject;
  return parts.map((p, i) => (
    <Fragment key={i}>
      {p}
      {i < parts.length - 1 ? subjectNode : null}
    </Fragment>
  ));
}

function sampleText(i18n: I18n, f: MemoryFact): string {
  const { t } = i18n;
  if (f.source === "merchant") return t("intel.mem.sample_seller");
  const e = (f.evidence[0] ?? {}) as Record<string, unknown>;
  if (f.fact_type.startsWith("fit_")) return t("intel.mem.sample_returns", { n: num(e.returns ?? f.value.returns) });
  if (f.fact_type === "repeat_cycle_days") return t("intel.mem.sample_intervals", { n: num(e.intervals) });
  if (f.fact_type === "peak_order_hours") return t("intel.mem.sample_orders", { n: num(e.orders) });
  return t("intel.mem.sample_parcels", { n: num(f.value.n) });
}

/** Editable fields per fact type: [key, min, max, kind]. Shares are shown as percent. */
const FIELDS: Record<string, [string, number, number, "int" | "pct" | "text"][]> = {
  fit_runs_small: [["share", 0, 100, "pct"]],
  fit_runs_large: [["share", 0, 100, "pct"]],
  repeat_cycle_days: [["days", 1, 365, "int"]],
  peak_order_hours: [
    ["start_hour", 0, 23, "int"],
    ["end_hour", 0, 23, "int"],
  ],
  best_courier_route: [["courier", 0, 0, "text"]],
};

/** UX-021: what Nivaro learned, with the seller's confirm / correct / reject. */
export function MemoryFacts() {
  const i18n = useI18n();
  const { t, number } = i18n;
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [history, setHistory] = useState(false);
  const q = useApiQuery((a) => a.intelligence.memoryFacts(history), [history]);
  const [correcting, setCorrecting] = useState<MemoryFact | null>(null);
  const [rejecting, setRejecting] = useState<MemoryFact | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [formErr, setFormErr] = useState<string | null>(null);
  const allowed = can("settings.manage");

  if (q.state.status === "loading") return <Skeleton height={80} />;
  if (q.state.status === "error") {
    if (isPlanGate(q.state.error))
      return (
        <InlineAlert tone="info" title={t("intel.profit.upsell")}>
          <LimitActions buyCredits={false} upgrade />
        </InlineAlert>
      );
    return <ErrorAlert error={q.state.error} />;
  }
  const items = q.state.data.items;
  const forbidden = isApiError(action.error) && action.error.status === 403;

  const openCorrect = (f: MemoryFact) => {
    const init: Record<string, string> = {};
    for (const [k, , , kind] of FIELDS[f.fact_type] ?? []) {
      const v = f.value[k];
      init[k] = v === null || v === undefined ? "" : kind === "pct" ? String(Math.round(num(v) * 100)) : String(v);
    }
    setValues(init);
    setNote("");
    setFormErr(null);
    setCorrecting(f);
  };

  const saveCorrection = async () => {
    if (!correcting) return;
    const out: Record<string, string | number> = {};
    for (const [k, min, max, kind] of FIELDS[correcting.fact_type] ?? []) {
      const raw = (values[k] ?? "").trim();
      if (kind === "text") {
        if (!raw) return setFormErr(t("intel.mem.invalid"));
        out[k] = raw.slice(0, 80);
        continue;
      }
      const n = Number(raw);
      if (!raw || !Number.isInteger(n) || n < min || n > max) return setFormErr(t("intel.mem.invalid"));
      out[k] = kind === "pct" ? n / 100 : n;
    }
    if (note.trim().length < 3) return setFormErr(t("intel.mem.note"));
    const done = await action.run(() => api.intelligence.correctFact(correcting.id, out, note.trim()));
    if (done) {
      setCorrecting(null);
      toast(t("intel.mem.saved"));
      q.reload();
    }
  };

  return (
    <section className={styles.card} aria-labelledby="mem-title" data-testid="memory-facts">
      <div className={styles.head}>
        <h2 id="mem-title">{t("intel.mem.title")}</h2>
        <Checkbox label={t("intel.mem.showHistory")} checked={history} onChange={(e) => setHistory(e.target.checked)} />
      </div>
      <span className={styles.muted}>{t("intel.mem.hint")}</span>
      {!allowed || forbidden ? <p className={styles.muted}>{t("intel.mem.managerOnly")}</p> : <ErrorAlert error={action.error} />}
      {items.length === 0 ? (
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.mem.empty")}
        </p>
      ) : (
        <ul className={styles.facts}>
          {items.map((f) => (
            <li key={f.id} className={styles.fact} data-fact={f.fact_type} data-status={f.status}>
              <span>{factSentence(i18n, f)}</span>
              <span className={styles.row}>
                {f.status === "active" ? (
                  <Badge tone={f.confirmed ? "success" : "neutral"} dot={false}>
                    {f.confirmed ? t("intel.mem.confirmed") : t("intel.mem.unconfirmed")}
                  </Badge>
                ) : (
                  <Badge tone="neutral" dot={false}>
                    {f.status === "superseded" ? t("intel.mem.superseded") : t("intel.mem.rejected")}
                  </Badge>
                )}
                <span className={styles.muted}>
                  {sampleText(i18n, f)} · {t("intel.mem.confidence", { pct: number(Math.round(f.confidence * 100)) })} · {t("intel.mem.version", { n: f.version })}
                  {f.source === "merchant" ? ` · ${t("intel.mem.byYou")}` : ""}
                </span>
              </span>
              {f.note ? <span className={styles.muted}>“{f.note}”</span> : null}
              {f.status === "active" && allowed ? (
                <span className={styles.row}>
                  {!f.confirmed ? (
                    <Button
                      size="sm"
                      variant="primary"
                      loading={action.pending}
                      onClick={async () => {
                        if (await action.run(() => api.intelligence.confirmFact(f.id))) {
                          toast(t("intel.mem.saved"));
                          q.reload();
                        }
                      }}
                    >
                      {t("intel.mem.confirm")}
                    </Button>
                  ) : null}
                  {FIELDS[f.fact_type] ? (
                    <Button size="sm" onClick={() => openCorrect(f)}>
                      {t("intel.mem.correct")}
                    </Button>
                  ) : null}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setNote("");
                      setRejecting(f);
                    }}
                  >
                    {t("intel.mem.reject")}
                  </Button>
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <ConfirmDialog
        open={correcting !== null}
        onOpenChange={(v) => !v && setCorrecting(null)}
        title={t("intel.mem.correctTitle")}
        confirmLabel={t("intel.mem.correct")}
        pending={action.pending}
        onConfirm={() => void saveCorrection()}
      >
        {correcting
          ? (FIELDS[correcting.fact_type] ?? []).map(([k, min, max, kind]) => (
              <TextField
                key={k}
                label={t.dynamic(`intel.mem.field_${k}`) ?? k}
                inputMode={kind === "text" ? "text" : "numeric"}
                min={kind === "text" ? undefined : min}
                max={kind === "text" ? undefined : max}
                value={values[k] ?? ""}
                onChange={(e) => setValues((s) => ({ ...s, [k]: e.target.value }))}
              />
            ))
          : null}
        <TextField label={t("intel.mem.note")} value={note} onChange={(e) => setNote(e.target.value)} minLength={3} maxLength={300} required />
        {formErr ? (
          <p role="alert" className={styles.negative} style={{ fontSize: "var(--font-size-sm)", margin: 0 }}>
            {formErr}
          </p>
        ) : null}
      </ConfirmDialog>
      <ConfirmDialog
        open={rejecting !== null}
        onOpenChange={(v) => !v && setRejecting(null)}
        title={t("intel.mem.rejectTitle")}
        confirmLabel={t("intel.mem.reject")}
        pending={action.pending}
        destructive
        onConfirm={async () => {
          if (!rejecting || note.trim().length < 3) return;
          if (await action.run(() => api.intelligence.rejectFact(rejecting.id, note.trim()))) {
            setRejecting(null);
            toast(t("intel.mem.saved"));
            q.reload();
          }
        }}
      >
        <TextField label={t("intel.mem.note")} value={note} onChange={(e) => setNote(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
    </section>
  );
}
