"use client";

import { isApiError, type AiCredential, type AiProviderCode } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, Skeleton, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import wf from "../shared/workflow.module.css";
import cx from "./connect.module.css";

export const AI_PROVIDERS: AiProviderCode[] = ["anthropic", "openai", "gemini"];

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

function How() {
  const { t } = useI18n();
  return (
    <>
      <p className={cx.howTitle} id="ai-how">
        {t("aiKeys.howTitle")}
      </p>
      <ul className={cx.how} aria-labelledby="ai-how">
        <li>
          <Icon name="check" />
          <span>{t("aiKeys.howDefault")}</span>
        </li>
        <li>
          <Icon name="cash" />
          <span>{t("aiKeys.howOwn")}</span>
        </li>
        <li>
          <Icon name="lock" />
          <span>{t("aiKeys.howSafe")}</span>
        </li>
      </ul>
    </>
  );
}

/** Settings → AI. Never calls the keys API without the plan feature and the permission (ADR-072). */
export function AiKeysView() {
  const { t } = useI18n();
  const { feature, can } = useAuth();
  const f = feature("ai.byok");
  return (
    <>
      <PageHeader level={2} title={t("aiKeys.title")} subtitle={t("aiKeys.subtitle")} />
      <How />
      {f === "pending" ? (
        <Skeleton height={120} />
      ) : f === "no" ? (
        <InlineAlert tone="info" title={t("aiKeys.upsellTitle")} live={false}>
          <p style={{ margin: "0 0 var(--space-2)" }}>{t("aiKeys.upsellBody")}</p>
          <LimitActions buyCredits={false} upgrade />
        </InlineAlert>
      ) : !can("ai.credentials.manage") ? (
        <InlineAlert tone="info" live={false}>
          {t("aiKeys.noAccess")}
        </InlineAlert>
      ) : (
        <AiKeysTable />
      )}
    </>
  );
}

