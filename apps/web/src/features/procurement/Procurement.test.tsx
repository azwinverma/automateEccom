import { ApiError, type PurchaseOrder, type RecommendationView, type SupplierPerformance } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithI18n } from "@/test/render";
import { Recommendations } from "../intelligence/Recommendations";
import { PurchaseOrderPage } from "./PurchaseOrderDetail";
import { PurchaseOrderForm } from "./PurchaseOrderForm";
import { PurchaseOrdersView } from "./PurchaseOrdersView";
import { landedUnitCosts, toMinor } from "./shared";
import { PerformanceCard } from "./SupplierDetail";

vi.mock("next/navigation", async (orig) => ({
  ...(await orig<typeof import("next/navigation")>()),
  usePathname: () => "/inventory/purchase-orders",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

const api = {
  procurement: {
    supplier: vi.fn(), suppliers: vi.fn(), purchaseOrders: vi.fn(), createPurchaseOrder: vi.fn(), updatePurchaseOrder: vi.fn(),
    submit: vi.fn(), approve: vi.fn(), reject: vi.fn(), markSent: vi.fn(), cancel: vi.fn(), receive: vi.fn(), incoming: vi.fn(),
  },
  catalog: { products: vi.fn(), product: vi.fn() },
  automation: { policy: vi.fn() },
  intelligence: { recommendations: vi.fn(), accept: vi.fn(), reject: vi.fn() },
};
let perms = new Set<string>();
let features: Record<string, "yes" | "no"> = {};
vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ feature: (c: string) => features[c] ?? "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }),
}));

const supplierDetail = {
  id: "s1", name: "Bhaktapur Weavers", status: "active", currency: "NPR", performance: null,
  products: [{ variant_id: "v1", product_id: "p1", title: "Cotton Kurta", variant: null, sku: "KURTA-M", supplier_sku: null, cost_minor: 100000, moq: 50, lead_time_days: 10, is_preferred: true, current_cost_minor: null, price_minor: 245000 }],
};

const po = (over: Partial<PurchaseOrder> = {}): PurchaseOrder => ({
  id: "po1", number: "PO-1001", status: "pending_approval", source: "seller", supplier: { id: "s1", name: "Bhaktapur Weavers", phone: null }, location_id: null, currency: "NPR",
  subtotal_minor: 4000000, freight_minor: 200000, duty_minor: 100000, other_minor: 0, total_minor: 4300000, expected_at: null, notes: null, approval_reason: "above_threshold",
  submitted_at: new Date().toISOString(), approved_at: null, sent_at: null, received_at: null, cancelled_at: null, cancel_reason: null, recommendation_id: null, version: 2,
  created_at: new Date().toISOString(),
  lines: [{ id: "l1", variant_id: "v1", product_id: "p1", title: "Cotton Kurta", variant: null, sku: "KURTA-M", quantity: 40, unit_cost_minor: 100000, landed_unit_cost_minor: 107500, received_quantity: 0, defective_quantity: 0, remaining: 40 }],
  receipts: [], warnings: [{ code: "below_moq", variant_id: "v1", moq: 50 }], share_text: "Purchase order PO-1001\nTo: Bhaktapur Weavers\n- Cotton Kurta [KURTA-M]: 40",
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["procurement.read", "procurement.write", "procurement.approve", "automation.read"]);
  features = {};
  api.procurement.supplier.mockResolvedValue(supplierDetail);
  api.automation.policy.mockResolvedValue({ thresholds: { po_minor: 0 }, confidence_threshold: 0.8, enabled_r2: [], r2_actions: [] });
});

describe("landed cost", () => {
  it("shares freight and duty by line value, like the server", () => {
    expect(landedUnitCosts([{ quantity: 40, unit_cost_minor: 100000 }], 300000)).toEqual([107500]);
    expect(landedUnitCosts([{ quantity: 10, unit_cost_minor: 100000 }, { quantity: 10, unit_cost_minor: 300000 }], 40000)).toEqual([101000, 303000]);
    expect(toMinor("1,250.50")).toBe(125050);
    expect(toMinor("")).toBeNull();
    expect(Number.isNaN(toMinor("-5"))).toBe(true);
  });
});

