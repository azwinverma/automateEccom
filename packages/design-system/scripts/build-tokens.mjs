#!/usr/bin/env node
// Generates platform token outputs from design-tokens.json.
// Outputs: dist/tokens.css (CSS custom properties, light + dark), dist/tokens.ts, and
// apps/mobile/lib/design/tokens.g.dart. Never edit generated files by hand.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { FLOW, MARK, WORDMARK } from "../brand/geometry.mjs";

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

// ---------- semantic layer ----------
const literal = (v) => /^(#|rgba?\()/.test(v);
function resolve_(ref) {
  if (literal(ref)) return ref;
  let node = t;
  for (const k of ref.split(".")) {
    node = node?.[k];
    if (node === undefined) throw new Error(`token ref not found: ${ref}`);
  }
  return typeof node === "string" ? node : node.value;
}
const semKey = (k) => kebab(k.replace(/\./g, "-"));
const semLight = Object.fromEntries(Object.entries(t.semantic.light).map(([k, v]) => [semKey(k), resolve_(v)]));
const semDark = Object.fromEntries(Object.entries(t.semantic.dark).map(([k, v]) => [semKey(k), resolve_(v)]));
for (const k of Object.keys(semDark)) if (!(k in semLight)) throw new Error(`dark-only semantic token: ${k}`);
const statusVars = Object.fromEntries(
  Object.entries(t.status).filter(([k]) => !k.startsWith("$")).map(([k, v]) => [kebab(k), semKey(v)]),
);
const riskVars = Object.fromEntries(
  Object.entries(t.risk).filter(([k]) => !k.startsWith("$")).map(([k, v]) => [kebab(k), semKey(v)]),
);
// Legacy component aliases (pre-Nivaro names). They point at the semantic layer; new code uses --color-*.
const legacy = {
  "surface-page": "surface-canvas",
  "surface-raised": "surface-raised",
  "surface-sunken": "surface-sunken",
  "text-primary": "text-primary",
  "text-secondary": "text-secondary",
  "text-muted": "text-muted",
  "border-default": "border-default",
  "border-strong": "border-strong",
  "action-primary": "action-primary",
  "action-primary-hover": "action-primary-hover",
  "action-primary-text": "action-primary-text",
  "focus-ring": "focus-ring",
  "row-hover": "surface-hover",
  "overlay-scrim": "scrim",
  "status-attention": "status-attention-fill",
};
const darkPrimitiveOverrides = {
  "semantic-success": dark.success,
  "semantic-warning": dark.warning,
  "semantic-danger": dark.danger,
  "semantic-info": dark.info,
};

// ---------- CSS ----------
const css = [`/* ${header} */`, ":root {"];
for (const [k, v] of Object.entries(colors)) css.push(`  --color-${k}: ${v};`);
for (const [k, v] of Object.entries(semLight)) css.push(`  --color-${k}: ${v};`);
for (const [k, v] of Object.entries(space)) css.push(`  --space-${k}: ${v}px;`);
for (const [k, v] of Object.entries(radius)) css.push(`  --radius-${k}: ${v}px;`);
for (const [k, v] of Object.entries(fontSize)) css.push(`  --font-size-${k}: ${v / 16}rem;`);
for (const [k, v] of Object.entries(weight)) css.push(`  --font-weight-${k}: ${v};`);
for (const [k, v] of Object.entries(lineHeight)) css.push(`  --line-height-${k}: ${v};`);
for (const [k, v] of Object.entries(family)) css.push(`  --font-family-${k}: ${v};`);
for (const [k, v] of Object.entries(duration)) css.push(`  --duration-${k}: ${v}ms;`, `  --motion-${k}: ${v}ms;`);
for (const [k, v] of Object.entries(easing)) css.push(`  --easing-${k}: ${v};`);
for (const [k, v] of Object.entries(elevation)) css.push(`  --elevation-${k}: ${v};`);
for (const [k, v] of Object.entries(statusVars)) css.push(`  --status-${k}: var(--color-${v});`);
for (const [k, v] of Object.entries(riskVars)) css.push(`  --risk-${k}: var(--color-${v});`);
for (const [k, v] of Object.entries(legacy)) css.push(`  --${k}: var(--color-${v});`);
css.push("  color-scheme: light;", "}");
const darkBody = [
  ...Object.entries(semDark).map(([k, v]) => `--color-${k}: ${v};`),
  ...Object.entries(darkPrimitiveOverrides).map(([k, v]) => `--color-${k}: ${v};`),
  "color-scheme: dark;",
];
css.push("@media (prefers-color-scheme: dark) {", '  :root:not([data-theme="light"]) {', ...darkBody.map((l) => `    ${l}`), "  }", "}");
css.push(':root[data-theme="dark"] {', ...darkBody.map((l) => `  ${l}`), "}");
css.push(
  ":lang(ne) { font-family: var(--font-family-devanagari); line-height: var(--line-height-devanagari); }",
  "@media (prefers-reduced-motion: reduce) { :root { " +
    Object.keys(duration).map((k) => `--duration-${k}: 0ms; --motion-${k}: 0ms;`).join(" ") +
    " } }",
  "",
);

// ---------- TS ----------
const ts = `// ${header}
export const tokens = ${JSON.stringify({ colors, dark, semantic: { light: semLight, dark: semDark }, space, radius, fontSize, weight, lineHeight, family, duration, easing, elevation, status: t.status }, null, 2)} as const;
export type ColorToken = keyof typeof tokens.colors;
`;

// ---------- Dart ----------
const hex = (h) => `Color(0xFF${h.replace("#", "").toUpperCase()})`;
const camel = (s) => s.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
const dart = [`// ${header}`, "// ignore_for_file: constant_identifier_names", "import 'package:flutter/painting.dart';", "", "abstract final class AppColors {"];
for (const [k, v] of Object.entries(colors)) dart.push(`  static const ${camel(k)} = ${hex(v)};`);
for (const [k, v] of Object.entries(dark)) dart.push(`  static const dark${camel("-" + k).replace(/^./, (c) => c.toUpperCase())} = ${hex(v)};`);
dart.push("}", "");
for (const [cls, sem] of [["AppColorsLight", semLight], ["AppColorsDark", semDark]]) {
  dart.push(`/// Semantic colours (${cls === "AppColorsLight" ? "light" : "dark"}). Widgets use these, not primitives.`, `abstract final class ${cls} {`);
  for (const [k, v] of Object.entries(sem)) {
    if (!v.startsWith("#")) continue; // rgba scrims are web-only
    dart.push(`  static const ${camel(k)} = ${hex(v)};`);
  }
  dart.push("}", "");
}
dart.push("abstract final class AppSpace {");
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
// ---------- Dart brand geometry (mark + wordmark primitives for CustomPainter) ----------
const seg = (n, g) => `  static const ${n} = [${g.x1}, ${g.y1}, ${g.x2}, ${g.y2}];`;
const geo = [
  `// ${header} (brand geometry from packages/design-system/brand/geometry.mjs)`,
  "// ignore_for_file: constant_identifier_names",
  "import 'package:flutter/painting.dart';",
  "",
  "/// N-loop mark in a 64×64 box. Segments are [x1, y1, x2, y2]; ribbon width 12, round caps.",
  "abstract final class NivaroMarkGeometry {",
  "  static const box = 64.0;",
  "  static const ribbon = 12.0;",
  seg("diagonal", MARK.diagonal),
  seg("left", MARK.left),
  seg("right", MARK.right),
  `  static const flowStart = ${hex(FLOW.start)};`,
  `  static const flowMid1 = ${hex(FLOW.mid1)};`,
  `  static const flowMid2 = ${hex(FLOW.mid2)};`,
  `  static const flowEnd = ${hex(FLOW.end)};`,
  `  static const fold = ${hex(FLOW.fold)};`,
  "}",
  "",
  "/// Wordmark \"nivaro\" (viewBox 150×46, stroke 6.4). Circles are [cx, cy, r].",
  "abstract final class NivaroWordmarkGeometry {",
  "  static const width = 150.0;",
  "  static const height = 46.0;",
  `  static const stroke = ${WORDMARK.stroke};`,
  `  static const circles = [${WORDMARK.circles.map((c) => `[${c.cx}, ${c.cy}, ${c.r}]`).join(", ")}];`,
  `  static const dot = [${WORDMARK.dot.cx}, ${WORDMARK.dot.cy}, ${WORDMARK.dot.r}];`,
  "}",
  "",
];
writeFileSync(resolve(repo, "apps/mobile/lib/design/brand_geometry.g.dart"), geo.join("\n"));
console.log("tokens: wrote dist/tokens.css, dist/tokens.ts, apps/mobile/lib/design/tokens.g.dart");
