#!/usr/bin/env node
// Regenerates every Nivaro brand file from packages/design-system/brand/geometry.mjs.
//   node assets/brand/scripts/render.mjs
// Writes: assets/brand/** (SVG + PNG), web icons (apps/web/src/app, apps/web/public), Flutter launcher
// icons (Android mipmaps, iOS AppIcon). Rasterises with the system Chrome via Playwright (web devDependency).
// Never hand-edit the outputs; change the geometry or this script and re-run.
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { FLOW, MARK, WORDMARK, trailSegments } from "../../../packages/design-system/brand/geometry.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../../..");
const brand = resolve(repo, "assets/brand");
const tokens = JSON.parse(readFileSync(resolve(repo, "packages/design-system/design-tokens.json"), "utf8"));
const C = {
  blue: tokens.color.brand.blue.value,
  teal: tokens.color.brand.teal.value,
  navy: tokens.color.neutral.ink.value,
  white: tokens.color.neutral.white.value,
  cloud: tokens.color.neutral.cloud.value,
  slate300: tokens.color.neutral.lineStrong.value,
  coral: tokens.color.brand.coral.value,
};
const out = (p, s) => {
  const f = resolve(repo, p);
  mkdirSync(dirname(f), { recursive: true });
  writeFileSync(f, s);
  return f;
};
const line = (s, extra = "") => `<path d="M${s.x1} ${s.y1} L${s.x2} ${s.y2}" ${extra}/>`;

// ---------------------------------------------------------------- mark
function markInner(id = "nv", { mono = null } = {}) {
  const r = `stroke-width="12" stroke-linecap="round"`;
  if (mono) {
    return `<defs><mask id="${id}-m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64"><rect width="64" height="64" fill="#fff"/><path d="${MARK.monoFolds}" stroke="#000" stroke-width="2.2" stroke-linecap="round"/></mask></defs>
<g stroke="${mono}" ${r}>${line(MARK.diagonal, `mask="url(#${id}-m)"`)}${line(MARK.left)}${line(MARK.right)}</g>`;
  }
  const g = (n, s, a, b) =>
    `<linearGradient id="${id}-${n}" x1="${s.x1}" y1="${s.y1}" x2="${s.x2}" y2="${s.y2}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient>`;
  const d = MARK.diagonal;
  return `<defs>${g("a", MARK.left, FLOW.start, FLOW.mid1)}${g("b", d, FLOW.mid1, FLOW.mid2)}${g("c", MARK.right, FLOW.mid2, FLOW.end)}<linearGradient id="${id}-f" x1="${d.x1}" y1="${d.y1}" x2="${d.x2}" y2="${d.y2}" gradientUnits="userSpaceOnUse"><stop offset="0.08" stop-color="${FLOW.fold}" stop-opacity="0.34"/><stop offset="0.34" stop-color="${FLOW.fold}" stop-opacity="0"/><stop offset="0.66" stop-color="${FLOW.fold}" stop-opacity="0"/><stop offset="0.92" stop-color="${FLOW.fold}" stop-opacity="0.22"/></linearGradient></defs>
${line(d, `stroke="url(#${id}-b)" ${r}`)}${line(d, `stroke="url(#${id}-f)" ${r}`)}${line(MARK.left, `stroke="url(#${id}-a)" ${r}`)}${line(MARK.right, `stroke="url(#${id}-c)" ${r}`)}`;
}
const wordInner = (color) =>
  `<g stroke="${color}" fill="none" stroke-width="${WORDMARK.stroke}" stroke-linecap="round" stroke-linejoin="round">${WORDMARK.paths.map((p) => `<path d="${p}"/>`).join("")}${WORDMARK.circles.map((c) => `<circle cx="${c.cx}" cy="${c.cy}" r="${c.r}"/>`).join("")}</g><circle cx="${WORDMARK.dot.cx}" cy="${WORDMARK.dot.cy}" r="${WORDMARK.dot.r}" fill="${color}"/>`;
const svg = (vb, inner, label = "Nivaro") =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" role="img" aria-label="${label}">\n${inner}\n</svg>\n`;
const lockup = (mark, word) => svg("0 0 228 64", `${mark}<g transform="translate(70 9)">${wordInner(word)}</g>`);

