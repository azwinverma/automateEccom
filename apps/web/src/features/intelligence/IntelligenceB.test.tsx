import { ApiError, type MemoryFact, type ProductBrain, type ProfitComponent, type ProfitSummary, type RecommendationView } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { renderWithI18n } from "@/test/render";
import { MemoryFacts } from "./MemoryFacts";
import { ProductBrainView } from "./ProductBrainCard";
import { ProfitView } from "./ProfitView";
import { Recommendations } from "./Recommendations";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const c = (code: ProfitComponent["code"], amount: number | null, status: ProfitComponent["status"] = "included", missing = 0, reason: string | null = null): ProfitComponent => ({ code, amount_minor: amount, status, missing, reason });
const summary = (over: Partial<ProfitSummary> = {}): ProfitSummary => ({
  currency: "NPR",
  window_days: 30,
  shop: {
    components: [
      c("goods", 980000),
      c("delivery_fees", 60000),
      c("cogs", -300000, "partial", 1),
      c("packaging", null, "not_included", 4, "packaging_not_set"),
      c("ads", null, "not_included", 0, "no_ad_account"),
    ],
    revenue_minor: 1040000,
    contribution_minor: 362500,
    margin_pct: 34.9,
    complete: false,
    units: 4,
    orders: 4,
  },
  products: [
    { product_id: "p2", title: "Pashmina Shawl", components: [c("cogs", null, "not_included", 1)], revenue_minor: 245000, contribution_minor: 200000, margin_pct: null, complete: false, units: 1, orders: 1, contribution_per_unit_minor: 200000 },
  ],
  counts: { sold: 4, failed: 1, open: 1, cost_from_current: 0 },
  allocation: "order_amounts_by_line_value",
  method_version: "profit-1.0",
  as_of: new Date().toISOString(),
  settings: { packaging_cost_minor: null, min_margin_pct: 20, min_contribution_minor: 0, max_return_rate_pct: 15 },
  ...over,
});
const fact = (over: Partial<MemoryFact> = {}): MemoryFact => ({
  id: "f1", subject_type: "shop", subject_id: "m1", subject_label: null, fact_type: "repeat_cycle_days", value: { days: 20, customers: 6 }, confidence: 0.64,
  evidence: [{ metric: "days_between_orders", intervals: 12 }], status: "active", source: "derived", confirmed: false, version: 1, method_version: "mem-1.0",
  valid_from: new Date().toISOString(), valid_to: null, note: null, ...over,
});
const brain = (over: Partial<ProductBrain> = {}): ProductBrain => ({
  product_id: "p1", currency: "NPR", units_7d: 6, units_30d: 20, units_90d: 20, in_stock_days_90d: 52, demand_per_day: 1.6, available: 5, cover_days: 3.1, stockouts_90d: 1,
  margin_pct: null, contribution_per_unit_minor: null, return_rate: null, completeness: 0.4, stock_risk: "high", fit: null, sold_90d_delivered: 0, returned_90d: 0,
  top_reasons: [], by_variant: [], contribution_basis: "cost_not_set", stock_tracked: true,
  not_included: { margin: "cost_not_set", contribution: "cost_not_set", returns: "no_delivered_sales", seasonality: "needs_12_months" },
  method_version: "pbr-1.0", as_of: new Date().toISOString(), return_insights: null, facts: [], ...over,
});
const rec = (over: Partial<RecommendationView> = {}): RecommendationView => ({
  id: "r1", type: "return_prevention", status: "open", subject_type: "product", subject_id: "p1",
  explanation: { what: "fit_note_size_small", why: "return_pattern", vars: { title: "Dhaka Kurta", returned: 6, sold: 12, rate_pct: 50, baseline_pct: 13, reason: "size_small", share_pct: 83 } },
  evidence: [], confidence: 0.6, estimated_impact: { return_rate_now: 0.5 }, action: { type: "confirm_fact", params: { fact_type: "fit_runs_small" } },
  method_version: "rec-1.0", created_at: new Date().toISOString(), expires_at: null, resolved_at: null, reason: null, outcome: null, outcome_measured_at: null, ...over,
});

