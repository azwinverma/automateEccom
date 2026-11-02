"use client";

import { isApiError } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import styles from "@/app/(auth)/auth.module.css";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId } from "@/components/ui/misc";
import { errorMessage, fieldErrorMessages } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { bffLogin, isBrowserSession } from "@/lib/auth/bff";
import { EMAIL_RE, MIN_PASSWORD } from "@/lib/validation";

type Fields = "full_name" | "email" | "phone" | "password";

export function RegisterForm() {
  const { t, locale } = useI18n();
  const { api, establishSession } = useAuth();
  const router = useRouter();
  const [values, setValues] = useState<Record<Fields, string>>({ full_name: "", email: "", phone: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<Fields, string>>>({});
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);

  const set = (k: Fields) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value }));

  const validate = () => {
    const errs: Partial<Record<Fields, string>> = {};
    if (!values.full_name.trim()) errs.full_name = t("errors.field.required");
    if (!EMAIL_RE.test(values.email.trim())) errs.email = t("errors.field.email");
    if (values.password.length < MIN_PASSWORD) errs.password = t("errors.field.passwordShort");
    else if (values.password.toLowerCase() === values.email.trim().toLowerCase()) errs.password = t("errors.field.invalid");
    return errs;
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const errs = validate();
    setFieldErrors(errs);
    if (Object.keys(errs).length) return;
    setPending(true);
    setError(null);
    const email = values.email.trim();
    try {
      await api.auth.register({
        email,
        password: values.password,
        full_name: values.full_name.trim(),
        phone: values.phone.trim() || undefined,
        locale,
      });
    } catch (err) {
      setPending(false);
      if (isApiError(err) && err.code === "email_taken") {
        setFieldErrors({ email: t("errors.email_taken") });
        return;
      }
      if (isApiError(err) && err.code === "validation_error") {
        setFieldErrors(fieldErrorMessages(t, err.fieldErrors()) as Partial<Record<Fields, string>>);
      }
      setError(err);
      return;
    }
    try {
      const result = await bffLogin(email, values.password);
      if (isBrowserSession(result)) {
        await establishSession(result);
        router.replace("/onboarding");
      } else {
        router.replace("/login?next=/onboarding");
      }
    } catch {
      router.replace("/login?next=/onboarding");
    } finally {
      setPending(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      <div className={styles.formHead}>
        <h1>{t("auth.register.title")}</h1>
        <p className={styles.subtitle}>{t("auth.register.subtitle")}</p>
      </div>
      {error ? (
        <InlineAlert tone="danger">
          {errorMessage(t, error)}
          <RequestId id={isApiError(error) ? error.requestId : null} />
        </InlineAlert>
      ) : null}
      <TextField label={t("auth.register.fullName")} autoComplete="name" value={values.full_name} onChange={set("full_name")} error={fieldErrors.full_name} required />
      <TextField label={t("auth.register.email")} type="email" autoComplete="email" value={values.email} onChange={set("email")} error={fieldErrors.email} required />
      <TextField
        label={t("auth.register.phone")}
        optionalLabel={t("common.optional")}
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        placeholder="98XXXXXXXX"
        value={values.phone}
        onChange={set("phone")}
        hint={t("auth.register.phoneHint")}
        error={fieldErrors.phone}
      />
      <TextField
        label={t("auth.register.password")}
        type="password"
        autoComplete="new-password"
        value={values.password}
        onChange={set("password")}
        hint={t("auth.register.passwordHint")}
        error={fieldErrors.password}
        minLength={MIN_PASSWORD}
        required
      />
      <Button type="submit" variant="primary" className={styles.submit} loading={pending}>
        {pending ? t("auth.register.submitting") : t("auth.register.submit")}
      </Button>
      <p className={styles.alt}>
        {t("auth.register.haveAccount")} <Link href="/login">{t("auth.register.signIn")}</Link>
      </p>
    </form>
  );
}
