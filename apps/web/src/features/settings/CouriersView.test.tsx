import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { CouriersView } from "./CouriersView";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const api = {
  couriers: { list: vi.fn(), providers: vi.fn(), connect: vi.fn(), update: vi.fn(), disconnect: vi.fn(), feeRules: vi.fn(), saveFeeRules: vi.fn(), settings: vi.fn(), updateSettings: vi.fn() },
  intelligence: { courierPerformance: vi.fn(async () => ({ items: [], min_sample: 20, period_days: 90, method_version: "cri-1.0" })) },
  reference: { nepal: vi.fn(async () => ({ provinces: [], districts: [{ code: "kathmandu", name: "Kathmandu", province: "bagmati" }, { code: "kaski", name: "Kaski", province: "gandaki" }], max_ward: 35 })) },
};
let perms = new Set(["fulfillment.read", "settings.manage"]);
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["fulfillment.read", "settings.manage"]);
  api.couriers.list.mockResolvedValue({ items: [] });
  api.couriers.providers.mockResolvedValue({
    items: [
      { code: "manual", name: "Own rider or other courier", sandbox: false, capabilities: ["manual_updates", "cod_collection"], auth_fields: [] },
      { code: "sandbox_courier", name: "Sandbox courier", sandbox: true, capabilities: ["rates", "tracking"], auth_fields: [] },
    ],
  });
  api.couriers.feeRules.mockResolvedValue({ items: [] });
  api.couriers.settings.mockResolvedValue({ notify_customers: true, default_weight_grams: 500, recovery_wait_hours: 24, courier_selection: "smart" });
});

describe("CouriersView", () => {
  it("adds a courier with its pickup address", async () => {
    const u = userEvent.setup();
    api.couriers.connect.mockResolvedValue({ id: "c1" });
    renderWithI18n(<CouriersView />);
    expect(await screen.findByText(en.couriers.empty)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: en.couriers.add }));
    const drawer = await screen.findByRole("dialog");
    await u.selectOptions(within(drawer).getByLabelText(en.couriers.provider), "sandbox_courier");
    await u.type(within(drawer).getByLabelText(en.couriers.pickupName), "Thamel Threads");
    await u.type(within(drawer).getByLabelText(en.couriers.pickupPhone), "9801234567");
    await waitFor(() => expect(within(drawer).getByRole("option", { name: "Kathmandu" })).toBeInTheDocument());
    await u.selectOptions(within(drawer).getByLabelText(en.couriers.pickupDistrict), "kathmandu");
    await u.click(within(drawer).getByRole("button", { name: en.couriers.add }));
    await waitFor(() =>
      expect(api.couriers.connect).toHaveBeenCalledWith({
        provider: "sandbox_courier",
        display_name: null,
        credentials: {},
        pickup: { name: "Thamel Threads", phone: "9801234567", district: "kathmandu", municipality: null, area: null },
      }),
    );
  });

  it("saves delivery charges in paisa, district rules included", async () => {
    const u = userEvent.setup();
    api.couriers.saveFeeRules.mockResolvedValue({ items: [] });
    renderWithI18n(<CouriersView />);
    const form = await screen.findByTestId("fee-rules");
    await u.type(within(form).getByLabelText(`${en.couriers.fees.fee} · ${en.couriers.fees.scope.default}`), "175");
    await u.type(within(form).getByLabelText(`${en.couriers.fees.fee} · ${en.couriers.fees.scope.inside_valley}`), "100");
    await u.type(within(form).getByLabelText(`${en.couriers.fees.freeOver} · ${en.couriers.fees.scope.inside_valley}`), "5000");
    await u.click(within(form).getByRole("button", { name: en.couriers.fees.addDistrict }));
    await waitFor(() => expect(within(form).getByRole("option", { name: "Kaski" })).toBeInTheDocument());
    await u.selectOptions(within(form).getByLabelText(en.couriers.fees.scope.district), "kaski");
    await u.type(within(form).getByLabelText(`${en.couriers.fees.fee} · ${en.couriers.fees.scope.district}`), "150.5");
    await u.click(within(form).getByRole("button", { name: en.couriers.save }));
    await waitFor(() =>
      expect(api.couriers.saveFeeRules).toHaveBeenCalledWith([
        { scope: "default", district: null, fee_minor: 17500, free_over_minor: null },
        { scope: "inside_valley", district: null, fee_minor: 10000, free_over_minor: 500000 },
        { scope: "district", district: "kaski", fee_minor: 15050, free_over_minor: null },
      ]),
    );
  });

  it("is read-only without settings.manage", async () => {
    perms = new Set(["fulfillment.read"]);
    renderWithI18n(<CouriersView />);
    await screen.findByText(en.couriers.empty);
    expect(screen.queryByRole("button", { name: en.couriers.add })).toBeNull();
  });
});
