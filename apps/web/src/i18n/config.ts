export const LOCALES = ["en", "ne"] as const;
export type AppLocale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: AppLocale = "ne";
export const LOCALE_COOKIE = "cos_locale";

/** BCP-47 tags used for Intl formatting (Nepal region for both languages). */
export const INTL_LOCALE: Record<AppLocale, string> = { en: "en-NP", ne: "ne-NP" };

export function isLocale(v: unknown): v is AppLocale {
  return typeof v === "string" && (LOCALES as readonly string[]).includes(v);
}

/** Pick a locale from cookie, then Accept-Language, else default. */
export function resolveLocale(cookieValue: string | undefined | null, acceptLanguage: string | null): AppLocale {
  if (isLocale(cookieValue)) return cookieValue;
  if (acceptLanguage) {
    const tags = acceptLanguage
      .split(",")
      .map((p) => p.trim().split(";")[0]?.toLowerCase() ?? "")
      .filter(Boolean);
    for (const tag of tags) {
      if (tag.startsWith("ne")) return "ne";
      if (tag.startsWith("en")) return "en";
    }
  }
  return DEFAULT_LOCALE;
}
