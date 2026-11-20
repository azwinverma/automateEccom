import { ApiError, type SimulationRunView, type TwinSummary } from "@commerce-os/api-client";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithI18n } from "@/test/render";
import { StoreGlance } from "./StoreGlance";
import { Freshness, SimulationResult, WhatIf } from "./WhatIf";

vi.mock("next/navigation", async (orig) => ({
  ...(await orig<typeof import("next/navigation")>()),
  usePathname: () => "/analytics",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("../procurement/VariantPicker", () => ({
  VariantPicker: ({ onPick }: { onPick: (v: unknown) => void }) => (
    <button
      type="button"
      onClick={() => onPick({ variant_id: "v1", product_id: "p1", title: "Dhaka Topi", variant: null, sku: "TOPI-1", price_minor: 120000, cost_minor: 60000 })}
    >
      Pick Dhaka Topi
    </button>
  ),
}));

const api = {
  twin: { summary: vi.fn(), freshness: vi.fn(), reconcile: vi.fn() },
  simulations: { create: vi.fn(), list: vi.fn(), get: vi.fn(), calibration: vi.fn() },
};
let perms = new Set<string>(["analytics.read"]);
let features: Record<string, "yes" | "no" | "pending"> = {};
vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ feature: (c: string) => features[c] ?? "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }),
}));

const now = new Date().toISOString();
const sec = (section: string, state: Record<string, unknown>, stale = false) => ({
  section,
  owner: section,
  state,
  as_of: now,
  computed_at: now,
  source_version: 1,
  age_s: 5,
  stale,
  max_staleness_s: { ui: 600, automation: 120 },
});

const summary = (over: Partial<Record<string, ReturnType<typeof sec>>> = {}): TwinSummary =>
  ({
    sections: {
      orders: sec("orders", { open: 4, needs_review: 1 }),
      inventory: sec("inventory", { out_of_stock: 2, low_stock: 0 }),
      cod: sec("cod", { cash_with_courier_minor: 1250000 }),
      returns: sec("returns", { open: 0 }),
      suppliers: sec("suppliers", { awaiting_approval: 1, overdue: 0 }),
      exceptions: sec("exceptions", { total: 3 }),
      ...over,
    },
    registry: [],
  }) as TwinSummary;

const discountRun = (over: Partial<SimulationRunView> = {}): SimulationRunView => ({
  id: "s1",
  kind: "discount",
  status: "completed",
  inputs: { product_id: "p1", discount_pct: 20, days: 14 },
  outputs: {
    label: "estimate",
    product_id: "p1",
    title: "Dhaka Topi",
    days: 14,
    discount_pct: 20,
    price_minor: 120000,
    discounted_price_minor: 96000,
    demand_per_day: { baseline: 2, expected: 2.8, low: 2.2, high: 3.7 },
    units: { baseline: 28, expected: 39, low: 31, high: 52 },
    stock: 30,
    stock_days: 10.7,
    stockout_probability: 0.82,
    margin_pct: { before: 50, after: 37.5 },
    contribution_per_unit_minor: { before: 50000, after: 26000 },
    contribution_minor: { with_discount: { expected: 780000, low: 806000, high: 780000 }, without_discount: 1400000 },
    difference_minor: -620000,
    return_rate: 0.05,
    warnings: [
      { code: "earns_less_than_no_discount", difference_minor: -620000 },
      { code: "stockout_likely", probability: 0.82 },
    ],
    not_included: [],
  },
  assumptions: [
    { code: "baseline_demand", vars: { per_day: 2, in_stock_days: 40, source: "product_brain" } },
    { code: "elasticity_typical_range", vars: { value: -1.5, range: [-0.5, -3], source: "typical_range" } },
    { code: "stock_caps_sales", vars: { stock: 30, incoming: 0 } },
    { code: "something_new", vars: {} },
  ],
  confidence: "low",
  label: "estimate",
  executes_nothing: true,
  method_version: "sim-1.0",
  baseline_as_of: now,
  error_code: null,
  created_at: now,
  completed_at: now,
  actual: null,
  abs_pct_error: null,
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["analytics.read"]);
  features = {};
  api.twin.summary.mockResolvedValue(summary());
  api.simulations.list.mockResolvedValue({ items: [] });
  api.simulations.calibration.mockResolvedValue({
    demand_backtest: { holdout_days: 14, products: 6, mape: 0.23, median_ape: 0.18, items: [], note: "" },
    discount_runs_compared: 0,
    discount_runs_mape: null,
  });
});

