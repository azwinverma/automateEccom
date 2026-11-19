import type { CreativeAttribute } from "@commerce-os/api-client";
import type { useI18n } from "@/i18n/I18nProvider";

type I18n = ReturnType<typeof useI18n>;
type T = I18n["t"];

/** Controlled vocabularies the backend learns from (creative.features). */
export const CREATIVE_VOCAB: Record<CreativeAttribute, string[]> = {
  format: ["post", "story", "reel"],
  hook_type: ["price_first", "product_closeup", "problem_solution", "social_proof", "offer"],
  price_timing: ["first_2s", "later", "shown", "no_price"],
  language_mix: ["ne", "en", "ne_en_mixed"],
  caption_length: ["short", "medium", "long"],
  cta_type: ["dm", "comment", "link", "call", "none"],
  human_presence: ["yes", "no"],
  posting_window: ["morning", "afternoon", "evening", "night"],
  duration_band: ["up_to_7s", "8_11s", "12_20s", "over_20s"],
  background: ["white", "lifestyle", "blurred_photo", "other"],
};
export const CREATIVE_ATTRIBUTES = Object.keys(CREATIVE_VOCAB) as CreativeAttribute[];

export function attrLabel(t: T, attribute: string): string {
  return t.dynamic(`intel.creative.attr.${attribute}`) ?? attribute;
}

/** "Price in the first 2 seconds" — the pattern as a phrase a seller recognises. */
export function valueLabel(t: T, attribute: string, value: string): string {
  return t.dynamic(`intel.creative.v.${attribute}_${value}`) ?? `${attrLabel(t, attribute)}: ${value}`;
}

export function outcomeWord(t: T, outcome: string | undefined): string {
  return t(outcome === "inquiries" ? "intel.creative.outcome_inquiries" : "intel.creative.outcome_orders");
}

/** lift 1.1 → "2.1" (times the shop average). */
export function times(number: I18n["number"], lift: number): string {
  return number(1 + lift, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

/** 18 → "6 PM" / "६ बजे" in the seller's language. */
export function hourLabel(locale: string, hour: number): string {
  const d = new Date(2000, 0, 1, ((hour % 24) + 24) % 24);
  return new Intl.DateTimeFormat(locale === "ne" ? "ne-NP" : "en-US", { hour: "numeric" }).format(d);
}

/** Seconds per slide so `photos × seconds` lands inside the target range (slider: 1.5–6 in 0.5 steps). */
export function paceFor(target: [number, number], photos: number): number {
  const n = Math.max(1, photos);
  const ideal = (target[0] + target[1]) / 2 / n;
  const stepped = Math.round(ideal * 2) / 2;
  return Math.min(6, Math.max(1.5, stepped));
}
