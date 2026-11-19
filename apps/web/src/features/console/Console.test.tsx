import type { AdminMerchantDetail, Me } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithI18n } from "@/test/render";
import { ConsoleGate } from "./ConsoleShell";
import { C } from "./copy";
import { MerchantDetail } from "./MerchantsView";

let me: Me;
const admin = {
  merchant: vi.fn(),
  setStatus: vi.fn(),
  createOverride: vi.fn(),
  endOverride: vi.fn(),
  grantCredits: vi.fn(),
};
const api = { admin };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, me, merchantId: null, signOut: vi.fn() }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }), usePathname: () => "/console/merchants" }));

function user(over: Partial<Me["user"]> = {}, mfa = false): Me {
  return {
    user: { id: "u1", email: "ops@nivaro.example", full_name: "Ops", phone: null, locale: "en", email_verified: true, mfa_enabled: false, is_platform_staff: false, ...over },
    memberships: [],
    session: { mfa },
  };
}

function detail(over: Partial<AdminMerchantDetail["merchant"]> = {}): AdminMerchantDetail {
  return {
    merchant: { id: "m1", name: "Thamel Threads", slug: "thamel-threads", status: "active", created_at: "2026-11-01T00:00:00Z", country: "NP", currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "ne", ...over },
    members: 1,
    team: [{ user_id: "u2", email: "sita@example.com", full_name: "Sita", role: "owner", status: "active", mfa_enabled: false, last_login_at: null }],
    plan: "starter",
    subscription_status: "trialing",
    usage: [
      { resource: "ai_text_generations", period: "month", kind: "consumable", overage_policy: "credits", included: true, limit: 300, used: 270, reserved: 0, burst: null, alert_level: "85" },
      { resource: "products", period: "lifetime", kind: "gauge", overage_policy: "block", included: true, limit: 100, used: 3, reserved: 0, burst: null, alert_level: null },
    ] as AdminMerchantDetail["usage"],
    credit_balance: 0,
    connections: [],
    overrides: [],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  admin.merchant.mockResolvedValue(detail());
});

describe("ConsoleGate", () => {
  it("hides the Console from non-staff (looks like a missing page)", () => {
    me = user();
    renderWithI18n(<ConsoleGate>secret</ConsoleGate>);
    expect(screen.queryByText("secret")).toBeNull();
    expect(screen.getByText(C.gate.notFoundTitle)).toBeInTheDocument();
  });
  it("asks staff without a two-step sign-in to set it up or sign in again", () => {
    me = user({ is_platform_staff: true });
    const { unmount } = renderWithI18n(<ConsoleGate>secret</ConsoleGate>);
    expect(screen.getByText(C.gate.mfaTitle)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: C.gate.setUpMfa })).toHaveAttribute("href", "/settings/security");
    unmount();
    me = user({ is_platform_staff: true, mfa_enabled: true });
    renderWithI18n(<ConsoleGate>secret</ConsoleGate>);
    expect(screen.getByRole("button", { name: C.gate.signInAgain })).toBeInTheDocument();
  });
  it("lets MFA-verified staff in", () => {
    me = user({ is_platform_staff: true, mfa_enabled: true }, true);
    renderWithI18n(<ConsoleGate>secret</ConsoleGate>);
    expect(screen.getByText("secret")).toBeInTheDocument();
  });
});

describe("MerchantDetail", () => {
  beforeEach(() => {
    me = user({ is_platform_staff: true, mfa_enabled: true }, true);
  });

  it("shows plan, usage alert and team", async () => {
    renderWithI18n(<MerchantDetail id="m1" />);
    const usage = await screen.findByTestId("merchant-usage");
    expect(within(usage).getByText("270 of 300")).toBeInTheDocument();
    expect(within(usage).getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("sita@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: C.merchants.auditLink })).toHaveAttribute("href", "/console/audit?merchant_id=m1");
  });

  it("suspends with a reason", async () => {
    const u = userEvent.setup();
    admin.setStatus.mockResolvedValue({ id: "m1", status: "suspended" });
    renderWithI18n(<MerchantDetail id="m1" />);
    const form = await screen.findByRole("form", { name: C.merchants.suspend });
    await u.type(within(form).getByLabelText(C.common.reason), "Chargeback review");
    await u.click(within(form).getByRole("button", { name: C.merchants.suspend }));
    await waitFor(() => expect(admin.setStatus).toHaveBeenCalledWith("m1", "suspended", "Chargeback review"));
  });

  it("gauge overrides are lifetime, consumables monthly", async () => {
    const u = userEvent.setup();
    admin.createOverride.mockResolvedValue({});
    renderWithI18n(<MerchantDetail id="m1" />);
    const form = await screen.findByRole("form", { name: C.merchants.addOverride });
    await u.selectOptions(within(form).getByLabelText(C.merchants.resource), "products");
    await u.type(within(form).getByLabelText(C.merchants.limit), "500");
    await u.type(within(form).getByLabelText(C.common.reason), "Pilot shop");
    await u.click(within(form).getByRole("button", { name: C.merchants.addOverride }));
    await waitFor(() =>
      expect(admin.createOverride).toHaveBeenCalledWith("m1", { resource_code: "products", period: "lifetime", limit_value: 500, reason: "Pilot shop", expires_at: null }),
    );
  });

  it("a retried credit grant reuses its idempotency key; a new grant gets a new one", async () => {
    const u = userEvent.setup();
    admin.grantCredits.mockRejectedValueOnce(new Error("network")).mockResolvedValue({ transaction_id: "t1", balance: 50 });
    renderWithI18n(<MerchantDetail id="m1" />);
    const form = await screen.findByRole("form", { name: C.merchants.grant });
    await u.type(within(form).getByLabelText(C.merchants.amount), "50");
    await u.type(within(form).getByLabelText(C.common.reason), "Outage goodwill");
    const submit = within(form).getByRole("button", { name: C.merchants.grant });
    await u.click(submit);
    await waitFor(() => expect(admin.grantCredits).toHaveBeenCalledTimes(1));
    await u.click(submit);
    await waitFor(() => expect(admin.grantCredits).toHaveBeenCalledTimes(2));
    const [k1, k2] = admin.grantCredits.mock.calls.map((c) => c[1].idempotency_key);
    expect(k1).toBe(k2);
    await waitFor(() => expect(within(form).getByLabelText(C.merchants.amount)).toHaveValue(null)); // cleared for the next grant
  });
});