describe("StoreGlance", () => {
  it("shows only non-zero facts as links, with when they were true", async () => {
    renderWithI18n(<StoreGlance />);
    const strip = await screen.findByTestId("store-glance");
    expect(api.twin.summary).toHaveBeenCalledWith(["orders", "inventory", "cod", "returns", "suppliers", "exceptions"]);
    expect(screen.getByRole("link", { name: "Open orders: 4" })).toHaveAttribute("href", "/orders");
    expect(screen.getByRole("link", { name: "Out of stock: 2" })).toHaveAttribute("href", "/inventory");
    expect(screen.getByRole("link", { name: /With couriers/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "POs to approve: 1" })).toHaveAttribute("href", "/inventory/purchase-orders?status=pending_approval");
    expect(screen.queryByText(/Returns open/)).toBeNull();
    expect(strip).toHaveTextContent(/As of/);
    expect(screen.queryByTestId("glance-stale")).toBeNull();
  });

  it("says when the summary may be out of date, and when nothing is waiting", async () => {
    api.twin.summary.mockResolvedValue(
      summary({
        orders: sec("orders", { open: 0, needs_review: 0 }, true),
        inventory: sec("inventory", { out_of_stock: 0, low_stock: 0 }),
        cod: sec("cod", { cash_with_courier_minor: 0 }),
        suppliers: sec("suppliers", { awaiting_approval: 0, overdue: 0 }),
        exceptions: sec("exceptions", { total: 0 }),
      }),
    );
    renderWithI18n(<StoreGlance />);
    expect(await screen.findByTestId("glance-stale")).toHaveTextContent("May be out of date");
    expect(screen.getByText("Nothing waiting right now")).toBeInTheDocument();
  });

  it("formats money in the shop's currency", async () => {
    api.twin.summary.mockResolvedValue({ ...summary(), currency: "INR" });
    renderWithI18n(<StoreGlance />);
    expect(await screen.findByRole("link", { name: /With couriers: .*12,500/ })).toHaveTextContent(/INR|₹/);
    expect(screen.queryByRole("link", { name: /Rs/ })).toBeNull();
  });

  it("is not fetched or shown without analytics access (shop totals are for managers)", () => {
    perms = new Set();
    const { container } = renderWithI18n(<StoreGlance />);
    expect(container).toBeEmptyDOMElement();
    expect(api.twin.summary).not.toHaveBeenCalled();
  });

  it("stays silent when the summary can't be loaded", async () => {
    api.twin.summary.mockRejectedValue(new ApiError({ status: 500, code: "internal", message: "x", requestId: "r" }));
    const { container } = renderWithI18n(<StoreGlance />);
    await waitFor(() => expect(api.twin.summary).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});

describe("SimulationResult", () => {
  it("labels an estimate, gives the trade-off, warnings and every assumption", () => {
    renderWithI18n(<SimulationResult run={discountRun()} />);
    const r = screen.getByTestId("sim-result");
    expect(r).toHaveTextContent("Estimate");
    expect(r).toHaveTextContent("Low confidence");
    expect(r).toHaveTextContent(/At 20% off for 14 days you'd sell about 39 \(31–52\) and earn .*6,200.* less than without the discount\./);
    expect(r).toHaveTextContent(/You'll probably sell out \(82/);
    const list = screen.getByTestId("sim-assumptions");
    expect(list).toHaveTextContent("No discounts in your sales history yet, so a typical range is used (price sensitivity -0.5 to -3).");
    expect(list).toHaveTextContent("You can't sell more than the 30 in stock (including 0 on order).");
    expect(list).toHaveTextContent("Other assumption: something_new.");
    expect(r).toHaveTextContent("Nothing changes until you act.");
    expect(r).toHaveTextContent("50% → 37.5%");
  });

  it("uses the run's currency for every amount", () => {
    renderWithI18n(<SimulationResult run={discountRun({ currency: "INR" })} />);
    const r = screen.getByTestId("sim-result");
    expect(r).toHaveTextContent(/INR|₹/);
    expect(r).not.toHaveTextContent(/Rs/);
  });

  it("explains a run that couldn't be estimated", () => {
    renderWithI18n(<SimulationResult run={discountRun({ status: "failed", outputs: null, error_code: "simulation_not_enough_sales", assumptions: [] })} />);
    expect(screen.getByText(/Not enough sales yet to estimate demand/)).toBeInTheDocument();
  });

  it("reads a purchase estimate in plain words", () => {
    renderWithI18n(
      <SimulationResult
        run={discountRun({
          kind: "purchase_quantity",
          inputs: { variant_id: "v1", quantity: 40 },
          confidence: "medium",
          outputs: {
            label: "estimate",
            variant_id: "v1",
            title: "Dhaka Topi",
            variant: "Red",
            quantity: 40,
            supplier: "Bhaktapur Weavers",
            per_day: 1.5,
            lead_days: 10,
            available: 6,
            incoming: 0,
            stockout_before_arrival_probability: 0.97,
            stock_after_arrival: 40,
            cover_days_after_arrival: 27,
            sell_out_within_60d_probability: 0.9,
            units_sold_90d: 40,
            leftover_after_90d: 0,
            cash_tied_up_minor: 2400000,
            contribution_90d_minor: null,
            warnings: [{ code: "may_sell_out_before_delivery", probability: 0.97 }],
            not_included: ["contribution"],
          },
          assumptions: [{ code: "lead_time_supplier_terms", vars: { days: 10 } }],
        })}
      />,
    );
    const r = screen.getByTestId("sim-result");
    expect(r).toHaveTextContent("Buying 40 of Dhaka Topi (Red): about 27 days of stock after it arrives, with about 0 likely left after 90 days.");
    expect(r).toHaveTextContent("Medium confidence");
    expect(r).toHaveTextContent("Delivery takes about 10 days, from the supplier's terms.");
    expect(r).toHaveTextContent("Not included: profit (not enough sales)");
  });
});

describe("WhatIf", () => {
  it("offers ad budget only after an ad account is connected", async () => {
    renderWithI18n(<WhatIf />);
    expect(await screen.findByRole("radio", { name: "Moving ad budget" })).toBeDisabled();
    expect(screen.getByText(/Connect an ad account first/)).toBeInTheDocument();
  });

  it("shows the plan upsell without calling the API when the plan lacks it", async () => {
    features = { "intelligence.simulation": "no" };
    renderWithI18n(<WhatIf />);
    expect(screen.getByText("What-if estimates are on the Business plan.")).toBeInTheDocument();
    expect(api.simulations.list).not.toHaveBeenCalled();
  });

  it("validates, queues, polls until done and shows the estimate", async () => {
    const user = userEvent.setup();
    api.simulations.create.mockResolvedValue(discountRun({ status: "queued", outputs: null, assumptions: [] }));
    api.simulations.get.mockResolvedValueOnce(discountRun({ status: "running", outputs: null, assumptions: [] })).mockResolvedValue(discountRun());
    renderWithI18n(<WhatIf />);
    await user.click(await screen.findByRole("button", { name: "Estimate it" }));
    expect(screen.getByText("Pick a product first.")).toBeInTheDocument();
    expect(api.simulations.create).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Pick Dhaka Topi" }));
    await user.clear(screen.getByLabelText("Discount (%)"));
    await user.type(screen.getByLabelText("Discount (%)"), "90");
    await user.click(screen.getByRole("button", { name: "Estimate it" }));
    expect(screen.getByText("Enter a discount from 1 to 70.")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Discount (%)"));
    await user.type(screen.getByLabelText("Discount (%)"), "20");
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      await user.click(screen.getByRole("button", { name: "Estimate it" }));
      expect(api.simulations.create).toHaveBeenCalledWith({ kind: "discount", discount: { product_id: "p1", discount_pct: 20, days: 14 } });
      expect(await screen.findByTestId("sim-pending")).toHaveTextContent("Queued…");
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1600);
      });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1600);
      });
      expect(await screen.findByTestId("sim-result")).toHaveTextContent("Estimate");
      expect(api.simulations.get).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
    expect(screen.getByTestId("sim-calibration")).toHaveTextContent("Checked against the last 14 days for 6 products");
    expect(screen.getByTestId("sim-calibration")).toHaveTextContent("None of your discount estimates has been tried yet");
  });
});

describe("Freshness", () => {
  it("shows age and update delay per part against the 60 s target", async () => {
    api.twin.freshness.mockResolvedValue({
      target_p95_s: 60,
      p95_lag_s: 4.2,
      meets_target: true,
      sections: [{ section: "orders", age_s: 30, ttl_s: 300, last_lag_ms: 2100, trigger: "orders.created" }],
      note: "",
    });
    renderWithI18n(<Freshness />);
    const p = await screen.findByTestId("twin-freshness");
    expect(p).toHaveTextContent("95% of updates arrive within 4 seconds (target 60 s).");
    expect(screen.getByRole("rowheader", { name: "Orders" })).toBeInTheDocument();
    expect(p).toHaveTextContent("5 min");
  });

  it("is hidden from people without analytics access", () => {
    perms = new Set();
    const { container } = renderWithI18n(<Freshness />);
    expect(container).toBeEmptyDOMElement();
    expect(api.twin.freshness).not.toHaveBeenCalled();
  });
});