const files = {
  "logo/primary/nivaro-mark.svg": svg(MARK.viewBox, markInner()),
  "logo/primary/nivaro-wordmark.svg": svg(WORDMARK.viewBox, wordInner(C.navy), "nivaro"),
  "logo/primary/nivaro-lockup.svg": lockup(markInner(), C.navy),
  "logo/light/nivaro-lockup.svg": lockup(markInner(), C.navy),
  "logo/light/nivaro-mark-blue.svg": svg(MARK.viewBox, markInner("nv", { mono: C.blue })),
  "logo/dark/nivaro-lockup-on-navy.svg": lockup(markInner(), C.white),
  "logo/dark/nivaro-lockup-white.svg": lockup(markInner("nv", { mono: C.white }), C.white),
  "logo/dark/nivaro-mark-white.svg": svg(MARK.viewBox, markInner("nv", { mono: C.white })),
  "logo/dark/nivaro-wordmark-white.svg": svg(WORDMARK.viewBox, wordInner(C.white), "nivaro"),
  "logo/monochrome/nivaro-mark-ink.svg": svg(MARK.viewBox, markInner("nv", { mono: C.navy })),
  "logo/monochrome/nivaro-lockup-ink.svg": lockup(markInner("nv", { mono: C.navy }), C.navy),
  "logo/monochrome/nivaro-wordmark-ink.svg": svg(WORDMARK.viewBox, wordInner(C.navy), "nivaro"),
};

// ---------------------------------------------------------------- app icons (square, full-bleed; OS applies the mask)
const appIcon = (bg, scale = 0.62) => {
  const s = (1024 * scale) / 64;
  const o = (1024 - 64 * s) / 2;
  return svg("0 0 1024 1024", `<rect width="1024" height="1024" fill="${bg}"/><g transform="translate(${o} ${o}) scale(${s})">${markInner("ai")}</g>`);
};
files["app-icons/nivaro-app-icon-navy.svg"] = appIcon(C.navy);
files["app-icons/nivaro-app-icon-light.svg"] = appIcon(C.white);
files["app-icons/nivaro-app-icon-maskable.svg"] = appIcon(C.navy, 0.5); // keeps the mark inside the 80% safe zone
files["favicon/nivaro-favicon.svg"] = svg(MARK.viewBox, markInner("fv"));

