import type { ChannelListing, ProductDetail } from "@commerce-os/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { ListingsPanel } from "./ListingsPanel";

const product = {
  id: "p1",
  status: "active",
  variants: [{ price: { amount_minor: 650000, currency: "NPR" } }],
} as unknown as ProductDetail;

const conn = {
  id: "c1",
  provider: "woocommerce",
  display_name: "Thamel Woo",
  status: "connected",
  capabilities: ["product_listing"],
  needs_reconnect: false,
};

function listing(over: Partial<ChannelListing> = {}): ChannelListing {
  return {
    id: "l1",
    connection_id: "c1",
    product_id: "p1",
    provider: "woocommerce",
    status: "published",
    desired_state: "published",
    external_id: "11",
    last_error_code: null,
    last_synced_at: "2026-11-03T00:00:00Z",
    published_product_version: 2,
    drift: null,
    last_reconciled_at: null,
    ...over,
  };
}

const catalog = { listings: vi.fn(), publish: vi.fn(), unpublish: vi.fn(), resolveDrift: vi.fn() };
const channels = { list: vi.fn(async () => ({ items: [conn] })) };
const api = { catalog, channels };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: () => true }) }));

beforeEach(() => {
  vi.clearAllMocks();
  channels.list.mockResolvedValue({ items: [conn] });
});

describe("ListingsPanel drift (CHN-012)", () => {
  it("shows what changed on the channel and lets the seller push Nivaro's version", async () => {
    const user = userEvent.setup();
    catalog.listings.mockResolvedValue({
      items: [
        listing({
          drift: {
            code: "price_changed",
            details: { prices: [{ sku: "PASH-01", expected_minor: 650000, channel_minor: 600000 }] },
            detected_at: "2026-11-03T00:00:00Z",
          },
        }),
      ],
    });
    catalog.resolveDrift.mockResolvedValue(listing());
    renderWithI18n(<ListingsPanel product={product} canPublish />);
    const drift = await screen.findByTestId("listing-drift");
    expect(drift).toHaveTextContent(en.listings.drift.badge);
    expect(drift).toHaveTextContent(/PASH-01/);
    expect(drift).toHaveTextContent(/6,000/);
    // Update/Remove are replaced by the two resolutions while drift is open.
    expect(screen.queryByRole("button", { name: en.listings.update })).toBeNull();
    await user.click(screen.getByRole("button", { name: en.listings.drift.push }));
    await waitFor(() => expect(catalog.resolveDrift).toHaveBeenCalledWith("p1", "c1", "push"));
  });

  it("keep-channel-version calls accept; a deleted listing says so", async () => {
    const user = userEvent.setup();
    catalog.listings.mockResolvedValue({ items: [listing({ drift: { code: "missing_on_channel", details: {}, detected_at: null } })] });
    catalog.resolveDrift.mockResolvedValue(listing({ status: "unpublished" }));
    renderWithI18n(<ListingsPanel product={product} canPublish />);
    expect(await screen.findByText(en.listings.drift.missing_on_channel)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: en.listings.drift.accept }));
    await waitFor(() => expect(catalog.resolveDrift).toHaveBeenCalledWith("p1", "c1", "accept"));
  });

  it("no drift: normal Update/Remove actions", async () => {
    catalog.listings.mockResolvedValue({ items: [listing()] });
    renderWithI18n(<ListingsPanel product={product} canPublish />);
    expect(await screen.findByRole("button", { name: en.listings.update })).toBeInTheDocument();
    expect(screen.queryByTestId("listing-drift")).toBeNull();
  });
});
