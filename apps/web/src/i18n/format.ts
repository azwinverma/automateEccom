import { INTL_LOCALE, type AppLocale } from "./config";

export const DEFAULT_TIMEZONE = "Asia/Kathmandu";

/** Currency symbols sellers actually write; Intl gives "नेरू"/"NPR". */
const LOCAL_SYMBOL: Record<string, Record<AppLocale, string>> = {
  NPR: { ne: "रू", en: "Rs" },
};

function minorDigits(currency: string): number {
  try {
    return new Intl.NumberFormat("en", { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2;
  } catch {
    return 2;
  }
}

/**
 * Format money from minor units. NPR renders as "रू 1,250" (ne) / "Rs 1,250" (en).
 * Latin digits are used in both languages — that is what sellers type in chats and
 * on receipts; Devanagari digits are reserved for formal documents.
 */
export function formatMoney(amountMinor: number, currency: string, locale: AppLocale): string {
  const digits = minorDigits(currency);
  const amount = amountMinor / 10 ** digits;
  const nf = new Intl.NumberFormat(INTL_LOCALE[locale], {
    style: "currency",
    currency,
    numberingSystem: "latn",
    minimumFractionDigits: Number.isInteger(amount) ? 0 : digits,
    maximumFractionDigits: digits,
  });
  const symbol = LOCAL_SYMBOL[currency]?.[locale];
  if (!symbol) return nf.format(amount);
  const parts = nf.formatToParts(amount);
  let out = "";
  let symbolDone = false;
  for (const p of parts) {
    if (p.type === "currency") {
      out += symbol;
      symbolDone = true;
    } else if (p.type === "literal" && symbolDone && out.endsWith(symbol)) {
      out += " ";
    } else {
      out += p.value;
    }
  }
  // Guarantee "symbol space number" even if the locale data omits the literal.
  return out.replace(new RegExp(`^(-?)${symbol}\\s*`), `$1${symbol} `);
}

export function formatNumber(value: number, locale: AppLocale, options: Intl.NumberFormatOptions = {}): string {
  return new Intl.NumberFormat(INTL_LOCALE[locale], { numberingSystem: "latn", ...options }).format(value);
}

export function formatPercent(ratio: number, locale: AppLocale): string {
  return formatNumber(ratio, locale, { style: "percent", maximumFractionDigits: 0 });
}

function toDate(v: string | Date): Date | null {
  const d = typeof v === "string" ? new Date(v) : v;
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDateTime(v: string | Date, locale: AppLocale, timeZone = DEFAULT_TIMEZONE): string {
  const d = toDate(v);
  if (!d) return "";
  return new Intl.DateTimeFormat(INTL_LOCALE[locale], {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone,
    numberingSystem: "latn",
  }).format(d);
}

export function formatDate(v: string | Date, locale: AppLocale, timeZone = DEFAULT_TIMEZONE): string {
  const d = toDate(v);
  if (!d) return "";
  return new Intl.DateTimeFormat(INTL_LOCALE[locale], { dateStyle: "medium", timeZone, numberingSystem: "latn" }).format(d);
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31536000],
  ["month", 2592000],
  ["week", 604800],
  ["day", 86400],
  ["hour", 3600],
  ["minute", 60],
  ["second", 1],
];

export function formatRelative(v: string | Date, locale: AppLocale, now: Date = new Date()): string {
  const d = toDate(v);
  if (!d) return "";
  const diff = Math.round((d.getTime() - now.getTime()) / 1000);
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto", numberingSystem: "latn" } as Intl.RelativeTimeFormatOptions);
  for (const [unit, secs] of UNITS) {
    if (Math.abs(diff) >= secs || unit === "second") return rtf.format(Math.round(diff / secs), unit);
  }
  return "";
}
