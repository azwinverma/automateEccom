"use client";

import { isApiError, type ChannelConnection } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, RequestId } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { validPageId } from "@/lib/channels/connect";
import { META_PENDING_PROVIDER, metaCallbackUrl, savePending, stateFromAuthorizeUrl } from "@/lib/channels/oauth";
import cx from "../settings/connect.module.css";
import wf from "../shared/workflow.module.css";

const STEPS = ["metaStep1", "metaStep2", "metaStep3", "metaStep4", "metaStep5"] as const;

/** Facebook Page (+ linked Instagram professional account) through the seller's own Meta app. */
export function MetaDrawer({
  open,
  oneClick = false,
  onOpenChange,
  onConnected,
}: {
  open: boolean;
  /** Nivaro's own Meta app is configured: lead with "Continue with Facebook" (posting + messages). */
  oneClick?: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called with every connection that came back (Page, and Instagram when linked). */
  onConnected: (items: ChannelConnection[]) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [pageId, setPageId] = useState("");
  const [token, setToken] = useState("");
  const [withInstagram, setWithInstagram] = useState(true);
  const [attempted, setAttempted] = useState(false);
  const [noInstagram, setNoInstagram] = useState<ChannelConnection[] | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const start = useAction();

  useEffect(() => {
    if (!open) return;
    setPageId("");
    setToken("");
    setWithInstagram(true);
    setAttempted(false);
    setNoInstagram(null);
    setAdvanced(false);
    action.clear();
    start.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const pageErr = attempted && !validPageId(pageId) ? t("messaging.pageIdInvalid") : undefined;
  const tokenErr = attempted && token.trim().length < 20 ? t("errors.invalid_api_keys") : undefined;
  const err = action.error;
  const missingPerm = isApiError(err) && err.code === "permission_missing" ? String(err.details?.provider_code ?? "") : null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!validPageId(pageId) || token.trim().length < 20) return;
    const res = await action.run(() => api.channels.connectMeta({ page_id: pageId.trim(), page_access_token: token.trim(), with_instagram: withInstagram }));
    if (!res) return;
    setToken("");
    onConnected(res.items);
    const gotInstagram = res.items.some((c) => c.provider === "instagram");
    if (withInstagram && !gotInstagram) setNoInstagram(res.items);
    else onOpenChange(false);
  };

  const continueWithFacebook = async () => {
    const res = await start.run(() => api.channels.metaStart(metaCallbackUrl(window.location.origin)));
    if (!res) return;
    savePending({
      provider: META_PENDING_PROVIDER,
      state: stateFromAuthorizeUrl(res.authorize_url) ?? "",
      reconnectId: null,
      returnTo: "/settings/channels",
      startedAt: Date.now(),
    });
    window.location.assign(res.authorize_url);
  };
  const showForm = !oneClick || advanced;

  const form = (
    <form id="meta-form" className={wf.stack} onSubmit={submit} noValidate>
      <ol className={cx.steps}>
        {STEPS.map((k) => (
          <li key={k}>{t(`messaging.${k}`)}</li>
        ))}
      </ol>
      <InlineAlert tone="info" live={false}>
        {t("messaging.metaNoReview")} {t("messaging.metaPublishOnly")}
      </InlineAlert>
      {err ? (
        <InlineAlert tone="danger">
          {missingPerm !== null
            ? missingPerm
              ? t("messaging.permissionMissing", { permission: missingPerm })
              : t("messaging.permissionMissingGeneric")
            : errorMessage(t, err)}
          <RequestId id={isApiError(err) ? err.requestId : null} />
        </InlineAlert>
      ) : null}
      <TextField
        label={t("messaging.pageId")}
        hint={t("messaging.pageIdHint")}
        value={pageId}
        onChange={(e) => setPageId(e.target.value.replace(/\s/g, ""))}
        error={pageErr}
        inputMode="numeric"
        maxLength={25}
        autoComplete="off"
        spellCheck={false}
        mono
      />
      <TextField
        label={t("messaging.pageToken")}
        hint={`${t("messaging.secretNote")} ${t("messaging.metaReconnect")}`}
        value={token}
        onChange={(e) => setToken(e.target.value)}
        error={tokenErr}
        type="password"
        maxLength={600}
        autoComplete="off"
        spellCheck={false}
        mono
      />
      <Checkbox label={t("messaging.withInstagram")} checked={withInstagram} onChange={(e) => setWithInstagram(e.target.checked)} />
    </form>
  );

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("messaging.metaTitle")}
      description={noInstagram ? undefined : t("messaging.metaBody")}
      footer={
        noInstagram ? (
          <Button variant="primary" onClick={() => onOpenChange(false)}>
            {t("messaging.done")}
          </Button>
        ) : (
          <>
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            {showForm ? (
              <Button variant={oneClick ? "secondary" : "primary"} type="submit" form="meta-form" loading={action.pending}>
                {action.pending ? t("messaging.submitting", { name: "Meta" }) : t("messaging.submit")}
              </Button>
            ) : null}
          </>
        )
      }
    >
      {noInstagram ? (
        <div className={wf.stack} data-testid="meta-no-instagram">
          <InlineAlert tone="warning" title={t("errors.instagram_not_linked")}>
            {t("messaging.metaNoInstagram")}
          </InlineAlert>
          <p className={wf.hint}>{t("messaging.metaConnected", { names: noInstagram.map((c) => c.display_name).join(", ") })}</p>
        </div>
      ) : oneClick ? (
        <div className={wf.stack}>
          <section className={cx.provider} aria-labelledby="meta-oneclick" data-testid="meta-one-click">
            <strong id="meta-oneclick">
              {t("messaging.metaOneClick")} <Badge tone="success" dot={false}>{t("messaging.metaRecommended")}</Badge>
            </strong>
            <p>{t("messaging.metaOneClickBody")}</p>
            {start.error ? (
              <InlineAlert tone="danger">
                {errorMessage(t, start.error)}
                <RequestId id={isApiError(start.error) ? start.error.requestId : null} />
              </InlineAlert>
            ) : null}
            <Button variant="primary" loading={start.pending} onClick={continueWithFacebook}>
              {start.pending ? t("messaging.metaOpening") : t("messaging.metaOneClick")}
            </Button>
          </section>
          <details open={advanced} onToggle={(e) => setAdvanced((e.currentTarget as HTMLDetailsElement).open)}>
            <summary style={{ cursor: "pointer", fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-3)" }}>{t("messaging.metaAdvanced")}</summary>
            {form}
          </details>
        </div>
      ) : (
        form
      )}
    </Drawer>
  );
}
