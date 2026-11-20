import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { PaymentsView } from "./PaymentsView";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const api = {
  paymentGateways: { providers: vi.fn(), list: vi.fn(), connect: vi.fn(), test: vi.fn(), makeDefault: vi.fn(), disconnect: vi.fn() },
};
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

const PROVIDERS = [
  { code: "khalti", name: "Khalti", secret_fields: ["secret_key"], public_fields: [], modes: ["test", "live"] },
  { code: "esewa", name: "eSewa", secret_fields: ["secret_key"], public_fields: ["product_code"], modes: ["test", "live"] },
];
const gw = (over: Record<string, unknown> = {}) => ({
  id: "g1",
  provider: "khalti",
  name: "Khalti",
  mode: "test",
  status: "active",
  is_default: true,
  public_id: null,
  secret_hint: "••••9e8b",
  verified: true,
  last_error_code: null,
  last_payment_at: null,
  connected_at: "2026-11-20T10:00:00Z",
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["payments.read", "payments.manage"]);
  api.paymentGateways.providers.mockResolvedValue({ items: PROVIDERS });
  api.paymentGateways.list.mockResolvedValue({ items: [] });
});

describe("PaymentsView", () => {
  it("explains how keys and payments are handled, and connects eSewa with its merchant code", async () => {
    const u = userEvent.setup();
    api.paymentGateways.connect.mockResolvedValue(gw({ id: "g2", provider: "esewa", name: "eSewa", verified: null, public_id: "EPAYTEST" }));
    renderWithI18n(<PaymentsView />);
    expect(screen.getByText(en.payments.howKeys)).toBeInTheDocument();
    expect(screen.getByText(en.payments.howVerify)).toBeInTheDocument();
    expect(screen.getByText(en.payments.howRefunds)).toBeInTheDocument();
    expect(await screen.findByText(en.payments.empty)).toBeInTheDocument();
    const cards = await screen.findByTestId("gateway-providers");
    await u.click(within(cards).getByRole("button", { name: "Connect eSewa" }));
    const drawer = await screen.findByRole("dialog");
    // Nothing is sent until the required fields are filled.
    await u.click(within(drawer).getByRole("button", { name: en.payments.connect }));
    expect(api.paymentGateways.connect).not.toHaveBeenCalled();
    expect(within(drawer).getByText(en.errors.product_code_required)).toBeInTheDocument();
    await u.type(within(drawer).getByLabelText(en.payments.productCode), "EPAYTEST");
    const secret = within(drawer).getByLabelText(en.payments.secretKey);
    expect(secret).toHaveAttribute("type", "password");
    expect(secret).toHaveAttribute("autocomplete", "off");
    await u.type(secret, "  esewa-secret-0042  ");
    await u.click(within(drawer).getByRole("radio", { name: new RegExp(en.payments.modeLive) }));
    await u.click(within(drawer).getByRole("button", { name: en.payments.connect }));
    await waitFor(() =>
      expect(api.paymentGateways.connect).toHaveBeenCalledWith({ provider: "esewa", mode: "live", secret_key: "esewa-secret-0042", public_id: "EPAYTEST", is_default: false }),
    );
  });

  it("shows key states plainly: accepted, rejected, or proven by the first payment", async () => {
    api.paymentGateways.list.mockResolvedValue({
      items: [gw(), gw({ id: "g2", provider: "esewa", name: "eSewa", is_default: false, verified: null, public_id: "EPAYTEST" })],
    });
    renderWithI18n(<PaymentsView />);
    const rows = await screen.findByTestId("gateways");
    const khalti = within(rows).getByText("Khalti").closest("tr")!;
    expect(within(khalti).getByText(en.payments.statusAccepted)).toBeInTheDocument();
    expect(within(khalti).getByText("Key ••••9e8b")).toBeInTheDocument();
    expect(within(khalti).getByText(en.payments.default)).toBeInTheDocument();
    const esewa = within(rows).getByText("eSewa").closest("tr")!;
    expect(within(esewa).getByText(en.payments.statusUnproven)).toBeInTheDocument();
    expect(within(esewa).getByText(en.payments.statusUnprovenHelp)).toBeInTheDocument();
    // eSewa can't be checked in advance, so there is no "check keys" button for it.
    expect(within(esewa).queryByRole("button", { name: /Check keys/ })).toBeNull();
    expect(within(khalti).getByRole("button", { name: "Check keys: Khalti" })).toBeInTheDocument();
  });

  it("disconnects after confirmation", async () => {
    const u = userEvent.setup();
    api.paymentGateways.list.mockResolvedValue({ items: [gw()] });
    api.paymentGateways.disconnect.mockResolvedValue(undefined);
    renderWithI18n(<PaymentsView />);
    await u.click(await screen.findByRole("button", { name: "Disconnect: Khalti" }));
    const dialog = await screen.findByRole("alertdialog").catch(() => screen.findByRole("dialog"));
    expect(within(dialog).getByText(en.payments.disconnectBody)).toBeInTheDocument();
    await u.click(within(dialog).getByRole("button", { name: en.payments.disconnect }));
    await waitFor(() => expect(api.paymentGateways.disconnect).toHaveBeenCalledWith("g1"));
    await waitFor(() => expect(screen.getByText(en.payments.empty)).toBeInTheDocument());
  });

  it("people without payments.manage can see gateways but not change them", async () => {
    perms = new Set(["payments.read"]);
    api.paymentGateways.list.mockResolvedValue({ items: [gw()] });
    renderWithI18n(<PaymentsView />);
    expect(await screen.findByText(en.payments.manageOnly)).toBeInTheDocument();
    await screen.findByTestId("gateways");
    expect(screen.queryByRole("button", { name: /Disconnect/ })).toBeNull();
    expect(screen.queryByTestId("gateway-providers")).toBeNull();
  });
});
