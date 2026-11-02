import { describe, expect, it } from "vitest";
import { normalizeChanges } from "./audit";
import { safeNext } from "./auth/bff";
import { isPremiumVideoResource, parseLimitOptions } from "./usage";
import { slugify } from "./validation";

describe("safeNext", () => {
  it("allows relative app paths only", () => {
    expect(safeNext("/settings/team")).toBe("/settings/team");
    expect(safeNext("//evil.example")).toBe("/home");
    expect(safeNext("https://evil.example")).toBe("/home");
    expect(safeNext("/\\evil")).toBe("/home");
    expect(safeNext("/login")).toBe("/home");
    expect(safeNext(null)).toBe("/home");
  });
});

describe("normalizeChanges", () => {
  it("handles before/after snapshots", () => {
    expect(normalizeChanges({ before: { role: "staff", name: "A" }, after: { role: "admin", name: "A" } })).toEqual([
      { field: "role", before: "staff", after: "admin" },
    ]);
  });
  it("handles per-field pairs", () => {
    expect(normalizeChanges({ role: { old: "staff", new: "manager" }, status: ["invited", "active"], email: "x@y.z" })).toEqual([
      { field: "role", before: "staff", after: "manager" },
      { field: "status", before: "invited", after: "active" },
      { field: "email", before: undefined, after: "x@y.z" },
    ]);
  });
  it("returns nothing for null", () => {
    expect(normalizeChanges(null)).toEqual([]);
  });
});

describe("helpers", () => {
  it("slugifies Latin names and drops Devanagari", () => {
    expect(slugify("Thamel Threads & Co.")).toBe("thamel-threads-co");
    expect(slugify("ठमेल थ्रेड्स")).toBe("");
  });
  it("detects premium video resources but not auto reels", () => {
    expect(isPremiumVideoResource("premium_video_clips")).toBe(true);
    expect(isPremiumVideoResource("video_seconds")).toBe(true);
    expect(isPremiumVideoResource("auto_reels")).toBe(false);
  });
  it("parses limit options defensively", () => {
    expect(parseLimitOptions(["upgrade", "bogus"])).toEqual(["upgrade"]);
    // Without server options, never offer Buy credits: default to Upgrade only.
    expect(parseLimitOptions(undefined)).toEqual(["upgrade"]);
  });
});

describe("billing labels", () => {
  it("uses localized labels and falls back to neutral generic copy for unknown codes", async () => {
    const { createTranslator } = await import("@/i18n/dictionaries");
    const { creditKindLabel, featureLabel, resourceLabel, resourceUnit } = await import("@/i18n/labels");
    const t = createTranslator("en");
    expect(featureLabel(t, "ai.product_studio")).toBe("AI product studio");
    expect(featureLabel(t, "never.seen-before")).toBe("Other feature");
    expect(resourceLabel(t, "team_members")).toBe("Team seats");
    expect(resourceLabel(t, "mystery")).toBe("Other usage");
    expect(resourceUnit(t, "mystery")).toBe("units");
    expect(creditKindLabel(t, "hold")).toBe("Held for a job in progress");
    expect(creditKindLabel(t, undefined)).toBe("Other");
    expect(creditKindLabel(t, "__proto__")).toBe("Other");
  });
});
