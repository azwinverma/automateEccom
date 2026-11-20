import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { AiKeysView } from "./AiKeysView";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const api = { aiCredentials: { list: vi.fn(), create: vi.fn(), rotate: vi.fn(), test: vi.fn(), revoke: vi.fn() } };
let perms = new Set<string>();
let byok: "yes" | "no" | "pending" = "yes";
vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ feature: (c: string) => (c === "ai.byok" ? byok : "yes"), api, merchantId: "m1", can: (p: string) => perms.has(p) }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["ai.credentials.manage"]);
  byok = "yes";
  api.aiCredentials.list.mockResolvedValue({ items: [] });
});

describe("AiKeysView", () => {
  it("on a plan without own keys: explains and offers an upgrade, and never calls the keys API", async () => {
    byok = "no";
    renderWithI18n(<AiKeysView />);
    expect(screen.getByText(en.aiKeys.upsellTitle)).toBeInTheDocument();
    expect(screen.getByText(en.aiKeys.howDefault)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.usage.upgrade })).toBeInTheDocument();
    expect(api.aiCredentials.list).not.toHaveBeenCalled();
  });

  it("lists Claude, ChatGPT and Gemini; adds a key without echoing it", async () => {
    const u = userEvent.setup();
    api.aiCredentials.create.mockResolvedValue({ id: "k1", provider: "anthropic", key_last4: "AbCd", status: "active", fallback_to_platform: false, last_tested_at: null, last_test_ok: null, rotated_at: null, created_at: "2026-11-20T10:00:00Z" });
    renderWithI18n(<AiKeysView />);
    const rows = await screen.findByTestId("ai-keys");
    for (const n of ["Claude (Anthropic)", "ChatGPT (OpenAI)", "Gemini (Google)"]) expect(within(rows).getByText(n)).toBeInTheDocument();
    expect(within(rows).getAllByText(en.aiKeys.usingNivaro)).toHaveLength(3);
    await u.click(within(rows).getByRole("button", { name: "Add key: Claude (Anthropic)" }));
    const drawer = await screen.findByRole("dialog");
    const field = within(drawer).getByLabelText(en.aiKeys.apiKey);
    expect(field).toHaveAttribute("type", "password");
    await u.type(field, "short");
    await u.click(within(drawer).getByRole("button", { name: en.aiKeys.addKey }));
    expect(api.aiCredentials.create).not.toHaveBeenCalled();
    expect(within(drawer).getByText(en.errors.invalid_api_key)).toBeInTheDocument();
    await u.clear(field);
    await u.type(field, "sk-ant-api03-0123456789abcdefAbCd");
    await u.click(within(drawer).getByRole("checkbox", { name: en.aiKeys.fallback }));
    await u.click(within(drawer).getByRole("button", { name: en.aiKeys.addKey }));
    await waitFor(() =>
      expect(api.aiCredentials.create).toHaveBeenCalledWith({ provider: "anthropic", api_key: "sk-ant-api03-0123456789abcdefAbCd", fallback_to_platform: false }),
    );
  });

  it("shows only the last four characters and the last check result", async () => {
    api.aiCredentials.list.mockResolvedValue({
      items: [{ id: "k1", provider: "openai", key_last4: "9xYz", status: "active", fallback_to_platform: true, last_tested_at: "2026-11-20T09:00:00Z", last_test_ok: false, rotated_at: null, created_at: "2026-11-19T10:00:00Z" }],
    });
    renderWithI18n(<AiKeysView />);
    const row = (await screen.findByTestId("ai-keys")).querySelector('[data-provider="openai"]') as HTMLElement;
    expect(within(row).getByText("Your key ••••9xYz")).toBeInTheDocument();
    expect(within(row).getByText(/Failed when checked/)).toBeInTheDocument();
    expect(within(row).getByText(new RegExp(en.aiKeys.fallbackOn))).toBeInTheDocument();
  });

  it("without the permission: says who can, never calls the API", () => {
    perms = new Set();
    renderWithI18n(<AiKeysView />);
    expect(screen.getByText(en.aiKeys.noAccess)).toBeInTheDocument();
    expect(api.aiCredentials.list).not.toHaveBeenCalled();
  });
});
