# Nivaro brand assets

Rules: [`specs/26_NIVARO_BRAND_SYSTEM.md`](../../specs/26_NIVARO_BRAND_SYSTEM.md).
Geometry source: [`packages/design-system/brand/geometry.mjs`](../../packages/design-system/brand/geometry.mjs).

The **logo is the owner-approved artwork** (ADR-032). Its masters are cut from the concept board:

```bash
python assets/brand/scripts/extract_logo.py   # reference board → logo/source/*.png (needs numpy, pillow)
node assets/brand/scripts/render.mjs          # masters + motifs → everything else (needs system Chrome)
```

`render.mjs` writes:
- lockups, app icons, favicons, OG image and the motif SVGs here
- web icons (`apps/web/src/app/{favicon.ico,icon.png,apple-icon.png,opengraph-image.png}`,
  `apps/web/public/icons/*`) and logo copies (`apps/web/public/brand`)
- Flutter logo copies (`apps/mobile/assets/brand`) and launcher icons (Android mipmaps, iOS AppIcon)

Never edit outputs by hand.

| Folder | Status |
|---|---|
| `logo/source/` | Masters from the owner artwork (raster; vector master pending, GAP-BRAND-LOGO-VECTOR) |
| `logo/primary`, `logo/dark` | Generated lockups (light / navy) |
| `app-icons/`, `favicon/` | Generated (navy primary, light alternative, maskable) |
| `graphics/` | N-trail, commerce loop, four hand-drawn accents (generated SVG) |
| `banners/` | Default OG/social image. Campaign set: BRD-007 |
| `characters/`, `illustrations/`, `motion/` | **Briefs only.** No placeholder art ships (BRD-009/010/011) |
| `reference/` | Owner-supplied concept boards: the source of the logo. Their hex palette is superseded by specs/26 §5 |
