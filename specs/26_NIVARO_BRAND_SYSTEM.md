# Nivaro Brand System

> v1.0 (2026-11-02). Owner-approved brand: **NIVARO**. Visual concept: the two concept boards in
> `assets/brand/reference/`. This document is the rulebook; `18_BRAND_DESIGN_SYSTEM.md` covers product
> UI patterns and components. Where they disagree, this document wins on brand and 18 on UI behaviour.

## 1. Brand strategy
| | |
|---|---|
| Name | **Nivaro** (wordmark `nivaro`; `NIVARO` in legal, corporate, deck and formal contexts) |
| Category | **Autonomous Commerce OS** |
| Tagline | **Your store, on autopilot.** |
| Promise | **From product photo to delivered order — automatically.** |
| USP | **Your store runs itself. You handle exceptions.** |
| Supporting statement | **Create once. Sell everywhere. Let Nivaro handle the routine work.** |
| Positioning | Nivaro helps online sellers create, publish, sell, fulfill, support and optimize commerce from one place. |

Nivaro is **one product**, not a family of apps. Module names exist only where they help navigation or
communication. They are product areas, never separate brands with their own logos.

| Module | Covers | Use the module name when |
|---|---|---|
| Nivaro Studio | AI product studio, photos, descriptions | Navigation, feature pages, release notes |
| Nivaro Video | Auto Reels, premium AI video | Plans, credits, campaign graphics |
| Nivaro Inbox | Unified inbox, AI sales agent | Navigation, feature pages |
| Nivaro Commerce | Orders, COD, payments, fulfilment, returns | Marketing and sales material only |
| Nivaro Autopilot | Automation engine, decision policy, Autopilot Score | Navigation, plan pages |
| Nivaro Intelligence | Product Brain, Commerce Memory, Store Twin, intelligence engines | Marketing; in product use plain names ("Product Brain") |
| Nivaro Console | Internal admin/operations console | Internal staff only |
| Nivaro Enterprise | Enterprise plan and controls | Plans and contracts |

Do not over-brand features. It is "Return insights", not "Nivaro Return Intelligence™ Pro".

## 2. Brand character
Capable, energetic, human, modern, intelligent, joyful, trustworthy, fast, global, commerce-native.

It is **not** sterile corporate software, a generic AI startup, futuristic, crypto/gaming, glassy,
gradient-heavy, or "innovation theatre".

**Target feeling:** a highly capable commerce operating system with a human, energetic visual identity.
The seller sees calm operational clarity, expressive brand moments, recognisable Nivaro components,
subtle automation motion and no generic AI look.

## 3. Voice (summary; full rules in 19)
- Specific commerce language: "COD", "courier", "listing", "ready to ship". Never "leverage AI to
  unlock growth".
- Banned: revolutionary, next-gen, supercharge, unlock (your) potential, AI-powered everything,
  seamless, game-changing.
- Honest about automation: say what Nivaro did, what it needs from the seller, and how sure it is.

## 4. Logo
### Symbol: the N-loop
One continuous ribbon draws an **N**:
1. It rises (**Create**).
2. It crosses down (**Sell → Fulfill**).
3. It rises again (**Learn**).

Each stem folds over the diagonal, so the mark reads as one loop that keeps going. It means flow,
continuity, automation, connected commerce, the learning loop and forward motion.

**Geometry is code, not a drawing.** The single source is `packages/design-system/brand/geometry.mjs`:
- **Mark:** a 64-unit box with a 12-unit ribbon and round caps. The diagonal runs from (24,16) to
  (40,48), the left stem from (14,50) to (24,16), and the right stem from (40,48) to (50,14).
- **Colour:** the ribbon runs Nivaro Blue → Teal. A navy fold shade sits at each end of the diagonal.
- **Wordmark:** `nivaro` built from stroked geometric letters with a 6.4-unit stroke and an x-height
  of 23. It needs no font file and renders identically everywhere.

`assets/brand/scripts/render.mjs` regenerates every SVG and PNG from that geometry.

