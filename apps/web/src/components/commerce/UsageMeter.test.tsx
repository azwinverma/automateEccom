import type { UsageLimit } from "@commerce-os/api-client";
import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { en } from "@/i18n/messages/en";
import { atLimitActions, meterState, stateFromRatio } from "@/lib/usage";
import { renderWithI18n } from "@/test/render";
import { UsageMeter } from "./UsageMeter";
import { VideoCreditMeter } from "./VideoCreditMeter";

const PERIOD_END = "2026-12-01T00:00:00Z";

function usage(over: Partial<UsageLimit> = {}): UsageLimit {
  return {
    resource: "ai_text_generations",
    period: "month",
    kind: "consumable",
    overage_policy: "block",
    included: true,
    limit: 500,
    used: 120,
    reserved: 0,
    burst: null,
    alert_level: null,
    ...over,
  };
}

const gauge = (over: Partial<UsageLimit> = {}) => usage({ kind: "gauge", period: "lifetime", ...over });

describe("meter state rules", () => {
  it.each([
    [0, "ok"],
    [0.69, "ok"],
    [0.7, "70"],
    [0.849, "70"],
    [0.85, "85"],
    [0.99, "85"],
    [1, "100"],
    [1.3, "100"],
  ] as const)("ratio %s → %s", (ratio, expected) => {
    expect(stateFromRatio(ratio)).toBe(expected);
  });

  it("counts reserved usage and prefers the more severe server alert", () => {
    expect(meterState(usage({ used: 60, reserved: 10, limit: 100 }))).toBe("70");
    expect(meterState(usage({ used: 10, limit: 100, alert_level: "85" }))).toBe("85");
    expect(meterState(usage({ used: 100, limit: 100, alert_level: "70" }))).toBe("100");
  });

  it("not included (included:false or limit 0) is never an alert", () => {
    expect(meterState(usage({ included: false, limit: 0, used: 0, alert_level: "100" }))).toBe("not_included");
    expect(meterState(usage({ included: undefined, limit: 0, used: 0 }))).toBe("not_included");
    expect(atLimitActions(usage({ included: false, limit: 0, used: 0 }))).toMatchObject({ buyCredits: false, blocking: false });
  });

  it("null used is 'uncounted', never 0", () => {
    expect(meterState(gauge({ used: null, limit: 100 }))).toBe("uncounted");
    expect(meterState(gauge({ used: null, limit: null }))).toBe("unlimited");
  });

  it("at-limit actions follow overage_policy", () => {
    const at = { used: 500, limit: 500 };
    expect(atLimitActions(usage({ ...at, overage_policy: "credits" }))).toEqual({ buyCredits: true, upgrade: true, overageNote: false, blocking: true });
    expect(atLimitActions(usage({ ...at, overage_policy: "overage" }))).toEqual({ buyCredits: false, upgrade: false, overageNote: true, blocking: false });
    expect(atLimitActions(usage({ ...at, overage_policy: "block" }))).toEqual({ buyCredits: false, upgrade: true, overageNote: false, blocking: true });
    expect(atLimitActions(usage({ ...at, overage_policy: undefined }))).toMatchObject({ buyCredits: false, upgrade: true });
    // Below the limit no actions, whatever the policy.
    expect(atLimitActions(usage({ used: 10, overage_policy: "credits" })).buyCredits).toBe(false);
  });
});

