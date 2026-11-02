# Layout directions: key Nivaro surfaces

> 2026-11-02. Two considered directions per surface. Each is scored 1–5 on **U**sability,
> **O**riginality, **B**rand fit, **A**ccessibility and **C**ommerce clarity. The stronger direction
> is chosen. Built surfaces were verified against the real backend (screenshots under "Status").
> Rules: specs/26 (brand), specs/18 (components).

---

## 1. Marketing homepage
**A: "The loop" (chosen).** One continuous N-trail runs down the page. Each fold is a section of the
lifecycle, and real UI fragments sit at the folds.
```
┌──────────────────────────────────────────────────────────────┐
│ nivaro                         Pricing  Sign in  [Start free] │
│                                                              │
│ Your store,                                     ╱╲  ╱╲  ╱╲    │
│ on autopilot.                                  ╱  ╲╱  ╲╱  ╲   │  ← N-trail enters from right
│ ‾‾‾‾‾‾‾‾‾  (hand underline)                                   │
│ From product photo to delivered order …   [Start free]       │
├── fold 1 ── photo → listing ─────────────────────────────────┤
│ [real Studio fragment: 3 photos → drafted listing]           │
├── fold 2 ── Autopilot Control Center ────────────────────────┤
│ "Your store is running."  [live-style fragment, no fake nos] │
├── fold 3 ── one product, every channel (sync lanes) ─────────┤
├── fold 4 ── Studio · Video · Sales agent (3 unequal columns) ┤
├── fold 5 ── order → COD → courier → delivered (order route)  ┤
├── fold 6 ── returns & refunds   ── fold 7 ── profit/intel ───┤
├── proof (only when real data exists) ── pricing ── CTA ──────┤
```
**B: "Bento".** A hero, then a grid of feature tiles of mixed sizes with screenshots.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 4 | 5 | 5 | 4 | 5 | The lifecycle is the story; the ribbon carries the reader; sections differ in shape |
| B | 4 | 1 | 2 | 4 | 3 | The bento grid is the current generic SaaS formula; it fails the anti-generic test |

**Status:** not built (no marketing site in repo; BRD-014). OG/share image built from direction A.

---

## 2. Web dashboard (seller home)
**A: "Exceptions first" (chosen).** A greeting line, the Autopilot strip as a single typographic row,
then "Needs your attention" as a severity-ruled list, then setup. No KPI cards.
```
Namaste, Sita                                    Thamel Threads
Mode  Assisted ▔▔ Smart ▁▁ Autopilot ▁▁ │ Handled auto 0 │ Needs you 0 │ note
─────────────────────────────────────────────────────────────────
Needs your attention
▌ danger  Payment mismatch · Order #1042 · रू 3,200      [Review]
▌ warn    Instagram token expires in 2 days               [Reconnect]
─────────────────────────────────────────────────────────────────
Finish setting up   ☐ Verify email  ☐ Two-step  ☐ Invite packer
```
**B: "KPI board".** Four stat cards (orders, revenue, messages, shipments), a revenue chart, then
exceptions below the fold.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 5 | 4 | 4 | 5 | 5 | The USP is "you handle exceptions", so exceptions come first; it reads in one pass |
| B | 3 | 1 | 2 | 4 | 3 | Card grid + chart = any CRM; it pushes the actual work below the fold |

**Status:** built (A). Brand pass: logo in nav, active ribbon, outlined-trail empty state.

---

## 3. Autopilot Control Center
**A: "Running report" (chosen).** The headline "Your store is running." with a timestamp, then
outcomes as sentences with numbers ("Nivaro confirmed 14 COD orders and booked 9 couriers"). The
Autopilot Score sits right with capability bars, and the exception list follows.

**B: "Mission control".** A dense grid of live tiles with sparkline animation.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 5 | 5 | 5 | 5 | 5 | Plain-language outcomes are honest and translatable; no vanity motion |
| B | 3 | 2 | 1 | 3 | 3 | Animated tiles are decorative motion; the "control room" trope is generic |

**Status:** partial (the strip and exceptions are A's skeleton). The full Control Center needs
orders/automation data (Phase 2–3) and APS (Phase 6).

---

## 4. Product Brain
**A: "Margin rail" (chosen).** A right-hand panel on the product page. Margin and cover days are on
top as numbers, then return reasons, top FAQ and best content, each with "n=" and a window. "Not
right? Correct it" sits on every learned fact.

**B: "Insights tab".** A separate tab with charts per metric.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 5 | 4 | 4 | 5 | 5 | Intelligence sits where the seller edits the product, the core principle of 18 |
| B | 3 | 2 | 3 | 4 | 3 | Hidden behind a tab, so it gets ignored |

**Status:** planned (PBR, Phase 6). Placement reserved in the product page right column.

---

## 5. AI Product Studio
**A: "Photo → draft split" (chosen).** Step 1 is a drop target (photos), notes and draft language.
Step 2 is a split pane: photos left, an editable draft right, with low-confidence fields marked "AI —
please check" in brand blue and price always empty for the seller. The ribbon trace runs while
processing.

**B: "Chat to create".** The seller chats with an assistant that asks questions and builds the
listing.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 5 | 4 | 5 | 5 | 5 | Fast to review; AI never fills price; matches the mobile capture flow |
| B | 2 | 2 | 1 | 3 | 3 | Chat-first is the "AI SaaS" trope 18 forbids and is slower for 6 photos |

**Status:** built (A). Brand pass: native file input → branded drop target with drag and drop.

---

## 6. Flutter home
**A: "Today strip" (chosen).**
- Mark + shop name.
- Greeting and date.
- Autopilot strip.
- Today metrics: orders, revenue, AI-handled conversations, ready to ship.
- "Needs you" list.
- Quick actions as a 3×2 grid of text buttons with icons: Add product, Capture, Generate content,
  Create Reel, Orders, Messages.

**B: "Feed".** A single scrolling feed mixing events, tips and actions.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 5 | 3 | 4 | 5 | 5 | Thumb-reachable actions; status first; works offline with cached counts |
| B | 3 | 3 | 3 | 4 | 2 | Feeds bury exceptions and confuse "done" vs "to do" |

**Status:** built (A). Brand pass: native NivaroMark in header, Nivaro app icon and display name.

---

## 7. Nivaro Console (internal admin)
**A: "Navy rail + dense tables" (chosen).**
- Navy top bar: white lockup, "Console" suffix, environment badge.
- A left rail of queues: merchants, support, DLQ, AI cost, risk.
- Dense tables with saved filters and a right drawer for detail.
- Audit link on every row.

**B: "Light dashboard".** The seller-app look, with cards per metric.

| | U | O | B | A | C | Notes |
|---|---|---|---|---|---|---|
| A | 5 | 3 | 4 | 5 | 4 | Staff speed and risk visibility; visually distinct from the seller app, so no confusion about context |
| B | 3 | 2 | 3 | 4 | 3 | Too close to the seller UI; cards waste density |

**Status:** UI not built (GAP-CONSOLE-UI). Backend admin API exists. The brand header spec is in
26 §15.
