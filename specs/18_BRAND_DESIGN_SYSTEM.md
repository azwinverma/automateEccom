# Brand & Design System

> v2 (2026-11-02): adds Autonomous Commerce OS signature surfaces. **Pending owner decision:** adopt the
> "Nivaro" brand (name, tagline "Your store, on autopilot.", palette Blue #185CFF / Teal #00D7B2 /
> Deep Navy #0B1B3D) supplied as images in the repo root. Until decided, tokens follow the palette
> below.

## Brand character
Joyful, fast, capable, warm, human, trustworthy, modern, commerce-focused.

## Core experience
**Human-crafted commerce software with AI inside, not AI aesthetics pasted on top.** Intelligence is
embedded in commerce workflows (a fit warning on the product, a courier choice on the shipment), not a
chat bubble as the main UX.

## Color balance
~70% neutral surfaces, 20% primary/soft brand, 10% vivid accent.

Suggested palette (current tokens, `packages/design-system/design-tokens.json`):

| Name | Hex |
|---|---|
| Primary Blue | #2563EB |
| Indigo | #4F46E5 |
| Fresh Teal | #14B8A6 |
| Joy Coral | #FF6B6B |
| Sun Yellow | #FBBF24 |
| Ink | #0F172A |
| Slate | #475569 |
| Cloud | #F8FAFC |
| White | #FFFFFF |

- Semantic success/warning/danger/info are separate design tokens.
- **Indigo** is reserved for automation/AI-performed things (automated actions, AI suggestions).
- Status tokens: healthy, automated, needsAttention, failed, pending, celebrate.
- Risk-level tokens (COD/decision): low, medium, higher. These are neutral-to-warning hues, never
  alarming red for "medium".

## Typography
English: Inter. Nepali: Noto Sans Devanagari (line-height 1.7). Readable, not "futuristic AI".

## Signature components & surfaces
| Surface | Purpose / rules |
|---|---|
| **Autopilot Control Center** *(home)* | Headline "Your store is running." Today's operations as plain outcomes: orders processed, revenue, AI-handled messages, shipments created, returns resolved, content published, current Autopilot Score, active exceptions. A calm, typographic layout; no chart wall. |
| **Needs Your Attention** | The Exception Inbox section of the Control Center, ordered by severity, with a one-line why and a single primary action each (high-value refund, expired Instagram, stockout risk, ambiguous order, courier failure, payment mismatch, low AI confidence). |
| **Autopilot Score** | Number + capability breakdown bars + "excluded" disclosure + one improvement suggestion. Thin data shows "not enough activity", never 0%. |
| Autopilot Status Strip | Mode (Assisted/Smart/Autopilot) + automated vs needs-attention counts. |
| **Product Brain card** | A compact product intelligence panel inside the product page and the inbox: margin, demand, cover days, return reasons, top FAQ, best-performing content. |
| **Commerce Memory insight** | A single learned fact with evidence and "Not right? Correct it". |
| **Creative Genome panel** | Learned content preferences with sample sizes ("based on 41 posts"). |
| **Profit Recommendation Card** | What/why/evidence/confidence/impact/action (07 framework); impact shown as a range. |
| **Return Insight Card** | Pattern ("61% say fit is small, n=33"), suspected cause, recommended fix, before/after once measured. |
| **Courier Recommendation Card** | Chosen courier + reason + alternatives with price/ETA/success. |
| Channel Sync Rail | Per-channel listing state for a product. |
| Order Journey | Order lifecycle timeline with automated vs manual steps. |
| AI Action Timeline | Feed of automated actions with undo where possible. |
| Product Profit Card | True-profit waterfall for a product. |
| Video Credit Meter | Monthly quota + daily burst. |
| Inventory Risk Meter | Days of cover vs lead time. |
| Conversation-to-Order Card | Extracted order fields with missing-field prompts. |
| Automation Recipe Card | Commerce-specific automation templates. |

## Explanation UI pattern
- The "why" is always one tap away. Evidence is shown as numbers with windows and sample sizes.
- Confidence is shown as words (low/medium/high), with the number on hover or press.
- Estimates are labelled "estimate", with ranges.

## Anti-generic rules
Do not use:
- purple/blue gradient everywhere or generic gradient dashboards
- cards around every section; repetitive card grids
- giant pill controls
- sparkles as generic AI branding; fake futuristic visuals
- generic "AI assistant" chat bubbles as the main UX
- random 3D blobs or clay characters
- fake logos or testimonials
- the repeated generic SaaS landing-page formula
- vague "unlock/revolutionize/supercharge" copy

## Photography
Real sellers, products, shelves, packaging, couriers, studios, shops and warehouses. No staged
handshake or high-five stock.

## Marketing site
Show the real lifecycle: add product → AI assets → publish → customer conversation → order →
delivery → profit/retention → "your store ran overnight".

## Web app
Operational pages are calm and neutral. Color is reserved for action, risk, automation and growth.

## Flutter
Warmer and faster. Clear capture/upload, progress, exceptions, orders and content preview. The Control
Center is the mobile home.

## Motion
150ms fast, ~220ms standard, ~320ms large. No decorative infinite motion.

## Mandatory design process
brief → wireframe → 2 considered layout directions for major surfaces → component review → build →
responsive QA → accessibility QA → human review.

## Acceptance test
If the logo were removed, the interface should still feel recognisably like this commerce product.
