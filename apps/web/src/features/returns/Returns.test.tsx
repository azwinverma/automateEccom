import type { OrderDetail, ReturnDetail, Returnable } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { exceptionSummaryKey, exceptionTarget } from "@/lib/exceptions";
import { renderWithI18n } from "@/test/render";
import { ReturnDetailView } from "./ReturnDetail";
import { ReturnsPanel } from "./ReturnsPanel";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), usePathname: () => "/returns", useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const M = (n: number) => ({ amount_minor: n, currency: "NPR" });
const order = { id: "o1", number: 1001, status: "delivered", version: 5, currency: "NPR" } as unknown as OrderDetail;
const returnable: Returnable = {
  order_id: "o1",
  order_status: "delivered",
  delivered_at: new Date().toISOString(),
  deadline: new Date(Date.now() + 5 * 86400000).toISOString(),
  currency: "NPR",
  refundable_minor: 260000,
  policy: { window_days: 7, allow_refund: true, allow_exchange: true, evidence_reasons: ["quality_defect"], return_shipping_fee_minor: 0, auto_approve: false, auto_refund_max_minor: 0, notes: null },
  lines: [
    { order_line_id: "l1", title: "Dhaka Kurta", variant_title: "M", sku: "DHK-M", returnable_quantity: 2, unit_refund_minor: 245000, final_sale: false, exchange_options: [{ variant_id: "vL", title: "L", available: 3 }] },
  ],
};
const detail = (over: Partial<ReturnDetail> = {}): ReturnDetail => ({
  id: "r1", number: "R-1001-1", order_id: "o1", order_number: 1001, customer_name: "Bikash Rai", status: "requested", resolution: "refund", source: "seller",
  eligible: true, signals: [], refund_due: M(245000), return_shipping_fee_minor: 0, customer_pays_shipping: true, created_at: new Date().toISOString(),
  decided_at: null, received_at: null, closed_at: null, exchange_order_id: null,
  lines: [{ id: "rl1", order_line_id: "l1", title: "Dhaka Kurta", variant_title: "M", sku: "DHK-M", quantity: 1, unit_refund_minor: 245000, reason: "size_small", reason_note: null, evidence_asset_ids: [], exchange: null, condition: null, restocked_quantity: 0, inspection_note: null }],
  eligibility: { checks: [{ code: "order_delivered", ok: true, soft: false }, { code: "within_window", ok: true, soft: true }], policy_window_days: 7 },
  override_reason: null, rejection_reason: null, note: null, refunds: [], pickup: null, refundable_minor: 260000, actions: ["approve", "reject", "cancel"],
  ...over,
});

const api = {
  returns: { forOrder: vi.fn(), returnable: vi.fn(), check: vi.fn(), create: vi.fn(), get: vi.fn(), approve: vi.fn(), reject: vi.fn(), cancel: vi.fn(), received: vi.fn(), inspect: vi.fn(), bookPickup: vi.fn() },
  refunds: { create: vi.fn(), approve: vi.fn(), reject: vi.fn(), retry: vi.fn() },
  couriers: { list: vi.fn(async () => ({ items: [] })) },
};
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["returns.read", "returns.write", "returns.approve", "refunds.read", "refunds.create", "fulfillment.write"]);
  api.returns.forOrder.mockResolvedValue({ items: [] });
  api.returns.returnable.mockResolvedValue(returnable);
  api.returns.check.mockResolvedValue({ eligible: false, can_request: true, checks: [{ code: "evidence", ok: false, soft: true, items: ["Dhaka Kurta"] }] });
});

