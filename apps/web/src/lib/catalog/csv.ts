import type { ImportRowError } from "@commerce-os/api-client";

/** Header row from the backend import docstring (apps/backend/.../catalog/imports.py). */
export const IMPORT_HEADERS = [
  "handle",
  "title",
  "description",
  "category",
  "brand",
  "tags",
  "option1_name",
  "option1_value",
  "option2_name",
  "option2_value",
  "option3_name",
  "option3_value",
  "sku",
  "barcode",
  "price",
  "compare_at_price",
  "cost",
  "weight_grams",
] as const;

/** Example rows: one kurta in two sizes, one single-variant product. Prices in rupees. */
const TEMPLATE_ROWS: string[][] = [
  ["cotton-kurta", "Cotton Kurta", "Handloom cotton, breathable", "Clothing > Women > Kurta", "Thamel Threads", "kurta,cotton", "Size", "M", "Colour", "Maroon", "", "", "", "", "1250", "1500", "700", "300"],
  ["cotton-kurta", "Cotton Kurta", "", "", "", "", "Size", "L", "Colour", "Maroon", "", "", "", "", "1250", "1500", "700", "320"],
  ["dhaka-topi", "Dhaka Topi", "Palpali dhaka", "Accessories > Caps", "", "topi", "", "", "", "", "", "", "", "", "650", "", "300", "80"],
];

/** Quote a CSV cell; neutralise spreadsheet formulas (=, +, -, @) in exported text. */
export function csvCell(value: unknown, guardFormulas = true): string {
  let s = value === null || value === undefined ? "" : String(value);
  if (guardFormulas && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(rows: unknown[][]): string {
  return rows.map((r) => r.map((c) => csvCell(c)).join(",")).join("\r\n") + "\r\n";
}

export function templateCsv(): string {
  return toCsv([[...IMPORT_HEADERS], ...TEMPLATE_ROWS]);
}

export function errorsCsv(errors: ImportRowError[], headers: [string, string, string, string]): string {
  return toCsv([headers, ...errors.map((e) => [e.row ?? "", e.handle ?? "", e.code, e.message])]);
}

/** Trigger a browser download (UTF-8 BOM so Excel shows Devanagari correctly). */
export function downloadText(fileName: string, text: string, type = "text/csv;charset=utf-8") {
  const url = URL.createObjectURL(new Blob(["﻿", text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
