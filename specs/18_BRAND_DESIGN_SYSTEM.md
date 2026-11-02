# Brand & Design System (product UI)

> v3 (2026-11-02): the product is **Nivaro**. Brand rules (logo, palette, motifs, characters, motion,
> application matrix) live in `26_NIVARO_BRAND_SYSTEM.md`. This document covers product UI: tokens in
> use, signature components, explanation patterns and process. Layout directions for key surfaces:
> `docs/design/LAYOUT_DIRECTIONS.md`.

## Core experience
**Human-crafted commerce software with automation inside, not AI aesthetics pasted on top.**
Intelligence lives inside commerce workflows: a fit warning on the product, a courier choice on the
shipment. It is never a chat bubble as the main UX.

Operational screens are calm. Brand energy is spent on onboarding, milestones and marketing (26 §14).

## Tokens (`packages/design-system/design-tokens.json`, v1.0)
There are three tiers:

1. **Primitives:** `color.brand.*`, `color.neutral.*`, `color.semantic.*` and `color.dark.*`.
2. **Semantic layer:** `semantic.light` and `semantic.dark`. Components use only this tier.
3. **Status and risk mappings:** these reference the semantic layer.

| Semantic token (CSS `--color-…`) | Light | Dark | Use |
|---|---|---|---|
| `brand-primary` / `action-primary` | Blue #2563EB | #60A5FA | Primary actions, focus, automation marker |
| `action-primary-hover` | #1D4ED8 | #93C5FD | Hover/pressed |
| `brand-secondary` / `flow-end` | Teal #14B8A6 | #2DD4BF | Healthy, synced, completed; end of ribbon |
| `brand-accent` | Coral #FF6B6B | | Celebrate only |
| `text-primary` / `-secondary` / `-muted` | Ink / Slate 700 / Slate 500 | #E2E8F0 / #94A3B8 | Text |
| `text-brand` | #1D4ED8 | #93C5FD | AI tag text, links on tint |
| `text-positive` | #0F766E | #2DD4BF | Teal as text (contrast-safe) |
| `surface-canvas` / `-raised` / `-sunken` / `-hover` | Cloud / White / Slate 100 / Slate 100 | #0B1220 / #111A2E / #0B1220 / #16213A | Surfaces |
| `surface-inverse` | Deep Navy | #111A2E | Sign-in brand panel, Console header |
| `surface-brand-tint` | #DBEAFE | #16264A | AI tag background, drop target hover |
| `status-success/warning/danger/info` (+ `-soft`) | Semantic | Semantic dark | States, never brand colours |
| `status-attention-fill` | Sun #FBBF24 | #FBBF24 | 70% meter fill (fill only) |

- **Status:** healthy → `flow-end`, automated → `brand-primary`, needsAttention →
  `status-attention-fill`, failed → `status-danger`, pending → `text-muted`, celebrate →
  `brand-accent`.
- **Risk** (COD/decision): low → `flow-end`, medium → `status-warning`, higher → `status-danger`.
  Medium is never alarming red.
- **Radius:** `control` 6, `card` 10, `full` only for avatars, dots and meter tracks.
- **Motion:** `fast` 150, `standard` 220, `large` 320, `flow` 1600. All are zero under
  reduced-motion.
- **Legacy aliases** (`--surface-page`, `--text-secondary`, …) point at the semantic layer. New code
  uses `--color-*`.
- **Indigo is removed** (ADR-031). AI and automation are marked with brand blue: the "AI" tag in
  `text-brand` on `surface-brand-tint`, and the node icon.

## Typography
English: Inter. Nepali: Noto Sans Devanagari (line-height 1.7). Weights follow 26 §6. Product UI tops
out at 700. Tabular numerals are used in tables and meters.

## Signature components
Each one has to look recognisably Nivaro and commerce-specific. The "Nivaro language" column says how
the brand shows up in it.

