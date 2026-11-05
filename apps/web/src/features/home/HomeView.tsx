"use client";

import { useState } from "react";
import { ExceptionInbox } from "@/components/commerce/ExceptionInbox";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { InlineAlert, PageHeader, RequestId, SectionHeader } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ControlCenter } from "../automation/ControlCenter";
import styles from "./home.module.css";
import { useExceptions } from "./useExceptions";

export function HomeView() {
  const { t } = useI18n();
  const { me, membership, api } = useAuth();
  const verify = useAction();
  const [sent, setSent] = useState(false);
  const exceptions = useExceptions();
  if (!me) return null;
  const firstName = me.user.full_name.split(/\s+/)[0] || me.user.full_name;

  const sendVerification = async () => {
    const ok = await verify.run(async () => {
      await api.auth.requestEmailVerification();
      return true;
    });
    if (ok) setSent(true);
  };

  return (
    <>
      <PageHeader
        title={t("home.greeting", { name: firstName })}
        subtitle={t("home.subtitle", { business: membership?.merchant.name ?? "" })}
      />

      <ControlCenter onChanged={exceptions.query.reload} />

      {exceptions.commandError ? (
        <div style={{ marginTop: "var(--space-4)" }}>
          <InlineAlert tone="danger">
            {exceptions.commandError.message}
            <RequestId id={exceptions.commandError.requestId} />
          </InlineAlert>
        </div>
      ) : null}
      {exceptions.query.state.status === "loading" ? (
        <ExceptionInbox state="loading" />
      ) : exceptions.query.state.status === "error" ? (
        <ExceptionInbox state="error" error={exceptions.query.state.error} onRetry={exceptions.query.reload} />
      ) : (
        <ExceptionInbox state="ready" items={exceptions.items} renderAction={exceptions.renderAction} />
      )}

      <SectionHeader title={t("home.setupTitle")} />
      {verify.error ? <InlineAlert tone="danger">{errorMessage(t, verify.error)}</InlineAlert> : null}
      <ul className={styles.setup}>
        <li className={[styles.setupItem, me.user.email_verified && styles.done].filter(Boolean).join(" ")}>
          <span className={styles.check} aria-hidden="true">
            <Icon name="check" size={12} />
          </span>
          <span className={styles.label}>{me.user.email_verified ? t("home.verifyEmailDone") : t("home.verifyEmail")}</span>
          {me.user.email_verified ? null : sent ? (
            <span className={styles.sent} role="status">
              {t("home.linkSent", { email: me.user.email })}
            </span>
          ) : (
            <Button size="sm" onClick={sendVerification} loading={verify.pending}>
              {verify.pending ? t("home.sending") : t("home.sendLink")}
            </Button>
          )}
        </li>
        <li className={[styles.setupItem, me.user.mfa_enabled && styles.done].filter(Boolean).join(" ")}>
          <span className={styles.check} aria-hidden="true">
            <Icon name="check" size={12} />
          </span>
          <span className={styles.label}>{me.user.mfa_enabled ? t("home.mfaDone") : t("home.mfa")}</span>
          {me.user.mfa_enabled ? null : (
            <ButtonLink size="sm" href="/settings/security">
              {t("home.open")}
            </ButtonLink>
          )}
        </li>
        <li className={styles.setupItem}>
          <span className={styles.check} aria-hidden="true">
            <Icon name="check" size={12} />
          </span>
          <span className={styles.label}>{t("home.team")}</span>
          <ButtonLink size="sm" href="/settings/team">
            {t("home.open")}
          </ButtonLink>
        </li>
      </ul>
    </>
  );
}
