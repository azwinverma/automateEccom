"use client";

import type { ProductStatus, PublishProblem } from "@commerce-os/api-client";
import { Button } from "@/components/ui/Button";
import { Badge, InlineAlert } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { PROBLEM_SECTION, allowedTransitions, transitionAction } from "@/lib/catalog/status";
import { STATUS_TONE } from "./ProductsList";
import styles from "./products.module.css";

/**
 * Current status plus one button per allowed transition only. Disabled (with the reason)
 * when the user can't publish or has unsaved edits.
 */
export function StatusControl({
  status,
  canPublish,
  dirty,
  pending,
  onChange,
}: {
  status: ProductStatus;
  canPublish: boolean;
  dirty: boolean;
  pending: ProductStatus | null;
  onChange: (to: ProductStatus) => void;
}) {
  const { t } = useI18n();
  const blocked = !canPublish || dirty;
  return (
    <div className={styles.statusControl} role="group" aria-label={t("products.editor.statusActions")} data-testid="status-control">
      <Badge tone={STATUS_TONE[status]}>{t(`products.status.${status}`)}</Badge>
      {allowedTransitions(status).map((to) => {
        const action = transitionAction(status, to);
        return (
          <Button
            key={to}
            size="sm"
            variant={action === "publish" ? "primary" : "secondary"}
            disabled={blocked || (pending !== null && pending !== to)}
            loading={pending === to}
            onClick={() => onChange(to)}
          >
            {t(`products.editor.statusAction.${action}`)}
          </Button>
        );
      })}
      {!canPublish ? (
        <span className={styles.statusHint}>{t("products.editor.noPublishPermission")}</span>
      ) : dirty ? (
        <span className={styles.statusHint}>{t("products.editor.saveFirst")}</span>
      ) : null}
    </div>
  );
}

export function PublishChecklist({ problems }: { problems: PublishProblem[] }) {
  const { t } = useI18n();
  if (!problems.length) return null;
  return (
    <InlineAlert tone="warning" title={t("products.editor.notPublishableTitle")}>
      <ul className={styles.checklist} data-testid="publish-checklist">
        {problems.map((p) => (
          <li key={p}>
            <a href={`#${PROBLEM_SECTION[p]}`}>{t(`products.editor.problem.${p}`)}</a>
          </li>
        ))}
      </ul>
    </InlineAlert>
  );
}
