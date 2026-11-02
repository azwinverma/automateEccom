import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithI18n } from "@/test/render";
import { SitePage } from "./SitePage";
import { siteEn, siteNe, type SiteCopy } from "./copy";

function shape(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(shape);
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, shape(x)]));
  return typeof v;
}

describe("public website", () => {
  it("Nepali copy has exactly the English shape (same sections, items and statuses)", () => {
    expect(shape(siteNe)).toEqual(shape(siteEn));
    const statuses = (c: SiteCopy) => [...c.loop.stages.map((s) => s.status), ...c.modules.items.map((m) => m.status)];
    expect(statuses(siteNe)).toEqual(statuses(siteEn));
  });

  it("only claims what is built: capture, create and publish are the stages available now", () => {
    expect(siteEn.loop.stages.filter((s) => s.status === "now").map((s) => s.name)).toEqual(["Capture", "Create", "Publish"]);
    expect(siteEn.modules.items.filter((m) => m.status === "now").map((m) => m.key)).toEqual(["studio", "video", "publish"]);
  });

  it("never shows prices, testimonials or the pre-Nivaro name", () => {
    for (const c of [siteEn, siteNe]) {
      const text = JSON.stringify(c);
      expect(text).not.toMatch(/\/month|per month|testimonial|(?<!Autonomous )Commerce OS/i);
      expect(c.plans.tiers.every((t) => !/\d/.test(t.value))).toBe(true);
    }
  });

  it("signed-out visitors get sign-up and sign-in; illustrative UI is labelled", () => {
    renderWithI18n(<SitePage copy={siteEn} signedIn={false} />);
    const header = screen.getByRole("banner");
    expect(within(header).getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(within(header).getByRole("link", { name: "Start free" })).toHaveAttribute("href", "/register");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Your store, on autopilot.");
    expect(screen.getAllByText("Illustrative").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("In development").length).toBeGreaterThan(0);
  });

  it("signed-in visitors go straight to the app", () => {
    renderWithI18n(<SitePage copy={siteEn} signedIn />);
    const header = screen.getByRole("banner");
    expect(within(header).getByRole("link", { name: "Open Nivaro" })).toHaveAttribute("href", "/home");
    expect(within(header).queryByRole("link", { name: "Sign in" })).toBeNull();
  });
});