### Variants (`assets/brand/logo/`)
| File | Use |
|---|---|
| `primary/nivaro-lockup.svg` | Default: colour mark + ink wordmark on light |
| `primary/nivaro-mark.svg` | Mark alone (favicon, avatar, small spaces) |
| `dark/nivaro-lockup-on-navy.svg` | Colour mark + white wordmark on Deep Navy |
| `dark/nivaro-lockup-white.svg`, `dark/nivaro-mark-white.svg` | Single-colour white on photos or dark |
| `monochrome/nivaro-*-ink.svg` | Single-colour ink (print, fax, embossing, partner co-branding) |
| `light/nivaro-mark-blue.svg` | Single-colour blue, for one-colour print on light |

In the single-colour mark the fold is kept by two short gaps where the stems cross the diagonal. The
mark is never a solid "N".

### Wordmark rules
- Always lowercase `nivaro` in the logo. Do not retype it in a font.
- "Nivaro" in running text. "NIVARO" only in legal, corporate and formal contexts.
- The ™ shown on the concept boards is a legal decision (GAP-BRAND-TRADEMARK). Do not add it until
  the trademark is filed.
- A product suffix (e.g. **Console**) is set in UI type (Inter 500, Slate 700) after a 1px divider.
  It is never part of the wordmark geometry.

### Clear space and minimum size
- **Clear space:** at least the ribbon width × 2 (= 3/8 of the mark height) on every side.
- **Minimum mark size:** 16px on screen (favicon) and 6mm in print.
- **Minimum lockup height:** 20px on screen and 8mm in print.
- **Below 24px:** use the mark alone. Below 20px, the wordmark loses its counters.

### Misuse (never)
- Stretch, skew, rotate or re-angle the stems.
- Recolour the ribbon outside the variants above, or put a gradient on the wordmark.
- Add drop shadows, glows, bevels, 3D effects or outlines.
- Place the colour mark on busy photos (use the white variant on a scrim).
- Rebuild the mark from a font "N".
- Enclose the mark in a circle, or add sparkles or "AI" badges to it.
- Combine it with another logo without the co-branding divider and clear space.

## 5. Colour
### Brand palette (authoritative; the concept boards' hex values are superseded, ADR-029)
| Role | Name | Hex | Token |
|---|---|---|---|
| Primary | Nivaro Blue | #2563EB | `color.brand.blue` → `brand.primary`, `action.primary` |
| Primary | Nivaro Teal | #14B8A6 | `color.brand.teal` → `brand.secondary`, `flow.end` |
| Primary | Deep Navy / Ink | #0F172A | `color.neutral.ink` → `text.primary`, `surface.inverse` |
| Accent | Joy Coral | #FF6B6B | `color.brand.coral` → `brand.accent` (celebrate) |
| Accent | Sun Yellow | #FBBF24 | `color.brand.sun` → `status.attentionFill`, credits |
| Neutral | Slate 700 / 500 / 300 / 200 / 100 | #334155 / #64748B / #CBD5E1 / #E2E8F0 / #F1F5F9 | `color.neutral.*` |
| Neutral | Cloud / White | #F8FAFC / #FFFFFF | `surface.canvas` / `surface.raised` |

### Rules
- **Logo colours:** Blue, Teal and Deep Navy only.
- **Balance:** ~70% neutral, 20% primary and soft brand, 10% vivid accent.
- **Accents:** use at most one accent colour per screen. Coral marks celebration and milestones and is
  never used for errors. Sun marks credits and attention fills and is never text on light.
