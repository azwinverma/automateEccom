"use client";

import type { DecisionRecordView } from "@commerce-os/api-client";
import { useI18n } from "@/i18n/I18nProvider";

/** Plain-words label for an automated action (including the Sales Agent and returns automation). */
export function useActionLabel() {
  const { t } = useI18n();
  return (action: string | null | undefined) =>
    action === "send_ai_reply"
      ? t("automation.activity.actionAi")
      : action === "issue_refund"
        ? t("automation.activity.issueRefund")
        : (t.dynamic(`automation.action.${action}`) ?? action ?? "");
}

export function useExplain() {
  const { t } = useI18n();
  return (d: Pick<DecisionRecordView, "rule"> | null | undefined) => (d ? (t.dynamic(`automation.rule.${d.rule}`) ?? d.rule) : "");
}
