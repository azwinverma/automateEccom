"use client";

import type { ReturnPolicy, ReturnReason } from "@commerce-os/api-client";
import { useEffect, useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Checkbox, TextField } from "@/components/ui/Field";
import { PageHeader, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import { RETURN_REASONS } from "../returns/shared";
import styles from "../returns/returns.module.css";

const toRs = (m: number) => String(m / 100);
const toMinor = (s: string) => Math.max(0, Math.round((Number(s.replace(/,/g, "")) || 0) * 100));

/** Settings → Returns: the policy the eligibility check and automation follow (RET-001/010). */
export function ReturnPolicyView() {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const policy = useApiQuery((a) => a.returns.policy());
  const [form, setForm] = useState<ReturnPolicy | null>(null);
  const [fee, setFee] = useState("0");
  const [autoMax, setAutoMax] = useState("0");
  const manage = can("settings.manage");
  useEffect(() => {
    if (policy.state.status === "success") {
      setForm(policy.state.data);
      setFee(toRs(policy.state.data.return_shipping_fee_minor));
      setAutoMax(toRs(policy.state.data.auto_refund_max_minor));
    }
  }, [policy.state]);
  if (policy.state.status === "error") return <QueryError error={policy.state.error} onRetry={policy.reload} />;
  if (!form) return <TableSkeleton columns="1fr" rows={5} label={t("common.loading")} />;
  const toggleReason = (r: ReturnReason, on: boolean) =>
    setForm({ ...form, evidence_reasons: on ? [...form.evidence_reasons, r] : form.evidence_reasons.filter((x) => x !== r) });
  return (
    <>
      <PageHeader title={t("returns.policy.title")} subtitle={t("returns.policy.subtitle")} level={2} />
      <form
        data-testid="return-policy"
        style={{ display: "grid", gap: "var(--space-4)", maxWidth: 620 }}
        onSubmit={async (e) => {
          e.preventDefault();
          const next = await action.run(() =>
            api.returns.updatePolicy({ ...form, return_shipping_fee_minor: toMinor(fee), auto_refund_max_minor: toMinor(autoMax) }),
          );
          if (next) {
            setForm(next);
            toast(t("returns.policy.saved"));
          }
        }}
      >
        <ErrorAlert error={action.error} />
        <TextField
          label={t("returns.policy.window")}
          type="number"
          min={0}
          max={90}
          value={form.window_days}
          disabled={!manage}
          onChange={(e) => setForm({ ...form, window_days: Math.max(0, Math.min(90, Number(e.target.value) || 0)) })}
        />
        <div className={styles.row}>
          <Checkbox label={t("returns.policy.allowRefund")} checked={form.allow_refund} disabled={!manage} onChange={(e) => setForm({ ...form, allow_refund: e.target.checked })} />
          <Checkbox label={t("returns.policy.allowExchange")} checked={form.allow_exchange} disabled={!manage} onChange={(e) => setForm({ ...form, allow_exchange: e.target.checked })} />
        </div>
        <fieldset style={{ border: 0, padding: 0, margin: 0, display: "grid", gap: "var(--space-2)" }}>
          <legend style={{ fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-2)" }}>{t("returns.policy.evidence")}</legend>
          <div className={styles.split}>
            {RETURN_REASONS.map((r) => (
              <Checkbox key={r} label={t(`returns.reason.${r}`)} checked={form.evidence_reasons.includes(r)} disabled={!manage} onChange={(e) => toggleReason(r, e.target.checked)} />
            ))}
          </div>
        </fieldset>
        <TextField label={t("returns.policy.fee")} inputMode="decimal" value={fee} disabled={!manage} onChange={(e) => setFee(e.target.value)} />
        <div>
          <Checkbox label={t("returns.policy.autoApprove")} checked={form.auto_approve} disabled={!manage} onChange={(e) => setForm({ ...form, auto_approve: e.target.checked })} />
          <p className={styles.muted} style={{ margin: "var(--space-1) 0 0" }}>
            {t("returns.policy.autoApproveHint")}
          </p>
        </div>
        <TextField label={t("returns.policy.autoRefund")} hint={t("returns.policy.autoRefundHint")} inputMode="decimal" value={autoMax} disabled={!manage} onChange={(e) => setAutoMax(e.target.value)} />
        <TextField label={t("returns.policy.notes")} value={form.notes ?? ""} disabled={!manage} onChange={(e) => setForm({ ...form, notes: e.target.value || null })} maxLength={1000} />
        {manage ? (
          <div>
            <Button type="submit" variant="primary" loading={action.pending}>
              {t("couriers.save")}
            </Button>
          </div>
        ) : null}
      </form>
    </>
  );
}
