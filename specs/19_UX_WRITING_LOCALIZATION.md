# UX Writing & Localization

> v1 (2026-11-02). The original 19 was never provided. Authored from current practice; owner and
> native-speaker review required (GAP-NE-COPY).

## Languages
English and Nepali from day one. No hard-coded UI strings. Typed dictionaries (web) and ARB files
(mobile) with key-parity tests.

## Product name
Customer-facing text always says **Nivaro** (wordmark `nivaro`; `NIVARO` only in legal/formal). The
category "Autonomous Commerce OS" appears in titles and marketing, not in UI labels. Module names
(Nivaro Studio, Nivaro Inbox, …) only where they help navigation (26 §1). Never show internal phase or
backlog codes ("P2", "Phase 3") to sellers; say "Soon". Transactional email: sender "Nivaro", signed
"— Nivaro". Nepali tagline: "तपाईंको पसल, अटोपाइलटमा।" (native review pending, GAP-NE-COPY).

## Voice
Plain, warm, specific and short, like a capable shop manager. Lead with outcomes, not technology:
"27 orders handled overnight", never "AI-powered". Nepali is written naturally for a Kathmandu seller,
not translated word for word. Common English commerce words (kurta, COD, size) are kept where sellers
use them.

## Numbers, money, dates
- Money: NPR as "रू 1,250" (ne) / "Rs 1,250" (en), with lakh grouping (1,25,000).
- Digits: Devanagari digits in Nepali where the surface supports it (reels and print). The web app
  currently uses Latin digits in both locales (documented choice; revisit after user research).
- Dates and times use the merchant timezone (Asia/Kathmandu, UTC+5:45).

## Error copy
Map API `code` → localized message. Every message says what happened and what to do next. Show a small
request ID for support.

## Explanation copy patterns (intelligence)
| Element | Pattern (en) | Notes |
|---|---|---|
| What | "Black XL may sell out in 5 days." | Concrete subject, number, timeframe |
| Why | "Average demand is 3.2/day and 16 are available." | Evidence numbers with window |
| Confidence | "High confidence (90 days of sales)." | Words first; data basis in parentheses |
| Impact | "Estimated Rs 4,000–7,000 more contribution this month." | Always a range; label "estimated" |
| Action | "Reorder 40 units" / "Add fit note" | Verb-first, specific |
| Thin data | "Not enough sales yet to judge this (12 orders)." | Never fake precision |
| Automated action | "Done automatically: exchange approved (under your Rs 1,500 limit)." | Cite the policy that allowed it |
| COD risk | "Higher delivery risk: 2 failed deliveries to this address before. Suggested: verify phone." | Factual factors; never judgemental language about the person |

Forbidden:
- unexplained claims ("trending", "smart pick")
- guarantees ("will sell")
- blame on customers
- "AI magic" language

## Nepali review checklist
- natural phrasing
- consistent terms (glossary: अर्डर, डेलिभरी, स्टक, फिर्ता/रिटर्न, भुक्तानी)
- correct honorifics (तपाईं)
- no broken Devanagari shaping in rendered media (libraqm required)
