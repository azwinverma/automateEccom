"use client";

/**
 * Email-link flows (QA-001, QA-008): forgot / reset password, confirm email, accept a team invitation.
 * Every page works signed out; tokens come from the link and are sent once, never stored.
 */
import { isApiError } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import styles from "@/app/(auth)/auth.module.css";
import { Button, ButtonLink } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { EMAIL_RE } from "@/lib/validation";

const MIN_PASSWORD = 10;

function Head({ title, subtitle }: { title: string; subtitle?: ReactNode }) {
  return (
    <div className={styles.formHead}>
      <h1>{title}</h1>
      {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
    </div>
  );
}

function ErrorBox({ error }: { error: unknown }) {
  const { t } = useI18n();
  if (!error) return null;
  return (
    <InlineAlert tone="danger">
      {errorMessage(t, error)}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  );
}

/* ------------------------------------------------------------------ forgot password */
export function ForgotPasswordForm() {
  const { t } = useI18n();
  const { api } = useAuth();
  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState<string>();
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const value = email.trim();
    if (!EMAIL_RE.test(value)) return setFieldError(t("errors.field.email"));
    setFieldError(undefined);
    setPending(true);
    setError(null);
    try {
      await api.auth.requestPasswordReset(value);
      setSentTo(value);
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  };

  if (sentTo) {
    return (
      <div className={styles.form} role="status">
        <Head title={t("auth.forgot.sentTitle")} subtitle={t("auth.forgot.sentBody", { email: sentTo })} />
        <Link href="/login" className={styles.linkButton}>
          {t("auth.forgot.back")}
        </Link>
      </div>
    );
  }
  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <Head title={t("auth.forgot.title")} subtitle={t("auth.forgot.subtitle")} />
      <ErrorBox error={error} />
      <TextField
        label={t("auth.forgot.email")}
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={fieldError}
        required
      />
      <Button type="submit" variant="primary" className={styles.submit} loading={pending}>
        {pending ? t("auth.forgot.submitting") : t("auth.forgot.submit")}
      </Button>
      <p className={styles.alt}>
        <Link href="/login">{t("auth.forgot.back")}</Link>
      </p>
    </form>
  );
}

/* ------------------------------------------------------------------ reset password */
export function ResetPasswordForm() {
  const { t } = useI18n();
  const { api } = useAuth();
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [fieldError, setFieldError] = useState<string>();
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  if (token.length < 20) {
    return (
      <div className={styles.form}>
        <Head title={t("auth.reset.title")} />
        <InlineAlert tone="warning">{t("auth.reset.missing")}</InlineAlert>
        <Link href="/forgot-password" className={styles.linkButton}>
          {t("auth.reset.newLink")}
        </Link>
      </div>
    );
  }
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD) return setFieldError(t("auth.register.passwordHint"));
    setFieldError(undefined);
    setPending(true);
    setError(null);
    try {
      await api.auth.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      if (isApiError(err) && err.code === "weak_password") setFieldError(errorMessage(t, err));
      else setError(err);
    } finally {
      setPending(false);
    }
  };
  if (done) {
    return (
      <div className={styles.form} role="status">
        <Head title={t("auth.reset.doneTitle")} subtitle={t("auth.reset.doneBody")} />
        <ButtonLink href="/login" variant="primary" className={styles.submit}>
          {t("auth.reset.signIn")}
        </ButtonLink>
      </div>
    );
  }
  const expired = isApiError(error) && error.code === "reset_invalid";
  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <Head title={t("auth.reset.title")} subtitle={t("auth.reset.subtitle")} />
      <ErrorBox error={error} />
      {expired ? (
        <Link href="/forgot-password" className={styles.linkButton}>
          {t("auth.reset.newLink")}
        </Link>
      ) : null}
      <TextField
        label={t("auth.reset.password")}
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        hint={t("auth.register.passwordHint")}
        error={fieldError}
        minLength={MIN_PASSWORD}
        required
      />
      <Button type="submit" variant="primary" className={styles.submit} loading={pending}>
        {pending ? t("auth.reset.submitting") : t("auth.reset.submit")}
      </Button>
    </form>
  );
}

