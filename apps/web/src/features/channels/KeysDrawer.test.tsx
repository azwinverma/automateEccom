import { ApiError } from "@commerce-os/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { renderWithI18n } from "@/test/render";
import { KeysDrawer } from "./ChannelsView";

const channels = { connectWithKeys: vi.fn() };
const api = { channels };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: () => true }) }));

const k = en.channels.keys;
const woo = { code: "woocommerce", name: "WooCommerce" };

async function fill(url: string, key = "ck_1234567890abcdef", secret = "cs_1234567890abcdef") {
  const user = userEvent.setup();
  if (url) await user.type(screen.getByLabelText(k.storeUrl), url);
  if (key) await user.type(screen.getByLabelText(k.consumerKey), key);
  if (secret) await user.type(screen.getByLabelText(k.consumerSecret), secret);
  await user.click(screen.getByRole("button", { name: k.submit }));
}

beforeEach(() => vi.clearAllMocks());

describe("WooCommerce keys form", () => {
  it("shows the help text and validates before calling the API", async () => {
    renderWithI18n(<KeysDrawer provider={woo} reconnect={false} onOpenChange={() => {}} onConnected={() => {}} />);
    expect(screen.getByText(k.help)).toBeInTheDocument();
    await fill("http://shop.np", "short", "");
    expect(screen.getByText(k.err.https_required)).toBeInTheDocument();
    expect(screen.getByText(k.err.too_short)).toBeInTheDocument();
    expect(screen.getByText(k.err.required)).toBeInTheDocument();
    expect(channels.connectWithKeys).not.toHaveBeenCalled();
  });

  it("sends trimmed keys and a normalised store URL", async () => {
    const onConnected = vi.fn();
    channels.connectWithKeys.mockResolvedValueOnce({ id: "c1", display_name: "Thamel Threads" });
    renderWithI18n(<KeysDrawer provider={woo} reconnect={false} onOpenChange={() => {}} onConnected={onConnected} />);
    await fill("https://thamelthreads.com.np/");
    await waitFor(() => expect(onConnected).toHaveBeenCalled());
    expect(channels.connectWithKeys).toHaveBeenCalledWith({
      provider: "woocommerce",
      store_url: "https://thamelthreads.com.np",
      consumer_key: "ck_1234567890abcdef",
      consumer_secret: "cs_1234567890abcdef",
    });
  });

  it.each([
    ["invalid_store_url", 400],
    ["invalid_api_keys", 400],
    ["store_unreachable", 400],
  ])("maps %s to localized copy", async (code, status) => {
    channels.connectWithKeys.mockRejectedValueOnce(new ApiError({ status, code, message: "x", requestId: "r1" }));
    renderWithI18n(<KeysDrawer provider={woo} reconnect={false} onOpenChange={() => {}} onConnected={() => {}} />);
    await fill("https://thamelthreads.com.np");
    expect(await screen.findByText(en.errors[code as "invalid_api_keys"])).toBeInTheDocument();
  });

  it("explains a currency mismatch with both currencies", async () => {
    channels.connectWithKeys.mockRejectedValueOnce(
      new ApiError({ status: 409, code: "currency_mismatch", message: "x", details: { store_currency: "USD", merchant_currency: "NPR" } }),
    );
    renderWithI18n(<KeysDrawer provider={woo} reconnect={false} onOpenChange={() => {}} onConnected={() => {}} />, { locale: "ne" });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(ne.channels.keys.storeUrl), "https://thamelthreads.com.np");
    await user.type(screen.getByLabelText(ne.channels.keys.consumerKey), "ck_1234567890abcdef");
    await user.type(screen.getByLabelText(ne.channels.keys.consumerSecret), "cs_1234567890abcdef");
    await user.click(screen.getByRole("button", { name: ne.channels.keys.submit }));
    expect(await screen.findByText(ne.channels.keys.currencyTitle)).toBeInTheDocument();
    expect(screen.getByText(/USD/)).toHaveTextContent("NPR");
  });

  it("offers plan options on usage_limit_reached for channels", async () => {
    channels.connectWithKeys.mockRejectedValueOnce(
      new ApiError({ status: 402, code: "usage_limit_reached", message: "x", details: { resource: "channels", options: ["upgrade"] } }),
    );
    renderWithI18n(<KeysDrawer provider={woo} reconnect onOpenChange={() => {}} onConnected={() => {}} />);
    expect(screen.getByText(k.reconnectNote)).toBeInTheDocument();
    await fill("https://thamelthreads.com.np");
    expect(await screen.findByRole("link", { name: en.usage.upgrade })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: en.usage.buyCredits })).not.toBeInTheDocument();
  });
});
