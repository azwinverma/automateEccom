/** Client-side mirrors of backend SKU/barcode rules (apps/backend/.../catalog/rules.py). */

export const SKU_RE = /^[A-Z0-9][A-Z0-9._-]{0,63}$/;
export const HANDLE_RE = /^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$/;

export function normalizeSku(sku: string): string {
  return sku.trim().toUpperCase().replace(/ /g, "-");
}

export function gtinValid(code: string): boolean {
  if (!/^\d+$/.test(code) || ![8, 12, 13, 14].includes(code.length)) return false;
  const digits = code.split("").map(Number);
  const check = digits.pop()!;
  const total = digits.reverse().reduce((sum, d, i) => sum + d * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (total % 10)) % 10 === check;
}

export type BarcodeProblem = "checksum" | "format";

/** null = fine (or empty). Numeric GTIN-length codes must have a valid check digit. */
export function barcodeProblem(raw: string): BarcodeProblem | null {
  const b = raw.trim().replace(/ /g, "");
  if (!b) return null;
  if (/^\d+$/.test(b) && [8, 12, 13, 14].includes(b.length)) return gtinValid(b) ? null : "checksum";
  return /^[A-Za-z0-9-]{4,32}$/.test(b) ? null : "format";
}
