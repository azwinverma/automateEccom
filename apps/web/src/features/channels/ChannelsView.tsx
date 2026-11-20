"use client";

import { isApiError, type ChannelConnection, type ChannelProvider } from "@commerce-os/api-client";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { connectFlow, normalizeStoreUrl, validateKeys, type KeysForm } from "@/lib/channels/connect";
import { callbackUrl, savePending, stateFromAuthorizeUrl } from "@/lib/channels/oauth";
import { parseLimitOptions } from "@/lib/usage";
import { MessagingDrawer } from "./MessagingDrawer";
import wf from "../shared/workflow.module.css";

const STATUS_TONE: Record<string, Tone> = { connected: "success", expired: "warning", revoked: "danger", error: "danger", disconnected: "neutral" };

export function Capabilities({ caps }: { caps: string[] }) {
  const { t } = useI18n();
  return (
    <span className={wf.capList}>
      {caps.map((c) => (
        <span key={c} className={wf.cap}>
          {t.dynamic(`channels.cap.${c}`) ?? c}
        </span>
      ))}
    </span>
  );
}

function ErrorLine({ error }: { error: unknown }) {
  const { t } = useI18n();
  if (!error) return null;
  return (
    <InlineAlert tone="danger">
      {errorMessage(t, error)}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  );
}

/** API-key connect (WooCommerce). Re-entering keys for the same store URL reconnects it. */
export function KeysDrawer({
  provider,
  reconnect,
  initialUrl,
  onOpenChange,
  onConnected,
}: {
  provider: { code: string; name: string } | null;
  reconnect: boolean;
  initialUrl?: string;
  onOpenChange: (open: boolean) => void;
  onConnected: (c: ChannelConnection) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const [form, setForm] = useState<KeysForm>({ store_url: initialUrl ?? "", consumer_key: "", consumer_secret: "" });
  const [attempted, setAttempted] = useState(false);
  const action = useAction();

  useEffect(() => {
    setForm({ store_url: initialUrl ?? "", consumer_key: "", consumer_secret: "" });
    setAttempted(false);
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider?.code, initialUrl]);

  const errs = attempted ? validateKeys(form) : {};
  const fieldErr = (k: keyof KeysForm) => (errs[k] ? t(`channels.keys.err.${errs[k]!}`) : undefined);
  const err = action.error;
  const currency = isApiError(err) && err.code === "currency_mismatch" ? err.details : null;
  const limit = isApiError(err) && err.code === "usage_limit_reached" ? err.details : null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!provider || Object.keys(validateKeys(form)).length) return;
    const c = await action.run(() =>
      api.channels.connectWithKeys({
        provider: provider.code,
        store_url: normalizeStoreUrl(form.store_url),
        consumer_key: form.consumer_key.trim(),
        consumer_secret: form.consumer_secret.trim(),
      }),
    );
    if (c) onConnected(c);
  };

  return (
    <Drawer
      open={provider !== null}
      onOpenChange={onOpenChange}
      title={t("channels.keys.title", { name: provider?.name ?? "" })}
      description={t("channels.keys.body")}
      footer={
        <>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" form="keys-form" loading={action.pending}>
            {action.pending ? t("channels.keys.submitting") : t("channels.keys.submit")}
          </Button>
        </>
      }
    >
      <form id="keys-form" className={wf.stack} onSubmit={submit} noValidate>
        <p className={wf.hint}>{t("channels.keys.help")}</p>
        {reconnect ? <p className={wf.hint}>{t("channels.keys.reconnectNote")}</p> : null}
        {currency ? (
          <InlineAlert tone="warning" title={t("channels.keys.currencyTitle")}>
            {t("channels.keys.currencyBody", { store: String(currency.store_currency ?? ""), merchant: String(currency.merchant_currency ?? "") })}
          </InlineAlert>
        ) : limit ? (
          <InlineAlert tone="warning" title={t("errors.usage_limit_reached")}>
            <LimitActions
              buyCredits={parseLimitOptions(limit.options).includes("buy_credits")}
              upgrade={parseLimitOptions(limit.options).includes("upgrade")}
            />
          </InlineAlert>
        ) : (
          <ErrorLine error={err} />
        )}
        <TextField
          label={t("channels.keys.storeUrl")}
          hint={t("channels.keys.storeUrlHint")}
          value={form.store_url}
          onChange={(e) => setForm((f) => ({ ...f, store_url: e.target.value }))}
          error={fieldErr("store_url")}
          type="url"
          inputMode="url"
          placeholder="https://"
          autoComplete="url"
          spellCheck={false}
        />
        <TextField
          label={t("channels.keys.consumerKey")}
          value={form.consumer_key}
          onChange={(e) => setForm((f) => ({ ...f, consumer_key: e.target.value }))}
          error={fieldErr("consumer_key")}
          autoComplete="off"
          spellCheck={false}
          mono
        />
        <TextField
          label={t("channels.keys.consumerSecret")}
          value={form.consumer_secret}
          onChange={(e) => setForm((f) => ({ ...f, consumer_secret: e.target.value }))}
          error={fieldErr("consumer_secret")}
          type="password"
          autoComplete="off"
          spellCheck={false}
          mono
        />
      </form>
    </Drawer>
  );
}

