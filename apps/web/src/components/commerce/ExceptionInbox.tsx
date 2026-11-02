"use client";

import type { Money } from "@commerce-os/api-client";
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
  "ambiguous_variant",
  "customer_escalation",
  "provider_failure",
] as const;

export type ExceptionType = (typeof EXCEPTION_TYPES)[number];
export type ExceptionSeverity = "high" | "medium" | "low";

export interface ExceptionItem {
  id: string;
  type: ExceptionType;
  severity: ExceptionSeverity;
  /** Server-provided, already-localized one-line summary (e.g. order + customer). */
  summary: string;
  /** Order number, product SKU, channel name… */
  reference?: string;
  amount?: Money;
  occurredAt: string;
}

export type ExceptionInboxProps =
  | { state: "loading" }
  | { state: "error"; error: unknown; onRetry?: () => void }
  | { state: "ready"; items: ExceptionItem[]; onAction?: (item: ExceptionItem) => void };

const SEVERITY_CLASS: Record<ExceptionSeverity, string | undefined> = {
  high: styles.sevHigh,
  medium: styles.sevMedium,
  low: undefined,
};

const SEVERITY_ORDER: Record<ExceptionSeverity, number> = { high: 0, medium: 1, low: 2 };

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
            .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.occurredAt.localeCompare(a.occurredAt))
            .map((item) => (
              <li key={item.id} className={[styles.inboxItem, SEVERITY_CLASS[item.severity]].filter(Boolean).join(" ")} data-type={item.type}>
                <div>
                  <div className={styles.itemType}>
                    <span>{t(`exceptions.type.${item.type}`)}</span>
                    <span className={styles.itemSeverity}>
                      {t(item.severity === "high" ? "exceptions.severityHigh" : item.severity === "medium" ? "exceptions.severityMedium" : "exceptions.severityLow")}
                    </span>
                  </div>
                  <p className={styles.itemSummary}>{item.summary}</p>
                  <div className={styles.itemMeta}>
                    {item.reference ? <span className="mono">{item.reference}</span> : null}
                    {item.amount ? <span className="tabular">{money(item.amount.amount_minor, item.amount.currency)}</span> : null}
                    <time dateTime={item.occurredAt} title={dateTime(item.occurredAt)}>
                      {relative(item.occurredAt)}
                    </time>
                  </div>
                </div>
                <Button size="sm" onClick={() => props.onAction?.(item)}>
                  {t(`exceptions.action.${item.type}`)}
                </Button>
              </li>
            ))}
        </ul>
      ) : null}
    </section>
  );
}
