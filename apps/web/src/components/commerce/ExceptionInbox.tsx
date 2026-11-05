"use client";

import type { Money } from "@commerce-os/api-client";
import type { ReactNode } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/misc";
import { EmptyState, ErrorState } from "../states/States";
import styles from "./commerce.module.css";

export const EXCEPTION_TYPES = [
  "payment_mismatch",
  "low_confidence_ai",
  "refund_above_threshold",
  "courier_failed",
  "channel_expired",
  "inventory_mismatch",
  "publish_failed",
  "listing_drift",
  "usage_limit",
  "ambiguous_variant",
  "customer_escalation",
  "provider_failure",
  "delivery_failed",
  "shipment_stuck",
  "shipment_lost",
  "return_to_receive",
  "cod_settlement_mismatch",
  "courier_error",
  "return_requested",
  "return_to_inspect",
  "refund_due",
  "refund_failed",
  "automation_approval",
  "automation_paused",
] as const;

export type ExceptionType = (typeof EXCEPTION_TYPES)[number];
/** Matches `GET /exceptions` severities. */
export type ExceptionSeverity = "urgent" | "high" | "normal";

export interface ExceptionItem {
  id: string;
  /** Known types get a label; unknown future types fall back to a generic one. */
  type: ExceptionType | (string & {});
  severity: ExceptionSeverity;
  /** Server-provided, already-localized one-line summary (e.g. order + customer). */
  summary: string;
  /** Order number, product SKU, channel name… */
  reference?: string;
  amount?: Money;
  occurredAt: string | null;
}

export type ExceptionInboxProps =
  | { state: "loading" }
  | { state: "error"; error: unknown; onRetry?: () => void }
  | {
      state: "ready";
      items: ExceptionItem[];
      onAction?: (item: ExceptionItem) => void;
      /** Custom control per item (link or command); defaults to a button calling onAction. */
      renderAction?: (item: ExceptionItem) => ReactNode;
    };

const SEVERITY_CLASS: Record<ExceptionSeverity, string | undefined> = {
  urgent: styles.sevHigh,
  high: styles.sevMedium,
  normal: undefined,
};

const SEVERITY_ORDER: Record<ExceptionSeverity, number> = { urgent: 0, high: 1, normal: 2 };
const SEVERITY_LABEL = {
  urgent: "exceptions.severityHigh",
  high: "exceptions.severityMedium",
  normal: "exceptions.severityLow",
} as const;

export function ExceptionInbox(props: ExceptionInboxProps) {
  const { t, number, money, relative, dateTime } = useI18n();
  const headingId = "exception-inbox-heading";
  const count = props.state === "ready" ? props.items.length : null;

  return (
    <section aria-labelledby={headingId} data-testid="exception-inbox" data-state={props.state}>
      <div className={styles.inboxHeader}>
        <h2 id={headingId}>{t("exceptions.title")}</h2>
        {count ? <span className={styles.inboxCount}>{t("exceptions.openCount", { count: number(count) })}</span> : null}
      </div>

      {props.state === "loading" ? (
        <div role="status" aria-label={t("exceptions.loading")} className={styles.inboxList}>
          {[0, 1, 2].map((i) => (
            <div key={i} className={styles.skeletonItem}>
              <Skeleton width={120} height={10} />
              <Skeleton width="60%" height={14} />
            </div>
          ))}
        </div>
      ) : null}

      {props.state === "error" ? (
        <ErrorState title={t("exceptions.errorTitle")} error={props.error} onRetry={props.onRetry} />
      ) : null}

      {props.state === "ready" && props.items.length === 0 ? (
        <EmptyState title={t("exceptions.emptyTitle")} body={t("exceptions.emptyBody")} />
      ) : null}

      {props.state === "ready" && props.items.length > 0 ? (
        <ul className={styles.inboxList}>
          {[...props.items]
            .sort(
              (a, b) =>
                (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3) ||
                (b.occurredAt ?? "").localeCompare(a.occurredAt ?? ""),
            )
            .map((item) => (
              <li key={item.id} className={[styles.inboxItem, SEVERITY_CLASS[item.severity]].filter(Boolean).join(" ")} data-type={item.type}>
                <div>
                  <div className={styles.itemType}>
                    <span>{t.dynamic(`exceptions.type.${item.type}`) ?? t("exceptions.summary.generic")}</span>
                    <span className={styles.itemSeverity}>{t(SEVERITY_LABEL[item.severity] ?? "exceptions.severityLow")}</span>
                  </div>
                  <p className={styles.itemSummary}>{item.summary}</p>
                  <div className={styles.itemMeta}>
                    {item.reference ? <span className="mono">{item.reference}</span> : null}
                    {item.amount ? <span className="tabular">{money(item.amount.amount_minor, item.amount.currency)}</span> : null}
                    {item.occurredAt ? (
                      <time dateTime={item.occurredAt} title={dateTime(item.occurredAt)}>
                        {relative(item.occurredAt)}
                      </time>
                    ) : null}
                  </div>
                </div>
                {props.renderAction ? (
                  props.renderAction(item)
                ) : (
                  <Button size="sm" onClick={() => props.onAction?.(item)}>
                    {t.dynamic(`exceptions.action.${item.type}`) ?? t("exceptions.actionLabel.review_post")}
                  </Button>
                )}
              </li>
            ))}
        </ul>
      ) : null}
    </section>
  );
}
