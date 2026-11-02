"use client";

import { isApiError } from "@commerce-os/api-client";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { InlineAlert, PageHeader, RequestId, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { resolveCallback, takePending, type CallbackResolution } from "@/lib/channels/oauth";
import wf from "../shared/workflow.module.css";

/** OAuth return page: validates the pending connect, exchanges the code once, then returns. */
export function ChannelCallback() {
  const { t } = useI18n();
  const { api } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const toast = useToast();
  const [outcome, setOutcome] = useState<CallbackResolution | null>(null);
  const [error, setError] = useState<unknown>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // strict mode / re-render: exchange the code exactly once
    started.current = true;
    const res = resolveCallback(new URLSearchParams(params.toString()), takePending());
    setOutcome(res);
    // Drop code/state from the address bar and history.
    window.history.replaceState(null, "", "/channels/callback");
    if (res.kind !== "exchange") return;
    api.channels
      .callback({ provider: res.provider, state: res.state, code: res.code })
      .then((c) => {
        toast(t("channels.connectedToast", { name: c.display_name }));
        router.replace(res.returnTo);
      })
      .catch(setError);
  }, [api, params, router, t, toast]);

  const back = outcome?.returnTo ?? "/settings/channels";
  return (
    <>
      <PageHeader level={1} title={t("channels.title")} />
      <div className={wf.stack} style={{ maxWidth: 560 }} aria-live="polite">
        {!outcome || (outcome.kind === "exchange" && !error) ? (
          <div className={wf.working}>
            <strong>{t("channels.callbackWorking")}</strong>
            <div className={wf.track} aria-hidden="true">
              <span />
            </div>
          </div>
        ) : outcome.kind === "denied" ? (
          <InlineAlert tone="info">{t("channels.callbackDenied")}</InlineAlert>
        ) : outcome.kind === "invalid" ? (
          <InlineAlert tone="warning">{t("channels.callbackInvalid")}</InlineAlert>
        ) : (
          <InlineAlert tone="danger">
            {errorMessage(t, error)}
            <RequestId id={isApiError(error) ? error.requestId : null} />
          </InlineAlert>
        )}
        {outcome && (outcome.kind !== "exchange" || error) ? (
          <div>
            <ButtonLink href={back}>{t("channels.backToChannels")}</ButtonLink>
          </div>
        ) : null}
      </div>
    </>
  );
}