function AiKeysTable() {
  const { t, relative } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const creds = useApiQuery((a) => a.aiCredentials.list());
  const [editing, setEditing] = useState<{ provider: AiProviderCode; existing: AiCredential | null } | null>(null);
  const [removing, setRemoving] = useState<AiCredential | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const action = useAction();
  const remove = useAction();
  const name = (p: AiProviderCode) => t(`aiKeys.provider.${p}`);

  const items = creds.state.status === "success" ? creds.state.data.items : [];
  const test = async (c: AiCredential) => {
    setBusy(c.id);
    const res = await action.run(() => api.aiCredentials.test(c.id));
    setBusy(null);
    if (!res) return;
    toast(res.ok ? t("aiKeys.testOk", { name: name(c.provider) }) : t("aiKeys.testFailed", { name: name(c.provider) }));
    creds.reload();
  };

  return (
    <>
      <SectionHeader title={t("aiKeys.providersHeading")} id="ai-providers-heading" />
      <ErrorLine error={action.error} />
      {creds.state.status === "loading" ? (
        <TableSkeleton columns="1.2fr 1.6fr 1fr" rows={3} label={t("common.loading")} />
      ) : creds.state.status === "error" ? (
        <QueryError error={creds.state.error} onRetry={creds.reload} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="ai-providers-heading" data-testid="ai-keys">
            <tbody>
              {AI_PROVIDERS.map((p) => {
                const c = items.find((x) => x.provider === p) ?? null;
                return (
                  <tr key={p} data-provider={p}>
                    <th scope="row" style={{ fontWeight: "var(--font-weight-medium)", textAlign: "left" }}>
                      {name(p)}
                    </th>
                    <td>
                      {c ? (
                        <>
                          <Badge tone={c.last_test_ok === false ? "danger" : "success"}>{t("aiKeys.usingYours", { hint: `••••${c.key_last4}` })}</Badge>
                          <span className={cx.meta}>
                            {c.last_tested_at
                              ? t(c.last_test_ok ? "aiKeys.lastTestOk" : "aiKeys.lastTestFailed", { when: relative(c.last_tested_at) })
                              : t("aiKeys.notTested")}
                            {" · "}
                            {c.fallback_to_platform ? t("aiKeys.fallbackOn") : t("aiKeys.fallbackOff")}
                          </span>
                        </>
                      ) : (
                        <Badge tone="neutral" dot={false}>
                          {t("aiKeys.usingNivaro")}
                        </Badge>
                      )}
                    </td>
                    <td className={table.actions}>
                      <div className={wf.rowActions}>
                        {c ? (
                          <>
                            <Button size="sm" variant="ghost" loading={busy === c.id} onClick={() => test(c)} aria-label={`${t("aiKeys.test")}: ${name(p)}`}>
                              {t("aiKeys.test")}
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => setEditing({ provider: p, existing: c })} aria-label={`${t("aiKeys.replaceKey")}: ${name(p)}`}>
                              {t("aiKeys.replaceKey")}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                remove.clear();
                                setRemoving(c);
                              }}
                              aria-label={`${t("aiKeys.remove")}: ${name(p)}`}
                            >
                              {t("aiKeys.remove")}
                            </Button>
                          </>
                        ) : (
                          <Button size="sm" onClick={() => setEditing({ provider: p, existing: null })} aria-label={`${t("aiKeys.addKey")}: ${name(p)}`}>
                            {t("aiKeys.addKey")}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <KeyDrawer
        target={editing}
        onClose={() => setEditing(null)}
        onSaved={(c) => {
          setEditing(null);
          creds.reload();
          toast(t("aiKeys.saved", { name: name(c.provider) }));
        }}
      />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(o) => !o && setRemoving(null)}
        title={t("aiKeys.removeTitle", { name: removing ? name(removing.provider) : "" })}
        body={t("aiKeys.removeBody")}
        confirmLabel={t("aiKeys.remove")}
        destructive
        pending={remove.pending}
        onConfirm={async () => {
          if (!removing) return;
          const ok = await remove.run(() => api.aiCredentials.revoke(removing.id).then(() => true));
          if (ok) {
            creds.setData((d) => ({ items: d.items.filter((x) => x.id !== removing.id) }));
            toast(t("aiKeys.removed", { name: name(removing.provider) }));
            setRemoving(null);
          }
        }}
      >
        <ErrorLine error={remove.error} />
      </ConfirmDialog>
    </>
  );
}

function KeyDrawer({
  target,
  onClose,
  onSaved,
}: {
  target: { provider: AiProviderCode; existing: AiCredential | null } | null;
  onClose: () => void;
  onSaved: (c: AiCredential) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [key, setKey] = useState("");
  const [fallback, setFallback] = useState(true);
  const [attempted, setAttempted] = useState(false);
  const name = target ? t(`aiKeys.provider.${target.provider}`) : "";

  useEffect(() => {
    setKey("");
    setFallback(target?.existing?.fallback_to_platform ?? true);
    setAttempted(false);
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.provider, target?.existing?.id]);

  const invalid = key.trim().length < 20 || /\s/.test(key.trim());
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!target || invalid) return;
    const apiKey = key.trim();
    const c = await action.run(() =>
      target.existing
        ? api.aiCredentials.rotate(target.existing.id, { api_key: apiKey, fallback_to_platform: fallback })
        : api.aiCredentials.create({ provider: target.provider, api_key: apiKey, fallback_to_platform: fallback }),
    );
    if (c) {
      setKey("");
      onSaved(c);
    }
  };

  return (
    <Drawer
      open={target !== null}
      onOpenChange={(o) => !o && onClose()}
      title={t("aiKeys.drawerTitle", { name })}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" form="ai-key-form" loading={action.pending}>
            {t("aiKeys.addKey")}
          </Button>
        </>
      }
    >
      <form id="ai-key-form" className={wf.stack} onSubmit={submit} noValidate>
        <ErrorLine error={action.error} />
        <TextField
          label={t("aiKeys.apiKey")}
          hint={`${t("aiKeys.apiKeyHint", { name })} ${t("aiKeys.keyNote")}`}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          error={attempted && invalid ? t("errors.invalid_api_key") : undefined}
          type="password"
          maxLength={400}
          autoComplete="off"
          spellCheck={false}
          mono
        />
        <Checkbox label={t("aiKeys.fallback")} checked={fallback} onChange={(e) => setFallback(e.target.checked)} />
      </form>
    </Drawer>
  );
}