export function ChannelsView() {
  const { t, relative, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const params = useSearchParams();
  const highlight = params.get("reconnect");
  const canManage = can("channels.manage");
  const connections = useApiQuery((a) => a.channels.list());
  const providers = useApiQuery((a) => a.channels.providers());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [keysFor, setKeysFor] = useState<{ provider: ChannelProvider; reconnect: ChannelConnection | null } | null>(null);
  const [disconnecting, setDisconnecting] = useState<ChannelConnection | null>(null);
  const [messagingFor, setMessagingFor] = useState<ChannelProvider | null>(null);
  const [setupFor, setSetupFor] = useState<ChannelConnection | null>(null);
  const disconnect = useAction();

  const providerByCode = new Map((providers.state.status === "success" ? providers.state.data.items : []).map((p) => [p.code, p]));

  const startConnect = async (provider: ChannelProvider, reconnect: ChannelConnection | null) => {
    setError(null);
    const flow = connectFlow(provider.code, provider.auth_kind);
    if (flow === "keys") {
      setKeysFor({ provider, reconnect });
      return;
    }
    if (flow === "messaging") {
      setMessagingFor(provider);
      return;
    }
    setBusy(reconnect?.id ?? provider.code);
    try {
      const { authorize_url } = await api.channels.connect({
        provider: provider.code,
        redirect_uri: callbackUrl(window.location.origin),
        reconnect_connection_id: reconnect?.id ?? null,
      });
      savePending({
        provider: provider.code,
        state: stateFromAuthorizeUrl(authorize_url) ?? "",
        reconnectId: reconnect?.id ?? null,
        returnTo: "/settings/channels",
        startedAt: Date.now(),
      });
      window.location.assign(authorize_url);
    } catch (e) {
      setError(e);
      setBusy(null);
    }
  };

  const check = async (c: ChannelConnection) => {
    setBusy(c.id);
    setError(null);
    try {
      const next = await api.channels.health(c.id);
      connections.setData((d) => ({ items: d.items.map((x) => (x.id === c.id ? next : x)) }));
      // A healthy listing channel also gets its live listings compared with the channel (CHN-012).
      const listings = canManage && next.status === "connected" && next.capabilities.includes("product_listing");
      if (listings) await api.channels.reconcile(c.id);
      toast(t(listings ? "channels.checkedListings" : "channels.checked"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  const doDisconnect = async () => {
    if (!disconnecting) return;
    const ok = await disconnect.run(async () => {
      await api.channels.disconnect(disconnecting.id);
      return true;
    });
    if (ok) {
      connections.setData((d) => ({ items: d.items.filter((x) => x.id !== disconnecting.id) }));
      toast(t("channels.disconnectedToast", { name: disconnecting.display_name }));
      setDisconnecting(null);
    }
  };

  const expired = connections.state.status === "success" ? connections.state.data.items.filter((c) => c.needs_reconnect) : [];

  return (
    <>
      <PageHeader level={2} title={t("channels.title")} subtitle={t("channels.subtitle")} />
      {!canManage ? <InlineAlert tone="info" live={false}>{t("channels.manageOnly")}</InlineAlert> : null}
      {expired.map((c) => (
        <div key={c.id} style={{ marginBottom: "var(--space-3)" }}>
          <InlineAlert
            tone="warning"
            title={t("channels.expiredBanner", { name: c.display_name })}
            action={
              canManage && providerByCode.get(c.provider) ? (
                <Button variant="primary" size="sm" loading={busy === c.id} onClick={() => startConnect(providerByCode.get(c.provider)!, c)}>
                  {t("channels.reconnect")}
                </Button>
              ) : null
            }
          />
        </div>
      ))}
      <ErrorLine error={error} />

      <SectionHeader title={t("channels.connectedHeading")} id="connected-heading" />
      {connections.state.status === "loading" ? (
        <TableSkeleton columns="1.4fr 1fr 2fr 1fr 1fr" rows={2} label={t("common.loading")} />
      ) : connections.state.status === "error" ? (
        <QueryError error={connections.state.error} onRetry={connections.reload} />
      ) : connections.state.data.items.length === 0 ? (
        <EmptyState title={t("channels.empty")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="connected-heading" data-testid="connections">
            <thead>
              <tr>
                <th scope="col">{t("channels.colChannel")}</th>
                <th scope="col">{t("channels.colStatus")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("channels.colCan")}
                </th>
                <th scope="col" className={table.hideSm}>
                  {t("channels.colChecked")}
                </th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{t("common.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {connections.state.data.items.map((c) => {
                const provider = providerByCode.get(c.provider);
                return (
                  <tr key={c.id} className={highlight === c.id ? wf.rowHighlight : undefined} data-provider={c.provider}>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>{c.display_name}</strong>
                        <span>{provider?.name ?? c.provider}</span>
                      </div>
                    </td>
                    <td>
                      <Badge tone={STATUS_TONE[c.status] ?? "neutral"}>{t.dynamic(`channels.status.${c.status}`) ?? c.status}</Badge>
                      {c.last_error_code && c.status !== "connected" ? (
                        <div className={table.muted} style={{ fontSize: "var(--font-size-xs)", marginTop: 2 }}>
                          {t.dynamic(`errors.${c.last_error_code}`) ?? c.last_error_code}
                        </div>
                      ) : null}
                    </td>
                    <td className={table.hideSm}>
                      <Capabilities caps={c.capabilities} />
                    </td>
                    <td className={[table.hideSm, table.muted].join(" ")}>
                      {c.last_healthy_at ? <time title={dateTime(c.last_healthy_at)}>{relative(c.last_healthy_at)}</time> : t("common.none")}
                    </td>
                    <td className={table.actions}>
                      <div className={wf.rowActions}>
                        {c.needs_reconnect && canManage && provider ? (
                          <Button size="sm" variant="primary" loading={busy === c.id} onClick={() => startConnect(provider, c)}>
                            {t("channels.reconnect")}
                          </Button>
                        ) : (
                          <Button size="sm" variant="ghost" loading={busy === c.id} onClick={() => check(c)}>
                            {t("channels.checkHealth")}
                          </Button>
                        )}
                        {canManage && c.provider === "whatsapp_cloud" ? (
                          <Button size="sm" variant="ghost" onClick={() => setSetupFor(c)} aria-label={`${t("messaging.setupAction")}: ${c.display_name}`}>
                            {t("messaging.setupAction")}
                          </Button>
                        ) : null}
                        {canManage ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              disconnect.clear();
                              setDisconnecting(c);
                            }}
                            aria-label={`${t("channels.disconnect")}: ${c.display_name}`}
                          >
                            {t("channels.disconnect")}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <SectionHeader title={t("channels.availableHeading")} id="providers-heading" />
      {providers.state.status === "loading" ? (
        <TableSkeleton columns="1.4fr 2fr 1fr" rows={2} label={t("common.loading")} />
      ) : providers.state.status === "error" ? (
        <QueryError error={providers.state.error} onRetry={providers.reload} />
      ) : providers.state.data.items.length === 0 ? (
        <EmptyState title={t("channels.noProviders")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="providers-heading" data-testid="providers">
            <tbody>
              {providers.state.data.items.map((p) => (
                <tr key={p.code}>
                  <td>
                    <strong style={{ fontWeight: "var(--font-weight-medium)" }}>{p.name}</strong>{" "}
                    {p.sandbox ? <Badge dot={false}>{t("channels.sandbox")}</Badge> : null}
                  </td>
                  <td className={table.hideSm}>
                    <Capabilities caps={p.capabilities} />
                  </td>
                  <td className={table.actions}>
                    {canManage ? (
                      <Button size="sm" loading={busy === p.code} onClick={() => startConnect(p, null)} aria-label={`${t("channels.connect")}: ${p.name}`}>
                        {busy === p.code ? t("channels.connecting") : t("channels.connect")}
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <KeysDrawer
        provider={keysFor ? { code: keysFor.provider.code, name: keysFor.provider.name } : null}
        reconnect={keysFor?.reconnect !== null && keysFor !== null}
        initialUrl={keysFor?.reconnect?.external_account_id?.startsWith("https://") ? keysFor.reconnect.external_account_id : undefined}
        onOpenChange={(o) => !o && setKeysFor(null)}
        onConnected={(c) => {
          setKeysFor(null);
          connections.reload();
          toast(t("channels.connectedToast", { name: c.display_name }));
        }}
      />
      <MessagingDrawer
        provider={messagingFor}
        setupFor={setupFor}
        onOpenChange={(o) => {
          if (!o) {
            setMessagingFor(null);
            setSetupFor(null);
          }
        }}
        onConnected={(c) => {
          connections.reload();
          toast(t("channels.connectedToast", { name: c.display_name }));
        }}
      />
      <ConfirmDialog
        open={disconnecting !== null}
        onOpenChange={(o) => !o && setDisconnecting(null)}
        title={t("channels.disconnectTitle", { name: disconnecting?.display_name ?? "" })}
        body={t("channels.disconnectBody")}
        confirmLabel={t("channels.disconnect")}
        onConfirm={doDisconnect}
        pending={disconnect.pending}
        destructive
      >
        <ErrorLine error={disconnect.error} />
      </ConfirmDialog>
    </>
  );
}
