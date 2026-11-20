"use client";

import { isApiError, type RecommendationView } from "@commerce-os/api-client";
import Link from "next/link";
import { useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, SectionHeader, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import { outcomeWord, valueLabel } from "./creativeLabels";
import styles from "./intelligence.module.css";

/** UX-019: suggestion cards with what / why / confidence / impact; applying needs a manager. */
export function Recommendations() {
  const { t, money: fmt } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const q = useApiQuery((a) =>
    can("analytics.read") ? a.intelligence.recommendations("open") : Promise.resolve({ items: [] as RecommendationView[], currency: undefined as string | undefined }),
  );
  const [dismissing, setDismissing] = useState<RecommendationView | null>(null);
  const [reason, setReason] = useState("");
  const [draftReady, setDraftReady] = useState(false);
  const items = q.state.status === "success" ? q.state.data.items : [];
  const currency = q.state.status === "success" ? q.state.data.currency : undefined;
  const money: Money = (minor, c) => fmt(minor, c ?? currency);
  // Applying a reorder creates a draft PO: say where it is even after the card disappears.
  const draftNote = draftReady ? (
    <InlineAlert tone="success" live>
      <span className={styles.row}>
        {t("intel.rec.reorderApplied")}
        <Link href="/inventory/purchase-orders?status=draft">{t("intel.rec.openDrafts")}</Link>
      </span>
    </InlineAlert>
  ) : null;
  if (!items.length) return draftNote;
  const forbidden = isApiError(action.error) && action.error.status === 403;
  return (
    <section data-testid="recommendations" aria-labelledby="rec-title" style={{ marginBottom: "var(--space-5)" }}>
      <SectionHeader title={t("intel.rec.title")} id="rec-title" />
      {forbidden ? <p className={styles.muted}>{t("intel.rec.managerOnly")}</p> : <ErrorAlert error={action.error} />}
      {draftNote}
      <ul className={styles.recs}>
        {items.map((r) => (
          <li key={r.id} className={styles.rec} data-type={r.type}>
            <strong>{what(t, r)}</strong>
            <span style={{ fontSize: "var(--font-size-sm)" }}>{why(t, money, r)}</span>
            <span className={styles.row}>
              <Badge tone={r.confidence >= 0.8 ? "info" : "neutral"} dot={false}>
                {t(r.confidence >= 0.8 ? "intel.rec.confidence.high" : "intel.rec.confidence.medium")}
              </Badge>
              {impact(t, money, r) ? <span className={styles.muted}>{impact(t, money, r)}</span> : null}
            </span>
            <span className={styles.row}>
              {r.action.type === "plan_upgrade" ? (
                <ButtonLink size="sm" href="/settings/plan">
                  {t("intel.rec.openPlan")}
                </ButtonLink>
              ) : r.action.type === "none" ? (
                r.subject_type === "product" && r.subject_id ? (
                  <ButtonLink size="sm" href={`/products/${r.subject_id}`}>
                    {t("intel.rec.openProduct")}
                  </ButtonLink>
                ) : null
              ) : (
                <Button
                  size="sm"
                  variant="primary"
                  loading={action.pending}
                  onClick={async () => {
                    if (await action.run(() => api.intelligence.accept(r.id))) {
                      if (r.action.type === "create_po_draft") setDraftReady(true);
                      else toast(t("intel.rec.applied"));
                      q.reload();
                    }
                  }}
                >
                  {t("intel.rec.apply")}
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={() => setDismissing(r)}>
                {r.action.type === "none" ? t("intel.rec.acknowledge") : t("intel.rec.dismiss")}
              </Button>
            </span>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={dismissing !== null}
        onOpenChange={(v) => !v && setDismissing(null)}
        title={t("intel.rec.dismissTitle")}
        confirmLabel={t("intel.rec.dismiss")}
        pending={action.pending}
        onConfirm={async () => {
          if (!dismissing || reason.trim().length < 3) return;
          if (await action.run(() => api.intelligence.reject(dismissing.id, reason.trim()))) {
            setDismissing(null);
            setReason("");
            q.reload();
          }
        }}
      >
        <TextField label={t("intel.rec.dismissReason")} value={reason} onChange={(e) => setReason(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
    </section>
  );
}

type T = ReturnType<typeof useI18n>["t"];
const v = (r: RecommendationView) => r.explanation.vars ?? {};

const label = (vars: Record<string, unknown>) => [String(vars.title ?? ""), vars.variant ? `(${String(vars.variant)})` : ""].filter(Boolean).join(" ");

function what(t: T, r: RecommendationView): string {
  const vars = v(r);
  if (r.explanation.what === "reorder") return t("intel.rec.what.reorder", { label: label(vars) });
  if (r.explanation.what === "switch_supplier") return t("intel.rec.what.switch_supplier", { label: label(vars), to: String(vars.to ?? "") });
  if (r.type === "creative_tip") {
    const attribute = String(r.action.params?.attribute ?? r.explanation.what.replace(/^creative_/, ""));
    return t("intel.rec.what.creative_tip", { pattern: valueLabel(t, attribute, String(vars.value ?? "")) });
  }
  return t.dynamic(`intel.rec.what.${r.explanation.what.replace(".", "_")}`, { title: String(vars.title ?? ""), variant: String(vars.variant ?? "") }) ?? r.type;
}

type Money = ReturnType<typeof useI18n>["money"];

function why(t: T, money: Money, r: RecommendationView): string {
  const vars = v(r);
  const cap = typeof vars.capability === "string" ? (t.dynamic(`intel.aps.capability.${vars.capability}`) ?? vars.capability) : "";
  const pct = (x: unknown) => (typeof x === "number" ? Math.round(x * 100) : 0);
  const amount = (x: unknown) => (typeof x === "number" ? money(x) : "–");
  if (r.explanation.why === "runs_out_before_delivery") {
    const num = (x: unknown) => (typeof x === "number" ? x : 0);
    const main = t("intel.rec.why.runs_out_before_delivery", {
      label: label(vars),
      days_left: num(vars.days_left),
      per_day: num(vars.per_day),
      available: num(vars.available),
      supplier: String(vars.supplier ?? ""),
      lead_days: num(vars.lead_days),
    });
    const incoming = num(vars.incoming) > 0 ? ` ${t("intel.rec.why.runs_out_incoming", { incoming: num(vars.incoming) })}` : "";
    const qty = num(vars.quantity);
    const atMoq = typeof vars.moq === "number" && qty === vars.moq;
    return `${main}${incoming} ${t(atMoq ? "intel.rec.reorderQtyMoq" : "intel.rec.reorderQty", { quantity: qty })}`;
  }
  if (r.explanation.why === "true_economics") {
    return t("intel.rec.why.true_economics", {
      to: String(vars.to ?? ""),
      from: String(vars.from ?? ""),
      gain: amount(vars.gain_per_unit),
      to_landed: amount(vars.to_landed),
      from_landed: amount(vars.from_landed),
      to_defect: Number(vars.to_defect_pct ?? 0),
      from_defect: Number(vars.from_defect_pct ?? 0),
    });
  }
  if (r.explanation.why === "creative_pattern") {
    return t("intel.rec.why.creative_pattern", { lift_pct: Number(vars.lift_pct ?? 0), outcome: outcomeWord(t, String(vars.outcome ?? "orders")), n: Number(vars.n ?? 0) });
  }
  if (r.explanation.why === "return_pattern") {
    const base = vars.baseline_pct;
    const main = t(base === null || base === undefined ? "intel.rec.why.return_pattern_nobase" : "intel.rec.why.return_pattern", {
      returned: Number(vars.returned ?? 0),
      sold: Number(vars.sold ?? 0),
      rate_pct: Number(vars.rate_pct ?? 0),
      baseline_pct: Number(base ?? 0),
    });
    const reason = typeof vars.reason === "string" ? (t.dynamic(`intel.retReason.${vars.reason}`) ?? vars.reason) : null;
    return reason && vars.share_pct != null ? `${main} ${t("intel.rec.why.return_share", { share_pct: Number(vars.share_pct), reason })}` : main;
  }
  return (
    t.dynamic(`intel.rec.why.${r.explanation.why}`, {
      manual: Number(vars.manual ?? 0),
      eligible: Number(vars.eligible ?? 0),
      capability: cap,
      their_pct: pct(vars.their_success),
      default_pct: pct(vars.default_success),
      destination: String(vars.destination ?? ""),
      their_n: Number(vars.their_n ?? 0),
      sold_30d: Number(vars.sold_30d ?? 0),
      available: Number(vars.available ?? 0),
      cover_days: vars.cover_days ?? "–",
      units: Number(vars.units ?? 0),
      contribution: amount(vars.contribution),
      per_unit: amount(vars.per_unit),
      revenue: amount(vars.revenue),
    }) ?? ""
  );
}

function impact(t: T, money: Money, r: RecommendationView): string | null {
  const i = r.estimated_impact;
  if (i.capability && i.score_to != null) {
    const p = (x: unknown) => (typeof x === "number" ? `${Math.round(x * 100)}%` : "–");
    return t("intel.rec.impact.score", { capability: t.dynamic(`intel.aps.capability.${i.capability}`) ?? String(i.capability), from: p(i.score_from), to: p(i.score_to) });
  }
  if (i.routes) return t("intel.rec.impact.routes", { routes: Number(i.routes), points: Number(i.success_gain_points ?? 0) });
  if (r.type === "supplier_switch" && typeof i.gain_per_unit_minor === "number") {
    return t("intel.rec.impactGain", { amount: money(i.gain_per_unit_minor) });
  }
  if (r.type === "restock" && typeof i.contribution_30d_minor === "number" && i.contribution_30d_minor > 0) {
    return t("intel.rec.impactContribution", { amount: money(i.contribution_30d_minor) });
  }
  return null;
}