- **Teal as text or icon on light** uses `text.positive` (#0F766E). #14B8A6 is fill-only (2.5:1).
- **Gradients:** only along the ribbon (mark, trail motif, the active-nav ribbon). No gradient
  backgrounds, buttons, cards or text.
- **Semantic success/warning/danger/info** are separate from brand colours. Danger red is never brand
  coral; success green is never brand teal.
- **Components** use semantic tokens (`--color-text-primary`, `--color-action-primary`, …), never
  primitives or hex. CI rule: no hex in component CSS (BRD-016).

## 6. Typography
| Use | Family | Weight |
|---|---|---|
| English | Inter | 400 body, 500 labels, 600 cards/navigation, 700 headings, 800 hero/emphasis only |
| Nepali | Noto Sans Devanagari | Same scale; line-height 1.7 for matras |
| Numbers | Inter with tabular numerals in tables and meters | |

No "AI futuristic" display faces. Hero and milestone headlines may use 800 at the `display` size with
−2.5% tracking. Product UI tops out at 700.

## 7. Iconography
- **One family:** the in-house 16px line set (`apps/web/src/components/ui/Icon.tsx`). It uses a 1.5px
  stroke, round joins and commerce subjects (box, receipt, truck, return arrow, inbox, store).
- **Mobile:** Material Symbols Outlined at weight 300 until the in-house set is exported for Flutter
  (BRD-012).
- **No sparkle icon for AI.** AI-originated content is marked with the "AI" text tag in brand blue.
  Automation is marked with the node icon.
- **App category icons** (Create, Sell, Fulfill, Grow) on the concept board are marketing
  illustrations, not UI icons.

## 8. Graphic system: the ribbon
Every Nivaro graphic is built from the mark's ribbon, at the same angles and ribbon proportion
(width = 12/64 of the rise height). That keeps one art style everywhere.

| Motif | What it is | Where |
|---|---|---|
| **N-trail** (`graphics/n-trail.svg`, `<NTrail>`) | The N continued: rises and crosses repeating, Blue → Teal | Banners, OG images, onboarding, campaign art |
| **Commerce loop** (`graphics/commerce-loop.svg`, `<CommerceLoop>`) | N-trail with four labelled stages: **Create → Sell → Fulfill → Learn** | Sign-in panel, marketing lifecycle, onboarding |
| **Outlined trail** (`EmptyState`) | Two rises in outline, "nothing has flowed here yet". The first rise is filled when there is a next step | Empty states in product UI |
| **Active ribbon** (shell nav) | A 4px ribbon at the 16° rise angle | Current navigation item |
| Channel sync stream | Parallel ribbons per channel converging on the product (planned, BRD-008) | Channel Sync Rail header, campaign art |
| Order route | The trail laid along a delivery route, with stops as fold points (planned, BRD-008) | Order Journey, courier marketing |

**Not part of the system:** blobs, abstract waves, nodes-and-lines "AI networks", isometric 3D,
glassmorphism cards and floating dashboard mock-ups.

## 9. Graffiti / street-energy accents
These are controlled, hand-drawn marks that carry creator-led energy.

| Accent | File | Colour |
|---|---|---|
| Underline swash | `graphics/accent-underline.svg`, `<HandUnderline>` | Teal |
| Hand arrow | `graphics/accent-arrow.svg` | Ink |
| Hand ring | `graphics/accent-ring.svg` | Coral |
| Tick | `graphics/accent-tick.svg` | Teal |

- **Limit:** one accent per composition. It marks one or two words or one element.
- **Allowed:** marketing site, social campaigns, onboarding and sign-in, merchant milestones,
  selected banners.
- **Never:** payments, returns, refunds, admin, analytics tables, finance, dense operational screens,
  error states.
- **Style:** tapered single strokes. No spray texture, drips, tags or distressed type.

## 10. Banners
Banners are compositions, not "gradient rectangle + text".

**Layout grammar.** Headline block left. The ribbon motif enters from one edge and bleeds off the
other, then rises on the right third. A single CTA sits below the copy. Deep Navy or Cloud ground.

**Variants and uses:**
| Variant | Ground | Motif | Accent |
|---|---|---|---|
| Launch | Navy | Trail | Underline |
| Onboarding | Navy | Commerce loop | Underline |
| Feature discovery | Cloud | Trail, half height | None |
| Seasonal campaign | Navy | Trail plus a seasonal product photo | Coral ring |
| AI Video | Navy | Trail rendered as film frames | None |
| Autopilot | Navy | Trail with the loop stages | None |
| Upgrade | Cloud | Outlined trail with one filled rise | None |
| Milestone | Navy | Trail | Coral tick or ring |

**Shipped:**
- `banners/og-default.svg/png`, the default share image.
- The banner grammar, in the sign-in panel.

**Still to build:** the per-variant banner set (BRD-007). Use real product photos from sellers who
have consented; never stock.

## 11. Characters (system defined; assets pending, BRD-009)
A small, ownable cast used sparingly:
- **Seller.** Runs a shop from a phone.
- **Creator.** Shoots product content.
- **Packer / operations.**
- **Courier rider.** Kathmandu traffic.
- **Customer.**
- **Growth.** Seller with a milestone.
- **Assistant presence.** Not a robot: a ribbon-shaped "helper" line that points and underlines.

**Illustration guide:**
| Aspect | Rule |
|---|---|
| Style | Editorial flat illustration; one 2px ink line weight at 1× (scales with the drawing); no gradients except ribbon elements |
| Proportions | Slightly elongated (7.5 heads); hands and phones drawn clearly because commerce happens in hands |
| Colour | Skin tones from a defined inclusive set; clothing in neutrals + one brand colour per figure; Coral/Sun for small props only |
| Expression | Subtle: focused, relieved, pleased. Never cartoon-ecstatic. |
| Environments | Real Nepali commerce settings: shop counters, packing tables, scooters, Thamel streets, home studios. Not temples-and-mountains cliché. |
| Do | Show real work (packing, labelling, photographing) and the product as hero |
| Don't | 3D clay, mascots, robot heads, floating devices, generic "diverse team high-five" |

- **Allowed on:** onboarding, empty states with a teaching moment, help, major milestones, marketing
  and selected banners.
- **Not allowed on:** any business workflow screen.

**No placeholder characters ship.** Until an illustrator delivers the cast, those surfaces use the
ribbon motifs. `assets/brand/characters/` holds only the brief.

## 12. Photography
Real sellers, products, packaging, couriers, shops and home studios. Natural light, true product
colour. No staged handshakes, high-fives, VR headsets or "person pointing at a hologram".

## 13. Motion
Motion explains state change: flow, continuity, completion, progress.

| Token | ms | Use |
|---|---|---|
| `motion.fast` | 150 | Hover, press, toggles (120–180) |
| `motion.standard` | 220 | Drawers, tabs, reveals (180–260) |
| `motion.large` | 320 | Page-level, milestone reveal (250–400) |
| `motion.flow` | 1600 | One trace of the ribbon while work is in progress (publishing, AI processing, sync) |

### Signature motions
| Motion | Behaviour | Status |
|---|---|---|
| Ribbon trace | Segments draw in sequence along the trail (`<NTrail animate>`) | Shipped |
| Sync pulse | One pass along a channel row when a listing syncs | BRD-011 |
| Order step settle | A completed Order Journey step fills from the previous step's fold | BRD-011 |
| Milestone | The trail draws once, then the coral tick lands | BRD-011 |

### Rules
- No infinite loops on idle screens, no bouncing, no parallax, and no decoration that delays work.
- `prefers-reduced-motion` sets every duration to 0, and the end state still shows. This is enforced
  in the generated tokens.

## 14. Surfaces: brand application matrix
| Surface | Visual energy | What is allowed |
|---|---|---|
| Marketing website | High | Full ribbon compositions, accents, characters, banners, motion |
| Social media | High | Same as marketing; one accent per post |
| Onboarding / sign-in | Medium–High | Navy brand panel, commerce loop, one underline accent |
| Flutter home | Medium | Mark in header, Autopilot strip, milestone moments |
| Web dashboard (home) | Medium–Low | Logo in nav, active ribbon, Autopilot strip, outlined-trail empty states |
| AI Studio / content | Medium | Ribbon trace while processing; AI tag in brand blue |
| Orders | Low | Tokens and status colours only |
| Payments | Low | Same; no accents, no characters |
| Returns | Low | Same |
| Analytics | Low | Data colours from the chart palette; no brand gradients |
| Admin (Nivaro Console) | Very Low | Navy header, blue accents, density first, no accents or characters |

## 15. Platform use
- **Web app.**
  - Operational efficiency first: tables, drawers, split panes, timelines, filters, bulk actions,
    command palette and exception-first layouts.
  - Brand presence: logo in the nav, the active ribbon, outlined-trail empty states, the navy sign-in
    panel, and the ribbon trace during long work.
- **Flutter.**
  - The mark draws natively from generated geometry (`NivaroMark`, `NivaroLogo`).
  - App icon: the navy ground with the colour mark (ADR-030); light variant in `app-icons/`.
  - Home: Autopilot status, today's orders, revenue, AI-handled conversations, ready to ship and
    exception count.
  - Quick actions: Add product, Capture, Generate content, Create Reel, Orders, Messages.
- **Nivaro Console.** Navy top bar with the white lockup and "Console" suffix, blue accents, neutral
  surfaces and minimal graphics. Priorities: speed, clarity, risk visibility, auditability. (UI not
  built yet: GAP-CONSOLE-UI.)
- **Email.** Sender display name "Nivaro" (`COS_EMAIL_FROM_NAME`). Plain text first, signed "—
  Nivaro". The HTML template uses the lockup at 24px and no imagery.
- **Social.** Lockup top-left or bottom-left; one ribbon composition; one accent; real product photos.

## 16. Dark and light mode
- Semantic tokens carry both modes.
- In dark mode:
  - Ribbon gradient: lighter blue (#60A5FA) → lighter teal (#2DD4BF).
  - Canvas: #0B1220. Raised surface: #111A2E.
  - The wordmark follows `brand.ink`, which is white in dark mode.
- The colour mark is used unchanged on Deep Navy and dark canvases. It already reads, so there is no
  "dark logo" recolour.

## 17. Accessibility
- **Contrast:** body text ≥4.5:1 and large text ≥3:1, in both modes.
- **Colour:** never the only carrier of state. Status always has text or a shape.
- **Focus:** visible 2px rings in `focus.ring`.
- **Targets:** at least 44px on touch.
- **Logos:** have accessible names. Decorative motifs are `aria-hidden`.
- **Motion:** respects reduced motion.
- **Nepali:** at 360dp without overflow.

## 18. Design QA (every custom visual)
1. Is it recognisable as Nivaro: built from the ribbon, the palette and the type?
2. Does it support commerce rather than distract from it?
3. Does it feel human-crafted rather than template-generated?
4. Is it consistent with the existing motifs (no new art style)?
5. Is it appropriate for the surface's energy level (§14)?
6. Does it still work in monochrome and at small sizes, where relevant?
7. Does it avoid AI clichés (sparkles, glow, robots, blobs, purple gradients)?
8. Does it meet accessibility (§17)?

A "no" on any point means revise it before merging.

## 19. Anti-generic rules
- No purple/blue gradient pages, glow, glassmorphism, random 3D blobs, clay people, sparkles on every
  AI action, floating meaningless dashboards, or perfectly repeated section patterns.
- No cards around every section and no pill buttons or tabs. Radius is 6px for controls and 10px for
  genuine panels; full-round only for avatars, dots and meter tracks.
- No fake logos, testimonials, metrics or customer counts.
- **The test:** if a screen could belong unchanged to an unrelated CRM, fintech or project tool,
  redesign it until it shows commerce and automation.

## 20. Asset architecture
```text
assets/brand/
  logo/{primary,monochrome,dark,light}/   SVG (+ PNG previews) — generated
  app-icons/                              navy / light / maskable sources + 1024 PNGs — generated
  favicon/                                SVG + 32px PNG — generated
  graphics/                               n-trail, commerce-loop, hand accents — generated
  banners/                                og-default (svg/png); campaign banners (BRD-007)
  characters/  illustrations/  motion/    briefs only until real assets exist (no placeholders)
  reference/                              owner-supplied concept boards (not for production use)
  scripts/render.mjs                      regenerates everything above + web/Flutter icons
```
- **Feature code** never copies brand files. Web uses `components/brand/*`; Flutter uses
  `design/widgets/nivaro_brand.dart`.
- **Generated icons** land in `apps/web/src/app` (icon, apple-icon, OG), `apps/web/public/icons`
  (PWA), and the Flutter Android mipmaps and iOS AppIcon set.
