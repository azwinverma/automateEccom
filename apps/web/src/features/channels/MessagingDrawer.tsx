"use client";

import { isApiError, type ChannelConnection, type ChannelProvider, type MessagingProviderCode, type WebhookSetup } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId, Skeleton } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { missingMessagingFields } from "@/lib/channels/connect";
import wf from "../shared/workflow.module.css";
import cx from "../settings/connect.module.css";

/** Fallback field lists if the providers endpoint is older than the messaging channels. */
const FIELDS: Record<MessagingProviderCode, { required: string[]; optional: string[] }> = {
  telegram: { required: ["bot_token"], optional: [] },
  whatsapp_cloud: { required: ["access_token", "app_secret", "phone_number_id"], optional: ["business_account_id"] },
};
const NOT_SECRET = new Set(["phone_number_id", "business_account_id"]);

function fieldsFor(p: ChannelProvider): { required: string[]; optional: string[] } {
  const base = FIELDS[p.code as MessagingProviderCode] ?? { required: [], optional: [] };
  const secret = p.secret_fields ?? [];
  const optional = p.optional_fields ?? base.optional;
  // phone_number_id is optional to the adapter class but required by the connect endpoint for WhatsApp.
  const required = Array.from(new Set([...secret, ...base.required])).filter((f) => !optional.includes(f) || base.required.includes(f));
  return { required, optional: optional.filter((f) => !required.includes(f)) };
}

function CopyRow({ label, value, id }: { label: string; value: string; id: string }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  return (
    <div className={cx.copyRow}>
      <span id={`${id}-label`}>{label}</span>
      <div className={cx.copyValue}>
        <code aria-labelledby={`${id}-label`} data-testid={id}>
          {value}
        </code>
        <Button
          size="sm"
          variant="secondary"
          aria-label={`${t("messaging.copy")}: ${label}`}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value);
              setCopied(true);
              window.setTimeout(() => setCopied(false), 2000);
            } catch {
              /* clipboard blocked: the value is visible to select by hand */
            }
          }}
        >
          {copied ? t("messaging.copied") : t("messaging.copy")}
        </Button>
      </div>
    </div>
  );
}

/** The callback URL + verify token the seller pastes into their own Meta app. */
export function WebhookSetupPanel({ connectionId }: { connectionId: string }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const [setup, setSetup] = useState<WebhookSetup | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let live = true;
    api.channels.webhookSetup(connectionId).then(
      (s) => live && setSetup(s),
      (e) => live && setError(e),
    );
    return () => {
      live = false;
    };
  }, [api, connectionId]);
  if (error) return <InlineAlert tone="danger">{errorMessage(t, error)}</InlineAlert>;
  if (!setup) return <Skeleton height={120} />;
  return (
    <div className={wf.stack} data-testid="webhook-setup">
      <p className={wf.hint}>{t("messaging.setupBody")}</p>
      <ol className={cx.steps}>
        <li>{t("messaging.setupStep1")}</li>
        <li>{t("messaging.setupStep2")}</li>
        <li>{t("messaging.setupStep3")}</li>
      </ol>
      <CopyRow id="callback-url" label={t("messaging.callbackUrl")} value={setup.callback_url} />
      <CopyRow id="verify-token" label={t("messaging.verifyToken")} value={setup.verify_token} />
      <InlineAlert tone="info" live={false}>
        {t("messaging.whatsappRule")}
      </InlineAlert>
    </div>
  );
}

/** Telegram bot / the seller's own WhatsApp Business app. WhatsApp then shows the webhook step. */
export function MessagingDrawer({
  provider,
  setupFor,
  onOpenChange,
  onConnected,
}: {
  provider: ChannelProvider | null;
  /** Reopen only the webhook step for an existing WhatsApp connection. */
  setupFor?: ChannelConnection | null;
  onOpenChange: (open: boolean) => void;
  onConnected: (c: ChannelConnection) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [values, setValues] = useState<Record<string, string>>({});
  const [attempted, setAttempted] = useState(false);
  const [connected, setConnected] = useState<ChannelConnection | null>(null);
  const code = (provider?.code ?? setupFor?.provider ?? "telegram") as MessagingProviderCode;
  const whatsapp = code === "whatsapp_cloud";
  const { required, optional } = provider ? fieldsFor(provider) : { required: [], optional: [] };
  const open = provider !== null || Boolean(setupFor);
  const step = setupFor ?? connected;

  useEffect(() => {
    setValues({});
    setAttempted(false);
    setConnected(null);
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider?.code, setupFor?.id]);

  const missing = missingMessagingFields(required, values);
  const err = action.error;
  const serverMissing = isApiError(err) && err.code === "missing_fields" && Array.isArray(err.details?.fields) ? (err.details.fields as string[]) : [];
  const label = (f: string) => t.dynamic(`messaging.field.${f}`) ?? f;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!provider || missing.length) return;
    const fields = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
    const c = await action.run(() => api.channels.connectMessaging({ provider: code, fields }));
    if (!c) return;
    setValues({});
    onConnected(c);
    if (whatsapp) setConnected(c);
    else onOpenChange(false);
  };

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={step ? t("messaging.setupTitle") : whatsapp ? t("messaging.whatsappTitle") : t("messaging.telegramTitle")}
      description={step ? undefined : whatsapp ? t("messaging.whatsappBody") : t("messaging.telegramBody")}
      footer={
        step ? (
          <Button variant="primary" onClick={() => onOpenChange(false)}>
            {t("messaging.done")}
          </Button>
        ) : (
          <>
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="primary" type="submit" form="messaging-form" loading={action.pending}>
              {action.pending ? t("messaging.submitting", { name: provider?.name ?? "" }) : t("messaging.submit")}
            </Button>
          </>
        )
      }
    >
      {step ? (
        <WebhookSetupPanel connectionId={step.id} />
      ) : (
        <form id="messaging-form" className={wf.stack} onSubmit={submit} noValidate>
          <ol className={cx.steps}>
            {(whatsapp ? (["whatsappStep1", "whatsappStep2", "whatsappStep3"] as const) : (["telegramStep1", "telegramStep2", "telegramStep3"] as const)).map((k) => (
              <li key={k}>{t(`messaging.${k}`)}</li>
            ))}
          </ol>
          {err ? (
            <InlineAlert tone="danger">
              {serverMissing.length ? t("messaging.missing", { fields: serverMissing.map(label).join(", ") }) : errorMessage(t, err)}
              <RequestId id={isApiError(err) ? err.requestId : null} />
            </InlineAlert>
          ) : null}
          {[...required, ...optional].map((f) => (
            <TextField
              key={f}
              label={label(f)}
              optionalLabel={optional.includes(f) ? t("messaging.optional") : undefined}
              hint={f === "business_account_id" ? t("messaging.businessAccountHint") : undefined}
              value={values[f] ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [f]: e.target.value }))}
              error={attempted && missing.includes(f) ? t("errors.field.required") : undefined}
              type={NOT_SECRET.has(f) ? "text" : "password"}
              inputMode={NOT_SECRET.has(f) ? "numeric" : undefined}
              maxLength={600}
              autoComplete="off"
              spellCheck={false}
              mono
            />
          ))}
          <p className={wf.hint}>{t("messaging.secretNote")}</p>
          {whatsapp ? (
            <InlineAlert tone="info" live={false}>
              {t("messaging.whatsappRule")}
            </InlineAlert>
          ) : null}
        </form>
      )}
    </Drawer>
  );
}