describe("UsageMeter", () => {
  it("shows ok state with percent and the localized resource label", () => {
    renderWithI18n(<UsageMeter usage={usage({ reserved: 3 })} />);
    expect(screen.getByTestId("usage-meter")).toHaveAttribute("data-state", "ok");
    expect(screen.getByText("AI text")).toBeInTheDocument();
    expect(screen.getByText("25% used")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "AI text" })).toHaveAttribute("aria-valuenow", "120");
  });

  it("shows 85% copy without actions", () => {
    renderWithI18n(<UsageMeter usage={usage({ used: 870, limit: 1000 })} />);
    expect(screen.getByText(en.usage.state85)).toBeInTheDocument();
    expect(screen.queryByTestId("limit-actions")).not.toBeInTheDocument();
  });

  it("not included: calm 'Not in your plan' + See plans, no red, no Buy credits", () => {
    renderWithI18n(<UsageMeter usage={usage({ resource: "api_requests", included: false, limit: 0, used: 0, alert_level: "100", overage_policy: "credits" })} />);
    const row = screen.getByTestId("usage-meter");
    expect(row).toHaveAttribute("data-state", "not_included");
    expect(within(row).getByText(en.usage.notIncluded)).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: en.usage.seePlans })).toHaveAttribute("href", "/settings/plan#plans");
    expect(within(row).queryByText(en.usage.state100)).not.toBeInTheDocument();
    expect(within(row).queryByRole("link", { name: en.usage.buyCredits })).not.toBeInTheDocument();
    expect(within(row).queryByRole("meter")).not.toBeInTheDocument();
  });

  it("credits policy at limit: Buy credits + Upgrade + renewal date", () => {
    renderWithI18n(<UsageMeter usage={usage({ used: 500, overage_policy: "credits" })} periodEnd={PERIOD_END} />);
    expect(screen.getByText(en.usage.state100)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.usage.buyCredits })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.usage.upgrade })).toBeInTheDocument();
    expect(screen.getByText(/Renews/)).toBeInTheDocument();
  });

  it("overage policy at limit: neutral billed note, no red, no buttons", () => {
    renderWithI18n(<UsageMeter usage={usage({ resource: "orders", used: 1000, limit: 1000, overage_policy: "overage" })} periodEnd={PERIOD_END} />);
    expect(screen.getByText(en.usage.overageState)).toBeInTheDocument();
    expect(screen.getByText(en.usage.overageNote)).toBeInTheDocument();
    expect(screen.queryByText(en.usage.state100)).not.toBeInTheDocument();
    expect(screen.queryByTestId("limit-actions")).not.toBeInTheDocument();
  });

  it("block policy at limit: Upgrade only", () => {
    renderWithI18n(<UsageMeter usage={usage({ used: 500, overage_policy: "block" })} periodEnd={PERIOD_END} />);
    expect(screen.getByRole("link", { name: en.usage.upgrade })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: en.usage.buyCredits })).not.toBeInTheDocument();
    expect(screen.queryByText(/Renews/)).not.toBeInTheDocument();
  });

  it("gauge: 'in use' count, 'Current total', never 'Renews'", () => {
    renderWithI18n(<UsageMeter usage={gauge({ resource: "team_members", used: 1, limit: 2 })} periodEnd={PERIOD_END} />);
    expect(screen.getByText("1 of 2 seats in use")).toBeInTheDocument();
    expect(screen.getByText(en.usage.current)).toBeInTheDocument();
    expect(screen.queryByText(/Renews/)).not.toBeInTheDocument();
    expect(screen.queryByText(en.usage.perMonth)).not.toBeInTheDocument();
    expect(screen.queryByText(/% used/)).not.toBeInTheDocument();
  });

  it("gauge at limit with credits policy still shows no renewal date", () => {
    renderWithI18n(<UsageMeter usage={gauge({ resource: "stores", used: 1, limit: 1, overage_policy: "credits" })} periodEnd={PERIOD_END} />);
    expect(screen.getByTestId("limit-actions")).toBeInTheDocument();
    expect(screen.queryByText(/Renews/)).not.toBeInTheDocument();
  });

  it("gauge with used:null shows the limit only — no bar, no percentage, no 0", () => {
    renderWithI18n(<UsageMeter usage={gauge({ resource: "products", used: null, limit: 100 })} />);
    const row = screen.getByTestId("usage-meter");
    expect(row).toHaveAttribute("data-state", "uncounted");
    expect(within(row).getByText("Up to 100 products")).toBeInTheDocument();
    expect(within(row).queryByRole("meter")).not.toBeInTheDocument();
    expect(row.textContent).not.toMatch(/%|\b0\b/);
  });

  it("unlimited consumables show the count", () => {
    renderWithI18n(<UsageMeter usage={usage({ resource: "orders", used: 1840, limit: null })} />);
    expect(screen.getByTestId("usage-meter")).toHaveAttribute("data-state", "unlimited");
    expect(screen.getByText("1,840 used")).toBeInTheDocument();
  });

  it("unknown resource codes get a neutral generic label", () => {
    renderWithI18n(<UsageMeter usage={usage({ resource: "brand_new_meter" })} />);
    expect(screen.getByText(en.usage.resourceOther)).toBeInTheDocument();
  });
});

describe("VideoCreditMeter", () => {
  const video = (over: Partial<UsageLimit> = {}) =>
    usage({ resource: "premium_video_clips", limit: 20, used: 6, burst: { period: "day", limit: 4, used: 1 }, overage_policy: "credits", ...over });

  it("shows monthly clips and the daily burst separately", () => {
    renderWithI18n(<VideoCreditMeter usage={video()} credits={40} periodEnd={null} />);
    expect(screen.getByText("6 of 20 clips")).toBeInTheDocument();
    expect(screen.getByTestId("video-burst")).toHaveTextContent("1 of 4 today");
    expect(screen.getByText("40 credits available")).toBeInTheDocument();
  });

  it("flags the daily cap without month-level actions", () => {
    renderWithI18n(<VideoCreditMeter usage={video({ used: 8, burst: { period: "day", limit: 4, used: 4 } })} credits={0} periodEnd={null} />);
    expect(screen.getByText(en.video.dailyCapHit)).toBeInTheDocument();
    expect(screen.queryByTestId("limit-actions")).not.toBeInTheDocument();
  });

  it("credits policy at limit offers Buy credits", () => {
    renderWithI18n(<VideoCreditMeter usage={video({ used: 20, alert_level: "100" })} credits={0} periodEnd={PERIOD_END} />);
    expect(screen.getByRole("link", { name: en.usage.buyCredits })).toBeInTheDocument();
    expect(screen.getByText(en.video.atLimitCredits)).toBeInTheDocument();
  });

  it("block policy at limit offers Upgrade only", () => {
    renderWithI18n(<VideoCreditMeter usage={video({ used: 20, overage_policy: "block" })} credits={0} periodEnd={PERIOD_END} />);
    expect(screen.queryByRole("link", { name: en.usage.buyCredits })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.usage.upgrade })).toBeInTheDocument();
    expect(screen.getByText(en.video.atLimitBlock)).toBeInTheDocument();
  });

  it("overage policy at limit is neutral", () => {
    renderWithI18n(<VideoCreditMeter usage={video({ used: 20, overage_policy: "overage" })} credits={0} periodEnd={PERIOD_END} />);
    expect(screen.queryByText(en.usage.state100)).not.toBeInTheDocument();
    expect(screen.getByText(en.usage.overageNote)).toBeInTheDocument();
  });
});
