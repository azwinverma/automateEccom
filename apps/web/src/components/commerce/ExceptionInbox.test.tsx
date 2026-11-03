import { ApiError } from "@commerce-os/api-client";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { renderWithI18n } from "@/test/render";
import { EXCEPTION_TYPES, ExceptionInbox, type ExceptionItem } from "./ExceptionInbox";

const now = new Date().toISOString();
const items: ExceptionItem[] = EXCEPTION_TYPES.map((type, i) => ({
  id: `e${i}`,
  type,
  severity: i % 3 === 0 ? "urgent" : i % 3 === 1 ? "high" : "normal",
  summary: `summary ${type}`,
  occurredAt: now,
}));

describe("ExceptionInbox", () => {
  it("shows the calm empty state when nothing needs attention", () => {
    renderWithI18n(<ExceptionInbox state="ready" items={[]} />);
    expect(screen.getByText(en.exceptions.emptyTitle)).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(screen.getByTestId("exception-inbox")).toHaveAttribute("data-state", "ready");
  });

  it("renders the empty state in Nepali", () => {
    renderWithI18n(<ExceptionInbox state="ready" items={[]} />, { locale: "ne" });
    expect(screen.getByText(ne.exceptions.emptyTitle)).toBeInTheDocument();
  });

  it("shows a skeleton with an accessible label while loading", () => {
    renderWithI18n(<ExceptionInbox state="loading" />);
    expect(screen.getByRole("status", { name: en.exceptions.loading })).toBeInTheDocument();
  });

  it("shows localized error, request id and a working retry", async () => {
    const onRetry = vi.fn();
    const error = new ApiError({ status: 503, code: "dependency_unavailable", message: "x", requestId: "req-123" });
    renderWithI18n(<ExceptionInbox state="error" error={error} onRetry={onRetry} />);
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(en.errors.dependency_unavailable)).toBeInTheDocument();
    expect(within(alert).getByText("Ref: req-123")).toBeInTheDocument();
    await userEvent.click(within(alert).getByRole("button", { name: en.common.retry }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders every exception type with its label and action, high severity first", async () => {
    const onAction = vi.fn();
    renderWithI18n(<ExceptionInbox state="ready" items={items} onAction={onAction} />);
    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(EXCEPTION_TYPES.length);
    for (const type of EXCEPTION_TYPES) {
      const row = rows.find((r) => r.getAttribute("data-type") === type)!;
      expect(within(row).getByText(en.exceptions.type[type])).toBeInTheDocument();
      expect(within(row).getByRole("button", { name: en.exceptions.action[type] })).toBeInTheDocument();
    }
    expect(within(rows[0]!).getByText(en.exceptions.severityHigh)).toBeInTheDocument();
    expect(screen.getByText(`${EXCEPTION_TYPES.length} open`)).toBeInTheDocument();
    await userEvent.click(within(rows[0]!).getByRole("button"));
    expect(onAction).toHaveBeenCalledWith(expect.objectContaining({ severity: "urgent" }));
  });

  it("formats amounts as NPR", () => {
    renderWithI18n(
      <ExceptionInbox
        state="ready"
        items={[{ ...items[0]!, amount: { amount_minor: 125000, currency: "NPR" } }]}
      />,
      { locale: "ne" },
    );
    expect(screen.getByText("रू 1,250")).toBeInTheDocument();
  });
});
