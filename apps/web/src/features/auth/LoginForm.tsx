"use client";

import { isApiError } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import styles from "@/app/(auth)/auth.module.css";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { bffLogin, bffMfaVerify, isBrowserSession, safeNext } from "@/lib/auth/bff";
import type { BrowserSession } from "@/lib/session-constants";
import { EMAIL_RE } from "@/lib/validation";

export function LoginForm() {
  const { t } = useI18n();
  const { establishSession } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState("");
  const [code, setCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string; code?: string }>({});
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const codeRef = useRef<HTMLInputElement>(null);

  const finish = async (session: BrowserSession) => {
    const me = await establishSession(session);
    const hasBusiness = me.memberships.some((m) => m.status === "active" || !m.status);
    const next = safeNext(params.get("next"));
    // An invitee may not have a business yet: the invitation itself is where they're going (QA-008).
    router.replace(hasBusiness || next.startsWith("/invite") ? next : "/onboarding");
  };

  const submitCredentials = async (e: FormEvent) => {
    e.preventDefault();
    const errs: typeof fieldErrors = {};
    if (!EMAIL_RE.test(email.trim())) errs.email = t("errors.field.email");
    if (!password) errs.password = t("errors.field.required");
    setFieldErrors(errs);
    if (Object.keys(errs).length) return;
    setPending(true);
    setError(null);
    try {
      const result = await bffLogin(email.trim(), password);
      if (isBrowserSession(result)) {
        await finish(result);
      } else {
        setMfaToken(result.mfa_token);
        setPassword("");
        setStep("mfa");
        requestAnimationFrame(() => codeRef.current?.focus());
      }
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  };

  const submitCode = async (e: FormEvent) => {
    e.preventDefault();
    const clean = code.replace(/\s+/g, "");
    if (!useRecovery && !/^\d{6}$/.test(clean)) {
      setFieldErrors({ code: t("errors.field.code") });
      return;
    }
    if (!clean) {
      setFieldErrors({ code: t("errors.field.required") });
      return;
    }
    setFieldErrors({});
    setPending(true);
    setError(null);
    try {
      await finish(await bffMfaVerify(mfaToken, clean));
    } catch (err) {
      // An expired MFA challenge means starting over.
      if (isApiError(err) && err.status === 401 && err.code !== "mfa_invalid_code") {
        setStep("credentials");
        setMfaToken("");
      }
      setCode("");
      setError(err);
    } finally {
      setPending(false);
    }
  };

  const alert = error ? (
    <InlineAlert tone="danger">
      {errorMessage(t, error)}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  ) : null;

  if (step === "mfa") {
    return (
      <form className={styles.form} onSubmit={submitCode} noValidate>
        <div className={styles.formHead}>
          <h1>{t("auth.mfa.title")}</h1>
          <p className={styles.subtitle}>{useRecovery ? t("auth.mfa.recoverySubtitle") : t("auth.mfa.subtitle")}</p>
        </div>
        {alert}
        <TextField
          ref={codeRef}
          key={useRecovery ? "recovery" : "totp"}
          label={useRecovery ? t("auth.mfa.recoveryCode") : t("auth.mfa.code")}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          error={fieldErrors.code}
          inputMode={useRecovery ? "text" : "numeric"}
          autoComplete="one-time-code"
          maxLength={useRecovery ? 32 : 6}
          mono
          autoFocus
          required
        />
        <Button type="submit" variant="primary" className={styles.submit} loading={pending}>
          {pending ? t("auth.mfa.submitting") : t("auth.mfa.submit")}
        </Button>
        <button
          type="button"
          className={styles.linkButton}
          onClick={() => {
            setUseRecovery((v) => !v);
            setCode("");
            setFieldErrors({});
          }}
        >
          {useRecovery ? t("auth.mfa.useApp") : t("auth.mfa.useRecovery")}
        </button>
        <button
          type="button"
          className={styles.linkButton}
          onClick={() => {
            setStep("credentials");
            setMfaToken("");
            setCode("");
            setError(null);
          }}
        >
          {t("auth.mfa.startOver")}
        </button>
      </form>
    );
  }

  return (
    <form className={styles.form} onSubmit={submitCredentials} noValidate>
      <div className={styles.formHead}>
        <h1>{t("auth.login.title")}</h1>
        <p className={styles.subtitle}>{t("auth.login.subtitle")}</p>
      </div>
      {alert}
      <TextField
        label={t("auth.login.email")}
        type="email"
        name="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={fieldErrors.email}
        required
      />
      <TextField
        label={t("auth.login.password")}
        type="password"
        name="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={fieldErrors.password}
        required
      />
      <Link href="/forgot-password" className={styles.forgot}>
        {t("auth.login.forgot")}
      </Link>
      <Button type="submit" variant="primary" className={styles.submit} loading={pending}>
        {pending ? t("auth.login.submitting") : t("auth.login.submit")}
      </Button>
      <p className={styles.alt}>
        {t("auth.login.noAccount")} <Link href="/register">{t("auth.login.createAccount")}</Link>
      </p>
    </form>
  );
}
