"use client";

import { isApiError, type ExceptionRecord } from "@commerce-os/api-client";
import { useCallback, useMemo, useState } from "react";
import type { ExceptionItem } from "@/components/commerce/ExceptionInbox";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { exceptionSummaryKey, exceptionTarget } from "@/lib/exceptions";

const str = (v: unknown): string | null => (typeof v === "string" && v ? v : null);

/** Loads `GET /exceptions` and maps each record to an Exception Inbox item plus its fix-it control. */
export function useExceptions() {
  const { t, money } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const query = useApiQuery((a) => a.exceptions.list());
  const [busy, setBusy] = useState<string | null>(null);
  const [commandError, setCommandError] = useState<unknown>(null);

  const records = useMemo(
    () => (query.state.status === "success" ? new Map(query.state.data.items.map((r) => [r.id, r])) : new Map<string, ExceptionRecord>()),
    [query.state],
  );

  const items: ExceptionItem[] = useMemo(
    () =>
      [...records.values()].map((r) => {
        const { key, vars } = exceptionSummaryKey(r);
        if (key === "escalation" && typeof vars.reason === "string") vars.reason = t.dynamic(`inbox.reason.${vars.reason}`) ?? vars.reason;
        if (key === "orderReview" && typeof vars.reason === "string") vars.reason = t.dynamic(`orders.review.${vars.reason}`) ?? vars.reason;
        if ((key === "refundDue" || key === "refundToApprove") && typeof vars.amount === "number") vars.amount = money(vars.amount, str(r.details.currency) ?? "NPR");
        if (key === "deliveryFailed" && typeof vars.reason === "string") vars.reason = t.dynamic(`fulfillment.reason.${vars.reason}`) ?? vars.reason;
        if (r.type === "usage_limit" && typeof vars.resource === "string") {
          vars.resource = t.dynamic(`usage.resource.${vars.resource}`) ?? vars.resource;
        }
        const code = typeof r.details.error_code === "string" ? r.details.error_code : null;
        return {
          id: r.id,
          type: r.type,
          severity: r.severity,
          summary: t.dynamic(`exceptions.summary.${key}`, vars) ?? t("exceptions.summary.generic"),
          reference: code ? (t.dynamic(`errors.${code}`) ?? code) : undefined,
          occurredAt: r.occurred_at,
        };
      }),
    [records, t, money],
  );

  const run = useCallback(
    async (r: ExceptionRecord, command: "retry_publish" | "retry_draft" | "remove_file") => {
      setBusy(r.id);
      setCommandError(null);
      try {
        if (command === "retry_publish") await api.catalog.publish(r.resource.id, [String(r.details.connection_id)]);
        else if (command === "retry_draft") await api.studio.retry(r.resource.id);
        else await api.media.remove(r.resource.id);
        toast(t("exceptions.commandDone"));
        query.reload();
      } catch (e) {
        setCommandError(e);
      } finally {
        setBusy(null);
      }
    },
    [api, query, t, toast],
  );

  const renderAction = useCallback(
    (item: ExceptionItem) => {
      const r = records.get(item.id);
      if (!r) return null;
      const target = exceptionTarget(r);
      if (target.kind === "none") return null;
      const label = t(`exceptions.actionLabel.${target.label}`);
      if (target.kind === "link") {
        return (
          <ButtonLink size="sm" href={target.href}>
            {label}
          </ButtonLink>
        );
      }
      return (
        <Button size="sm" loading={busy === r.id} disabled={busy !== null && busy !== r.id} onClick={() => run(r, target.command)}>
          {label}
        </Button>
      );
    },
    [busy, records, run, t],
  );

  return {
    query,
    items,
    total: query.state.status === "success" ? query.state.data.total : null,
    renderAction,
    commandError: commandError ? { message: errorMessage(t, commandError), requestId: isApiError(commandError) ? commandError.requestId : null } : null,
  };
}
