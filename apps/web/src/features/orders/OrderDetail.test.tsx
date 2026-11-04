import type { OrderDetail } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { OrderDetailView } from "./OrderDetail";

const M = (n: number) => ({ amount_minor: n, currency: "NPR" });
function order(over: Partial<OrderDetail> = {}): OrderDetail {
  return {
    id: "o1", number: 1001, status: "cod_pending", source: "chat", external_number: null, connection_id: null,
    customer: { id: "c1", display_name: "Bikash Rai", phone: "+9779807654321" }, currency: "NPR", total: M(260000),
    payment_method: "cod", payment_status: "cod_pending", needs_review: null, placed_at: "2026-11-04T00:00:00Z", updated_at: "2026-11-04T00:00:00Z",
    version: 3, allowed_transitions: ["ready_to_ship", "cancelled"],
    lines: [{ id: "l1", product_id: "p1", variant_id: "v1", sku: "DHK-XL", title: "Dhaka Kurta", variant_title: "XL", unit_price: M(245000), quantity: 1, cancelled_quantity: 0, line_total: M(245000), matched: true }],
    totals: { subtotal: M(245000), discount: M(0), delivery_fee: M(15000), tax: M(0), total: M(260000) },
    shipping: { recipient_name: "Bikash Rai", phone: "+9779807654321", province: "gandaki", district: "kaski", district_name: "Kaski", municipality: "Pokhara", ward: 6, area: "Lakeside", landmark: null, text: null, completeness: 1 },
    notes: null, cancel_reason: null, conversation_id: "cv1", confirmed_at: null, cancelled_at: null,
    ...over,
  };
}

const orders = { get: vi.fn(), timeline: vi.fn(async () => ({ items: [] })), payments: vi.fn(async () => ({ items: [] })), transition: vi.fn(), recordPayment: vi.fn(), addNote: vi.fn(), cancelLines: vi.fn(), startOnlinePayment: vi.fn(), switchToCod: vi.fn(), verifyPayment: vi.fn() };
const shipments = { forOrder: vi.fn(async () => ({ items: [] })) };
const couriers = { list: vi.fn(async () => ({ items: [] })), rates: vi.fn() };
const api = { orders, shipments, couriers };
let perms = new Set(["orders.read", "orders.write", "orders.cancel", "payments.read", "payments.write"]);
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["orders.read", "orders.write", "orders.cancel", "payments.read", "payments.write"]);
  orders.timeline.mockResolvedValue({ items: [] });
  orders.payments.mockResolvedValue({ items: [] });
});

describe("OrderDetailView", () => {
  it("offers exactly the server's next steps and sends the version", async () => {
    const u = userEvent.setup();
    orders.get.mockResolvedValue(order());
    orders.transition.mockResolvedValue(order({ status: "ready_to_ship", allowed_transitions: ["shipped", "cancelled"], version: 4 }));
    renderWithI18n(<OrderDetailView id="o1" />);
    const btn = await screen.findByRole("button", { name: en.orders.actions.to.ready_to_ship });
    expect(screen.queryByRole("button", { name: en.orders.actions.to.delivered })).toBeNull();
    await u.click(btn);
    await waitFor(() => expect(orders.transition).toHaveBeenCalledWith("o1", "ready_to_ship", { expected_version: 3 }));
    expect(await screen.findByRole("button", { name: en.orders.actions.to.shipped })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.orders.detail.openChat })).toHaveAttribute("href", "/inbox?c=cv1");
  });

  it("hides cancel without orders.cancel", async () => {
    perms.delete("orders.cancel");
    orders.get.mockResolvedValue(order());
    renderWithI18n(<OrderDetailView id="o1" />);
    await screen.findByRole("button", { name: en.orders.actions.to.ready_to_ship });
    expect(screen.queryByRole("button", { name: en.orders.actions.to.cancelled })).toBeNull();
  });

  it("records an outside payment for the exact total, reusing its key on retry", async () => {
    const u = userEvent.setup();
    orders.get.mockResolvedValue(order({ payment_method: "prepaid", status: "payment_pending", payment_status: "pending", allowed_transitions: ["cancelled"] }));
    orders.recordPayment.mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ id: "pay1" });
    renderWithI18n(<OrderDetailView id="o1" />);
    const form = await screen.findByRole("form", { name: en.orders.pay.recordTitle });
    await u.type(within(form).getByLabelText(en.orders.pay.reference), "ES-77812");
    await u.click(within(form).getByRole("button", { name: en.orders.pay.record }));
    await u.click(within(form).getByRole("button", { name: en.orders.pay.record }));
    await waitFor(() => expect(orders.recordPayment).toHaveBeenCalledTimes(2));
    const [a, b] = orders.recordPayment.mock.calls;
    expect(a![1]).toEqual({ amount_minor: 260000, method: "esewa", reference: "ES-77812" });
    expect(a![2].idempotencyKey).toBe(b![2].idempotencyKey);
  });

  it("shows review flags and the order journey", async () => {
    orders.get.mockResolvedValue(order({ needs_review: "stock_short" }));
    renderWithI18n(<OrderDetailView id="o1" />);
    expect(await screen.findByText(en.orders.review.stock_short)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: en.orders.detail.journey })).toBeInTheDocument();
  });
});
