import type { AlertLevel, OveragePolicy, UsageLimit } from "@commerce-os/api-client";

/**
 * Display state of a limit:
 * - `not_included`: plan limit is 0 / `included: false` → calm "Not in your plan".
 * - `uncounted`: gauge whose `used` is null → show the limit only.
 * - `unlimited`: `limit` is null.
 * - `ok` | `70` | `85` | `100`: metered.
 */
export type MeterState = "not_included" | "uncounted" | "unlimited" | "ok" | AlertLevel;

type LimitLike = Pick<UsageLimit, "used" | "limit"> &
  Partial<Pick<UsageLimit, "reserved" | "alert_level" | "included" | "kind" | "period" | "overage_policy">>;

const ORDER: Record<string, number> = { ok: 0, "70": 1, "85": 2, "100": 3 };

export function isIncluded(l: Pick<LimitLike, "included" | "limit">): boolean {
  return l.included !== false && l.limit !== 0;
}

/** Gauges (and lifetime limits) are current counts, not period consumption: they never "renew". */
export function isGauge(l: Pick<LimitLike, "kind" | "period">): boolean {
  return l.kind === "gauge" || l.period === "lifetime";
}

/** Ratio of consumed (used + reserved) to limit; null when unlimited or uncounted. */
export function usageRatio(used: number | null, reserved: number, limit: number | null): number | null {
  if (limit === null || limit === undefined || used === null || used === undefined) return null;
  if (limit <= 0) return 1;
  return (used + (reserved || 0)) / limit;
}

export function stateFromRatio(ratio: number): "ok" | AlertLevel {
  if (ratio >= 1) return "100";
  if (ratio >= 0.85) return "85";
  if (ratio >= 0.7) return "70";
  return "ok";
}

/** The server's `alert_level` wins when it is more severe than our own calculation. */
export function meterState(l: LimitLike): MeterState {
  if (!isIncluded(l)) return "not_included";
  if (l.used === null || l.used === undefined) return l.limit === null ? "unlimited" : "uncounted";
  if (l.limit === null) return "unlimited";
  const computed = stateFromRatio(usageRatio(l.used, l.reserved ?? 0, l.limit) ?? 0);
  const server = l.alert_level ?? null;
  if (server && (ORDER[server] ?? 0) > (ORDER[computed] ?? 0)) return server;
  return computed;
}

export interface AtLimitActions {
  buyCredits: boolean;
  upgrade: boolean;
  /** `overage` policy: extra usage is billed — a neutral note, not an error. */
  overageNote: boolean;
  /** Red "Limit reached" is only for limits that actually block. */
  blocking: boolean;
}

const NONE: AtLimitActions = { buyCredits: false, upgrade: false, overageNote: false, blocking: false };

/** What to offer once a limit is reached, driven by `overage_policy` (default: block). */
export function atLimitActions(l: LimitLike): AtLimitActions {
  if (meterState(l) !== "100") return NONE;
  const policy: OveragePolicy = l.overage_policy ?? "block";
  if (policy === "credits") return { buyCredits: true, upgrade: true, overageNote: false, blocking: true };
  if (policy === "overage") return { buyCredits: false, upgrade: false, overageNote: true, blocking: false };
  return { buyCredits: false, upgrade: true, overageNote: false, blocking: true };
}

/** Premium (generative) video gets the Video Credit Meter; auto reels stay in the usage list. */
export function isPremiumVideoResource(resource: string): boolean {
  return /video/.test(resource) && !/reel/.test(resource);
}

/** Server-provided at-limit options (from `usage_limit_reached.details.options`). */
export type LimitOption = "buy_credits" | "upgrade" | "wait_for_renewal";
export const DEFAULT_LIMIT_OPTIONS: LimitOption[] = ["upgrade"];

export function parseLimitOptions(v: unknown): LimitOption[] {
  if (!Array.isArray(v)) return DEFAULT_LIMIT_OPTIONS;
  const valid = v.filter((o): o is LimitOption => o === "buy_credits" || o === "upgrade" || o === "wait_for_renewal");
  return valid.length ? valid : DEFAULT_LIMIT_OPTIONS;
}

/** Plan comparison anchor used by every "See plans" / "Upgrade" action. */
export const PLANS_HREF = "/settings/plan#plans";
export const CREDITS_HREF = "/settings/plan#credits";
