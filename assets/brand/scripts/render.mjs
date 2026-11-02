#!/usr/bin/env node
// Regenerates every Nivaro brand file. Logo/icons/OG come from the owner-approved artwork in
// assets/brand/logo/source (extract_logo.py); motifs come from packages/design-system/brand/geometry.mjs.
//   node assets/brand/scripts/render.mjs
// Writes: assets/brand/** (SVG + PNG), web icons (apps/web/src/app, apps/web/public), Flutter launcher
// icons (Android mipmaps, iOS AppIcon). Rasterises with the system Chrome via Playwright (web devDependency).
// Never hand-edit the outputs; change the geometry or this script and re-run.
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { FLOW, trailSegments } from "../../../packages/design-system/brand/geometry.mjs";

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

// ---------------------------------------------------------------- logo sources (owner-approved artwork, ADR-032)
// Extracted from the concept board by extract_logo.py. Every logo/icon/OG output is composed from these.
const SRC = resolve(brand, "logo/source");
const dataUrl = (f) => `data:image/png;base64,${readFileSync(resolve(SRC, f)).toString("base64")}`;
const MARK_PNG = dataUrl("nivaro-mark.png");
const WORD_INK = dataUrl("nivaro-wordmark-ink.png");
const WORD_WHITE = dataUrl("nivaro-wordmark-white.png");
const svg = (vb, inner, label = "Nivaro") =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" role="img" aria-label="${label}">\n${inner}\n</svg>\n`;
const files = {};

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
const { svg: OG_TRAIL } = trail({ count: 5, height: 250, x: 640, y: 380, id: "og" });

for (const [p, s] of Object.entries(files)) out(`assets/brand/${p}`, s);

// ---------------------------------------------------------------- rasterise
const req = createRequire(resolve(repo, "apps/web/package.json"));
const { chromium } = req("@playwright/test");
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage();
async function html(body, dest, w, h, { bg = "transparent", fonts = false } = {}) {
  await page.setViewportSize({ width: w, height: h });
  const head = fonts
    ? `<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;800&display=block" rel="stylesheet">`
    : "";
  await page.setContent(
    `<html><head>${head}<style>*{box-sizing:border-box}body{margin:0;width:${w}px;height:${h}px;background:${bg};font-family:Inter,system-ui,sans-serif}img{display:block}</style></head><body>${body}</body></html>`,
    { waitUntil: "networkidle" },
  );
  if (fonts) await page.evaluate(() => document.fonts.ready);
  const f = resolve(repo, dest);
  mkdirSync(dirname(f), { recursive: true });
  await page.screenshot({ path: f, omitBackground: bg === "transparent", clip: { x: 0, y: 0, width: w, height: h } });
}
const center = (inner) => `<div style="width:100%;height:100%;display:grid;place-items:center">${inner}</div>`;
// Mark is 384×263 (wider than tall): sized by width so the ribbon fills the optical centre.
async function appIcon(dest, px, { bg = C.navy, pct = 66 } = {}) {
  await html(center(`<img src="${MARK_PNG}" style="width:${pct}%">`), dest, px, px, { bg });
}
const lockup = (word, height) =>
  `<div style="display:flex;align-items:center;gap:${height * 0.22}px;padding:${height * 0.18}px"><img src="${MARK_PNG}" style="height:${height}px"><img src="${word}" style="height:${height * 0.62}px;margin-top:${height * 0.06}px"></div>`;