const api = {
  intelligence: { profit: vi.fn(), updateProfitSettings: vi.fn(), memoryFacts: vi.fn(), confirmFact: vi.fn(), correctFact: vi.fn(), rejectFact: vi.fn(), recommendations: vi.fn(), accept: vi.fn(), reject: vi.fn() },
};
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["analytics.read", "settings.manage", "automation.approve", "catalog.read"]);
  api.intelligence.profit.mockResolvedValue(summary());
  api.intelligence.memoryFacts.mockResolvedValue({ items: [fact()], fact_types: [] });
});

describe("ProfitView", () => {
  it("labels missing data as not included or partial, with a reason the seller can act on", async () => {
    renderWithI18n(<ProfitView />);
    const table = await screen.findByTestId("profit-waterfall");
    const packaging = within(table).getByText(en.intel.profit.comp.packaging).closest("tr")!;
    expect(packaging).toHaveAttribute("data-status", "not_included");
    expect(within(packaging).getByText(en.intel.profit.notIncluded)).toBeInTheDocument();
    expect(within(packaging).getByText(en.intel.profit.reason.packaging_not_set)).toBeInTheDocument();
    expect(within(packaging).getByText("–")).toBeInTheDocument(); // never a silent zero
    const cogs = within(table).getByText(en.intel.profit.comp.cogs).closest("tr")!;
    expect(within(cogs).getByText("Partial (1 missing)")).toBeInTheDocument();
    expect(within(cogs).getByText(en.intel.profit.reason.missing_cogs)).toBeInTheDocument();
    expect(screen.getByTestId("profit-completeness")).toHaveTextContent(en.intel.profit.incomplete);
    expect(screen.getByText(/4 reached the customer · 1 failed delivery/)).toBeInTheDocument();
    const pnl = screen.getByTestId("product-pnl");
    expect(within(pnl).getByText(en.intel.profit.costNotSet)).toBeInTheDocument();
  });

  it("saves the packaging cost in paisa and switches the window", async () => {
    const u = userEvent.setup();
    api.intelligence.updateProfitSettings.mockResolvedValue({ ...summary().settings, packaging_cost_minor: 2500 });
    renderWithI18n(<ProfitView />);
    const form = await screen.findByTestId("profit-settings");
    await u.type(within(form).getByLabelText(en.intel.profit.packaging), "25");
    await u.click(within(form).getByRole("button", { name: en.intel.profit.save }));
    await waitFor(() => expect(api.intelligence.updateProfitSettings).toHaveBeenCalledWith({ packaging_cost_minor: 2500, min_margin_pct: 20, max_return_rate_pct: 15 }));
    await u.click(screen.getByRole("button", { name: en.intel.profit.days90 }));
    await waitFor(() => expect(api.intelligence.profit).toHaveBeenLastCalledWith(90));
  });

  it("rejects an out-of-range limit before calling the API", async () => {
    const u = userEvent.setup();
    renderWithI18n(<ProfitView />);
    const form = await screen.findByTestId("profit-settings");
    const max = within(form).getByLabelText(en.intel.profit.maxReturn);
    await u.clear(max);
    await u.type(max, "140");
    await u.click(within(form).getByRole("button", { name: en.intel.profit.save }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(en.intel.profit.invalid);
    expect(api.intelligence.updateProfitSettings).not.toHaveBeenCalled();
  });

  it("shows the plan upsell instead of an error when profit isn't on the plan", async () => {
    api.intelligence.profit.mockRejectedValue(new ApiError({ status: 403, code: "feature_not_in_plan", message: "x", requestId: "q" }));
    renderWithI18n(<ProfitView />, { locale: "ne" });
    expect(await screen.findByText(ne.intel.profit.upsell)).toBeInTheDocument();
  });
});

describe("MemoryFacts", () => {
  it("corrects a fact with a validated value and a reason", async () => {
    const u = userEvent.setup();
    api.intelligence.correctFact.mockResolvedValue(fact({ version: 2, source: "merchant", confirmed: true, value: { days: 30, customers: 6 } }));
    renderWithI18n(<MemoryFacts />);
    const list = await screen.findByTestId("memory-facts");
    expect(within(list).getByText(/reorder about every 20 days \(6 repeat customers\)/)).toBeInTheDocument();
    expect(within(list).getByText(/Based on 12 repeat orders · 64% confidence · Version 1/)).toBeInTheDocument();
    await u.click(within(list).getByRole("button", { name: en.intel.mem.correct }));
    const dialog = await screen.findByRole("dialog");
    const days = within(dialog).getByLabelText(en.intel.mem.field_days);
    await u.clear(days);
    await u.type(days, "400");
    await u.type(within(dialog).getByLabelText(en.intel.mem.note), "Festival buyers");
    await u.click(within(dialog).getByRole("button", { name: en.intel.mem.correct }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(en.intel.mem.invalid);
    await u.clear(days);
    await u.type(days, "30");
    await u.click(within(dialog).getByRole("button", { name: en.intel.mem.correct }));
    await waitFor(() => expect(api.intelligence.correctFact).toHaveBeenCalledWith("f1", { days: 30 }, "Festival buyers"));
  });

  it("rejects with a note and links product facts", async () => {
    const u = userEvent.setup();
    api.intelligence.memoryFacts.mockResolvedValue({
      items: [fact({ id: "f2", subject_type: "product", subject_id: "p1", subject_label: "Dhaka Kurta", fact_type: "fit_runs_small", value: { share: 0.83, returns: 5, sold: 12 }, evidence: [{ returns: 5 }] })],
      fact_types: [],
    });
    api.intelligence.rejectFact.mockResolvedValue(fact({ status: "rejected_by_merchant" }));
    renderWithI18n(<MemoryFacts />);
    const list = await screen.findByTestId("memory-facts");
    expect(within(list).getByRole("link", { name: "Dhaka Kurta" })).toHaveAttribute("href", "/products/p1");
    expect(within(list).getByText(/runs small: 83% of its returns say too small/)).toBeInTheDocument();
    await u.click(within(list).getByRole("button", { name: en.intel.mem.reject }));
    const dialog = await screen.findByRole("dialog");
    await u.type(within(dialog).getByLabelText(en.intel.mem.note), "Sizes changed with the new batch");
    await u.click(within(dialog).getByRole("button", { name: en.intel.mem.reject }));
    await waitFor(() => expect(api.intelligence.rejectFact).toHaveBeenCalledWith("f2", "Sizes changed with the new batch"));
  });

  it("hides actions from people who can't change settings", async () => {
    perms = new Set(["analytics.read"]);
    renderWithI18n(<MemoryFacts />);
    const list = await screen.findByTestId("memory-facts");
    expect(within(list).queryByRole("button", { name: en.intel.mem.confirm })).toBeNull();
    expect(within(list).getByText(en.intel.mem.managerOnly)).toBeInTheDocument();
  });
});

describe("ProductBrainView", () => {
  it("says what it can't know yet in plain sentences", () => {
    renderWithI18n(<ProductBrainView brain={brain()} />);
    const card = screen.getByTestId("product-brain");
    expect(within(card).getByText(/from 52 days in stock/)).toBeInTheDocument();
    expect(within(card).getByRole("img", { name: "Stock risk: Runs out soon" })).toBeInTheDocument();
    const missing = within(card).getByTestId("brain-missing");
    expect(within(missing).getByText(en.intel.brain.missing_margin_cost_not_set)).toBeInTheDocument();
    expect(within(missing).getByText(en.intel.brain.missing_seasonality_needs_12_months)).toBeInTheDocument();
    expect(within(missing).getByText(en.intel.brain.missing_returns_no_delivered_sales)).toBeInTheDocument();
  });

  it("shows returns, the worst variant and a confirmed fit hint", () => {
    renderWithI18n(
      <ProductBrainView
        brain={brain({
          return_rate: 0.5, sold_90d_delivered: 12, returned_90d: 6, fit: "small", top_reasons: [{ reason: "size_small", units: 5 }],
          by_variant: [{ variant_id: "v1", variant: "M", sold: 8, returned: 5, rate: 0.625 }, { variant_id: "v2", variant: "L", sold: 4, returned: 1, rate: 0.25 }],
          margin_pct: 60, contribution_per_unit_minor: 52000, contribution_basis: "complete", not_included: {},
        })}
      />,
    );
    const card = screen.getByTestId("product-brain");
    expect(within(card).getByText(/50% returned \(6 of 12\)/)).toBeInTheDocument();
    expect(within(card).getByText(/too small \(5\)/)).toBeInTheDocument();
    expect(within(card).getByText(/Most returned: M \(63%\)/)).toBeInTheDocument();
    expect(within(card).getByTestId("brain-fit")).toHaveTextContent(en.intel.brain.fit_small);
    expect(within(card).queryByTestId("brain-missing")).toBeNull();
  });
});

describe("Recommendations (Phase 6B copy)", () => {
  it("explains a return pattern and applies the fit note", async () => {
    const u = userEvent.setup();
    api.intelligence.recommendations.mockResolvedValue({ items: [rec()] });
    api.intelligence.accept.mockResolvedValue(rec({ status: "executed" }));
    renderWithI18n(<Recommendations />);
    const card = await screen.findByTestId("recommendations");
    expect(within(card).getByText("Tell customers Dhaka Kurta runs small")).toBeInTheDocument();
    expect(within(card).getByText(/6 of 12 sold came back \(50%; your shop average is 13%\)\. 83% of those returns say: too small\./)).toBeInTheDocument();
    await u.click(within(card).getByRole("button", { name: en.intel.rec.apply }));
    await waitFor(() => expect(api.intelligence.accept).toHaveBeenCalledWith("r1"));
  });

  it("shows losses in money, links to the product and offers no Apply for informational ones", async () => {
    api.intelligence.recommendations.mockResolvedValue({
      items: [
        rec({ id: "r2", type: "profit_loss", explanation: { what: "review_price_or_cost", why: "losing_money", vars: { title: "Cheap Scarf", units: 6, contribution: -42000, per_unit: -7000 } }, action: { type: "none", params: { product_id: "p9" } }, subject_id: "p9" }),
        rec({ id: "r3", type: "profit_data", explanation: { what: "add_cost", why: "cost_not_set", vars: { title: "Topi", units: 3, revenue: 300000 } }, action: { type: "none" }, subject_id: "p8" }),
      ],
    });
    renderWithI18n(<Recommendations />);
    const card = await screen.findByTestId("recommendations");
    expect(within(card).getByText("Cheap Scarf is losing money")).toBeInTheDocument();
    expect(within(card).getByText(/Lost .*420 on 6 sold in 30 days/)).toBeInTheDocument();
    expect(within(card).getByText("Add the cost of Topi")).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: en.intel.rec.apply })).toBeNull();
    expect(within(card).getAllByRole("link", { name: en.intel.rec.openProduct }).map((a) => a.getAttribute("href"))).toEqual(["/products/p9", "/products/p8"]);
  });

  it("values a restock by its profit", async () => {
    api.intelligence.recommendations.mockResolvedValue({
      items: [rec({ id: "r4", type: "restock", explanation: { what: "restock", why: "selling_low_stock", vars: { title: "Kurta", variant: "M", sold_30d: 6, available: 1, cover_days: 5, contribution_30d: 120000 } }, estimated_impact: { cover_days: 5, contribution_30d_minor: 120000 }, action: { type: "none" }, subject_type: "variant" })],
    });
    renderWithI18n(<Recommendations />);
    const card = await screen.findByTestId("recommendations");
    expect(within(card).getByText(/Worth about .*1,200 profit over the next 30 days/)).toBeInTheDocument();
  });
});
