import { ApiError } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { PENDING_KEY } from "@/lib/channels/oauth";
import { renderWithI18n } from "@/test/render";
import { MetaCallback } from "./MetaCallback";
import { MetaDrawer } from "./MetaDrawer";

let search = new URLSearchParams();
const replace = vi.fn();
vi.mock("next/navigation", async (orig) => ({
  ...(await orig<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace }),
  useSearchParams: () => search,
}));

const channels = { connectMeta: vi.fn(), metaStart: vi.fn(), metaPages: vi.fn(), metaConnect: vi.fn() };
const api = { channels };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: () => true }) }));

const m = en.messaging;
const assign = vi.fn();
const realLocation = window.location;

beforeEach(() => {
  vi.clearAllMocks();
  window.sessionStorage.clear();
  Object.defineProperty(window, "location", { configurable: true, value: { ...realLocation, origin: "https://app.nivaro.test", assign } });
});
afterEach(() => {
  Object.defineProperty(window, "location", { configurable: true, value: realLocation });
});

describe("one-click Facebook & Instagram", () => {
  it("leads with Continue with Facebook and keeps the own-app method as an advanced option", async () => {
    const u = userEvent.setup();
    channels.metaStart.mockResolvedValue({ authorize_url: "https://www.facebook.com/v21.0/dialog/oauth?client_id=1&state=st-0123456789abcdefghij" });
    renderWithI18n(<MetaDrawer open oneClick onOpenChange={() => {}} onConnected={() => {}} />);
    const lead = screen.getByTestId("meta-one-click");
    expect(within(lead).getByText(m.metaRecommended)).toBeInTheDocument();
    expect(screen.queryByLabelText(m.pageToken)).not.toBeVisible();
    await u.click(screen.getByText(m.metaAdvanced));
    expect(screen.getByLabelText(m.pageToken)).toBeVisible();
    await u.click(within(lead).getByRole("button", { name: m.metaOneClick }));
    await waitFor(() => expect(channels.metaStart).toHaveBeenCalledWith("https://app.nivaro.test/settings/channels/meta"));
    expect(assign).toHaveBeenCalledWith(expect.stringContaining("facebook.com"));
    const pending = JSON.parse(window.sessionStorage.getItem(PENDING_KEY)!);
    expect(pending).toMatchObject({ provider: "meta", state: "st-0123456789abcdefghij", returnTo: "/settings/channels" });
  });

  it("without one-click: the pasted-token form only", () => {
    renderWithI18n(<MetaDrawer open onOpenChange={() => {}} onConnected={() => {}} />);
    expect(screen.queryByTestId("meta-one-click")).toBeNull();
    expect(screen.getByLabelText(m.pageToken)).toBeVisible();
  });

  it("callback: exchanges once, lets the seller pick the Page and Instagram, then connects", async () => {
    const u = userEvent.setup();
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify({ provider: "meta", state: "st-1", reconnectId: null, returnTo: "/settings/channels", startedAt: Date.now() }));
    search = new URLSearchParams({ code: "abc", state: "st-1" });
    channels.metaPages.mockResolvedValue({
      selection: "sel-0123456789abcdefghij",
      pages: [
        { id: "111111", name: "Thamel Threads", instagram: "thamelthreads" },
        { id: "222222", name: "Patan Brass", instagram: null },
      ],
    });
    channels.metaConnect.mockResolvedValue({ items: [{ id: "c1", provider: "facebook_page", display_name: "Thamel Threads", capabilities: ["content_publish", "messages"] }] });
    renderWithI18n(<MetaCallback />);
    const form = await screen.findByTestId("meta-pages");
    expect(channels.metaPages).toHaveBeenCalledTimes(1);
    expect(channels.metaPages).toHaveBeenCalledWith({ state: "st-1", code: "abc" });
    expect(within(form).getByText("Instagram @thamelthreads")).toBeInTheDocument();
    expect(within(form).getByText(m.metaPageNoIg)).toBeInTheDocument();
    expect(within(form).getByRole("checkbox", { name: m.withInstagram })).toBeChecked();
    await u.click(within(form).getByRole("radio", { name: /Patan Brass/ }));
    expect(within(form).queryByRole("checkbox", { name: m.withInstagram })).toBeNull(); // no Instagram to connect
    await u.click(within(form).getByRole("radio", { name: /Thamel Threads/ }));
    await u.click(within(form).getByRole("button", { name: m.metaConnectPage }));
    await waitFor(() => expect(channels.metaConnect).toHaveBeenCalledWith({ selection: "sel-0123456789abcdefghij", page_id: "111111", with_instagram: true }));
    expect(replace).toHaveBeenCalledWith("/settings/channels");
  });

  it("callback: an expired selection says to start again", async () => {
    const u = userEvent.setup();
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify({ provider: "meta", state: "st-2", reconnectId: null, returnTo: "/settings/channels", startedAt: Date.now() }));
    search = new URLSearchParams({ code: "abc", state: "st-2" });
    channels.metaPages.mockResolvedValue({ selection: "sel-x", pages: [{ id: "111111", name: "Thamel Threads", instagram: null }] });
    channels.metaConnect.mockRejectedValue(new ApiError({ status: 409, code: "meta_selection_expired", message: "x" }));
    renderWithI18n(<MetaCallback />);
    await u.click(await screen.findByRole("button", { name: m.metaConnectPage }));
    expect(await screen.findByText(en.errors.meta_selection_expired)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: m.metaStartAgain })).toHaveAttribute("href", "/settings/channels");
  });

  it("callback: a state that didn't start here is refused without calling the API", async () => {
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify({ provider: "meta", state: "st-3", reconnectId: null, returnTo: "/settings/channels", startedAt: Date.now() }));
    search = new URLSearchParams({ code: "abc", state: "forged" });
    renderWithI18n(<MetaCallback />);
    expect(await screen.findByText(en.channels.callbackInvalid)).toBeInTheDocument();
    expect(channels.metaPages).not.toHaveBeenCalled();
  });

  it("inbox send errors for Meta have plain explanations", () => {
    expect(en.errors.messaging_not_approved).toMatch(/Meta approves/);
    expect(en.errors.outside_reply_window).toMatch(/24 hours/);
  });
});
