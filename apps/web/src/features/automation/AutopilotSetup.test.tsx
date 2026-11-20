import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { AutopilotSetup, AutopilotSetupCard } from "./AutopilotSetup";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const api = { automation: { setup: vi.fn(), applySetup: vi.fn() } };
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

const s = en.autopilotSetup;
const WORKFLOWS = [
  { code: "book_courier_when_packed", name: "Book the courier when an order is packed", status: "active" },
  { code: "failed_delivery_followup", name: "Follow up failed deliveries", status: null },
  { code: "review_request_after_delivery", name: "Ask for a review after delivery", status: null },
  { code: "thank_first_order", name: "Thank customers for their first order", status: null },
  { code: "low_stock_alert", name: "Tell me when stock runs low", status: "paused" },
];
const readiness = (over: Record<string, unknown> = {}) => ({
  steps: [
    { key: "chat", state: "done", detail: "Telegram @thamel_bot, Thamel Threads", action: null },
    { key: "sales_agent", state: "todo", detail: "The AI Sales Agent answers price, stock and delivery questions and takes orders", action: null, mode: "assisted" },
    { key: "payments", state: "partial", detail: "Cash on delivery works now; connect eSewa or Khalti for online payment", action: "/settings/payments" },
    { key: "delivery", state: "partial", detail: "Own riders", action: "/settings/couriers" },
    { key: "posting", state: "todo", detail: "Turn on automatic posting", action: "/content" },
    { key: "workflows", state: "todo", detail: "1 of 5 recommended automations on", action: "/automation", workflows: WORKFLOWS },
    { key: "campaigns", state: "blocked", detail: "Start a win-back campaign", action: "/campaigns" },
  ],
  done: 1,
  total: 7,
  needs_reconnect: [] as string[],
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["automation.read", "automation.approve"]);
  api.automation.setup.mockResolvedValue(readiness());
});

describe("Set up autopilot", () => {
  it("shows the selling path in order with state, own copy, the seller's own details and links", async () => {
    renderWithI18n(<AutopilotSetup />);
    const steps = await screen.findByTestId("setup-steps");
    const items = within(steps).getAllByRole("listitem").filter((li) => li.hasAttribute("data-key"));
    expect(items.map((li) => li.getAttribute("data-key"))).toEqual(["chat", "sales_agent", "payments", "delivery", "posting", "workflows", "campaigns"]);
    const chat = items[0]!;
    expect(within(chat).getByText(s.step.chat)).toBeInTheDocument();
    expect(within(chat).getByText(s.state.done)).toBeInTheDocument();
    expect(within(chat).getByText("Telegram @thamel_bot, Thamel Threads")).toBeInTheDocument(); // the API's specific line
    const pay = items[2]!;
    expect(within(pay).getByText(s.stepHelp.payments)).toBeInTheDocument();
    expect(within(pay).getByRole("link", { name: `${s.open}: ${s.step.payments}` })).toHaveAttribute("href", "/settings/payments");
    // English to-do text from the API isn't shown; our own copy is.
    expect(within(items[4]!).queryByText("Turn on automatic posting")).toBeNull();
    expect(within(items[5]!).getByText(s.workflow.failed_delivery_followup)).toBeInTheDocument();
    expect(screen.getByText("1 of 7 ready")).toBeInTheDocument();
  });

  it("warns about accounts that need reconnecting", async () => {
    api.automation.setup.mockResolvedValue(readiness({ needs_reconnect: ["Instagram @thamelthreads"] }));
    renderWithI18n(<AutopilotSetup />);
    expect(await screen.findByText("Reconnect: Instagram @thamelthreads")).toBeInTheDocument();
  });

  it("turns on recommended automations after confirming, and says what changed and what was skipped", async () => {
    const u = userEvent.setup();
    api.automation.applySetup.mockResolvedValue({
      ...readiness({ done: 4 }),
      changed: ["mode:smart", "workflow:failed_delivery_followup", "posting"],
      skipped: [{ item: "campaigns", reason: "plan" }],
    });
    renderWithI18n(<AutopilotSetup />);
    const panel = await screen.findByTestId("setup-apply");
    expect(within(panel).getByRole("radio", { name: /Assisted/ })).toBeChecked(); // the shop's current mode
    await u.click(within(panel).getByRole("radio", { name: /Smart/ }));
    expect(within(panel).getByText(s.modeHelp.autopilot)).toBeInTheDocument();
    const summary = within(panel).getByTestId("setup-summary");
    for (const w of WORKFLOWS) expect(within(summary).getByText(w.name)).toBeInTheDocument();
    expect(within(summary).getByText("Mode: Smart")).toBeInTheDocument();
    await u.click(within(panel).getByRole("checkbox", { name: s.campaigns }));
    expect(within(summary).queryByText(s.summaryCampaign)).toBeNull();
    await u.click(within(panel).getByRole("button", { name: s.apply }));
    const confirm = (await screen.findByText(s.confirmBody)).closest("[role=alertdialog],[role=dialog]") as HTMLElement;
    await u.click(within(confirm).getByRole("button", { name: s.apply }));
    await waitFor(() => expect(api.automation.applySetup).toHaveBeenCalledWith({ mode: "smart", posting: true, campaigns: false }));
    const result = await screen.findByTestId("setup-result");
    expect(within(result).getByText("Mode set to Smart")).toBeInTheDocument();
    expect(within(result).getByText(s.workflow.failed_delivery_followup)).toBeInTheDocument();
    expect(within(result).getByText(s.changedPosting)).toBeInTheDocument();
    expect(within(result).getByText("Win-back campaign: Not in your plan")).toBeInTheDocument();
  });

  it("people who can't approve see the path but not the switch", async () => {
    perms = new Set(["automation.read"]);
    renderWithI18n(<AutopilotSetup />);
    expect(await screen.findByText(s.approveOnly)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: s.apply })).toBeNull();
  });

  it("Home card shows until everything is ready, and never calls the API without access", async () => {
    const { unmount } = renderWithI18n(<AutopilotSetupCard />);
    const card = await screen.findByTestId("setup-card");
    expect(within(card).getByRole("link", { name: s.cta })).toHaveAttribute("href", "/automation/setup");
    unmount();
    api.automation.setup.mockResolvedValue(readiness({ done: 7, total: 7 }));
    const done = renderWithI18n(<AutopilotSetupCard />);
    await waitFor(() => expect(api.automation.setup).toHaveBeenCalledTimes(2));
    expect(screen.queryByTestId("setup-card")).toBeNull();
    done.unmount();
    perms = new Set();
    renderWithI18n(<AutopilotSetupCard />);
    expect(api.automation.setup).toHaveBeenCalledTimes(2);
  });
});
