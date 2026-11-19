import type { ExceptionList } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExceptionInbox } from "@/components/commerce/ExceptionInbox";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { useExceptions } from "./useExceptions";

const list: ExceptionList = {
  total: 3,
  counts: { urgent: 1, high: 1, normal: 1 },
  items: [
    { id: "a", type: "channel_expired", severity: "urgent", resource: { type: "channel_connection", id: "c1" }, occurred_at: "2026-11-02T08:00:00Z", action: "reconnect", details: { name: "Thamel FB", provider: "sandbox_channel" } },
    { id: "b", type: "publish_failed", severity: "high", resource: { type: "product", id: "p1" }, occurred_at: "2026-11-02T07:00:00Z", action: "retry_publish", details: { product_title: "Dhaka Topi", connection_id: "c2", error_code: "rate_limited" } },
    { id: "c", type: "low_confidence_ai", severity: "normal", resource: { type: "studio_job", id: "j1" }, occurred_at: null, action: "review_draft", details: {} },
  ],
};
const api = {
  exceptions: { list: vi.fn(async () => list) },
  catalog: { publish: vi.fn(async () => ({ items: [] })) },
  studio: { retry: vi.fn() },
  media: { remove: vi.fn() },
};
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: () => true }) }));

function Harness() {
  const ex = useExceptions();
  if (ex.query.state.status !== "success") return <p>loading</p>;
  return <ExceptionInbox state="ready" items={ex.items} renderAction={ex.renderAction} />;
}

describe("Home exception inbox wiring", () => {
  it("renders summaries and routes each action", async () => {
    renderWithI18n(<Harness />);
    const rows = await screen.findAllByRole("listitem");
    expect(rows).toHaveLength(3);
    expect(within(rows[0]!).getByText("Thamel FB needs reconnecting")).toBeInTheDocument();
    expect(within(rows[0]!).getByRole("link", { name: en.exceptions.actionLabel.reconnect })).toHaveAttribute("href", "/settings/channels?reconnect=c1");
    expect(within(rows[2]!).getByRole("link", { name: en.exceptions.actionLabel.review_draft })).toHaveAttribute("href", "/products/studio/j1");
    expect(within(rows[1]!).getByText(en.errors.rate_limited)).toBeInTheDocument();
    await userEvent.click(within(rows[1]!).getByRole("button", { name: en.exceptions.actionLabel.retry_publish }));
    await waitFor(() => expect(api.catalog.publish).toHaveBeenCalledWith("p1", ["c2"]));
    expect(api.exceptions.list).toHaveBeenCalledTimes(2); // reloaded after the command
  });
});
