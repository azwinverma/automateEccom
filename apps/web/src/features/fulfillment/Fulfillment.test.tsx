import type { CodOverview, CodSettlement, CourierOptions, OrderDetail, Shipment } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { exceptionSummaryKey, exceptionTarget } from "@/lib/exceptions";
import { renderWithI18n } from "@/test/render";
import { CodView } from "./CodView";
import { DeliveryPanel } from "./DeliveryPanel";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), usePathname: () => "/fulfillment/cod", useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const M = (n: number) => ({ amount_minor: n, currency: "NPR" });
const order = (over: Partial<OrderDetail> = {}): OrderDetail =>
  ({
    id: "o1", number: 1001, status: "ready_to_ship", currency: "NPR", version: 4, total: M(260000), payment_method: "cod", payment_status: "cod_pending",
    shipping: { district: "kaski" }, ...over,
  }) as unknown as OrderDetail;

const options: CourierOptions = {
  weight_grams: 500,
  cod_amount_minor: 260000,
  options: [
    { courier_account_id: "own", provider: "manual", display_name: "Own rider", is_default: false, service_code: null, price: null, eta_days_min: null, eta_days_max: null, cod_supported: true, manual: true, recommended: false },
    { courier_account_id: "sbx", provider: "sandbox_courier", display_name: "Sandbox courier", is_default: true, service_code: "standard", price: M(17500), eta_days_min: 3, eta_days_max: 5, cod_supported: true, manual: false, recommended: true },
  ],
  unavailable: [],
  recommendation: { courier_account_id: "sbx", service_code: "standard", reason: "default_courier", method: "rules" },
};

const shipment = (over: Partial<Shipment> = {}): Shipment => ({
  id: "s1", order_id: "o1", order_number: 1001, customer_name: "Bikash Rai", destination_district: "kaski", destination_district_name: "Kaski",
  courier_account_id: "sbx", provider: "sandbox_courier", courier_name: "Sandbox courier", manual: false, service_code: "standard",
  status: "booked", tracking_number: "SBX1234ABCD", has_provider_label: false, weight_grams: 500, cod_amount: M(260000), charge: M(17500),
  eta_days_min: 3, eta_days_max: 5, attempt_count: 0, pickup_reference: null, created_at: new Date().toISOString(), pickup_requested_at: null,
  picked_up_at: null, delivered_at: null, returned_at: null, return_received_at: null, last_event_at: new Date().toISOString(), stuck: false,
  actions: ["request_pickup", "cancel", "refresh"], events: [], attempts: [], ...over,
});

const api = {
  shipments: { forOrder: vi.fn(), book: vi.fn(), requestPickup: vi.fn(), reattempt: vi.fn(), setStatus: vi.fn(), cancel: vi.fn(), refresh: vi.fn(), returnToSender: vi.fn(), receivedBack: vi.fn(), setTracking: vi.fn() },
  couriers: { list: vi.fn(), rates: vi.fn() },
  cod: { overview: vi.fn(), awaiting: vi.fn(), settlements: vi.fn(), settlement: vi.fn(), acceptLine: vi.fn(), confirm: vi.fn(), recheck: vi.fn(), recordCash: vi.fn(), importFile: vi.fn() },
  devCourier: { simulate: vi.fn(), settlement: vi.fn() },
};
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["fulfillment.read", "fulfillment.write", "payments.read", "payments.write", "inventory.adjust"]);
  api.couriers.list.mockResolvedValue({ items: [{ id: "sbx", provider: "sandbox_courier", manual: false }] });
  api.couriers.rates.mockResolvedValue(options);
});