describe("ReturnsPanel", () => {
  it("starts a return with the live policy check and a stable key across retries", async () => {
    const u = userEvent.setup();
    api.returns.create.mockRejectedValueOnce(new Error("offline")).mockResolvedValue(detail());
    const onChanged = vi.fn();
    renderWithI18n(<ReturnsPanel order={order} onChanged={onChanged} />);
    await u.click(await screen.findByRole("button", { name: en.returns.start }));
    const form = await screen.findByTestId("start-return");
    await u.selectOptions(within(form).getByLabelText(en.returns.reasonField), "quality_defect");
    expect(within(form).getByLabelText(en.returns.qtyOf.replace("{title}", "Dhaka Kurta (M)").replace("{max}", "2"))).toHaveValue(1);
    expect(await within(form).findByText(new RegExp(en.returns.check.evidence))).toBeInTheDocument(); // soft warning shown, still allowed
    const create = screen.getByRole("button", { name: en.returns.create });
    await u.click(create);
    await u.click(create);
    await waitFor(() => expect(api.returns.create).toHaveBeenCalledTimes(2));
    const [a, b] = api.returns.create.mock.calls;
    expect(a![1]).toEqual({ resolution: "refund", lines: [{ order_line_id: "l1", quantity: 1, reason: "quality_defect", reason_note: null }] });
    expect(a![2].idempotencyKey).toBe(b![2].idempotencyKey);
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("exchange needs a replacement choice", async () => {
    const u = userEvent.setup();
    api.returns.create.mockResolvedValue(detail({ resolution: "exchange" }));
    renderWithI18n(<ReturnsPanel order={order} onChanged={vi.fn()} />);
    await u.click(await screen.findByRole("button", { name: en.returns.start }));
    const form = await screen.findByTestId("start-return");
    await u.selectOptions(within(form).getByLabelText(en.returns.resolutionField), "exchange");
    await u.selectOptions(within(form).getByLabelText(en.returns.reasonField), "size_small");
    const create = screen.getByRole("button", { name: en.returns.create });
    expect(create).toBeDisabled();
    await u.selectOptions(within(form).getByLabelText(en.returns.exchangeFor), "vL");
    await u.click(create);
    await waitFor(() => expect(api.returns.create.mock.calls[0]![1].lines[0]).toMatchObject({ exchange_variant_id: "vL" }));
  });

  it("is hidden before delivery", () => {
    renderWithI18n(<ReturnsPanel order={{ ...order, status: "shipped" }} onChanged={vi.fn()} />);
    expect(screen.queryByTestId("returns-panel")).toBeNull();
  });
});

describe("ReturnDetailView", () => {
  it("approving outside policy asks for a reason; warning signs are shown as facts", async () => {
    const u = userEvent.setup();
    api.returns.get.mockResolvedValue(
      detail({ eligible: false, eligibility: { checks: [{ code: "within_window", ok: false, soft: true }], policy_window_days: 7 }, signals: [{ code: "frequent_returns", count: 2, days: 90 }] }),
    );
    api.returns.approve.mockResolvedValue(detail({ status: "approved", actions: ["book_pickup", "mark_received", "cancel"] }));
    renderWithI18n(<ReturnDetailView id="r1" />);
    expect(await screen.findByTestId("return-signals")).toHaveTextContent("2 other returns in 90 days");
    await u.click(screen.getByRole("button", { name: en.returns.actions.approve }));
    const dialog = (await screen.findAllByRole("dialog")).at(-1)!;
    await u.type(within(dialog).getByLabelText(en.returns.overrideReason), "Loyal customer");
    await u.click(within(dialog).getByRole("button", { name: en.returns.actions.approve }));
    await waitFor(() => expect(api.returns.approve).toHaveBeenCalledWith("r1", "Loyal customer"));
    expect(await screen.findByRole("button", { name: en.returns.actions.mark_received })).toBeInTheDocument();
  });

  it("inspection can't restock damaged items", async () => {
    const u = userEvent.setup();
    api.returns.get.mockResolvedValue(detail({ status: "received", actions: ["inspect"] }));
    api.returns.inspect.mockResolvedValue(detail({ status: "inspected", actions: ["refund"] }));
    renderWithI18n(<ReturnDetailView id="r1" />);
    await u.click(await screen.findByRole("button", { name: en.returns.actions.inspect }));
    const form = await screen.findByTestId("inspect-form");
    const restock = within(form).getByLabelText(en.returns.actions.restockOf.replace("{title}", "Dhaka Kurta (M)").replace("{max}", "1"));
    expect(restock).toHaveValue(1);
    await u.selectOptions(within(form).getByLabelText(en.returns.actions.conditionOf.replace("{title}", "Dhaka Kurta (M)")), "damaged");
    expect(restock).toBeDisabled();
    await u.click(screen.getByRole("button", { name: en.returns.actions.saveInspection }));
    await waitFor(() => expect(api.returns.inspect).toHaveBeenCalledWith("r1", [{ line_id: "rl1", condition: "damaged", restock: 0, note: null }]));
  });

  it("refund defaults to what's due, needs a reference for manual methods, and says when it waits for approval", async () => {
    const u = userEvent.setup();
    const pendingRefund = { id: "f1", order_id: "o1", return_id: "r1", amount: M(245000), method: "esewa" as const, provider: null, provider_refund_id: null, reference: "ES-1234", status: "pending_approval" as const, reason: null, failure_code: null, created_at: new Date().toISOString(), approved_at: null, completed_at: null };
    api.returns.get.mockResolvedValueOnce(detail({ status: "inspected", actions: ["refund"] })).mockResolvedValue(detail({ status: "inspected", actions: ["refund"], refunds: [pendingRefund] }));
    api.refunds.create.mockResolvedValue(pendingRefund);
    renderWithI18n(<ReturnDetailView id="r1" />);
    await u.click(await screen.findByRole("button", { name: en.returns.actions.refund }));
    const form = await screen.findByTestId("refund-form");
    expect(within(form).getByLabelText(en.returns.refund.amount)).toHaveValue("2450");
    const send = screen.getByRole("button", { name: en.returns.refund.send });
    expect(send).toBeDisabled(); // eSewa needs the transfer reference
    await u.type(within(form).getByLabelText(en.returns.refund.reference), "ES-1234");
    await u.click(send);
    await waitFor(() =>
      expect(api.refunds.create).toHaveBeenCalledWith("o1", { amount_minor: 245000, method: "esewa", return_id: "r1", reference: "ES-1234" }, expect.objectContaining({ idempotencyKey: expect.any(String) })),
    );
    expect(await within(await screen.findByTestId("refunds")).findByText(en.returns.refund.statuses.pending_approval)).toBeInTheDocument();
    // Without refunds.approve the seller can't approve it themselves.
    expect(screen.queryByRole("button", { name: en.returns.refund.approve })).toBeNull();
  });

  it("renders in Nepali", async () => {
    api.returns.get.mockResolvedValue(detail());
    renderWithI18n(<ReturnDetailView id="r1" />, { locale: "ne" });
    expect(await screen.findByText(ne.returns.reason.size_small)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: ne.returns.actions.approve })).toBeInTheDocument();
  });
});

describe("return exceptions", () => {
  const rec = (type: string, action: string, details: Record<string, unknown>, rtype = "return") =>
    ({ id: `${type}:x`, type, severity: "high", resource: { type: rtype, id: "r1" }, occurred_at: null, action, details }) as never;
  it("link to the return", () => {
    expect(exceptionTarget(rec("return_requested", "review_return", {}))).toEqual({ kind: "link", href: "/returns/r1", label: "review_return" });
    expect(exceptionTarget(rec("refund_above_threshold", "approve_refund", { return_id: "r9" }, "refund"))).toMatchObject({ href: "/returns/r9" });
    expect(exceptionSummaryKey(rec("return_requested", "review_return", { return_number: "R-1001-1", number: 1001 }))).toEqual({ key: "returnRequested", vars: { number: "R-1001-1", order: 1001 } });
  });
});
