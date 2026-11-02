/**
 * Rupee ↔ paisa conversion for price inputs. Pure string math — no floats touch the
 * amount, so "19.99" is exactly 1999 paisa (19.99 * 100 in floating point is 1998.9999…).
 */
export const MAX_MINOR = 10_000_000_000; // matches the backend guard (NPR 100M)

export type MoneyError = "invalid" | "decimals" | "negative" | "too_large";
export type MoneyParse = { ok: true; minor: number | null } | { ok: false; error: MoneyError };

const DEVANAGARI_DIGITS = "०१२३४५६७८९";

function normalise(input: string): string {
  let s = "";
  for (const ch of input) {
    const d = DEVANAGARI_DIGITS.indexOf(ch);
    s += d >= 0 ? String(d) : ch;
  }
  return s
    .trim()
    .replace(/^(?:NPR|Rs\.?|रू\.?)\s*/i, "")
    .replace(/[,\s]/g, "");
}

/** "1,250.50" / "Rs 1250.5" / "रू १२५०" → paisa. Empty input → `minor: null`. */
export function parseRupees(input: string): MoneyParse {
  const s = normalise(input);
  if (!s) return { ok: true, minor: null };
  if (s.startsWith("-")) return { ok: false, error: "negative" };
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(s)) return { ok: false, error: "invalid" };
  const [intPart = "", frac = ""] = s.split(".");
  if (frac.length > 2) return { ok: false, error: "decimals" };
  const digits = `${intPart || "0"}${frac.padEnd(2, "0")}`.replace(/^0+(?=\d)/, "");
  if (digits.length > String(MAX_MINOR).length) return { ok: false, error: "too_large" };
  const minor = Number(digits);
  if (!Number.isSafeInteger(minor) || minor > MAX_MINOR) return { ok: false, error: "too_large" };
  return { ok: true, minor };
}

/** Paisa → editable rupee string: 125000 → "1250", 125050 → "1250.50". */
export function minorToRupeesInput(minor: number | null | undefined): string {
  if (minor === null || minor === undefined || !Number.isInteger(minor) || minor < 0) return "";
  const rupees = Math.floor(minor / 100);
  const paisa = minor % 100;
  return paisa === 0 ? String(rupees) : `${rupees}.${String(paisa).padStart(2, "0")}`;
}