/* ------------------------------------------------------------------ confirm email */
export function VerifyEmailView() {
  const { t } = useI18n();
  const { api } = useAuth();
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"working" | "done" | "failed">(token.length >= 20 ? "working" : "failed");
  const [error, setError] = useState<unknown>(null);
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current || token.length < 20) return;
    sent.current = true; // a token is single-use: never send it twice (React strict mode re-runs effects)
    api.auth
      .confirmEmailVerification(token)
      .then(() => setState("done"))
      .catch((err) => {
        setError(err);
        setState("failed");
      });
  }, [api, token]);

  if (state === "working") return <Head title={t("auth.verify.title")} subtitle={t("auth.verify.working")} />;
  if (state === "done") {
    return (
      <div className={styles.form} role="status">
        <Head title={t("auth.verify.doneTitle")} subtitle={t("auth.verify.doneBody")} />
        <ButtonLink href="/home" variant="primary" className={styles.submit}>
          {t("auth.verify.continue")}
        </ButtonLink>
      </div>
    );
  }
  return (
    <div className={styles.form} role="alert">
      <Head title={t("auth.verify.failedTitle")} subtitle={t("auth.verify.failedBody")} />
      {error && !(isApiError(error) && error.code === "verification_invalid") ? <ErrorBox error={error} /> : null}
      <ButtonLink href="/login" variant="secondary">
        {t("auth.login.submit")}
      </ButtonLink>
    </div>
  );
}

/* ------------------------------------------------------------------ accept invitation */
export function AcceptInviteView() {
  const { t } = useI18n();
  const router = useRouter();
  const { api, status, me, ensureSession, reloadMe, selectMerchant, signOut } = useAuth();
  const token = useSearchParams().get("token") ?? "";
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const here = `/invite?token=${encodeURIComponent(token)}`;

  useEffect(() => ensureSession(), [ensureSession]);

  if (token.length < 20) {
    return (
      <div className={styles.form}>
        <Head title={t("auth.invite.title")} />
        <InlineAlert tone="warning">{t("auth.invite.missing")}</InlineAlert>
      </div>
    );
  }
  if (status === "idle" || status === "loading") {
    return <Head title={t("auth.invite.title")} subtitle={t("common.loading")} />;
  }
  const accept = async () => {
    setPending(true);
    setError(null);
    try {
      const res = (await api.team.acceptInvitation(token)) as { membership?: { merchant_id?: string } };
      setDone(true);
      await reloadMe();
      if (res.membership?.merchant_id) selectMerchant(res.membership.merchant_id);
      router.replace("/home");
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  };

  if (done) return <Head title={t("auth.invite.doneTitle")} subtitle={t("auth.invite.doneBody")} />;
  if (status !== "ready" || !me) {
    const next = encodeURIComponent(here);
    return (
      <div className={styles.form}>
        <Head title={t("auth.invite.title")} subtitle={t("auth.invite.subtitle")} />
        <p className={styles.subtitle}>{t("auth.invite.signInPrompt")}</p>
        <ButtonLink href={`/login?next=${next}`} variant="primary" className={styles.submit}>
          {t("auth.invite.signIn")}
        </ButtonLink>
        <ButtonLink href={`/register?next=${next}`} variant="secondary">
          {t("auth.invite.createAccount")}
        </ButtonLink>
      </div>
    );
  }
  return (
    <div className={styles.form}>
      <Head title={t("auth.invite.title")} subtitle={t("auth.invite.subtitle")} />
      <ErrorBox error={error} />
      <p className={styles.meta}>{t("auth.invite.signedInAs", { email: me.user.email })}</p>
      <Button type="button" variant="primary" className={styles.submit} loading={pending} onClick={() => void accept()}>
        {pending ? t("auth.invite.accepting") : t("auth.invite.accept")}
      </Button>
      <button
        type="button"
        className={styles.linkButton}
        onClick={() => void signOut().then(() => router.replace(`/login?next=${encodeURIComponent(here)}`))}
      >
        {t("auth.invite.useOther")}
      </button>
    </div>
  );
}