describe("PurchaseOrderForm", () => {
  it("prefills the supplier's price, shows landed cost and the MOQ warning, and sends paisa with a key", async () => {
    const user = userEvent.setup();
    api.catalog.products.mockResolvedValue({ items: [{ id: "p1", title: "Cotton Kurta", status: "active" }] });
    api.catalog.product.mockResolvedValue({ id: "p1", title: "Cotton Kurta", variants: [{ id: "v1", title: "Default", sku: "KURTA-M", status: "active", price: { amount_minor: 245000, currency: "NPR" }, cost: null }] });
    api.procurement.createPurchaseOrder.mockResolvedValue(po({ status: "draft" }));
    const onSaved = vi.fn();
    renderWithI18n(<PurchaseOrderForm suppliers={[{ id: "s1", name: "Bhaktapur Weavers", status: "active" }]} initialSupplierId="s1" onSaved={onSaved} />);
    await waitFor(() => expect(api.procurement.supplier).toHaveBeenCalledWith("s1"));
    await user.type(screen.getByLabelText("Find a product"), "kurta");
    await user.click(await screen.findByRole("button", { name: "Cotton Kurta" }));
    const line = await screen.findByTestId("po-line");
    expect(within(line).getByLabelText("Price per unit (Rs)")).toHaveValue("1000");
    expect(within(line).getByLabelText("Quantity")).toHaveValue("50"); // starts at the MOQ
    await user.clear(within(line).getByLabelText("Quantity"));
    await user.type(within(line).getByLabelText("Quantity"), "40");
    expect(within(line).getByTestId("po-moq-warning")).toHaveTextContent("minimum order of 50");
    await user.type(screen.getByLabelText("Freight (Rs)"), "2000");
    await user.type(screen.getByLabelText("Duty (Rs)"), "1000");
    expect(within(line).getByTestId("po-landed")).toHaveTextContent("1,075");
    expect(screen.getByTestId("po-totals")).toHaveTextContent("43,000");
    await user.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const [body, opts] = api.procurement.createPurchaseOrder.mock.calls[0]!;
    expect(body).toMatchObject({ supplier_id: "s1", lines: [{ variant_id: "v1", quantity: 40, unit_cost_minor: 100000 }], freight_minor: 200000, duty_minor: 100000, other_minor: 0 });
    expect(opts.idempotencyKey).toMatch(/^po-/);
  });

  it("checks quantities and prices before calling the API", async () => {
    const user = userEvent.setup();
    renderWithI18n(<PurchaseOrderForm suppliers={[{ id: "s1", name: "Bhaktapur Weavers", status: "active" }]} onSaved={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("Choose a supplier.")).toBeInTheDocument();
    expect(screen.getByText("Add at least one item.")).toBeInTheDocument();
    expect(api.procurement.createPurchaseOrder).not.toHaveBeenCalled();
  });
});

describe("PurchaseOrderPage", () => {
  it("explains why it waits and lets an approver approve", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    api.procurement.approve.mockResolvedValue(po({ status: "approved", approved_at: new Date().toISOString() }));
    renderWithI18n(<PurchaseOrderPage po={po()} onChange={onChange} reload={vi.fn()} />);
    // The limit loads after the page: wait for it rather than reading the placeholder.
    await waitFor(() => expect(screen.getByTestId("po-approval-reason")).toHaveTextContent("every purchase order needs one"));
    expect(screen.getByText(/Cotton Kurta: Below this supplier's minimum order of 50/)).toBeInTheDocument();
    expect(screen.getByTestId("po-total")).toHaveTextContent("43,000");
    await user.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: "approved" })));
  });

  it("hides approval from people who can't approve", () => {
    perms = new Set(["procurement.read", "procurement.write"]);
    renderWithI18n(<PurchaseOrderPage po={po({ approval_reason: "needs_approver" })} onChange={vi.fn()} reload={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    expect(screen.getByText("Only an owner or manager can approve.")).toBeInTheDocument();
    expect(screen.getByTestId("po-approval-reason")).toHaveTextContent("Waiting for an owner or manager");
  });

  it("validates a delivery, then receives good and damaged units with a lot and a key", async () => {
    const user = userEvent.setup();
    const sent = po({ status: "sent", approval_reason: null, approved_at: new Date().toISOString(), sent_at: new Date().toISOString(), warnings: [] });
    api.procurement.receive.mockResolvedValue({ ...sent, status: "partially_received" });
    const onChange = vi.fn();
    renderWithI18n(<PurchaseOrderPage po={sent} onChange={onChange} reload={vi.fn()} />);
    expect(screen.getByTestId("po-share")).toHaveTextContent("Purchase order PO-1001");
    const form = screen.getByTestId("receive-form");
    await user.click(within(form).getByRole("button", { name: "Receive" }));
    expect(within(form).getByText("Enter what arrived.")).toBeInTheDocument();
    await user.type(within(form).getByLabelText("Good units of Cotton Kurta"), "41");
    await user.click(within(form).getByRole("button", { name: "Receive" }));
    expect(within(form).getByText("Cotton Kurta: only 40 still to come.")).toBeInTheDocument();
    expect(api.procurement.receive).not.toHaveBeenCalled();
    await user.clear(within(form).getByLabelText("Good units of Cotton Kurta"));
    await user.type(within(form).getByLabelText("Good units of Cotton Kurta"), "23");
    await user.type(within(form).getByLabelText("Damaged units of Cotton Kurta"), "2");
    await user.type(within(form).getByLabelText(/Lot or batch code/), "LOT-A");
    await user.click(within(form).getByRole("button", { name: "Receive" }));
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const [id, body, opts] = api.procurement.receive.mock.calls[0]!;
    expect(id).toBe("po1");
    expect(body).toEqual({ lines: [{ po_line_id: "l1", quantity: 23, defective_quantity: 2 }], lot_code: "LOT-A", note: null });
    expect(opts.idempotencyKey).toMatch(/^rcv-/);
  });

  it("shows a server over-receipt error", async () => {
    const user = userEvent.setup();
    const sent = po({ status: "sent", approval_reason: null, warnings: [] });
    api.procurement.receive.mockRejectedValue(new ApiError({ status: 400, code: "receipt_over_order", message: "x", requestId: "r1" }));
    renderWithI18n(<PurchaseOrderPage po={sent} onChange={vi.fn()} reload={vi.fn()} />);
    const form = screen.getByTestId("receive-form");
    await user.type(within(form).getByLabelText("Good units of Cotton Kurta"), "5");
    await user.click(within(form).getByRole("button", { name: "Receive" }));
    expect(await within(form).findByText("That's more than is still to come on this order.")).toBeInTheDocument();
  });
});

