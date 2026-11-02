# Media, Image & Video Pipeline + Creative Genome

> v1 (2026-11-02). The original 09 was never provided. Authored from the build brief and the
> implementation; owner review required.

## Image pipeline (implemented, MED-001…004)
- **Upload:** signed PUT → complete → async processing (outbox). Originals stay private.
- **Validation:** format sniffed from bytes (JPEG/PNG/WebP/HEIC); decompression-bomb guard; malware
  scan (clamd; production refuses no-op).
- **Normalisation:** EXIF orientation applied; **all metadata including GPS stripped** from
  derivatives.
- **Quality flags:** `low_resolution`, `blurry`, `too_dark`, `overexposed`, with a score.
- **Derivatives:** thumb, medium, `square_white` (marketplace), `portrait_4_5`, `story_9_16`. Padding
  only; never crops into or recolours the product.
- **Provenance:** `seller_upload | ai_generated | ai_edited | channel_import | csv_import | auto_reel`.

## Fidelity rules (AI image edit/generation, MED-005…007; provider not chosen)
Generated imagery must never silently change:
- colour or pattern
- logos
- geometry or button count
- stitching or accessories
- material appearance

Fidelity checks compare the generated output with the source (colour histogram distance, structural
similarity on the product mask, logo region checks). If fidelity is uncertain, the image goes to
seller review. AI images are labelled with their provenance.

## Video
- **Auto Reels (implemented, MED-008/009):** seller photos only; the whole product stays visible over a
  blurred backdrop; Ken Burns + crossfades; the overlay is kept clear of the product; price from the
  catalog; 9:16/1:1/4:5/16:9; Nepali shaping requires libraqm (verified in Docker); metered.
- **Premium AI Video:** async with states QUEUED → SUBMITTED → GENERATING → POST_PROCESSING → READY /
  FAILED / CANCELLED. It tracks provider, model, duration, resolution, provider cost, credits, retries,
  prompt version and moderation.

## Creative attributes (recorded from Phase 1; Creative Genome input)
Every content post and generated video records structured creative attributes:

| Attribute | Values |
|---|---|
| format | post / story / reel / video |
| duration_s | number (video) |
| hook_type | price_first / product_closeup / problem_solution / social_proof / offer / unknown |
| price_shown / price_timing_s | bool / seconds from start (null if absent) |
| language_mix | ne / en / ne_en_mixed |
| caption_length_bucket | short (<80) / medium / long (>300) |
| cta_type | dm / comment / link / call / none |
| human_presence | bool (seller-declared or detected later) |
| background | white / lifestyle / blurred_photo / other |
| template_id | Auto Reel template / AI concept id |
| scheduled_window | local hour bucket (Asia/Kathmandu) |

## Creative Genome (Phase 7)
A per-merchant (and per-channel) **CreativeGenomeProfile** of learned preferences. Each preference
carries an effect size on a commerce outcome, a confidence and a sample size.

Example: "Your audience responds best to 8–11 s Reels, price in the first 2 s, Nepali-English mixed
copy, hand-held demos, 7–9 PM posts."

It is computed from CreativePerformanceMetric over creative attributes. It uses outcome-weighted
comparison with minimum sample sizes and shrinkage towards the merchant's baseline (and, in Phase 10,
the network prior).

The Genome influences:
- image-generation prompts
- Auto Reel template choice and parameters
- AI video concepts
- caption style
- publishing schedule suggestions

Generated content records `genome_version` so its impact can be measured.

## Closed-loop content learning (Phase 7)
**GENERATE → PUBLISH → MEASURE → ATTRIBUTE → LEARN → UPDATE CREATIVE GENOME → GENERATE BETTER**

- **Measure.** Channel insights where APIs allow: views, engagement, clicks. Also internal signals:
  inquiries (conversations referencing the post or product within a window) and orders.
- **Attribute.** Order and inquiry attribution in priority order:
  1. explicit (link/UTM/post reference in a conversation)
  2. product + time-window heuristics with decay
  3. unattributed

  The attribution method is recorded per metric.
- **Optimise for commerce outcomes.** Orders, attributed contribution and conversion come before
  engagement. Likes alone never promote a pattern.
- **Experiments.** CreativeExperiment compares variants with a declared hypothesis and stopping rule.
