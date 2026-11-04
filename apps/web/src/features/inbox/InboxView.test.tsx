import type { ConversationDetail, InboxMessage } from "@commerce-os/api-client";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { InboxView } from "./InboxView";

const conv: ConversationDetail = {
  id: "cv1", provider: "sandbox_channel", connection_id: "c1", status: "open", customer: { id: "cu1", display_name: "Bikash Rai", phone: null },
  assigned_user_id: null, labels: [], last_intent: "price", human_handoff: false, escalated: false, escalation_reason: null, unread_count: 1,
  locale: "en", last_message_at: "2026-11-04T00:00:00Z", first_response_due_at: null, last_message: { text: "kati?", direction: "in", status: "received" },
  ai_summary: null, ai_summary_at: null, order_draft: { id: "d1", status: "collecting", fields: {}, awaiting_field: "phone", order_id: null },
};
const msg = (over: Partial<InboxMessage>): InboxMessage => ({
  id: "m1", direction: "in", author_type: "customer", author_user_id: null, text: "Dhaka kurta kati?", status: "received", intent: null, confidence: null, grounding: {}, error_code: null, created_at: "2026-11-04T00:00:00Z", sent_at: null, ...over,
});

const inbox = {
  conversations: vi.fn(async () => ({ items: [conv], next_cursor: null })),
  conversation: vi.fn(async () => conv),
  messages: vi.fn(),
  markRead: vi.fn(async () => conv),
  approve: vi.fn(async () => msg({})),
  discard: vi.fn(async () => undefined),
  reply: vi.fn(async () => msg({})),
  update: vi.fn(async () => conv),
  summary: vi.fn(),
  retry: vi.fn(),
};
const api = { inbox };
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: () => true }) }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("c=cv1"),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/inbox",
}));

beforeEach(() => {
  vi.clearAllMocks();
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  inbox.messages.mockResolvedValue({
    items: [
      msg({}),
      msg({ id: "m2", direction: "out", author_type: "ai", status: "suggested", text: "Dhaka Kurta: Rs 2,450. In stock (4 available).", grounding: { get_price: {}, get_inventory: {} } }),
    ],
    next_cursor: null,
  });
});

describe("Inbox thread", () => {
  it("shows the AI suggestion with what it looked up, and sends it on approve", async () => {
    const u = userEvent.setup();
    renderWithI18n(<InboxView />);
    expect(await screen.findByText(/Rs 2,450/)).toBeInTheDocument();
    expect(screen.getByText(/Looked up: price, stock/)).toBeInTheDocument();
    expect(screen.getByTestId("order-draft")).toHaveTextContent("Next: phone");
    await u.click(screen.getByRole("button", { name: en.inbox.approve }));
    await waitFor(() => expect(inbox.approve).toHaveBeenCalledWith("m2"));
  });

  it("edit sends the seller's text; discard drops it", async () => {
    const u = userEvent.setup();
    renderWithI18n(<InboxView />);
    await u.click(await screen.findByRole("button", { name: en.inbox.edit }));
    const box = screen.getByRole("textbox", { name: en.inbox.edit });
    await u.clear(box);
    await u.type(box, "Rs 2,450, free delivery in Pokhara!");
    await u.click(screen.getByRole("button", { name: en.inbox.sendEdited }));
    await waitFor(() => expect(inbox.approve).toHaveBeenCalledWith("m2", "Rs 2,450, free delivery in Pokhara!"));
    await u.click(screen.getByRole("button", { name: en.inbox.discard }));
    await waitFor(() => expect(inbox.discard).toHaveBeenCalledWith("m2"));
  });

  it("replies with Enter and shows escalations", async () => {
    const u = userEvent.setup();
    inbox.conversation.mockResolvedValue({ ...conv, escalated: true, escalation_reason: "complaint" });
    renderWithI18n(<InboxView />);
    expect(await screen.findByText("Needs you: complaint")).toBeInTheDocument();
    await u.type(screen.getByRole("textbox", { name: en.inbox.composer }), "Sorry! Please send a photo.{Enter}");
    await waitFor(() => expect(inbox.reply).toHaveBeenCalledWith("cv1", "Sorry! Please send a photo."));
  });
});
