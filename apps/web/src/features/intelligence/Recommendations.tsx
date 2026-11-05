"use client";

import { isApiError, type RecommendationView } from "@commerce-os/api-client";
import { useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, SectionHeader, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./intelligence.module.css";

/** UX-019: suggestion cards with what / why / confidence / impact; applying needs a manager. */
export function Recommendations() {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const q = useApiQuery((a) => (can("analytics.read") ? a.intelligence.recommendations("open") : Promise.resolve({ items: [] as RecommendationView[] })));
  const [dismissing, setDismissing] = useState<RecommendationView | null>(null);
  const [reason, setReason] = useState("");
  const items = q.state.status === "success" ? q.state.data.items : [];
  if (!items.length) return null;
  const forbidden = isApiError(action.error) && action.error.status === 403;
  return (
    <section data-testid="recommendations" aria-labelledby="rec-title" style={{ marginBottom: "var(--space-5)" }}>
      <SectionHeader title={t("intel.rec.title")} id="rec-title" />
      {forbidden ? <p className={styles.muted}>{t("intel.rec.managerOnly")}</p> : <ErrorAlert error={action.error} />}
      <ul className={styles.recs}>
        {items.map((r) => (
          <li key={r.id} className={styles.rec} data-type={r.type}>
            <strong>{what(t, r)}</strong>
            <span style={{ fontSize: "var(--font-size-sm)" }}>{why(t, r)}</span>
            <span className={styles.row}>
              <Badge tone={r.confidence >= 0.8 ? "info" : "neutral"} dot={false}>
                {t(r.confidence >= 0.8 ? "intel.rec.confidence.high" : "intel.rec.confidence.medium")}
              </Badge>
              {impact(t, r) ? <span className={styles.muted}>{impact(t, r)}</span> : null}
            </span>
            <span className={styles.row}>
              {r.action.type === "plan_upgrade" ? (
                <ButtonLink size="sm" href="/settings/plan">
                  {t("intel.rec.openPlan")}
                </ButtonLink>
              ) : r.action.type === "none" ? null : (
                <Button
                  size="sm"
                  variant="primary"
                  loading={action.pending}
                  onClick={async () => {
                    if (await action.run(() => api.intelligence.accept(r.id))) {
                      toast(t("intel.rec.applied"));
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

function what(t: T, r: RecommendationView): string {
  const vars = v(r);
  return t.dynamic(`intel.rec.what.${r.explanation.what.replace(".", "_")}`, { title: String(vars.title ?? ""), variant: String(vars.variant ?? "") }) ?? r.type;
}

function why(t: T, r: RecommendationView): string {
  const vars = v(r);
  const cap = typeof vars.capability === "string" ? (t.dynamic(`intel.aps.capability.${vars.capability}`) ?? vars.capability) : "";
  const pct = (x: unknown) => (typeof x === "number" ? Math.round(x * 100) : 0);
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
    }) ?? ""
  );
}

function impact(t: T, r: RecommendationView): string | null {
  const i = r.estimated_impact;
  if (i.capability && i.score_to != null) {
    const p = (x: unknown) => (typeof x === "number" ? `${Math.round(x * 100)}%` : "–");
    return t("intel.rec.impact.score", { capability: t.dynamic(`intel.aps.capability.${i.capability}`) ?? String(i.capability), from: p(i.score_from), to: p(i.score_to) });
  }
  if (i.routes) return t("intel.rec.impact.routes", { routes: Number(i.routes), points: Number(i.success_gain_points ?? 0) });
  return null;
}