describe("PurchaseOrdersView", () => {
  it("shows the upsell and never calls the API without the plan", () => {
    features = { procurement: "no" };
    renderWithI18n(<PurchaseOrdersView />);
    expect(screen.getByText("Purchase orders, receiving and landed cost are on the Pro plan.")).toBeInTheDocument();
    expect(api.procurement.purchaseOrders).not.toHaveBeenCalled();
  });

  it("lists orders with their status", async () => {
    api.procurement.purchaseOrders.mockResolvedValue({ items: [po(), po({ id: "po2", number: "PO-1002", status: "draft", source: "recommendation" })] });
    renderWithI18n(<PurchaseOrdersView />);
    const table = await screen.findByTestId("po-list");
    expect(within(table).getByText("Waiting for approval")).toBeInTheDocument();
    expect(within(table).getByText("From a suggestion")).toBeInTheDocument();
    expect(within(table).getByRole("link", { name: "PO-1001" })).toHaveAttribute("href", "/inventory/purchase-orders/po1");
  });
});

describe("PerformanceCard", () => {
  const perf = (over: Partial<SupplierPerformance> = {}): SupplierPerformance => ({
    supplier_id: "s1", window_days: 180, received_units: 50, avg_unit_cost_minor: 80000, avg_landed_cost_minor: 80000, defect_rate: 0.2, sold_units: 20,
    return_rate: 0.3, quality_return_rate: 0.3, on_time_rate: 0, lead_time_days_avg: 12, lead_time_days_sd: null, fill_rate: 0.8, contribution_per_unit_minor: 100000,
    components: { price: 245000, landed: 80000, defect_cost: 20000, return_cost: 24000, fees_fulfilment: 21000 }, not_included: ["packaging"],
    purchase_orders: 1, lead_samples: 1, basis: "sold", method_version: "spi-1.0", computed_at: new Date().toISOString(), ...over,
  });

  it("shows the economics and what isn't included", () => {
    renderWithI18n(<PerformanceCard p={perf()} currency="NPR" />);
    expect(screen.getByTestId("perf-defect")).toHaveTextContent("20%");
    expect(screen.getByTestId("perf-econ")).toHaveTextContent("−Rs 800");
    expect(screen.getByTestId("perf-contribution")).toHaveTextContent("Rs 1,000");
    expect(screen.getByTestId("perf-not-included")).toHaveTextContent("packaging (set it in Analytics → Profit)");
    expect(screen.getByText("12 days")).toBeInTheDocument();
  });

  it("says so when nothing has sold yet", () => {
    renderWithI18n(<PerformanceCard p={perf({ basis: "no_sales_yet", sold_units: 0, contribution_per_unit_minor: null, not_included: ["no_sales"] })} />);
    expect(screen.getByTestId("perf-no-sales")).toBeInTheDocument();
    expect(screen.getByTestId("perf-contribution")).toHaveTextContent("–");
  });
});

