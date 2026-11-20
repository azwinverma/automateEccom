import { ApiError } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { AutopostPanel } from "./AutopostPanel";
import { SourceTag } from "./PostDrawer";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const api = { content: { getAutopost: vi.fn(), putAutopost: vi.fn() } };
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

const a = en.autopost;
const settings = (over: Record<string, unknown> = {}) => ({
  enabled: false,
  connection_ids: [],
  kind: "post",
  require_approval: true,
  available: [
    { id: "fb", provider: "facebook_page", display_name: "Thamel Threads" },
    { id: "ig", provider: "instagram", display_name: "@thamelthreads" },
  ],
  default_hour: 19,
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["content.read", "content.approve", "channels.manage"]);
  api.content.getAutopost.mockResolvedValue(settings());
});

describe("Automatic posting", () => {
  it("explains what gets posted and when, then saves the choice", async () => {
    const u = userEvent.setup();
    api.content.putAutopost.mockImplementation(async (b) => settings(b));
    renderWithI18n(<AutopostPanel />);
    const panel = screen.getByTestId("autopost");
    expect(within(panel).getByText(a.how1)).toBeInTheDocument();
    expect(within(panel).getByText(a.how2)).toBeInTheDocument();
    expect(within(panel).getByText(/7:00 pm/i)).toBeInTheDocument();
    await u.click(await within(panel).findByRole("checkbox", { name: a.enabled }));
    await u.click(within(panel).getByRole("button", { name: a.save }));
    expect(api.content.putAutopost).not.toHaveBeenCalled(); // pick an account first
    expect(within(panel).getByRole("alert")).toHaveTextContent(a.pickAccount);
    await u.click(within(panel).getByRole("checkbox", { name: /@thamelthreads/ }));
    expect(within(panel).getByText(a.approvalOn)).toBeInTheDocument();
    await u.click(within(panel).getByRole("checkbox", { name: a.approval }));
    expect(within(panel).getByText(a.approvalOff)).toBeInTheDocument();
    await u.click(within(panel).getByRole("button", { name: a.save }));
    await waitFor(() => expect(api.content.putAutopost).toHaveBeenCalledWith({ enabled: true, connection_ids: ["ig"], kind: "post", require_approval: false }));
    expect(await within(panel).findByText(a.statusOn)).toBeInTheDocument();
  });

  it("with no account that can post: points to connecting Facebook & Instagram instead of the form", async () => {
    api.content.getAutopost.mockResolvedValue(settings({ available: [] }));
    renderWithI18n(<AutopostPanel />);
    expect(await screen.findByText(a.noAccounts)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: a.connect })).toHaveAttribute("href", "/settings/channels");
    expect(screen.queryByRole("button", { name: a.save })).toBeNull();
  });

  it("read-only for people who can't approve content", async () => {
    perms = new Set(["content.read"]);
    renderWithI18n(<AutopostPanel />);
    expect(await screen.findByText(a.readOnly)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: a.enabled })).toBeDisabled();
    expect(screen.queryByRole("button", { name: a.save })).toBeNull();
  });

  it("shows server errors in plain words", async () => {
    const u = userEvent.setup();
    api.content.getAutopost.mockResolvedValue(settings({ enabled: true, connection_ids: ["fb"] }));
    api.content.putAutopost.mockRejectedValueOnce(new ApiError({ status: 400, code: "connection_cannot_post", message: "x" }));
    renderWithI18n(<AutopostPanel />);
    await u.click(await screen.findByRole("button", { name: a.save }));
    expect(await screen.findByText(en.errors.connection_cannot_post)).toBeInTheDocument();
  });

  it("labels automatic posts as Automatic", () => {
    renderWithI18n(<SourceTag source="autopost" />);
    expect(screen.getByText(en.content.source.autopost)).toBeInTheDocument();
  });
});
