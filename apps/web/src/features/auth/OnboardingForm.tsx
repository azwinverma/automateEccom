"use client";

import { isApiError, unwrap, type Locale, type Merchant } from "@commerce-os/api-client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import styles from "@/app/(auth)/auth.module.css";
import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId } from "@/components/ui/misc";
import { errorMessage, fieldErrorMessages } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { SLUG_RE, slugify } from "@/lib/validation";

const TIMEZONES = [
  { value: "Asia/Kathmandu", key: "kathmandu" },
  { value: "Asia/Kolkata", key: "kolkata" },
  { value: "Asia/Dubai", key: "dubai" },
  { value: "Asia/Qatar", key: "doha" },
  { value: "UTC", key: "utc" },
] as const;

// The Phase 0 contract fixes country NP / currency NPR; more currencies come with cross-border selling.
const CURRENCIES = ["NPR"] as const;

export function OnboardingForm() {
  const { t, locale } = useI18n();
  const { api, me, selectMerchant, reloadMe } = useAuth();
  const router = useRouter();
  const { keyFor, reset } = useIdempotencyKey();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [currency, setCurrency] = useState<string>("NPR");
  const [timezone, setTimezone] = useState("Asia/Kathmandu");
  const [defaultLocale, setDefaultLocale] = useState<Locale>(locale);
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; slug?: string }>({});
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);

  const effectiveSlug = slugTouched ? slug : slugify(name);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: typeof fieldErrors = {};
    if (!name.trim()) errs.name = t("errors.field.required");
    if (effectiveSlug && !SLUG_RE.test(effectiveSlug)) errs.slug = t("errors.field.slug");
    setFieldErrors(errs);
    if (Object.keys(errs).length) return;

    const body = {
      name: name.trim(),
      ...(effectiveSlug ? { slug: effectiveSlug } : {}),
      country: "NP" as const,
      currency,
      timezone,
      default_locale: defaultLocale,
    };
    setPending(true);
    setError(null);
    try {
      const res = await api.merchants.create(body, { idempotencyKey: keyFor(body) });
      const merchant = unwrap<Merchant>(res, "merchant");
      reset();
      selectMerchant(merchant.id);
      await reloadMe();
      router.replace("/home");
    } catch (err) {
      if (isApiError(err) && err.code === "slug_taken") {
        setSlugTouched(true);
        setSlug(effectiveSlug);
        setFieldErrors({ slug: t("errors.slug_taken") });
      } else {
        if (isApiError(err) && err.code === "validation_error") setFieldErrors(fieldErrorMessages(t, err.fieldErrors()));
        setError(err);
      }
    } finally {
      setPending(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      <div className={styles.formHead}>
        <span className={styles.eyebrow}>{t("onboarding.eyebrow")}</span>
        <h1>{t("onboarding.title")}</h1>
        <p className={styles.subtitle}>{t("onboarding.subtitle")}</p>
      </div>
      {error ? (
        <InlineAlert tone="danger">
          {errorMessage(t, error)}
          <RequestId id={isApiError(error) ? error.requestId : null} />
        </InlineAlert>
      ) : null}
      <TextField
        label={t("onboarding.name")}
        placeholder={t("onboarding.namePlaceholder")}
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={fieldErrors.name}
        autoComplete="organization"
        required
        autoFocus
      />
      <TextField
        label={t("onboarding.slug")}
        value={effectiveSlug}
        onChange={(e) => {
          setSlugTouched(true);
          setSlug(e.target.value.toLowerCase());
        }}
        hint={t("onboarding.slugHint")}
        error={fieldErrors.slug}
        autoCapitalize="none"
        spellCheck={false}
        mono
      />
      <div className={styles.row}>
        <SelectField label={t("onboarding.currency")} value={currency} onChange={(e) => setCurrency(e.target.value)} hint={t("onboarding.currencyHint")}>
          {CURRENCIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </SelectField>
        <SelectField label={t("onboarding.timezone")} value={timezone} onChange={(e) => setTimezone(e.target.value)}>
          {TIMEZONES.map((tz) => (
            <option key={tz.value} value={tz.value}>
              {t(`onboarding.tz.${tz.key}`)}
            </option>
          ))}
        </SelectField>
      </div>
      <SelectField
        label={t("onboarding.language")}
        value={defaultLocale}
        onChange={(e) => setDefaultLocale(e.target.value as Locale)}
        hint={t("onboarding.languageHint")}
      >
        <option value="ne">{t("language.ne")}</option>
        <option value="en">{t("language.en")}</option>
      </SelectField>
      <Button type="submit" variant="primary" className={styles.submit} loading={pending}>
        {pending ? t("onboarding.submitting") : t("onboarding.submit")}
      </Button>
      {me ? <p className={styles.meta}>{t("onboarding.signedInAs", { email: me.user.email })}</p> : null}
    </form>
  );
}
