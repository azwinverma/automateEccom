"use client";

import { isApiError } from "@commerce-os/api-client";
import type { ReactNode } from "react";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";
import { InlineAlert, RequestId, Skeleton } from "../ui/misc";
import styles from "./states.module.css";

export function EmptyState({ title, body, actions }: { title: ReactNode; body?: ReactNode; actions?: ReactNode }) {
  return (
    <div className={styles.block}>
      <span className={styles.mark} aria-hidden="true" />
      <p className={styles.title}>{title}</p>
      {body ? <p className={styles.body}>{body}</p> : null}
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  );
}

/** Full error state: localized message, small request id for support, retry. */
export function ErrorState({ error, onRetry, title }: { error: unknown; onRetry?: () => void; title?: ReactNode }) {
  const { t } = useI18n();
  return (
    <div className={styles.block} role="alert">
      <span className={[styles.mark, styles.markDanger].join(" ")} aria-hidden="true" />
      <p className={styles.title}>{title ?? t("states.errorTitle")}</p>
      <p className={styles.body}>{errorMessage(t, error)}</p>
      <RequestId id={isApiError(error) ? error.requestId : null} />
      {onRetry ? (
        <div className={styles.actions}>
          <Button onClick={onRetry}>
            <Icon name="refresh" />
            {t("common.retry")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export function PermissionDenied({ permission }: { permission?: string | null }) {
  const { t } = useI18n();
  return (
    <div className={styles.block}>
      <span className={styles.markLock} aria-hidden="true">
        <Icon name="lock" size={20} />
      </span>
      <p className={styles.title}>{t("states.permissionTitle")}</p>
      <p className={styles.body}>
        {permission ? t("states.permissionBody", { permission }) : t("states.permissionBodyGeneric")}
      </p>
    </div>
  );
}

export function isPermissionDenied(error: unknown): boolean {
  return isApiError(error) && error.status === 403 && error.code === "permission_denied";
}

export function deniedPermission(error: unknown): string | null {
  if (!isApiError(error)) return null;
  const p = error.details.permission;
  return typeof p === "string" ? p : null;
}

/** Choose permission-denied vs generic error view. */
export function QueryError({ error, onRetry, title }: { error: unknown; onRetry?: () => void; title?: ReactNode }) {
  if (isPermissionDenied(error)) return <PermissionDenied permission={deniedPermission(error)} />;
  return <ErrorState error={error} onRetry={onRetry} title={title} />;
}

export function DegradedBanner({ errors, onRetry }: { errors: unknown[]; onRetry?: () => void }) {
  const { t } = useI18n();
  const first = errors[0];
  return (
    <InlineAlert
      tone="warning"
      title={t("states.degraded")}
      action={
        onRetry ? (
          <Button size="sm" variant="ghost" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ) : null
      }
    >
      <RequestId id={isApiError(first) ? first.requestId : null} />
    </InlineAlert>
  );
}

/** Skeleton rows shaped like the table they stand in for. */
export function TableSkeleton({ columns, rows = 5, label }: { columns: string; rows?: number; label: string }) {
  const cols = columns.split(" ").length;
  return (
    <div className={styles.skeletonRows} role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className={styles.skeletonRow} style={{ gridTemplateColumns: columns }}>
          {Array.from({ length: cols }, (_, c) => (
            <Skeleton key={c} width={c === 0 ? "70%" : "50%"} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function FullPageMessage({ children }: { children: ReactNode }) {
  return <div className={styles.fullPage}>{children}</div>;
}
