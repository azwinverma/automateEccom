"use client";

import type { RefundRecord, ReturnCheck, ReturnReason, ReturnSignal, ReturnStatus } from "@commerce-os/api-client";
import { Badge, type Tone } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import styles from "./returns.module.css";

export const RETURN_REASONS: ReturnReason[] = [
  "size_small",
  "size_large",
  "colour_different",
  "quality_defect",
  "damaged_in_transit",
  "not_as_described",
  "changed_mind",
  "late_delivery",
  "wrong_item",
  "other",
];

export const RETURN_TONE: Record<ReturnStatus, Tone> = {
  requested: "warning",
  approved: "info",
  rejected: "neutral",
  in_transit: "info",
  received: "info",
  inspected: "warning",
  refunded: "success",
  exchanged: "success",
  closed: "neutral",
  cancelled: "neutral",
};

const REFUND_TONE: Record<RefundRecord["status"], Tone> = {
  pending_approval: "warning",
  processing: "info",
  succeeded: "success",
  failed: "danger",
  rejected: "neutral",
};

export function ReturnStatusBadge({ status }: { status: ReturnStatus }) {
  const { t } = useI18n();
  return <Badge tone={RETURN_TONE[status] ?? "neutral"}>{t(`returns.status.${status}`)}</Badge>;
}

export function RefundStatusBadge({ status }: { status: RefundRecord["status"] }) {
  const { t } = useI18n();
  return (
    <Badge tone={REFUND_TONE[status]} dot={false}>
      {t(`returns.refund.statuses.${status}`)}
    </Badge>
  );
}

/** Policy checks as a ticked list; soft failures are warnings (overridable), hard ones errors. */
export function Checks({ checks }: { checks: ReturnCheck[] }) {
  const { t, date } = useI18n();
  return (
    <ul className={styles.checks} aria-label={t("returns.checks")}>
      {checks.map((c) => (
        <li key={c.code} className={c.ok ? styles.ok : c.soft ? styles.warn : styles.bad} data-check={c.code} data-ok={c.ok}>
          <span aria-hidden>{c.ok ? "✓" : c.soft ? "!" : "✕"}</span>
          <span>
            {t.dynamic(`returns.check.${c.code}`) ?? c.code}
            {c.code === "within_window" && c.deadline ? ` · ${date(c.deadline)}` : ""}
            {c.items?.length ? ` · ${c.items.join(", ")}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function Signals({ signals }: { signals: ReturnSignal[] }) {
  const { t } = useI18n();
  if (!signals.length) return null;
  return (
    <div className={styles.signals} data-testid="return-signals">
      <strong>{t("returns.signalsTitle")}</strong>
      <ul>
        {signals.map((s) => (
          <li key={s.code}>
            {t.dynamic(`returns.signal.${s.code}`, {
              count: s.count ?? 0,
              days: s.days ?? 0,
              returned: s.returned ?? 0,
              orders: s.orders ?? 0,
            }) ?? s.code}
          </li>
        ))}
      </ul>
      <span className={styles.muted}>{t("returns.signalsHint")}</span>
    </div>
  );
}
