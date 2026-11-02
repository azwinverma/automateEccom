import { ApiError, type UsageLimit } from "@commerce-os/api-client";
import type { ExceptionItem } from "@/components/commerce/ExceptionInbox";

const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

/** Development fixtures only — realistic Nepal social-commerce situations. Never imported by app routes. */
export const EXCEPTION_FIXTURES: ExceptionItem[] = [
  { id: "x1", type: "payment_mismatch", severity: "urgent", summary: "Sita Gurung sent Rs 2,450 on eSewa; order total is Rs 2,650.", reference: "KTM-1042", amount: { amount_minor: 20000, currency: "NPR" }, occurredAt: minutesAgo(12) },
  { id: "x2", type: "low_confidence_ai", severity: "high", summary: "Reply draft to “size chart pathaunus na” is 54% confident.", reference: "Instagram DM", occurredAt: minutesAgo(25) },
  { id: "x3", type: "refund_above_threshold", severity: "urgent", summary: "Refund for damaged pashmina shawl exceeds your Rs 3,000 auto-approve limit.", reference: "PKR-0311", amount: { amount_minor: 480000, currency: "NPR" }, occurredAt: minutesAgo(40) },
  { id: "x4", type: "courier_failed", severity: "urgent", summary: "Pathao rider couldn't reach the customer in Lalitpur — 2nd attempt failed.", reference: "KTM-1029", occurredAt: minutesAgo(65) },
  { id: "x5", type: "channel_expired", severity: "high", summary: "Facebook Page token expired; new comments aren't being read.", reference: "Thamel Threads FB", occurredAt: minutesAgo(130) },
  { id: "x6", type: "inventory_mismatch", severity: "high", summary: "Dhaka topi (red, M): 3 in stock here, 0 counted on the shelf.", reference: "SKU DT-RED-M", occurredAt: minutesAgo(180) },
  { id: "x7", type: "publish_failed", severity: "normal", summary: "TikTok rejected the reel: video longer than allowed for this account.", reference: "Reel · Dashain sale", occurredAt: minutesAgo(240) },
  { id: "x8", type: "ambiguous_variant", severity: "high", summary: "Customer asked for “kalo wala, XL” — two black kurtas have XL.", reference: "Messenger", occurredAt: minutesAgo(300) },
  { id: "x9", type: "customer_escalation", severity: "urgent", summary: "Ramesh K. asked to talk to the owner about a late delivery.", reference: "Instagram DM", occurredAt: minutesAgo(360) },
  { id: "x10", type: "provider_failure", severity: "normal", summary: "Image generation provider is degraded; product photos are queued.", occurredAt: minutesAgo(420) },
];

const limit = (resource: string, used: number | null, lim: number | null, extra: Partial<UsageLimit> = {}): UsageLimit => ({
  resource,
  period: "month",
  kind: "consumable",
  overage_policy: "block",
  included: lim !== 0,
  limit: lim,
  used,
  reserved: 0,
  burst: null,
  alert_level: null,
  ...extra,
});

const gauge = (resource: string, used: number | null, lim: number | null, extra: Partial<UsageLimit> = {}) =>
  limit(resource, used, lim, { kind: "gauge", period: "lifetime", ...extra });

export const USAGE_FIXTURES: { note: string; usage: UsageLimit }[] = [
  { note: "consumable · ok", usage: limit("ai_text_generations", 120, 500, { reserved: 3, overage_policy: "credits" }) },
  { note: "consumable · 70", usage: limit("ai_images", 72, 100, { alert_level: "70" }) },
  { note: "consumable · 85", usage: limit("ai_inbox_replies", 870, 1000, { alert_level: "85" }) },
  { note: "at limit · credits policy", usage: limit("ai_text_generations", 500, 500, { overage_policy: "credits", alert_level: "100" }) },
  { note: "at limit · overage policy", usage: limit("orders", 1000, 1000, { overage_policy: "overage", alert_level: "100" }) },
  { note: "at limit · block policy", usage: limit("automation_runs", 200, 200, { alert_level: "100" }) },
  { note: "gauge · counted", usage: gauge("team_members", 1, 2) },
  { note: "gauge · at limit", usage: gauge("stores", 1, 1, { alert_level: "100" }) },
  { note: "gauge · not counted", usage: gauge("products", null, 100) },
  { note: "not included", usage: limit("api_requests", 0, 0, { included: false }) },
  { note: "unknown code", usage: limit("brand_new_meter", 3, 10) },
];

const burst = (used: number, lim: number) => ({ period: "day", limit: lim, used });

export const VIDEO_FIXTURES: { label: string; usage: UsageLimit; credits: number }[] = [
  { label: "Growth · healthy", usage: limit("premium_video_clips", 6, 20, { reserved: 1, burst: burst(1, 4), overage_policy: "credits" }), credits: 40 },
  { label: "Growth · 85% · daily cap hit", usage: limit("premium_video_clips", 17, 20, { burst: burst(4, 4), alert_level: "85", overage_policy: "credits" }), credits: 0 },
  { label: "Growth · at limit · credits policy", usage: limit("premium_video_clips", 20, 20, { burst: burst(2, 4), alert_level: "100", overage_policy: "credits" }), credits: 0 },
  { label: "Pro · at limit · block policy", usage: limit("premium_video_clips", 60, 60, { burst: burst(0, 10), alert_level: "100" }), credits: 0 },
  { label: "Business · 180/month", usage: limit("premium_video_clips", 64, 180, { burst: burst(9, 30), overage_policy: "overage" }), credits: 250 },
];

export const ERROR_FIXTURE = new ApiError({
  status: 503,
  code: "dependency_unavailable",
  message: "exceptions service down",
  requestId: "01JD3X7Q9K2V8W4T6Y0R5N1M3P",
});
