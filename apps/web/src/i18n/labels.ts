import type { Translate } from "./types";

/** Codes from the billing catalog. Every one has en + ne copy (enforced by tests). */
export const RESOURCE_CODES = [
  "products",
  "orders",
  "channels",
  "team_members",
  "stores",
  "ai_text_generations",
  "ai_inbox_replies",
  "ai_images",
  "auto_reels",
  "premium_video_clips",
  "storage_mb",
  "automation_runs",
  "automation_workflows",
  "api_requests",
] as const;

export const FEATURE_CODES = [
  "catalog.products",
  "ai.product_studio",
  "ai.text_generation",
  "ai.image_generation",
  "video.auto_reels",
  "video.premium",
  "inbox.unified",
  "inbox.ai_replies",
  "ai.sales_agent",
  "orders.chat_to_order",
  "automation.workflows",
  "marketing.campaigns",
  "automation.autopilot",
  "analytics.profit",
  "ai.store_manager",
  "procurement",
  "stores.multiple",
  "inventory.multi_location",
  "api.access",
  "ai.byok",
  "security.sso",
  "roles.custom",
  "audit.export",
] as const;

export const CREDIT_KINDS = ["grant", "purchase", "hold", "release", "consume", "refund", "expire", "adjustment"] as const;

/** Dictionary keys can't contain dots or other separators; codes map onto `[a-z0-9_]`. */
function keyPart(code: string): string {
  return code.replace(/[^a-zA-Z0-9_]/g, "_");
}

export function resourceLabel(t: Translate, code: string): string {
  return t.dynamic(`usage.resource.${keyPart(code)}`) ?? t("usage.resourceOther");
}

export function resourceUnit(t: Translate, code: string): string {
  return t.dynamic(`usage.unit.${keyPart(code)}`) ?? t("usage.unitOther");
}

export function featureLabel(t: Translate, code: string): string {
  return t.dynamic(`plan.feature.${keyPart(code)}`) ?? t("plan.featureOther");
}

export function creditKindLabel(t: Translate, kind: string | null | undefined): string {
  return (kind ? t.dynamic(`plan.creditKind.${keyPart(kind)}`) : undefined) ?? t("plan.creditKind.other");
}
