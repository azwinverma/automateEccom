"use client";

import { isApiError, type MetaPagesResponse } from "@commerce-os/api-client";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Field";
import { InlineAlert, PageHeader, RequestId, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { META_CALLBACK_PATH, META_PENDING_PROVIDER, resolveCallback, takePending, type CallbackResolution } from "@/lib/channels/oauth";
import cx from "../settings/connect.module.css";
import wf from "../shared/workflow.module.css";

const RESTART = new Set(["meta_selection_expired", "oauth_state_invalid", "oauth_exchange_failed"]);

/** Facebook returns here: exchange the code once, then the seller picks the Page (and its Instagram). */
export function MetaCallback() {
  const { t } = useI18n();
  const { api } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const toast = useToast();
  const [outcome, setOutcome] = useState<CallbackResolution | null>(null);
  const [pages, setPages] = useState<MetaPagesResponse | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [pageId, setPageId] = useState<string>("");
  const [withInstagram, setWithInstagram] = useState(true);
  const [attempted, setAttempted] = useState(false);
  const connect = useAction();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // exchange the code exactly once (strict mode, re-renders)
    started.current = true;
    const pending = takePending();
    const res = resolveCallback(new URLSearchParams(params.toString()), pending && pending.provider === META_PENDING_PROVIDER ? pending : null);
    setOutcome(res);
    window.history.replaceState(null, "", META_CALLBACK_PATH); // drop code/state from the address bar
    if (res.kind !== "exchange") return;
    api.channels
      .metaPages({ state: res.state, code: res.code })
      .then((p) => {
        setPages(p);
        setPageId(p.pages[0]?.id ?? "");
      })
      .catch(setLoadError);
  }, [api, params]);

  const selected = pages?.pages.find((p) => p.id === pageId) ?? null;
  const err = loadError ?? connect.error;
  const restart = isApiError(err) && RESTART.has(err.code);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!pages || !selected) return;
    const res = await connect.run(() => api.channels.metaConnect({ selection: pages.selection, page_id: selected.id, with_instagram: Boolean(selected.instagram) && withInstagram }));
    if (!res) return;
    toast(t("messaging.metaConnected", { names: res.items.map((c) => c.display_name).join(", ") }));
    router.replace("/settings/channels");
  };

  const working = !outcome || (outcome.kind === "exchange" && !pages && !loadError);

  return (
    <>
      <PageHeader level={2} title={pages ? t("messaging.metaPickTitle") : t("messaging.metaTitle")} subtitle={pages ? t("messaging.metaPickBody") : undefined} />
      <div className={wf.stack} style={{ maxWidth: 600 }} aria-live="polite">
        {working ? (
          <div className={wf.working}>
            <strong>{t("messaging.metaWorking")}</strong>
            <div className={wf.track} aria-hidden="true">
              <span />
            </div>
          </div>
        ) : outcome?.kind === "denied" ? (
          <InlineAlert tone="info">{t("channels.callbackDenied")}</InlineAlert>
        ) : outcome?.kind === "invalid" ? (
          <InlineAlert tone="warning">{t("channels.callbackInvalid")}</InlineAlert>
        ) : null}

        {err ? (
          <InlineAlert tone="danger">
            {errorMessage(t, err)}
            <RequestId id={isApiError(err) ? err.requestId : null} />
          </InlineAlert>
        ) : null}

        {pages && !restart ? (
          pages.pages.length === 0 ? (
            <InlineAlert tone="warning">{t("messaging.metaNoPages")}</InlineAlert>
          ) : (
            <form className={wf.stack} onSubmit={submit} noValidate data-testid="meta-pages">
              <fieldset className={cx.choice}>
                <legend className="srOnly">{t("messaging.metaPickTitle")}</legend>
                {pages.pages.map((p) => (
                  <label key={p.id} className={cx.choiceOption}>
                    <input type="radio" name="meta-page" value={p.id} checked={pageId === p.id} onChange={() => setPageId(p.id)} />
                    <strong>{p.name ?? p.id}</strong>
                    <span>{p.instagram ? t("messaging.metaPageIg", { username: p.instagram.replace(/^@/, "") }) : t("messaging.metaPageNoIg")}</span>
                  </label>
                ))}
              </fieldset>
              {attempted && !selected ? (
                <p className={wf.hint} role="alert">
                  {t("messaging.metaPickRequired")}
                </p>
              ) : null}
              {selected?.instagram ? (
                <Checkbox label={t("messaging.withInstagram")} checked={withInstagram} onChange={(e) => setWithInstagram(e.target.checked)} />
              ) : null}
              <div>
                <Button type="submit" variant="primary" loading={connect.pending}>
                  {t("messaging.metaConnectPage")}
                </Button>
              </div>
            </form>
          )
        ) : null}

        {!working && (!pages || restart || pages.pages.length === 0) ? (
          <div>
            <ButtonLink href="/settings/channels">{restart || pages ? t("messaging.metaStartAgain") : t("channels.backToChannels")}</ButtonLink>
          </div>
        ) : null}
      </div>
    </>
  );
}
