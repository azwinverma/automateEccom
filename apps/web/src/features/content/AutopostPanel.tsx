"use client";

import { isApiError, type AutopostSettings } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { QueryError } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, RequestId, SectionHeader, Skeleton, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import cx from "../settings/connect.module.css";
import wf from "../shared/workflow.module.css";

type Form = Pick<AutopostSettings, "enabled" | "connection_ids" | "kind" | "require_approval">;

function hourLabel(hour: number, locale: string): string {
  const d = new Date(Date.UTC(2026, 0, 1, hour, 0));
  return new Intl.DateTimeFormat(locale === "ne" ? "ne-NP" : "en-GB", { hour: "numeric", minute: "2-digit", hour12: locale !== "ne", timeZone: "UTC" }).format(d);
}

/** Content → Automatic posting: a post for each chosen account when a product goes live. */
export function AutopostPanel() {
  const { t, locale } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const q = useApiQuery((a) => a.content.getAutopost());
  const action = useAction();
  const [form, setForm] = useState<Form | null>(null);
  const [attempted, setAttempted] = useState(false);
  const canEdit = can("content.approve");

  useEffect(() => {
    if (q.state.status !== "success") return;
    const d = q.state.data;
    setForm({ enabled: d.enabled, connection_ids: d.connection_ids, kind: d.kind, require_approval: d.require_approval });
  }, [q.state]);

  const data = q.state.status === "success" ? q.state.data : null;
  const noAccount = data !== null && data.available.length === 0;
  const pickErr = attempted && form?.enabled && form.connection_ids.length === 0;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!form || (form.enabled && form.connection_ids.length === 0)) return;
    const next = await action.run(() => api.content.putAutopost(form));
    if (!next) return;
    q.setData(() => next);
    toast(t("autopost.saved"));
  };

  return (
    <section aria-labelledby="autopost-heading" data-testid="autopost" style={{ marginTop: "var(--space-8)" }}>
      <SectionHeader
        title={t("autopost.title")}
        id="autopost-heading"
        meta={data ? <Badge tone={data.enabled ? "automated" : "neutral"}>{data.enabled ? t("autopost.statusOn") : t("autopost.statusOff")}</Badge> : undefined}
      />
      <p className={wf.hint} style={{ marginTop: 0 }}>
        {t("autopost.body")}
      </p>
      <ul className={cx.how}>
        <li>
          <Icon name="check" />
          <span>{t("autopost.how1")}</span>
        </li>
        <li>
          <Icon name="content" />
          <span>{t("autopost.how2")}</span>
        </li>
        <li>
          <Icon name="products" />
          <span>{t("autopost.how3")}</span>
        </li>
        <li>
          <Icon name="clock" />
          <span>{t("autopost.how4", { hour: hourLabel(data?.default_hour ?? 19, locale) })}</span>
        </li>
      </ul>
      {q.state.status === "loading" || (data && !form) ? (
        <Skeleton height={140} />
      ) : q.state.status === "error" ? (
        <QueryError error={q.state.error} onRetry={q.reload} />
      ) : noAccount ? (
        <InlineAlert
          tone="info"
          title={t("autopost.noAccounts")}
          live={false}
          action={
            can("channels.manage") ? (
              <ButtonLink href="/settings/channels" size="sm" variant="primary">
                {t("autopost.connect")}
              </ButtonLink>
            ) : undefined
          }
        >
          {t("autopost.noAccountsBody")}
        </InlineAlert>
      ) : form && data ? (
        <form className={wf.stack} onSubmit={submit} noValidate style={{ maxWidth: 640 }}>
          {!canEdit ? (
            <InlineAlert tone="info" live={false}>
              {t("autopost.readOnly")}
            </InlineAlert>
          ) : null}
          {action.error ? (
            <InlineAlert tone="danger">
              {errorMessage(t, action.error)}
              <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
            </InlineAlert>
          ) : null}
          <Checkbox label={t("autopost.enabled")} checked={form.enabled} disabled={!canEdit} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
          <fieldset className={cx.choice} disabled={!canEdit} aria-describedby={pickErr ? "autopost-pick-error" : undefined}>
            <legend>{t("autopost.accounts")}</legend>
            {data.available.map((a) => (
              <label key={a.id} className={cx.choiceOption}>
                <input
                  type="checkbox"
                  checked={form.connection_ids.includes(a.id)}
                  onChange={(e) =>
                    setForm({ ...form, connection_ids: e.target.checked ? [...form.connection_ids, a.id] : form.connection_ids.filter((x) => x !== a.id) })
                  }
                />
                <strong>{a.display_name}</strong>
                <span>{a.provider === "instagram" ? "Instagram" : a.provider === "facebook_page" ? "Facebook" : a.provider}</span>
              </label>
            ))}
            {pickErr ? (
              <p id="autopost-pick-error" className={wf.hint} role="alert" style={{ color: "var(--status-critical, inherit)" }}>
                {t("autopost.pickAccount")}
              </p>
            ) : null}
          </fieldset>
          <fieldset className={cx.choice} disabled={!canEdit}>
            <legend>{t("autopost.kindLegend")}</legend>
            {(["post", "story"] as const).map((k) => (
              <label key={k} className={cx.choiceOption}>
                <input type="radio" name="autopost-kind" checked={form.kind === k} onChange={() => setForm({ ...form, kind: k })} />
                <strong>{t(`content.kind.${k}`)}</strong>
                <span />
              </label>
            ))}
          </fieldset>
          <div>
            <Checkbox label={t("autopost.approval")} checked={form.require_approval} disabled={!canEdit} onChange={(e) => setForm({ ...form, require_approval: e.target.checked })} />
            <p className={wf.hint} style={{ margin: "var(--space-1) 0 0" }}>
              {form.require_approval ? t("autopost.approvalOn") : t("autopost.approvalOff")}
            </p>
          </div>
          {canEdit ? (
            <div>
              <Button type="submit" variant="primary" loading={action.pending}>
                {t("autopost.save")}
              </Button>
            </div>
          ) : null}
        </form>
      ) : null}
    </section>
  );
}
