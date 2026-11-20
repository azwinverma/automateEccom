import { ApiError } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { connectFlow } from "@/lib/channels/connect";
import { renderWithI18n } from "@/test/render";
import { MessagingDrawer } from "./MessagingDrawer";

const channels = { connectMessaging: vi.fn(), webhookSetup: vi.fn() };
const api = { channels };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: () => true }) }));

const m = en.messaging;
const telegram = { code: "telegram", name: "Telegram", sandbox: false, capabilities: ["messages"], auth_kind: "api_keys" as const, secret_fields: ["bot_token"], optional_fields: [], manual_webhook: false };
const whatsapp = {
  code: "whatsapp_cloud",
  name: "WhatsApp Business",
  sandbox: false,
  capabilities: ["messages"],
  auth_kind: "api_keys" as const,
  secret_fields: ["access_token", "app_secret"],
  optional_fields: ["phone_number_id", "business_account_id"],
  manual_webhook: true,
};
const conn = (over: Record<string, unknown> = {}) => ({ id: "c1", provider: "telegram", display_name: "Telegram @thamel_bot", status: "connected", capabilities: ["messages"], ...over });

beforeEach(() => vi.clearAllMocks());

describe("messaging channels", () => {
  it("routes Telegram and WhatsApp to the messaging flow", () => {
    expect(connectFlow("telegram", "api_keys")).toBe("messaging");
    expect(connectFlow("whatsapp_cloud")).toBe("messaging");
    expect(connectFlow("woocommerce", "api_keys")).toBe("keys");
    expect(connectFlow("sandbox_channel", "oauth")).toBe("oauth");
  });

  it("Telegram: BotFather steps, a hidden token field, and one call with the token", async () => {
    const u = userEvent.setup();
    const onConnected = vi.fn();
    const onOpenChange = vi.fn();
    channels.connectMessaging.mockResolvedValue(conn());
    renderWithI18n(<MessagingDrawer provider={telegram} onOpenChange={onOpenChange} onConnected={onConnected} />);
    expect(screen.getByText(m.telegramStep1)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: m.submit }));
    expect(channels.connectMessaging).not.toHaveBeenCalled();
    const token = screen.getByLabelText(m.field.bot_token);
    expect(token).toHaveAttribute("type", "password");
    await u.type(token, " 7012345678:AAH-token ");
    await u.click(screen.getByRole("button", { name: m.submit }));
    await waitFor(() => expect(channels.connectMessaging).toHaveBeenCalledWith({ provider: "telegram", fields: { bot_token: "7012345678:AAH-token" } }));
    expect(onConnected).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("WhatsApp: needs the phone number ID, explains the 24-hour rule, then shows the webhook values to paste", async () => {
    const u = userEvent.setup();
    channels.connectMessaging.mockResolvedValue(conn({ id: "w1", provider: "whatsapp_cloud", display_name: "WhatsApp +977 980-0000000" }));
    channels.webhookSetup.mockResolvedValue({ callback_url: "https://api.nivaro.app/webhooks/whatsapp_cloud/w1", verify_token: "vt-123", fields: ["messages"] });
    renderWithI18n(<MessagingDrawer provider={whatsapp} onOpenChange={() => {}} onConnected={() => {}} />);
    expect(screen.getByText(m.whatsappRule)).toBeInTheDocument();
    expect(screen.getByLabelText(new RegExp(m.field.business_account_id))).toBeInTheDocument();
    await u.type(screen.getByLabelText(m.field.access_token), "EAAG-token-0123456789");
    await u.type(screen.getByLabelText(m.field.app_secret), "meta-secret");
    await u.click(screen.getByRole("button", { name: m.submit }));
    expect(channels.connectMessaging).not.toHaveBeenCalled(); // phone number ID still missing
    const phone = screen.getByLabelText(m.field.phone_number_id);
    expect(phone).toHaveAttribute("type", "text");
    await u.type(phone, "1098765432");
    await u.click(screen.getByRole("button", { name: m.submit }));
    await waitFor(() =>
      expect(channels.connectMessaging).toHaveBeenCalledWith({
        provider: "whatsapp_cloud",
        fields: { access_token: "EAAG-token-0123456789", app_secret: "meta-secret", phone_number_id: "1098765432" },
      }),
    );
    const setup = await screen.findByTestId("webhook-setup");
    expect(within(setup).getByTestId("callback-url")).toHaveTextContent("https://api.nivaro.app/webhooks/whatsapp_cloud/w1");
    expect(within(setup).getByTestId("verify-token")).toHaveTextContent("vt-123");
    expect(within(setup).getByRole("button", { name: `${m.copy}: ${m.verifyToken}` })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: m.done })).toBeInTheDocument();
  });

  it("names server-side missing fields and other errors in plain words", async () => {
    const u = userEvent.setup();
    channels.connectMessaging.mockRejectedValueOnce(new ApiError({ status: 409, code: "account_in_use", message: "x", requestId: "r1" }));
    renderWithI18n(<MessagingDrawer provider={telegram} onOpenChange={() => {}} onConnected={() => {}} />);
    await u.type(screen.getByLabelText(m.field.bot_token), "7012345678:AAH-token");
    await u.click(screen.getByRole("button", { name: m.submit }));
    expect(await screen.findByText(en.errors.account_in_use)).toBeInTheDocument();
  });
});