| Component | Purpose / rules | Nivaro language | Status |
|---|---|---|---|
| **Autopilot Control Center** *(home)* | Headline "Your store is running." Today's operations as plain outcomes: orders, revenue, AI-handled messages, shipments, returns, content published, Autopilot Score, active exceptions. Typographic, no chart wall | Mode segment control with ribbon underline; the counts are the hero; outlined-trail empty state | Partial: Autopilot strip + exceptions (web/mobile) |
| **Exception Inbox** ("Needs your attention") | Ordered by severity, a one-line why, one primary action each | Severity rule on the left edge (danger / warning / info); no cards | Built (derived, ADR-020) |
| **Autopilot Score** | Number + capability bars + "excluded" disclosure + one improvement. Thin data shows "not enough activity", never 0% | Bars as ribbon segments rising left → right | Planned (APS) |
| Autopilot Status Strip | Mode (Assisted / Smart / Autopilot) + automated vs needs-attention counts | Blue = automated, sun dot = attention | Built |
| **Product Brain** card | Margin, demand, cover days, return reasons, top FAQ, best content, inside product and inbox | Header "Product Brain" with mark-angle rule; evidence numbers with window and n | Planned (PBR) |
| **Channel Sync Rail** | Per-channel listing state for a product | Each channel is a horizontal lane; state dot (teal synced, sun pending, red failed); sync pulse when it runs | Built (web listings panel) |
| **Order Journey** | Lifecycle timeline with automated vs manual steps | The steps sit on the ribbon; automated steps carry the node icon; completed steps fill blue → teal | Planned (ORD) |
| **AI Action Timeline** | Automated actions with undo where possible | Time rail; "AI" tag; undo inline | Planned (AUT) |
| **Product Profit Card** | True-profit waterfall per product | Neutral bars; profit in `text-positive`, loss in danger; no gradients | Planned (ANA) |
| **Inventory Risk Meter** | Days of cover vs supplier lead time | A meter track with a lead-time notch; risk tokens | Planned (INV) |
| **Video Credit Meter** | Monthly quota + daily burst | Cell meter; sun at 70%, warning at 85% | Built |
| **Conversation-to-Order Card** | Extracted order fields with missing-field prompts | Fields filled in `text-brand` when AI-extracted; missing fields outlined | Planned (INB) |
| **Automation Recipe** | Commerce-specific automation templates ("When a COD order is over रू 5,000, confirm by call") | Trigger → condition → action on a short ribbon; risk class chip | Planned (AUT) |
| **Creative Genome Card** | What content sells, with sample sizes ("based on 41 posts") | Attribute rows with n; no word clouds | Planned (CGN); data captured (CNT-012) |
| **Courier Intelligence Card** | Chosen courier + reason + alternatives with price / ETA / success by route | Route line drawn as the ribbon with stops | Planned (CRI) |
| **Return Insight Card** | Pattern ("61% say fit is small, n=33"), cause, fix, before/after once measured | Neutral; before/after as paired bars | Planned (RTI) |
| **Supplier Intelligence Card** | True landed cost, lead-time reliability, defect/return rate | Neutral table card | Planned (SPI) |
| **Commerce Memory Insight** | One learned fact with evidence and "Not right? Correct it" | Quote-style rule in brand blue; correction link always visible | Planned (MEM) |
| **Digital Store Twin Summary** | Section freshness (`as_of`), stale flags, key positions | Each section is a lane with "as of" time; stale = hatched track | Planned (TWIN) |

**Brand primitives in code.** Web: `apps/web/src/components/brand/Brand.tsx` (`NivaroMark`,
`NivaroLogo`, `NTrail`, `CommerceLoop`, `HandUnderline`). Flutter: `lib/design/widgets/nivaro_brand.dart`.

## Explanation UI pattern
- The "why" is always one tap away. Evidence is numbers with windows and sample sizes.
- Confidence is shown in words (low / medium / high); the number appears on hover or press.
- Estimates are labelled "estimate" and shown as ranges.

## Empty, loading and error states
- **Empty:** the outlined trail (two rises). The first rise is filled in brand blue when the state
  offers a next step. Title + one sentence + at most two actions.
- **Loading:** skeleton rows in table shape. The ribbon trace only for real long-running work (AI
  processing, publishing).
- **Error:** a danger ribbon rise, then the message, the request id and Retry.

## Anti-generic rules
See 26 §19. In short: no gradient dashboards, card grids, pill controls, sparkles, chat-bubble-first
UI, blobs, clay characters, or fake logos and numbers. The acceptance test: **if the logo were
removed, the interface should still feel recognisably like Nivaro and like commerce.**

## Web app
Operational pages are calm and neutral. Colour is reserved for action, risk, automation and growth.
Patterns: tables, side drawers, split panes, timelines, filters, bulk actions, command palette,
exception-first layouts.

## Flutter
Warmer and faster: clear capture and upload, progress, exceptions, orders and content preview. The
Control Center is the mobile home.

## Mandatory design process
brief → wireframe → **two considered layout directions** for major surfaces (recorded in
`docs/design/LAYOUT_DIRECTIONS.md`) → component review → build → responsive QA → accessibility QA →
brand QA (26 §18) → human review.
