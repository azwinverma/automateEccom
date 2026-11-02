"use client";

import { useState } from "react";
import { AutopilotStatusStrip } from "@/components/commerce/AutopilotStatusStrip";
import { ExceptionInbox } from "@/components/commerce/ExceptionInbox";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { InlineAlert, PageHeader, SectionHeader } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { AUTOMATION_PHASE } from "@/lib/sections";
import styles from "./home.module.css";

export function HomeView() {
  const { t } = useI18n();
  const { me, membership, api } = useAuth();
  const verify = useAction();
  const [sent, setSent] = useState(false);
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

      {/* Phase 0: no automation engine or exception feed exists yet, so counts are real zeros. */}
      <AutopilotStatusStrip mode="assisted" automatedCount={0} needsAttentionCount={0} lockedUntilPhase={AUTOMATION_PHASE} />

      <ExceptionInbox state="ready" items={[]} />

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