// Brand files
await html(lockup(WORD_INK, 160), "assets/brand/logo/primary/nivaro-lockup.png", 820, 220);
await html(lockup(WORD_WHITE, 160), "assets/brand/logo/dark/nivaro-lockup-white-wordmark.png", 820, 220);
await html(lockup(WORD_WHITE, 160), "assets/brand/logo/dark/nivaro-lockup-on-navy.png", 820, 220, { bg: C.navy });
await appIcon("assets/brand/app-icons/nivaro-app-icon-navy-1024.png", 1024);
await appIcon("assets/brand/app-icons/nivaro-app-icon-light-1024.png", 1024, { bg: C.white });
await appIcon("assets/brand/app-icons/nivaro-app-icon-maskable-1024.png", 1024, { pct: 54 });
const ogBody = `<div style="position:relative;width:1200px;height:630px;background:${C.navy};overflow:hidden">
  <svg style="position:absolute;inset:0" width="1200" height="630" viewBox="0 0 1200 630">${OG_TRAIL}</svg>
  <div style="position:absolute;left:80px;top:70px">${lockup(WORD_WHITE, 64).replace(/padding:[^"]*"/, "padding:0\"")}</div>
  <div style="position:absolute;left:80px;top:205px;color:#fff;font-weight:800;font-size:76px;letter-spacing:-1.5px;line-height:1.08">Your store,<br>on <span style="position:relative">autopilot<svg style="position:absolute;left:-2%;bottom:-14px;width:104%;height:22px" viewBox="0 0 200 20" preserveAspectRatio="none"><path fill="${C.teal}" d="M3 13.6C42 6.4 118 3.6 195.4 8.2c2.4.2 2.6 3.2.2 3.5C131 9.2 63 11 5.2 17.4c-2.8.3-4.6-3.1-2.2-3.8Z"/></svg></span>.</div>
  <div style="position:absolute;left:80px;top:440px;color:${C.slate300};font-weight:500;font-size:28px">From product photo to delivered order.</div>
  <div style="position:absolute;left:80px;top:532px;color:${C.teal};font-weight:600;font-size:20px;letter-spacing:2px">AUTONOMOUS COMMERCE OS</div>
</div>`;
await html(ogBody, "assets/brand/banners/og-default.png", 1200, 630, { fonts: true });
await html(ogBody, "apps/web/src/app/opengraph-image.png", 1200, 630, { fonts: true });
// Web: favicon (transparent), apple + PWA icons
for (const px of [16, 32, 48]) await html(center(`<img src="${MARK_PNG}" style="width:100%">`), `assets/brand/favicon/favicon-${px}.png`, px, px);
await html(center(`<img src="${MARK_PNG}" style="width:100%">`), "apps/web/src/app/icon.png", 64, 64);
// favicon.ico (16/32/48) for legacy browsers and crawlers
const { execFileSync } = await import("node:child_process");
execFileSync("magick", [16, 32, 48].map((px) => resolve(brand, `favicon/favicon-${px}.png`)).concat(resolve(repo, "apps/web/src/app/favicon.ico")));
await appIcon("apps/web/src/app/apple-icon.png", 180);
await appIcon("apps/web/public/icons/icon-192.png", 192);
await appIcon("apps/web/public/icons/icon-512.png", 512);
await appIcon("apps/web/public/icons/icon-maskable-512.png", 512, { pct: 54 });
// Web: logo sources served to the app (mark + both wordmark colours)
for (const f of ["nivaro-mark.png", "nivaro-wordmark-ink.png", "nivaro-wordmark-white.png"])
  writeFileSync(resolve(repo, "apps/web/public/brand", f), readFileSync(resolve(SRC, f)));
// Flutter: bundled logo sources
for (const f of ["nivaro-mark.png", "nivaro-wordmark-ink.png", "nivaro-mark-white.png"])
  writeFileSync(resolve(repo, "apps/mobile/assets/brand", f), readFileSync(resolve(SRC, f)));
// Flutter Android launcher (legacy square icons; adaptive icon is a known gap)
const android = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
for (const [d, px] of Object.entries(android)) await appIcon(`apps/mobile/android/app/src/main/res/mipmap-${d}/ic_launcher.png`, px);
// Flutter iOS AppIcon set (opaque, square; iOS applies the corner mask)
const iosDir = "apps/mobile/ios/Runner/Assets.xcassets/AppIcon.appiconset";
const ios = JSON.parse(readFileSync(resolve(repo, iosDir, "Contents.json"), "utf8")).images;
const done = new Set();
for (const im of ios) {
  if (done.has(im.filename)) continue;
  done.add(im.filename);
  await appIcon(`${iosDir}/${im.filename}`, Math.round(parseFloat(im.size) * parseInt(im.scale)));
}
await browser.close();
console.log(`brand: wrote ${Object.keys(files).length} SVG motifs and all logo/icon rasters`);
