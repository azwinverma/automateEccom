"use client";

import { isApiError, type CodRiskAssessment, type CodRiskFactor, type OrderDetail } from "@commerce-os/api-client";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Badge, type Tone, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import orderStyles from "../orders/orders.module.css";
import { ErrorAlert } from "../orders/shared";
import styles from "./intelligence.module.css";

const TONE: Record<CodRiskAssessment["level"], Tone> = { LOW: "success", MEDIUM: "warning", HIGHER: "danger" };

/** COD Intelligence on the order page: level, why, what to do; override/dispute are audited. */
export function CodRiskCard({ order, onChanged }: { order: OrderDetail; onChanged: () => void }) {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const q = useApiQuery((a) => (order.payment_method === "cod" ? a.intelligence.codAssessment(order.id) : Promise.resolve(null)), [order.id, order.version]);
  const [open, setOpen] = useState<null | "override" | "dispute">(null);
  const [level, setLevel] = useState<CodRiskAssessment["level"]>("LOW");
  const [text, setText] = useState("");
  if (q.state.status === "error" && isApiError(q.state.error) && [403, 404].includes(q.state.error.status)) return null;
  if (q.state.status !== "success" || !q.state.data) return null;
  const a = q.state.data;
  const save = async (fn: () => Promise<CodRiskAssessment>) => {
    const next = await action.run(fn);
    if (next) {
      q.setData(() => next);
      toast(t("intel.cod.saved"));
      setOpen(null);
      setText("");
      onChanged();
    }
  };
  return (
    <section className={orderStyles.panel} aria-labelledby="o-codrisk" data-testid="cod-risk" data-level={a.level}>
      <h2 id="o-codrisk">{t("intel.cod.title")}</h2>
      <div className={styles.row} style={{ marginBottom: "var(--space-2)" }}>
        <Badge tone={TONE[a.level]}>{t(`intel.cod.level.${a.level}`)}</Badge>
        <strong style={{ fontSize: "var(--font-size-sm)" }}>{t(`intel.cod.action.${a.recommended_action}`)}</strong>
      </div>
      <ul className={styles.factors}>
        {a.factors.map((f) => (
          <li key={f.code}>
            <span>{factorText(t, f)}</span>
            <span className={f.contribution > 0 ? styles.up : styles.down}>{f.contribution > 0 ? "▲" : "▼"}</span>
          </li>
        ))}
      </ul>
      <span className={styles.muted}>{t("intel.cod.completeness", { pct: Math.round(a.data_completeness * 100) })}</span>
      {a.overridden && a.override_reason ? <span className={styles.muted}>{t("intel.cod.overridden", { reason: a.override_reason })}</span> : null}
      {a.disputed && a.dispute_note ? <span className={styles.muted}>{t("intel.cod.disputed", { note: a.dispute_note })}</span> : null}
      {can("orders.write") ? (
        <div className={styles.row} style={{ marginTop: "var(--space-2)" }}>
          <Button size="sm" variant="ghost" onClick={() => (setLevel(a.level), setOpen("override"))}>
            {t("intel.cod.override")}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setOpen("dispute")}>
            {t("intel.cod.dispute")}
          </Button>
        </div>
      ) : null}
      <p className={styles.fair}>{t("intel.cod.fairness")}</p>
      <Drawer
        open={open !== null}
        onOpenChange={(v) => !v && setOpen(null)}
        title={open === "dispute" ? t("intel.cod.disputeTitle") : t("intel.cod.overrideTitle")}
        footer={
          <Button
            variant="primary"
            disabled={text.trim().length < 3}
            loading={action.pending}
            onClick={() =>
              void save(() => (open === "dispute" ? api.intelligence.codDispute(order.id, text.trim()) : api.intelligence.codOverride(order.id, level, text.trim())))
            }
          >
            {t("couriers.save")}
          </Button>
        }
      >
        <div style={{ display: "grid", gap: "var(--space-3)" }}>
          <ErrorAlert error={action.error} />
          {open === "override" ? (
            <SelectField label={t("intel.cod.overrideLevel")} value={level} onChange={(e) => setLevel(e.target.value as CodRiskAssessment["level"])}>
              {(["LOW", "MEDIUM", "HIGHER"] as const).map((l) => (
                <option key={l} value={l}>
                  {t(`intel.cod.level.${l}`)}
                </option>
              ))}
            </SelectField>
          ) : null}
          <TextField label={open === "dispute" ? t("intel.cod.disputeNote") : t("intel.cod.reason")} value={text} onChange={(e) => setText(e.target.value)} minLength={3} maxLength={500} required />
        </div>
      </Drawer>
    </section>
  );
}

function factorText(t: ReturnType<typeof useI18n>["t"], f: CodRiskFactor): string {
  const e = f.evidence;
  switch (f.code) {
    case "delivery_history":
      return t("intel.cod.factor.delivery_history", { delivered: Number(e.delivered ?? 0), failed: Number(e.failed ?? 0) });
    case "new_customer":
      return t("intel.cod.factor.new_customer");
    case "return_history":
      return t("intel.cod.factor.return_history", { returns: Number(e.returns ?? 0) });
    case "address_completeness":
      return t(e.complete ? "intel.cod.factor.address_partial" : "intel.cod.factor.address_incomplete");
    case "order_value":
      return t("intel.cod.factor.order_value", { ratio: Number(e.ratio ?? 0) });
    case "route_failures":
      return t("intel.cod.factor.route_failures", { pct: Math.round(Number(e.failed_rate ?? 0) * 100), district: String(e.district ?? ""), n: Number(e.n ?? 0) });
  }
}
