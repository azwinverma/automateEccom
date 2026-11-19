"use client";

import type { ReturnInsightView } from "@commerce-os/api-client";
import Link from "next/link";
import { useState } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, Skeleton, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./intelligence.module.css";
import { isPlanGate } from "./ProfitView";

type T = ReturnType<typeof useI18n>["t"];
const pct = (x: number | null | undefined) => (typeof x === "number" ? Math.round(x * 100) : 0);

export function reasonLabel(t: T, reason: string): string {
  return t.dynamic(`intel.retReason.${reason}`) ?? reason;
}

export function patternSentence(t: T, i: ReturnInsightView): string {
  if (i.reason) return t("intel.ret.patternReason", { pct: pct(i.reason_share), reason: reasonLabel(t, i.reason) });
  return t("intel.ret.patternHigh");
}

/** One insight (UX-020 Return Insight Card). `onDismiss` omitted = read-only. */
export function ReturnInsightItem({ insight: i, showTitle, onDismiss }: { insight: ReturnInsightView; showTitle?: boolean; onDismiss?: (i: ReturnInsightView) => void }) {
  const { t } = useI18n();
  const causes = i.causes
    .map((c) =>
      c.type === "variant"
        ? t("intel.ret.causeVariant", { variant: c.variant ?? "", ret: pct(c.returned_share), sold: pct(c.sold_share) })
        : c.type === "supplier"
          ? t("intel.ret.causeSupplier", { supplier: c.supplier ?? "" })
          : t("intel.ret.causeContent"),
    )
    .filter(Boolean);
  return (
    <li className={styles.insight} data-testid="return-insight" data-pattern={i.pattern} data-status={i.status}>
      <span className={styles.row} style={{ justifyContent: "space-between" }}>
        <strong>
          {showTitle && i.title ? (
            <>
              <Link href={`/products/${i.product_id}`}>{i.title}</Link>
              {": "}
            </>
          ) : null}
          {patternSentence(t, i)}
        </strong>
        <Badge tone={i.status === "open" ? "warning" : i.status === "acted" || i.status === "resolved" ? "success" : "neutral"} dot={false}>
          {t.dynamic(`intel.ret.status_${i.status}`) ?? i.status}
        </Badge>
      </span>
      <span>
        {i.baseline_rate !== null
          ? t("intel.ret.rate", { rate: pct(i.rate), returned: i.returned, sold: i.sold, base: pct(i.baseline_rate) })
          : t("intel.ret.rateNoBase", { rate: pct(i.rate), returned: i.returned, sold: i.sold })}
      </span>
      {causes.length ? (
        <ul className={styles.missing} style={{ color: "var(--color-text-primary)" }}>
          {causes.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      ) : null}
      {i.status === "acted" ? (
        <span className={styles.muted}>
          {i.post_change_rate !== null ? t("intel.ret.after", { rate: pct(i.post_change_rate), sold: i.post_change_sold ?? 0 }) : t("intel.ret.measuring")}
        </span>
      ) : null}
      {onDismiss && (i.status === "open" || i.status === "acted") ? (
        <span className={styles.row}>
          <Button size="sm" variant="ghost" onClick={() => onDismiss(i)}>
            {t("intel.ret.dismiss")}
          </Button>
        </span>
      ) : null}
    </li>
  );
}

/** Return patterns across the shop, with dismiss (RTI-002/005). */
export function ReturnInsights() {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const q = useApiQuery((a) => a.intelligence.returnInsights());
  const [dismissing, setDismissing] = useState<ReturnInsightView | null>(null);
  const [reason, setReason] = useState("");
  if (q.state.status === "loading") return <Skeleton height={80} />;
  if (q.state.status === "error") {
    if (isPlanGate(q.state.error))
      return (
        <InlineAlert tone="info" title={t("intel.ret.upsell")}>
          <LimitActions buyCredits={false} upgrade />
        </InlineAlert>
      );
    return <ErrorAlert error={q.state.error} />;
  }
  const items = q.state.data.items;
  return (
    <section className={styles.card} aria-labelledby="ret-title" data-testid="return-insights">
      <div className={styles.head}>
        <h2 id="ret-title">{t("intel.ret.title")}</h2>
      </div>
      <span className={styles.muted}>{t("intel.ret.hint")}</span>
      <ErrorAlert error={action.error} />
      {items.length === 0 ? (
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.ret.empty")}
        </p>
      ) : (
        <ul className={styles.facts}>
          {items.map((i) => (
            <ReturnInsightItem
              key={i.id}
              insight={i}
              showTitle
              onDismiss={(x) => {
                setReason("");
                setDismissing(x);
              }}
            />
          ))}
        </ul>
      )}
      <ConfirmDialog
        open={dismissing !== null}
        onOpenChange={(v) => !v && setDismissing(null)}
        title={t("intel.ret.dismissTitle")}
        confirmLabel={t("intel.ret.dismiss")}
        pending={action.pending}
        onConfirm={async () => {
          if (!dismissing || reason.trim().length < 3) return;
          if (await action.run(() => api.intelligence.dismissReturnInsight(dismissing.id, reason.trim()))) {
            setDismissing(null);
            toast(t("intel.mem.saved"));
            q.reload();
          }
        }}
      >
        <TextField label={t("intel.ret.dismissReason")} value={reason} onChange={(e) => setReason(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
    </section>
  );
}
