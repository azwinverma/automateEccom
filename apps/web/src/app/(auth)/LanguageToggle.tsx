"use client";

import { LOCALES } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import styles from "./auth.module.css";

export function LanguageToggle() {
  const { t, locale, setLocale } = useI18n();
  return (
    <div className={styles.langSwitch} role="group" aria-label={t("language.label")}>
      {LOCALES.map((l) => (
        <button key={l} type="button" lang={l} aria-pressed={locale === l} onClick={() => setLocale(l)}>
          {t(`language.${l}`)}
        </button>
      ))}
    </div>
  );
}
