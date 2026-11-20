import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { CampaignsView } from "./CampaignsView";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const api = { campaigns: { templates: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), preview: vi.fn(), setStatus: vi.fn() } };
let perms = new Set<string>();
let plan: "yes" | "no" | "pending" = "yes";
vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ feature: (c: string) => (c === "marketing.campaigns" ? plan : "yes"), api, merchantId: "m1", can: (p: string) => perms.has(p) }),
}));

const c = en.campaigns;
const TEMPLATES = {
  items: [
    { kind: "win_back", message_en: "Namaste {name}! {shop} has new arrivals.", message_ne: "नमस्ते {name}!", default_days: 60 },
    { kind: "repeat_reminder", message_en: "Hi {name}, how is your {product}?", message_ne: "नमस्ते {name}", default_days: 30 },
    { kind: "broadcast", message_en: "Hi {name}, {shop} here.", message_ne: "नमस्ते {name}", default_days: null },
  ],
  placeholders: ["{name}", "{shop}", "{product}"],
};
const campaign = (over: Record<string, unknown> = {}) => ({
  id: "k1",
  name: "Come back",
  kind: "win_back",
  status: "draft",
  days: 60,
  segment: null,
  message_en: "Namaste {name}! {shop} has new arrivals.",
  message_ne: "नमस्ते {name}!",
  daily_limit: 200,
  activated_at: null,
  last_run_at: null,
  completed_at: null,
  created_at: "2026-11-20T10:00:00Z",
  stats: { sent: 0, replied: 0, orders: 0, revenue_minor: 0, skipped: {} },
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["customers.read", "automation.write", "automation.approve"]);
  plan = "yes";
  api.campaigns.templates.mockResolvedValue(TEMPLATES);
  api.campaigns.list.mockResolvedValue({ items: [] });
  api.campaigns.preview.mockResolvedValue({ audience: 3, reachable: 2, unreachable: { no_chat_channel: 1 }, sample_en: "Namaste Sita! Thamel Threads has new arrivals.\n\nReply STOP to stop these messages." });
});

describe("CampaignsView", () => {
  it("without the plan: the rules and an upgrade, never the API", () => {
    plan = "no";
    renderWithI18n(<CampaignsView />);
    expect(screen.getByText(c.upsellTitle)).toBeInTheDocument();
    expect(screen.getByText(c.ruleStop)).toBeInTheDocument();
    expect(api.campaigns.list).not.toHaveBeenCalled();
    expect(api.campaigns.templates).not.toHaveBeenCalled();
  });

  it("states the sending rules up front", async () => {
    renderWithI18n(<CampaignsView />);
    const rules = screen.getByTestId("campaign-rules");
    for (const r of [c.ruleChat, c.ruleStop, c.ruleCap, c.ruleHours, c.ruleResult]) expect(within(rules).getByText(r)).toBeInTheDocument();
    expect(await screen.findByText(c.empty)).toBeInTheDocument();
  });

  it("creates a win-back draft from the template, then shows who it reaches before starting", async () => {
    const u = userEvent.setup();
    api.campaigns.create.mockResolvedValue(campaign());
    api.campaigns.setStatus.mockResolvedValue(campaign({ status: "active", activated_at: "2026-11-20T10:05:00Z" }));
    renderWithI18n(<CampaignsView />);
    await u.click((await screen.findAllByRole("button", { name: c.new }))[0]!);
    const drawer = await screen.findByRole("dialog");
    await waitFor(() => expect(within(drawer).getByLabelText(c.messageEn)).toHaveValue(TEMPLATES.items[0]!.message_en));
    expect(within(drawer).getByLabelText(c.daysWinBack)).toHaveValue("60");
    expect(within(drawer).getByText("{product}")).toBeInTheDocument();
    await u.click(within(drawer).getByRole("button", { name: c.saveDraft }));
    expect(api.campaigns.create).not.toHaveBeenCalled(); // name is required
    await u.type(within(drawer).getByLabelText(c.name), "Come back");
    await u.click(within(drawer).getByRole("button", { name: c.saveDraft }));
    await waitFor(() =>
      expect(api.campaigns.create).toHaveBeenCalledWith({
        name: "Come back",
        kind: "win_back",
        days: 60,
        segment: null,
        message_en: TEMPLATES.items[0]!.message_en,
        message_ne: TEMPLATES.items[0]!.message_ne,
        daily_limit: 200,
      }),
    );
    const preview = await screen.findByTestId("campaign-preview");
    expect(await within(preview).findByText("2 of 3 customers can be reached")).toBeInTheDocument();
    expect(within(preview).getByText(c.reason.no_chat_channel)).toBeInTheDocument();
    expect(within(preview).getByTestId("campaign-sample")).toHaveTextContent("Reply STOP");
    await u.click(screen.getByRole("button", { name: c.start }));
    const confirm = await screen.findByText(c.startBody);
    const dialog = confirm.closest("[role=alertdialog],[role=dialog]") as HTMLElement;
    await u.click(within(dialog).getByRole("button", { name: c.start }));
    await waitFor(() => expect(api.campaigns.setStatus).toHaveBeenCalledWith("k1", "active"));
  });

  it("broadcasts pick an audience instead of days", async () => {
    const u = userEvent.setup();
    api.campaigns.create.mockResolvedValue(campaign({ id: "k2", kind: "broadcast", days: null, segment: "repeat" }));
    renderWithI18n(<CampaignsView />);
    await u.click((await screen.findAllByRole("button", { name: c.new }))[0]!);
    const drawer = await screen.findByRole("dialog");
    await u.click(within(drawer).getByRole("radio", { name: new RegExp(c.kind.broadcast) }));
    expect(within(drawer).queryByLabelText(c.daysWinBack)).toBeNull();
    await u.click(within(drawer).getByRole("radio", { name: c.segment.repeat }));
    await u.type(within(drawer).getByLabelText(c.name), "New stock");
    await u.click(within(drawer).getByRole("button", { name: c.saveDraft }));
    await waitFor(() => expect(api.campaigns.create).toHaveBeenCalledWith(expect.objectContaining({ kind: "broadcast", segment: "repeat", days: null })));
  });

  it("running campaigns show results and skip reasons; staff can't start or pause", async () => {
    const u = userEvent.setup();
    perms = new Set(["customers.read"]);
    api.campaigns.list.mockResolvedValue({
      items: [campaign({ status: "active", stats: { sent: 12, replied: 4, orders: 2, revenue_minor: 490000, skipped: { opted_out: 1, whatsapp_window_closed: 2 } }, last_run_at: "2026-11-20T09:00:00Z" })],
    });
    renderWithI18n(<CampaignsView />);
    const table = await screen.findByTestId("campaigns");
    expect(within(table).getByText("12 sent · 4 replied · 2 orders")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: c.new })).toBeNull();
    await u.click(within(table).getByRole("button", { name: "Come back" }));
    const drawer = await screen.findByRole("dialog");
    const stats = within(drawer).getByTestId("campaign-stats");
    expect(within(stats).getByText("12")).toBeInTheDocument();
    expect(within(drawer).getByText(c.reason.opted_out)).toBeInTheDocument();
    expect(within(drawer).getByText(c.reason.whatsapp_window_closed)).toBeInTheDocument();
    expect(within(drawer).getByText(c.approveOnly)).toBeInTheDocument();
    expect(within(drawer).queryByRole("button", { name: c.pause })).toBeNull();
    expect(within(drawer).getByLabelText(c.messageEn)).toBeDisabled();
  });
});