describe("DeliveryPanel", () => {
  it("preselects the rule-based recommendation, says why, and books with a stable key", async () => {
    const u = userEvent.setup();
    api.shipments.forOrder.mockResolvedValue({ items: [] });
    api.shipments.book.mockRejectedValueOnce(new Error("offline")).mockResolvedValue(shipment());
    const onChanged = vi.fn();
    renderWithI18n(<DeliveryPanel order={order()} onChanged={onChanged} />);
    const rec = await screen.findByRole("radio", { name: /Sandbox courier/ });
    expect(rec).toBeChecked();
    expect(screen.getByText(en.fulfillment.panel.why.default_courier)).toBeInTheDocument();
    expect(screen.getByText(en.fulfillment.panel.collect.replace("{amount}", "Rs 2,600"))).toBeInTheDocument();
    const book = screen.getByRole("button", { name: en.fulfillment.panel.book });
    await u.click(book);
    await u.click(book);
    await waitFor(() => expect(api.shipments.book).toHaveBeenCalledTimes(2));
    const [a, b] = api.shipments.book.mock.calls;
    expect(a![1]).toEqual({ courier_account_id: "sbx", service_code: "standard", weight_grams: 500 });
    expect(a![2].idempotencyKey).toBe(b![2].idempotencyKey); // a retry can't book twice
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("own rider asks for the rider's name and an optional tracking number", async () => {
    const u = userEvent.setup();
    api.shipments.forOrder.mockResolvedValue({ items: [] });
    api.shipments.book.mockResolvedValue(shipment({ manual: true }));
    renderWithI18n(<DeliveryPanel order={order()} onChanged={vi.fn()} />);
    await u.click(await screen.findByRole("radio", { name: /Own rider/ }));
    await u.type(screen.getByLabelText(en.fulfillment.panel.courierName), "Ram");
    await u.click(screen.getByRole("button", { name: en.fulfillment.panel.book }));
    await waitFor(() => expect(api.shipments.book.mock.calls[0]![1]).toMatchObject({ courier_account_id: "own", courier_name: "Ram", tracking_number: null }));
  });

  it("no courier yet: points to Settings instead of an empty form", async () => {
    api.shipments.forOrder.mockResolvedValue({ items: [] });
    api.couriers.list.mockResolvedValue({ items: [] });
    renderWithI18n(<DeliveryPanel order={order()} onChanged={vi.fn()} />);
    expect(await screen.findByRole("link", { name: en.fulfillment.connectCourier })).toHaveAttribute("href", "/settings/couriers");
  });

  it("failed delivery shows the reason, what the customer said, and requests a reattempt", async () => {
    const u = userEvent.setup();
    const failed = shipment({
      status: "delivery_failed",
      attempt_count: 1,
      actions: ["reattempt", "return_to_sender"],
      attempts: [
        { id: "a1", attempt_no: 1, failure_reason: "customer_unreachable", failed_at: new Date().toISOString(), recovery_status: "customer_replied", customer_contacted_at: new Date().toISOString(), customer_reply: "After 3pm please", customer_replied_at: new Date().toISOString(), reattempt_requested_at: null, reattempt_note: null, reattempt_by: null, escalated_at: null, resolved_at: null, resolution: null },
      ],
      events: [
        { id: "e1", status: "booked", raw_status: null, description: null, location: null, failure_reason: null, source: "seller", applied: true, occurred_at: new Date().toISOString() },
        { id: "e2", status: "in_transit", raw_status: null, description: null, location: null, failure_reason: null, source: "courier_webhook", applied: false, occurred_at: new Date().toISOString() },
      ],
    });
    api.shipments.forOrder.mockResolvedValue({ items: [failed] });
    api.shipments.reattempt.mockResolvedValue(shipment({ status: "reattempt_requested", actions: ["return_to_sender"] }));
    renderWithI18n(<DeliveryPanel order={order({ status: "delivery_failed" })} onChanged={vi.fn()} />);
    const attempt = await screen.findByTestId("delivery-attempt");
    expect(within(attempt).getByText(new RegExp(en.fulfillment.reason.customer_unreachable))).toBeInTheDocument();
    expect(within(attempt).getAllByText(/After 3pm please/).length).toBeGreaterThan(0);
    expect(screen.getByText(new RegExp(en.fulfillment.lateUpdate))).toBeInTheDocument(); // late courier event, not applied
    await u.click(screen.getByRole("button", { name: en.fulfillment.actions.reattempt }));
    const drawer = await screen.findByRole("dialog");
    await u.type(within(drawer).getByLabelText(en.fulfillment.actions.reattemptNote), "Call before coming");
    await u.click(within(drawer).getByRole("button", { name: en.fulfillment.actions.reattempt }));
    await waitFor(() => expect(api.shipments.reattempt).toHaveBeenCalledWith("s1", { note: "Call before coming" }));
  });

  it("own-rider status update needs a reason when the delivery failed", async () => {
    const u = userEvent.setup();
    api.shipments.forOrder.mockResolvedValue({ items: [shipment({ manual: true, provider: "manual", status: "picked_up", actions: ["update_status", "set_tracking"] })] });
    api.shipments.setStatus.mockResolvedValue(shipment({ status: "delivery_failed", actions: [] }));
    renderWithI18n(<DeliveryPanel order={order({ status: "shipped" })} onChanged={vi.fn()} />);
    await u.click(await screen.findByRole("button", { name: en.fulfillment.actions.update_status }));
    const drawer = await screen.findByRole("dialog");
    await u.selectOptions(within(drawer).getByLabelText(en.fulfillment.actions.statusField), "delivery_failed");
    const save = within(drawer).getByRole("button", { name: en.couriers.save });
    expect(save).toBeDisabled();
    await u.selectOptions(within(drawer).getByLabelText(en.fulfillment.actions.reasonField), "address_incorrect");
    await u.click(save);
    await waitFor(() => expect(api.shipments.setStatus).toHaveBeenCalledWith("s1", { status: "delivery_failed", failure_reason: "address_incorrect", note: null }));
  });

  it("is hidden without fulfillment.read", () => {
    perms = new Set();
    api.shipments.forOrder.mockResolvedValue({ items: [] });
    renderWithI18n(<DeliveryPanel order={order()} onChanged={vi.fn()} />);
    expect(screen.queryByTestId("delivery-panel")).toBeNull();
  });
});

describe("CodView", () => {
  const overview: CodOverview = {
    currency: "NPR",
    outstanding: { count: 2, amount_minor: 500000 },
    pending_settlement: { count: 3, amount_minor: 750000 },
    settled: { count: 1, amount_minor: 100000 },
    failed_delivery: { count: 0, amount_minor: 0 },
    return_exposure: { count: 0, amount_minor: 0 },
    awaiting_by_age: { d0_7: { count: 2, amount_minor: 500000 }, d8_14: { count: 0, amount_minor: 0 }, d15_plus: { count: 1, amount_minor: 250000 } },
    awaiting_by_courier: [],
    settlements_needing_review: 1,
    received_last_30_days: { count: 1, amount_minor: 90000 },
  };
  const settlement: CodSettlement = {
    id: "st1", courier_account_id: "sbx", courier_name: "Sandbox courier", provider: "sandbox_courier", source: "courier_api", reference: "SBX-STMT-1",
    status: "needs_review", currency: "NPR", collected_minor: 450000, fees_minor: 20000, net_minor: 430000, expected_minor: 500000, line_count: 2, issue_count: 1,
    period_start: null, period_end: null, created_at: new Date().toISOString(), confirmed_at: null, bank_reference: null,
    lines: [
      { id: "l1", tracking_number: "SBXA", shipment_id: "s1", order_id: "o1", order_number: 1001, collected_minor: 250000, fee_minor: 10000, expected_minor: 250000, match_status: "matched", accepted: false, accept_reason: null, note: null },
      { id: "l2", tracking_number: "SBXB", shipment_id: "s2", order_id: "o2", order_number: 1002, collected_minor: 200000, fee_minor: 10000, expected_minor: 250000, match_status: "amount_mismatch", accepted: false, accept_reason: null, note: null },
    ],
  };

  beforeEach(() => {
    api.cod.overview.mockResolvedValue(overview);
    api.cod.awaiting.mockResolvedValue({ items: [] });
    api.cod.settlements.mockResolvedValue({ items: [settlement] });
    api.cod.settlement.mockResolvedValue(settlement);
  });

  it("shows cash with couriers by age, and a statement that doesn't match can't be confirmed until accepted", async () => {
    const u = userEvent.setup();
    api.cod.acceptLine.mockResolvedValue({ ...settlement, status: "reconciled", issue_count: 0, lines: settlement.lines!.map((l) => ({ ...l, accepted: l.id === "l2", accept_reason: l.id === "l2" ? "Rest next week" : null })) });
    api.cod.confirm.mockResolvedValue({ ...settlement, status: "confirmed", issue_count: 0 });
    renderWithI18n(<CodView />);
    const ov = await screen.findByTestId("cod-overview");
    expect(within(ov).getByText("Rs 7,500")).toBeInTheDocument(); // 5,000 + 2,500 waiting
    expect(within(ov).getByRole("img").getAttribute("aria-label")).toContain(en.cod.age.d15_plus);
    await u.click(await screen.findByRole("button", { name: "SBX-STMT-1" }));
    const detail = await screen.findByTestId("settlement-detail");
    expect(within(detail).getByText(en.cod.match.amount_mismatch)).toBeInTheDocument();
    expect(within(detail).getByText(en.cod.expected.replace("{amount}", "Rs 2,500"))).toBeInTheDocument();
    expect(screen.getByTestId("confirm-settlement")).toBeDisabled();
    await u.click(within(detail).getByRole("button", { name: en.cod.accept }));
    const dialog = await screen.findByRole("alertdialog").catch(() => screen.getAllByRole("dialog").at(-1)!);
    await u.type(within(dialog).getByLabelText(en.cod.acceptReason), "Rest next week");
    await u.click(within(dialog).getByRole("button", { name: en.cod.accept }));
    await waitFor(() => expect(api.cod.acceptLine).toHaveBeenCalledWith("l2", "Rest next week"));
    await waitFor(() => expect(screen.getByTestId("confirm-settlement")).toBeEnabled());
  });

  it("renders in Nepali", async () => {
    renderWithI18n(<CodView />, { locale: "ne" });
    expect(await screen.findByText(ne.cod.withCouriers)).toBeInTheDocument();
    expect(screen.getByText(ne.cod.status.needs_review)).toBeInTheDocument();
  });
});

describe("delivery exceptions", () => {
  const rec = (type: string, action: string, details: Record<string, unknown>) =>
    ({ id: `${type}:x`, type, severity: "high", resource: { type: "shipment", id: "s1" }, occurred_at: null, action, details }) as never;

  it("route to the order's delivery panel, the COD page or courier settings", () => {
    expect(exceptionTarget(rec("delivery_failed", "call_customer", { order_id: "o1" }))).toEqual({ kind: "link", href: "/orders/o1#delivery", label: "call_customer" });
    expect(exceptionTarget(rec("cod_settlement_mismatch", "review_settlement", {}))).toMatchObject({ href: "/fulfillment/cod" });
    expect(exceptionTarget(rec("courier_error", "reconnect_courier", {}))).toMatchObject({ href: "/settings/couriers" });
    expect(exceptionSummaryKey(rec("delivery_failed", "request_reattempt", { number: 1001, recovery_status: "customer_replied" })).key).toBe("deliveryReplied");
    expect(exceptionSummaryKey(rec("shipment_stuck", "contact_courier", { number: 7, days_since_update: 5 }))).toEqual({ key: "shipmentStuck", vars: { number: 7, days: 5 } });
  });
});