// ---------------------------------------------------------------- motifs
function trail({ count, height, x = 0, y = 0, id = "tr", fade = true }) {
  const t = trailSegments({ count, height, x, y });
  const w = t.width;
  const r = `stroke-width="${t.ribbon.toFixed(2)}" stroke-linecap="round"`;
  const segs = t.segments
    .map((s, i) => {
      // Crosses are drawn first (under), rises on top, as in the mark.
      const shade =
        s.kind === "cross"
          ? line(s, `stroke="url(#${id}-f${i})" ${r}`) +
            `<linearGradient id="${id}-f${i}" x1="${s.x1}" y1="${s.y1}" x2="${s.x2}" y2="${s.y2}" gradientUnits="userSpaceOnUse"><stop offset="0.08" stop-color="${FLOW.fold}" stop-opacity="0.3"/><stop offset="0.34" stop-color="${FLOW.fold}" stop-opacity="0"/><stop offset="0.66" stop-color="${FLOW.fold}" stop-opacity="0"/><stop offset="0.92" stop-color="${FLOW.fold}" stop-opacity="0.2"/></linearGradient>`
          : "";
      return { z: s.kind === "cross" ? 0 : 1, s: line(s, `stroke="url(#${id}-g)" ${r}`) + shade };
    })
    .sort((a, b) => a.z - b.z)
    .map((x) => x.s)
    .join("");
  const defs = `<defs><linearGradient id="${id}-g" x1="${x}" y1="0" x2="${x + w}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${FLOW.start}"/><stop offset="1" stop-color="${FLOW.end}"/></linearGradient>${
    fade
      ? `<linearGradient id="${id}-fd" x1="${x}" y1="0" x2="${x + w}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.18" stop-color="#fff"/><stop offset="1" stop-color="#fff"/></linearGradient><mask id="${id}-mk" maskUnits="userSpaceOnUse" x="${x - 20}" y="${y - 20 - t.ribbon}" width="${w + 40}" height="${height + 40 + 2 * t.ribbon}"><rect x="${x - 20}" y="${y - 20 - t.ribbon}" width="${w + 40}" height="${height + 40 + 2 * t.ribbon}" fill="url(#${id}-fd)"/></mask>`
      : ""
  }</defs>`;
  return { svg: `${defs}<g ${fade ? `mask="url(#${id}-mk)"` : ""}>${segs}</g>`, t };
}
{
  const { svg: s, t } = trail({ count: 7, height: 120, x: 10, y: 10, fade: false });
  files["graphics/n-trail.svg"] = svg(`0 0 ${Math.ceil(t.width + 20)} 140`, s, "Nivaro trail motif");
}
{
  // Commerce loop: four rises = Create → Sell → Fulfill → Learn; label sits above each rise's peak.
  const { svg: s, t } = trail({ count: 4, height: 150, x: 20, y: 80, id: "cl", fade: false });
  const peaks = t.segments.filter((g) => g.kind === "rise");
  const labels = ["Create", "Sell", "Fulfill", "Learn"]
    .map((l, i) => `<text x="${peaks[i].x2}" y="${peaks[i].y2 - t.ribbon / 2 - 16}" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-weight="600" font-size="22" fill="${C.navy}">${l}</text><circle cx="${peaks[i].x2}" cy="${peaks[i].y2}" r="5" fill="${C.white}"/>`)
    .join("");
  files["graphics/commerce-loop.svg"] = svg(`0 0 ${Math.ceil(t.width + 40)} 250`, s + labels, "Create, Sell, Fulfill, Learn");
}
// Hand-drawn accents (graffiti energy, used sparingly: marketing, onboarding, milestones). Filled tapered strokes.
files["graphics/accent-underline.svg"] = svg(
  "0 0 200 20",
  `<path fill="${C.teal}" d="M3 13.6C42 6.4 118 3.6 195.4 8.2c2.4.2 2.6 3.2.2 3.5C131 9.2 63 11 5.2 17.4c-2.8.3-4.6-3.1-2.2-3.8Z"/>`,
  "",
);
files["graphics/accent-arrow.svg"] = svg(
  "0 0 120 80",
  `<g fill="none" stroke="${C.navy}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 70C20 34 52 14 98 18"/><path d="M84 6 100 18 86 31"/></g>`,
  "",
);
files["graphics/accent-ring.svg"] = svg(
  "0 0 220 90",
  `<path fill="none" stroke="${C.coral}" stroke-width="4" stroke-linecap="round" d="M128 8C70 2 10 18 8 46c-2 30 82 40 140 32 46-6 70-26 58-46C196 14 160 6 116 9"/>`,
  "",
);
files["graphics/accent-tick.svg"] = svg(
  "0 0 60 48",
  `<path fill="none" stroke="${C.teal}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M5 26c6 4 11 9 16 16C29 26 40 13 55 5"/>`,
  "",
);

// ---------------------------------------------------------------- OG / social banner (1200×630)
{
  const { svg: tr } = trail({ count: 5, height: 250, x: 640, y: 380, id: "og" });
  const ul = `<g transform="translate(186 386) scale(1.62 1.1)"><path fill="${C.teal}" d="M3 13.6C42 6.4 118 3.6 195.4 8.2c2.4.2 2.6 3.2.2 3.5C131 9.2 63 11 5.2 17.4c-2.8.3-4.6-3.1-2.2-3.8Z"/></g>`;
  files["banners/og-default.svg"] = svg(
    "0 0 1200 630",
    `<rect width="1200" height="630" fill="${C.navy}"/>${tr}<g transform="translate(80 80) scale(0.9)">${markInner("ogm")}<g transform="translate(70 9)">${wordInner(C.white)}</g></g>` +
      `<text x="80" y="290" font-family="Inter, system-ui, sans-serif" font-weight="800" font-size="76" letter-spacing="-1.5" fill="${C.white}">Your store,</text>` +
      `<text x="80" y="374" font-family="Inter, system-ui, sans-serif" font-weight="800" font-size="76" letter-spacing="-1.5" fill="${C.white}">on autopilot.</text>${ul}` +
      `<text x="80" y="470" font-family="Inter, system-ui, sans-serif" font-weight="500" font-size="28" fill="${C.slate300}">From product photo to delivered order.</text>` +
      `<text x="80" y="560" font-family="Inter, system-ui, sans-serif" font-weight="600" font-size="20" letter-spacing="2" fill="${C.teal}">AUTONOMOUS COMMERCE OS</text>`,
    "Nivaro — Your store, on autopilot.",
  );
}

