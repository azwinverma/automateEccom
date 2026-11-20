import { ApiError, type ChannelProvider } from "@commerce-os/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { connectableRows } from "./ChannelsView";
import { MetaDrawer } from "./MetaDrawer";

const channels = { connectMeta: vi.fn() };
const api = { channels };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: () => true }) }));

const m = en.messaging;
const conn = (provider: string, display_name: string) => ({ id: provider, provider, display_name, status: "connected", capabilities: ["content_publish"] });
const TOKEN = "EAAG-page-token-0123456789abcdef";

async function fill(pageId = "102938475610", token = TOKEN) {
  const u = userEvent.setup();
  if (pageId) await u.type(screen.getByLabelText(m.pageId), pageId);
  if (token) await u.type(screen.getByLabelText(m.pageToken), token);
  await u.click(screen.getByRole("button", { name: m.submit }));
  return u;
}

beforeEach(() => vi.clearAllMocks());

describe("Facebook & Instagram connect", () => {
  it("lists the setup steps, says no Meta review is needed and that it's publishing only", () => {
    renderWithI18n(<MetaDrawer open onOpenChange={() => {}} onConnected={() => {}} />);
    expect(screen.getByText(m.metaStep3)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(m.metaNoReview))).toHaveTextContent(m.metaPublishOnly);
    expect(screen.getByLabelText(m.pageToken)).toHaveAttribute("type", "password");
  });

  it("validates the Page ID before calling the API, then connects Page + Instagram", async () => {
    const onConnected = vi.fn();
    const onOpenChange = vi.fn();
    channels.connectMeta.mockResolvedValue({ items: [conn("facebook_page", "Thamel Threads"), conn("instagram", "@thamelthreads")] });
    renderWithI18n(<MetaDrawer open onOpenChange={onOpenChange} onConnected={onConnected} />);
    await fill("thamel");
    expect(channels.connectMeta).not.toHaveBeenCalled();
    expect(screen.getByText(m.pageIdInvalid)).toBeInTheDocument();
    const u = userEvent.setup();
    await u.clear(screen.getByLabelText(m.pageId));
    await u.type(screen.getByLabelText(m.pageId), "102938475610");
    await u.click(screen.getByRole("button", { name: m.submit }));
    await waitFor(() => expect(channels.connectMeta).toHaveBeenCalledWith({ page_id: "102938475610", page_access_token: TOKEN, with_instagram: true }));
    expect(onConnected).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ provider: "instagram" })]));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("says plainly when the Page has no Instagram professional account", async () => {
    channels.connectMeta.mockResolvedValue({ items: [conn("facebook_page", "Thamel Threads")] });
    renderWithI18n(<MetaDrawer open onOpenChange={() => {}} onConnected={() => {}} />);
    await fill();
    expect(await screen.findByTestId("meta-no-instagram")).toHaveTextContent(m.metaNoInstagram);
    expect(screen.getByText("No Instagram professional account is linked to this Page.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: m.done })).toBeInTheDocument();
  });

  it("names a missing permission from the server", async () => {
    channels.connectMeta.mockRejectedValueOnce(new ApiError({ status: 400, code: "permission_missing", message: "x", details: { provider_code: "pages_manage_posts" } }));
    renderWithI18n(<MetaDrawer open onOpenChange={() => {}} onConnected={() => {}} />);
    await fill();
    expect(await screen.findByText("The token is missing a permission: pages_manage_posts. Grant it in Graph API Explorer and generate a new token.")).toBeInTheDocument();
  });
});

describe("available channels list", () => {
  const p = (code: string, name: string, caps: string[] = ["content_publish"]): ChannelProvider => ({ code, name, sandbox: false, capabilities: caps, auth_kind: "api_keys" });

  it("shows Facebook and Instagram as one connect, and TikTok as coming soon only", () => {
    const rows = connectableRows([p("woocommerce", "WooCommerce", ["product_listing"]), p("facebook_page", "Facebook Page"), p("instagram", "Instagram"), p("tiktok", "TikTok"), p("telegram", "Telegram", ["messages"])]);
    expect(rows.map((r) => (r.kind === "soon" ? `soon:${r.code}` : `${r.kind}:${r.provider.code}`))).toEqual([
      "connect:woocommerce",
      "meta:facebook_page",
      "connect:telegram",
      "soon:tiktok",
    ]);
  });
});
