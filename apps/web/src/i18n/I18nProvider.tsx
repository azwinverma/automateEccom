"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { LOCALE_COOKIE, type AppLocale } from "./config";
import { createTranslator } from "./dictionaries";
import {
  formatDate,
  formatDateTime,
  formatMoney,
  formatNumber,
  formatPercent,
  formatRelative,
} from "./format";
import type { Translate } from "./types";

export interface I18nValue {
  locale: AppLocale;
  t: Translate;
  setLocale: (locale: AppLocale) => void;
  money: (amountMinor: number, currency?: string) => string;
  number: (value: number, options?: Intl.NumberFormatOptions) => string;
  percent: (ratio: number) => string;
  dateTime: (value: string | Date) => string;
  date: (value: string | Date) => string;
  relative: (value: string | Date) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({
  locale: initialLocale,
  timeZone,
  children,
}: {
  locale: AppLocale;
  timeZone?: string;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<AppLocale>(initialLocale);
  const router = useRouter();

  const setLocale = useCallback(
    (next: AppLocale) => {
      document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
      document.documentElement.lang = next;
      setLocaleState(next);
      router.refresh();
    },
    [router],
  );

  const value = useMemo<I18nValue>(
    () => ({
      locale,
      t: createTranslator(locale),
      setLocale,
      money: (amountMinor, currency = "NPR") => formatMoney(amountMinor, currency, locale),
      number: (v, o) => formatNumber(v, locale, o),
      percent: (r) => formatPercent(r, locale),
      dateTime: (v) => formatDateTime(v, locale, timeZone),
      date: (v) => formatDate(v, locale, timeZone),
      relative: (v) => formatRelative(v, locale),
    }),
    [locale, setLocale, timeZone],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}