for (const [p, s] of Object.entries(files)) out(`assets/brand/${p}`, s);

// ---------------------------------------------------------------- rasterise
const req = createRequire(resolve(repo, "apps/web/package.json"));
const { chromium } = req("@playwright/test");
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage();
async function png(src, dest, w, h = w, { bg = "transparent", fonts = false } = {}) {
  const body = readFileSync(resolve(brand, src), "utf8").replace("<svg ", `<svg width="${w}" height="${h}" `);
  await page.setViewportSize({ width: w, height: h });
  const head = fonts
    ? `<link rel="preconnect" href="https://fonts.gstatic.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;800&display=block" rel="stylesheet">`
    : "";
  await page.setContent(`<html><head>${head}</head><body style="margin:0;background:${bg}">${body}</body></html>`, { waitUntil: "networkidle" });
  if (fonts) await page.evaluate(() => document.fonts.ready);
  const f = resolve(repo, dest);
  mkdirSync(dirname(f), { recursive: true });
  await page.screenshot({ path: f, omitBackground: bg === "transparent", clip: { x: 0, y: 0, width: w, height: h } });
}
// Brand PNGs
await png("logo/primary/nivaro-mark.svg", "assets/brand/logo/primary/nivaro-mark-512.png", 512);
await png("logo/primary/nivaro-lockup.svg", "assets/brand/logo/primary/nivaro-lockup-912.png", 912, 256);
await png("logo/dark/nivaro-lockup-on-navy.svg", "assets/brand/logo/dark/nivaro-lockup-on-navy-912.png", 912, 256, { bg: C.navy });
await png("app-icons/nivaro-app-icon-navy.svg", "assets/brand/app-icons/nivaro-app-icon-navy-1024.png", 1024);
await png("app-icons/nivaro-app-icon-light.svg", "assets/brand/app-icons/nivaro-app-icon-light-1024.png", 1024);
await png("banners/og-default.svg", "assets/brand/banners/og-default.png", 1200, 630, { fonts: true });
// Web: Next.js file-based metadata icons + PWA manifest icons + OG image
out("apps/web/src/app/icon.svg", files["favicon/nivaro-favicon.svg"]);
await png("favicon/nivaro-favicon.svg", "assets/brand/favicon/favicon-32.png", 32);
await png("app-icons/nivaro-app-icon-navy.svg", "apps/web/src/app/apple-icon.png", 180);
await png("app-icons/nivaro-app-icon-navy.svg", "apps/web/public/icons/icon-192.png", 192);
await png("app-icons/nivaro-app-icon-navy.svg", "apps/web/public/icons/icon-512.png", 512);
await png("app-icons/nivaro-app-icon-maskable.svg", "apps/web/public/icons/icon-maskable-512.png", 512);
await png("banners/og-default.svg", "apps/web/src/app/opengraph-image.png", 1200, 630, { fonts: true });
// Flutter Android launcher (legacy square icons; adaptive icon is a known gap)
const android = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
for (const [d, s] of Object.entries(android))
  await png("app-icons/nivaro-app-icon-navy.svg", `apps/mobile/android/app/src/main/res/mipmap-${d}/ic_launcher.png`, s);
// Flutter iOS AppIcon set (opaque, square; iOS applies the corner mask)
const iosDir = "apps/mobile/ios/Runner/Assets.xcassets/AppIcon.appiconset";
const ios = JSON.parse(readFileSync(resolve(repo, iosDir, "Contents.json"), "utf8")).images;
const done = new Set();
for (const im of ios) {
  if (done.has(im.filename)) continue;
  done.add(im.filename);
  const px = Math.round(parseFloat(im.size) * parseInt(im.scale));
  await png("app-icons/nivaro-app-icon-navy.svg", `${iosDir}/${im.filename}`, px, px, { bg: C.navy });
}
await browser.close();
console.log(`brand: wrote ${Object.keys(files).length} SVGs and raster icons`);