describe("Recommendations: purchasing", () => {
  const rec = (over: Partial<RecommendationView>): RecommendationView =>
    ({
      id: "r1", type: "reorder", status: "open", subject_type: "variant", subject_id: "v1", confidence: 0.8, estimated_impact: {}, evidence: [],
      method_version: "rec-1.0", created_at: new Date().toISOString(), expires_at: null, resolved_at: null, reason: null, outcome: null, outcome_measured_at: null,
      explanation: { what: "reorder", why: "runs_out_before_delivery", vars: { title: "Kurta", variant: "Black XL", days_left: 5, per_day: 3.2, available: 16, incoming: 0, lead_days: 10, safety_days: 3, quantity: 50, supplier: "Bhaktapur Weavers", moq: 50, unit_cost: 90000, chosen_by: "preferred" } },
      action: { type: "create_po_draft", params: {} },
      ...over,
    }) as RecommendationView;

  it("explains a reorder and points to the draft after applying it", async () => {
    const user = userEvent.setup();
    perms = new Set(["analytics.read", "automation.approve"]);
    api.intelligence.recommendations.mockResolvedValueOnce({ items: [rec({})], currency: "NPR" }).mockResolvedValue({ items: [], currency: "NPR" });
    api.intelligence.accept.mockResolvedValue({});
    renderWithI18n(<Recommendations />);
    expect(await screen.findByText("Reorder Kurta (Black XL)")).toBeInTheDocument();
    expect(screen.getByText("Kurta (Black XL) may sell out in 5 days (3.2/day, 16 left; Bhaktapur Weavers takes 10 days). Order 50 (minimum order).")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Apply" }));
    expect(await screen.findByRole("link", { name: "Open draft purchase orders" })).toHaveAttribute("href", "/inventory/purchase-orders?status=draft");
  });

  it("explains a supplier switch in money", async () => {
    perms = new Set(["analytics.read"]);
    api.intelligence.recommendations.mockResolvedValue({
      currency: "NPR",
      items: [
        rec({
          type: "supplier_switch",
          explanation: { what: "switch_supplier", why: "true_economics", vars: { title: "Kurta", variant: null, from: "Cheap Fabrics", to: "Good Fabrics", gain_per_unit: 25000, from_landed: 80000, to_landed: 95000, from_defect_pct: 20, to_defect_pct: 0 } },
          estimated_impact: { gain_per_unit_minor: 25000 },
          action: { type: "set_preferred_supplier", params: {} },
        }),
      ],
    });
    renderWithI18n(<Recommendations />);
    expect(await screen.findByText("Buy Kurta from Good Fabrics")).toBeInTheDocument();
    expect(screen.getByText(/Good Fabrics earns Rs 250 more per unit than Cheap Fabrics/)).toBeInTheDocument();
    expect(screen.getByText("About Rs 250 more profit per unit")).toBeInTheDocument();
  });
});
