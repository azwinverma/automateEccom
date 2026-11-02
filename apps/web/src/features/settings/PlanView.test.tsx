import type { Credits, Entitlements, Subscription } from "@commerce-os/api-client";
import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { renderWithI18n } from "@/test/render";
import { PlanView } from "./PlanView";

const subscription: Subscription = {
  plan: { code: "starter", name: "Starter", tagline: "Create" },
  plan_version: 1,
  status: "trialing",
  trial_ends_at: "2026-11-16T00:00:00Z",
  current_period_start: "2026-11-02T00:00:00Z",
  current_period_end: "2026-12-02T00:00:00Z",
};

/** Shape of a real Starter (trial) merchant from the backend. */
const starter: Entitlements = {
  features: {
    "catalog.products": true,
    "ai.text_generation": true,
    "inbox.unified": true,
    "video.premium": false,
    "video.auto_reels": false,
    "security.sso": false,
    "x.brand_new_feature": true,
  },
  limits: [
    { resource: "premium_video_clips", period: "month", kind: "consumable", overage_policy: "credits", included: false, limit: 0, used: 0, reserved: 0, burst: { period: "day", limit: 0, used: 0 }, alert_level: "100" },
    { resource: "ai_text_generations", period: "month", kind: "consumable", overage_policy: "credits", included: true, limit: 100, used: 4, reserved: 0, burst: null, alert_level: null },
    { resource: "api_requests", period: "month", kind: "consumable", overage_policy: "block", included: false, limit: 0, used: 0, reserved: 0, burst: null, alert_level: "100" },
    { resource: "team_members", period: "lifetime", kind: "gauge", overage_policy: "block", included: true, limit: 2, used: 1, reserved: 0, burst: null, alert_level: null },
    { resource: "products", period: "lifetime", kind: "gauge", overage_policy: "block", included: true, limit: 100, used: null, reserved: 0, burst: null, alert_level: null },
  ],
};

const credits: Credits = {
  balance: 15,
  currency: "credits",
  transactions: [
    { id: "t1", amount: 20, balance_after: 20, kind: "grant", reference_type: "subscription", created_at: "2026-11-02T00:00:00Z" },
    { id: "t2", amount: -5, balance_after: 15, kind: "hold", reference_type: "ai_job", created_at: "2026-11-02T01:00:00Z" },
    { id: "t3", amount: 5, balance_after: 20, kind: "release", reference_type: "ai_job", created_at: "2026-11-02T01:05:00Z" },
    { id: "t4", amount: -5, balance_after: 15, kind: "mystery", reference_type: null, created_at: "2026-11-02T02:00:00Z" },
  ],
};

let entitlements: Entitlements = starter;
const api = {
  billing: {
    subscription: vi.fn(async () => subscription),
    entitlements: vi.fn(async () => entitlements),
    credits: vi.fn(async () => credits),
  },
};

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ api, merchantId: "m1" }),
}));

beforeEach(() => {
  entitlements = starter;
});

describe("PlanView — Starter trial", () => {
  it("never shows red limit states, daily cap or Buy credits for things not in the plan", async () => {
    renderWithI18n(<PlanView />);
    await screen.findByText("Starter");
    expect(screen.queryByText(en.usage.state100)).not.toBeInTheDocument();
    expect(screen.queryByText(en.video.dailyCapHit)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: en.usage.buyCredits })).not.toBeInTheDocument();
    expect(screen.queryByTestId("video-credit-meter")).not.toBeInTheDocument();
  });

  it("explains premium video is on higher plans with a single See plans action", async () => {
    renderWithI18n(<PlanView />);
    const note = await screen.findByTestId("video-unavailable");
    expect(within(note).getByText(en.video.premiumUnavailable)).toBeInTheDocument();
    expect(within(note).getAllByRole("link")).toHaveLength(1);
    expect(within(note).getByRole("link", { name: en.usage.seePlans })).toHaveAttribute("href", "/settings/plan#plans");
  });

  it("shows not-included limits calmly", async () => {
    renderWithI18n(<PlanView />);
    await screen.findByText("Starter");
    const row = screen.getAllByTestId("usage-meter").find((r) => r.dataset.resource === "api_requests")!;
    expect(row).toHaveAttribute("data-state", "not_included");
    expect(within(row).getByText(en.usage.notIncluded)).toBeInTheDocument();
  });

  it("shows gauges as current counts without renewal, and uncounted gauges as limits only", async () => {
    renderWithI18n(<PlanView />);
    await screen.findByText("Starter");
    const seats = screen.getAllByTestId("usage-meter").find((r) => r.dataset.resource === "team_members")!;
    expect(within(seats).getByText("1 of 2 seats in use")).toBeInTheDocument();
    expect(seats.textContent).not.toMatch(/Renews/);
    const products = screen.getAllByTestId("usage-meter").find((r) => r.dataset.resource === "products")!;
    expect(within(products).getByText("Up to 100 products")).toBeInTheDocument();
    expect(within(products).queryByRole("meter")).not.toBeInTheDocument();
    expect(screen.getByText(en.plan.capacityHeading)).toBeInTheDocument();
  });

  it("groups features: included first, then a quieter 'On higher plans' list", async () => {
    renderWithI18n(<PlanView />);
    const included = await screen.findByTestId("features-included");
    const higher = screen.getByTestId("features-higher");
    expect(within(included).getByText("Product catalog")).toBeInTheDocument();
    expect(within(included).getByText(en.plan.featureOther)).toBeInTheDocument();
    expect(within(included).queryByText("Premium AI video")).not.toBeInTheDocument();
    expect(within(higher).getByText("Premium AI video")).toBeInTheDocument();
    expect(within(higher).getByText("Single sign-on (SSO)")).toBeInTheDocument();
    // Included list renders before the higher-plans list.
    expect(included.compareDocumentPosition(higher) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("labels credit transactions by kind, including holds and releases", async () => {
    renderWithI18n(<PlanView />);
    await screen.findByText(en.plan.creditKind.grant);
    expect(screen.getByText(en.plan.creditKind.hold)).toBeInTheDocument();
    expect(screen.getByText(en.plan.creditKind.release)).toBeInTheDocument();
    expect(screen.getByText(en.plan.creditKind.other)).toBeInTheDocument();
  });

  it("renders localized labels in Nepali", async () => {
    renderWithI18n(<PlanView />, { locale: "ne" });
    const included = await screen.findByTestId("features-included");
    expect(within(included).getByText(ne.plan.feature.catalog_products)).toBeInTheDocument();
    expect(screen.getByText(ne.video.premiumUnavailable)).toBeInTheDocument();
    expect(screen.getByText(ne.plan.creditKind.hold)).toBeInTheDocument();
  });

  it("shows the Video Credit Meter when premium video is included", async () => {
    entitlements = {
      features: { ...starter.features, "video.premium": true },
      limits: [
        { resource: "premium_video_clips", period: "month", kind: "consumable", overage_policy: "credits", included: true, limit: 20, used: 3, reserved: 0, burst: { period: "day", limit: 4, used: 1 }, alert_level: null },
      ],
    };
    renderWithI18n(<PlanView />);
    expect(await screen.findByTestId("video-credit-meter")).toBeInTheDocument();
    expect(screen.queryByTestId("video-unavailable")).not.toBeInTheDocument();
  });
});
