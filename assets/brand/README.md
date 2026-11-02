# Nivaro brand assets

Rules: [`specs/26_NIVARO_BRAND_SYSTEM.md`](../../specs/26_NIVARO_BRAND_SYSTEM.md).
Geometry source: [`packages/design-system/brand/geometry.mjs`](../../packages/design-system/brand/geometry.mjs).

Everything in `logo/`, `app-icons/`, `favicon/`, `graphics/` and `banners/og-default.*` is **generated**:

```bash
node assets/brand/scripts/render.mjs   # needs the system Chrome (Playwright, web devDependency)
```

The script also writes the web icons (`apps/web/src/app/icon.svg`, `apple-icon.png`,
`opengraph-image.png`, `apps/web/public/icons/*`) and the Flutter launcher icons (Android mipmaps,
iOS AppIcon set). Never edit outputs by hand; change the geometry or the script and re-run.

| Folder | Status |
|---|---|
| `logo/` | Final v1 (mark, wordmark, lockups; colour, white, ink, blue) |
| `app-icons/`, `favicon/` | Final v1 (navy primary, light alternative, maskable) |
| `graphics/` | N-trail, commerce loop, four hand-drawn accents |
| `banners/` | Default OG/social image only. Campaign set: BRD-007 |
| `characters/`, `illustrations/`, `motion/` | **Briefs only.** No placeholder art ships (BRD-009/010/011) |
| `reference/` | Owner-supplied concept boards. Their hex values are superseded by specs/26 §5 (ADR-029) |
