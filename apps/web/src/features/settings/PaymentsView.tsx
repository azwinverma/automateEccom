"use client";

import { isApiError, type GatewayMode, type PaymentGateway, type PaymentGatewayProvider } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import wf from "../shared/workflow.module.css";
import cx from "./connect.module.css";

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

function keysState(g: PaymentGateway): { tone: Tone; key: "payments.statusAccepted" | "payments.statusRejected" | "payments.statusUnproven" } {
  if (g.verified === false || g.status === "error") return { tone: "danger", key: "payments.statusRejected" };
  if (g.verified === true) return { tone: "success", key: "payments.statusAccepted" };
  return { tone: "info", key: "payments.statusUnproven" };
}

/** Settings → Payments: the seller's own eSewa / Khalti merchant accounts. */
export function PaymentsView() {
  const { t, relative, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const manage = can("payments.manage");
  const gateways = useApiQuery((a) => a.paymentGateways.list());
  const providers = useApiQuery((a) => a.paymentGateways.providers());
  const [connecting, setConnecting] = useState<{ provider: PaymentGatewayProvider; replacing: PaymentGateway | null } | null>(null);
  const [removing, setRemoving] = useState<PaymentGateway | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const action = useAction();
  const remove = useAction();

  const items = gateways.state.status === "success" ? gateways.state.data.items : [];
  const providerList = providers.state.status === "success" ? providers.state.data.items : [];
  const providerOf = (code: string) => providerList.find((p) => p.code === code);

  const replaceRow = (next: PaymentGateway) =>
    gateways.setData((d) => ({ items: d.items.map((x) => (x.id === next.id ? next : next.is_default ? { ...x, is_default: false } : x)) }));

  const run = async (g: PaymentGateway, kind: "test" | "default") => {
    setBusy(`${kind}:${g.id}`);
    const next = await action.run(() => (kind === "test" ? api.paymentGateways.test(g.id) : api.paymentGateways.makeDefault(g.id)));
    setBusy(null);
    if (!next) return;
    replaceRow(next);
    toast(kind === "test" ? t("payments.checked") : t("payments.defaultSet", { name: next.name }));
  };

  return (
    <>
      <PageHeader level={2} title={t("payments.title")} subtitle={t("payments.subtitle")} />
      <p className={cx.howTitle} id="pay-how">
        {t("payments.howTitle")}
      </p>
      <ul className={cx.how} aria-labelledby="pay-how">
        {(["howKeys", "howCheckout", "howVerify", "howRefunds"] as const).map((k) => (
          <li key={k}>
            <Icon name={k === "howKeys" ? "lock" : k === "howVerify" ? "shield" : "check"} />
            <span>{t(`payments.${k}`)}</span>
          </li>
        ))}
      </ul>
      {!manage ? (
        <InlineAlert tone="info" live={false}>
          {t("payments.manageOnly")}
        </InlineAlert>
      ) : null}
      <ErrorLine error={action.error} />

      <SectionHeader title={t("payments.yours")} id="gateways-heading" />
      {gateways.state.status === "loading" ? (
        <TableSkeleton columns="1.4fr 1.2fr 1fr 1fr" rows={1} label={t("common.loading")} />
      ) : gateways.state.status === "error" ? (
        <QueryError error={gateways.state.error} onRetry={gateways.reload} />
      ) : items.length === 0 ? (
        <EmptyState title={t("payments.empty")} body={t("payments.emptyBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="gateways-heading" data-testid="gateways">
            <thead>
              <tr>
                <th scope="col">{t("payments.colGateway")}</th>
                <th scope="col">{t("payments.colStatus")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("payments.colActivity")}
                </th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{t("common.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((g) => {
                const st = keysState(g);
                return (
                  <tr key={g.id} data-provider={g.provider}>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>
                          {g.name}{" "}
                          <Badge tone={g.mode === "live" ? "success" : "warning"} dot={false}>
                            {g.mode === "live" ? t("payments.modeLive") : t("payments.modeTest")}
                          </Badge>
                        </strong>
                        <span>{g.is_default ? t("payments.default") : g.public_id ?? ""}</span>
                      </div>
                    </td>
                    <td>
                      <Badge tone={st.tone}>{t(st.key)}</Badge>
                      {g.secret_hint ? <span className={[cx.meta, cx.mono].join(" ")}>{t("payments.keyHint", { hint: g.secret_hint })}</span> : null}
                      {g.verified === null && g.status !== "error" ? <span className={cx.meta}>{t("payments.statusUnprovenHelp")}</span> : null}
                    </td>
                    <td className={[table.hideSm, table.muted].join(" ")}>
                      {g.last_payment_at ? (
                        <time dateTime={g.last_payment_at} title={dateTime(g.last_payment_at)}>
                          {t("payments.lastPayment", { when: relative(g.last_payment_at) })}
                        </time>
                      ) : (
                        t("payments.noPaymentYet")
                      )}
                    </td>
                    <td className={table.actions}>
                      {manage ? (
                        <div className={wf.rowActions}>
                          {!g.is_default && g.status === "active" ? (
                            <Button size="sm" variant="ghost" loading={busy === `default:${g.id}`} onClick={() => run(g, "default")}>
                              {t("payments.makeDefault")}
                            </Button>
                          ) : null}
                          {g.provider === "khalti" ? (
                            <Button size="sm" variant="ghost" loading={busy === `test:${g.id}`} onClick={() => run(g, "test")} aria-label={`${t("payments.test")}: ${g.name}`}>
                              {t("payments.test")}
                            </Button>
                          ) : null}
                          {providerOf(g.provider) ? (
                            <Button size="sm" variant="ghost" onClick={() => setConnecting({ provider: providerOf(g.provider)!, replacing: g })} aria-label={`${t("payments.replaceKeys")}: ${g.name}`}>
                              {t("payments.replaceKeys")}
                            </Button>
                          ) : null}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              remove.clear();
                              setRemoving(g);
                            }}
                            aria-label={`${t("payments.disconnect")}: ${g.name}`}
                          >
                            {t("payments.disconnect")}
                          </Button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {manage ? (
        <>
          <SectionHeader title={t("payments.add")} id="gateway-providers" />
          {providers.state.status === "error" ? (
            <QueryError error={providers.state.error} onRetry={providers.reload} />
          ) : (
            <ul className={cx.providers} aria-labelledby="gateway-providers" data-testid="gateway-providers">
              {providerList.map((p) => {
                const existing = items.find((g) => g.provider === p.code);
                return (
                  <li key={p.code} className={cx.provider}>
                    <strong>{p.name}</strong>
                    <p>{p.code === "esewa" ? t("payments.secretHintEsewa") : t("payments.secretHintKhalti")}</p>
                    <Button size="sm" variant={existing ? "ghost" : "secondary"} onClick={() => setConnecting({ provider: p, replacing: existing ?? null })}>
                      {existing ? t("payments.replaceKeys") : t("payments.connectName", { name: p.name })}
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ) : null}

      <GatewayDrawer
        target={connecting}
        firstGateway={items.length === 0}
        onClose={() => setConnecting(null)}
        onSaved={(g) => {
          setConnecting(null);
          gateways.reload();
          toast(t("payments.saved", { name: g.name }));
        }}
      />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(o) => !o && setRemoving(null)}
        title={t("payments.disconnectTitle", { name: removing?.name ?? "" })}
        body={t("payments.disconnectBody")}
        confirmLabel={t("payments.disconnect")}
        destructive
        pending={remove.pending}
        onConfirm={async () => {
          if (!removing) return;
          const ok = await remove.run(() => api.paymentGateways.disconnect(removing.id).then(() => true));
          if (ok) {
            gateways.setData((d) => ({ items: d.items.filter((x) => x.id !== removing.id) }));
            toast(t("payments.removed", { name: removing.name }));
            setRemoving(null);
          }
        }}
      >
        <ErrorLine error={remove.error} />
      </ConfirmDialog>
    </>
  );
}

function GatewayDrawer({
  target,
  firstGateway,
  onClose,
  onSaved,
}: {
  target: { provider: PaymentGatewayProvider; replacing: PaymentGateway | null } | null;
  firstGateway: boolean;
  onClose: () => void;
  onSaved: (g: PaymentGateway) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [mode, setMode] = useState<GatewayMode>("test");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [makeDefault, setMakeDefault] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const provider = target?.provider ?? null;
  const needsCode = provider?.public_fields.includes("product_code") ?? false;

  useEffect(() => {
    setMode(target?.replacing?.mode ?? "test");
    setSecret("");
    setCode(target?.replacing?.public_id ?? "");
    setMakeDefault(false);
    setAttempted(false);
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.provider.code, target?.replacing?.id]);

  const secretErr = attempted && secret.trim().length < 8 ? t("errors.invalid_secret_key") : undefined;
  const codeErr = attempted && needsCode && code.trim().length < 2 ? t("errors.product_code_required") : undefined;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!provider || secret.trim().length < 8 || (needsCode && code.trim().length < 2)) return;
    const g = await action.run(() =>
      api.paymentGateways.connect({
        provider: provider.code,
        mode,
        secret_key: secret.trim(),
        public_id: needsCode ? code.trim() : null,
        is_default: makeDefault,
      }),
    );
    if (g) {
      setSecret("");
      onSaved(g);
    }
  };

  return (
    <Drawer
      open={target !== null}
      onOpenChange={(o) => !o && onClose()}
      title={target?.replacing ? `${t("payments.replaceKeys")}: ${provider?.name ?? ""}` : t("payments.connectName", { name: provider?.name ?? "" })}
      description={target?.replacing ? t("payments.replaceNote") : undefined}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" form="gateway-form" loading={action.pending}>
            {t("payments.connect")}
          </Button>
        </>
      }
    >
      <form id="gateway-form" className={wf.stack} onSubmit={submit} noValidate>
        <ErrorLine error={action.error} />
        <fieldset className={cx.choice}>
          <legend>{t("payments.modeLegend")}</legend>
          {(["test", "live"] as const).map((m) => (
            <label key={m} className={cx.choiceOption}>
              <input type="radio" name="gateway-mode" value={m} checked={mode === m} onChange={() => setMode(m)} />
              <strong>{m === "live" ? t("payments.modeLive") : t("payments.modeTest")}</strong>
              <span>{m === "live" ? t("payments.modeLiveHelp") : t("payments.modeTestHelp")}</span>
            </label>
          ))}
        </fieldset>
        {needsCode ? (
          <TextField
            label={t("payments.productCode")}
            hint={t("payments.productCodeHint")}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            error={codeErr}
            maxLength={80}
            autoComplete="off"
            spellCheck={false}
            mono
          />
        ) : null}
        <TextField
          label={t("payments.secretKey")}
          hint={`${provider?.code === "esewa" ? t("payments.secretHintEsewa") : t("payments.secretHintKhalti")} ${t("payments.secretNote")}`}
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          error={secretErr}
          type="password"
          maxLength={200}
          autoComplete="off"
          spellCheck={false}
          mono
        />
        {!firstGateway && !target?.replacing?.is_default ? (
          <Checkbox label={t("payments.useForLinks")} checked={makeDefault} onChange={(e) => setMakeDefault(e.target.checked)} />
        ) : null}
      </form>
    </Drawer>
  );
}
