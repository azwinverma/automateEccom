#!/usr/bin/env node
// Generates platform token outputs from design-tokens.json.
// Outputs: dist/tokens.css (CSS custom properties, light + dark), dist/tokens.ts, and
// apps/mobile/lib/design/tokens.g.dart. Never edit generated files by hand.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const repo = resolve(root, "../..");
const t = JSON.parse(readFileSync(resolve(root, "design-tokens.json"), "utf8"));

const kebab = (s) => s.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
const header = "Generated from packages/design-system/design-tokens.json. Do not edit.";

// Flatten color groups (excluding dark) to { "brand-blue": "#..", "semantic-success": "#..", "semantic-success-soft": ".." }
const colors = {};
for (const [group, entries] of Object.entries(t.color)) {
  if (group === "dark") continue;
  for (const [name, tok] of Object.entries(entries)) {
    colors[`${group}-${kebab(name)}`] = tok.value;
    if (tok.soft) colors[`${group}-${kebab(name)}-soft`] = tok.soft;
  }
}
const dark = Object.fromEntries(Object.entries(t.color.dark).map(([k, v]) => [kebab(k), v.value]));
const val = (g) => Object.fromEntries(Object.entries(g).map(([k, v]) => [k, v.value]));
const space = val(t.space), radius = val(t.radius), fontSize = val(t.font.size);
const weight = val(t.font.weight), lineHeight = val(t.font.lineHeight), duration = val(t.motion.duration);
const easing = val(t.motion.easing), elevation = val(t.elevation), family = val(t.font.family);

// ---------- CSS ----------
const css = [`/* ${header} */`, ":root {"];
for (const [k, v] of Object.entries(colors)) css.push(`  --color-${k}: ${v};`);
for (const [k, v] of Object.entries(space)) css.push(`  --space-${k}: ${v}px;`);
for (const [k, v] of Object.entries(radius)) css.push(`  --radius-${k}: ${v}px;`);
for (const [k, v] of Object.entries(fontSize)) css.push(`  --font-size-${k}: ${v / 16}rem;`);
for (const [k, v] of Object.entries(weight)) css.push(`  --font-weight-${k}: ${v};`);
for (const [k, v] of Object.entries(lineHeight)) css.push(`  --line-height-${k}: ${v};`);
for (const [k, v] of Object.entries(family)) css.push(`  --font-family-${k}: ${v};`);
for (const [k, v] of Object.entries(duration)) css.push(`  --duration-${k}: ${v}ms;`);
for (const [k, v] of Object.entries(easing)) css.push(`  --easing-${k}: ${v};`);
for (const [k, v] of Object.entries(elevation)) css.push(`  --elevation-${k}: ${v};`);
// Semantic surface aliases (what components should use)
css.push(
  "  --surface-page: var(--color-neutral-cloud);",
  "  --surface-raised: var(--color-neutral-white);",
  "  --surface-sunken: var(--color-neutral-paper);",
  "  --text-primary: var(--color-neutral-ink);",
  "  --text-secondary: var(--color-neutral-slate);",
  "  --text-muted: var(--color-neutral-slate-muted);",
  "  --border-default: var(--color-neutral-line);",
  "  --border-strong: var(--color-neutral-line-strong);",
  "  --action-primary: var(--color-brand-blue);",
  "  --focus-ring: var(--color-brand-blue);",
  "}",
  "@media (prefers-color-scheme: dark) {",
  "  :root:not([data-theme=\"light\"]) {",
  `    --surface-page: ${dark.surface};`,
  `    --surface-raised: ${dark["surface-raised"]};`,
  `    --surface-sunken: ${dark.surface};`,
  `    --text-primary: ${dark.text};`,
  `    --text-secondary: ${dark["text-muted"]};`,
  `    --text-muted: ${dark["text-muted"]};`,
  `    --border-default: ${dark.line};`,
  `    --border-strong: ${dark.line};`,
  `    --action-primary: ${dark["brand-blue"]};`,
  `    --focus-ring: ${dark["brand-blue"]};`,
  `    --color-semantic-success: ${dark.success};`,
  `    --color-semantic-warning: ${dark.warning};`,
  `    --color-semantic-danger: ${dark.danger};`,
  `    --color-semantic-info: ${dark.info};`,
  "  }",
  "}",
  ":lang(ne) { font-family: var(--font-family-devanagari); line-height: var(--line-height-devanagari); }",
  "@media (prefers-reduced-motion: reduce) { :root { --duration-fast: 0ms; --duration-standard: 0ms; --duration-large: 0ms; } }",
  ""
);

// ---------- TS ----------
const ts = `// ${header}
export const tokens = ${JSON.stringify({ colors, dark, space, radius, fontSize, weight, lineHeight, family, duration, easing, elevation, status: t.status }, null, 2)} as const;
export type ColorToken = keyof typeof tokens.colors;
`;

// ---------- Dart ----------
const hex = (h) => `Color(0xFF${h.replace("#", "").toUpperCase()})`;
const camel = (s) => s.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
const dart = [`// ${header}`, "// ignore_for_file: constant_identifier_names", "import 'package:flutter/painting.dart';", "", "abstract final class AppColors {"];
for (const [k, v] of Object.entries(colors)) dart.push(`  static const ${camel(k)} = ${hex(v)};`);
for (const [k, v] of Object.entries(dark)) dart.push(`  static const dark${camel("-" + k).replace(/^./, (c) => c.toUpperCase())} = ${hex(v)};`);
dart.push("}", "", "abstract final class AppSpace {");
for (const [k, v] of Object.entries(space)) dart.push(`  static const double s${k} = ${v};`);
dart.push("}", "", "abstract final class AppRadius {");
for (const [k, v] of Object.entries(radius)) dart.push(`  static const double ${k} = ${v};`);
dart.push("}", "", "abstract final class AppFontSize {");
for (const [k, v] of Object.entries(fontSize)) dart.push(`  static const double ${/^\d/.test(k) ? "x" + k : k} = ${v};`);
dart.push("}", "", "abstract final class AppMotion {");
for (const [k, v] of Object.entries(duration)) dart.push(`  static const ${k} = Duration(milliseconds: ${v});`);
dart.push("}", "", "abstract final class AppLineHeight {");
for (const [k, v] of Object.entries(lineHeight)) dart.push(`  static const double ${k} = ${v};`);
dart.push("}", "");

mkdirSync(resolve(root, "dist"), { recursive: true });
writeFileSync(resolve(root, "dist/tokens.css"), css.join("\n"));
writeFileSync(resolve(root, "dist/tokens.ts"), ts);
const dartOut = resolve(repo, "apps/mobile/lib/design/tokens.g.dart");
mkdirSync(dirname(dartOut), { recursive: true });
writeFileSync(dartOut, dart.join("\n"));
console.log("tokens: wrote dist/tokens.css, dist/tokens.ts, apps/mobile/lib/design/tokens.g.dart");
