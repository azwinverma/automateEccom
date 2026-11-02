import { ApiError } from "@commerce-os/api-client";
import { describe, expect, it } from "vitest";
import { resolveLocale } from "./config";
import { createTranslator } from "./dictionaries";
import { errorMessage, fieldErrorMessages } from "./errors";
import { formatMoney, formatNumber } from "./format";
import { en } from "./messages/en";
import { ne } from "./messages/ne";

function leaves(obj: unknown, prefix = ""): string[] {
  if (typeof obj === "string") return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) => leaves(v, prefix ? `${prefix}.${k}` : k));
}

const CONTRACT_CODES = [
  "validation_error",
  "not_authenticated",
  "token_expired",
  "invalid_credentials",
  "mfa_invalid_code",
  "permission_denied",
  "feature_not_in_plan",
  "not_found",
  "conflict",
  "idempotency_in_progress",
  "slug_taken",
  "email_taken",
  "usage_limit_reached",
  "idempotency_key_reused",
  "invalid_state_transition",
  "rate_limited",
  "dependency_unavailable",
  "last_owner",
  "refresh_token_reused",
];

describe("dictionaries", () => {
  it("Nepali has exactly the English keys and no empty strings", () => {
    expect(leaves(ne).sort()).toEqual(leaves(en).sort());
    for (const key of leaves(ne)) {
      expect(createTranslator("ne").dynamic(key)?.trim(), key).toBeTruthy();
    }
  });

  it("keeps placeholders identical across languages", () => {
    const tEn = createTranslator("en");
    const tNe = createTranslator("ne");
    for (const key of leaves(en)) {
      const ph = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");
      expect(ph(tNe.dynamic(key)!), key).toBe(ph(tEn.dynamic(key)!));
    }
  });

  it("interpolates variables", () => {
    expect(createTranslator("en")("team.inviteSent", { email: "sita@example.com" })).toBe("Invitation sent to sita@example.com.");
  });
});

describe("billing catalog labels", () => {
  it.each(["en", "ne"] as const)("every feature, resource and credit kind has %s copy", async (locale) => {
    const { CREDIT_KINDS, FEATURE_CODES, RESOURCE_CODES } = await import("./labels");
    const t = createTranslator(locale);
    for (const code of FEATURE_CODES) expect(t.dynamic(`plan.feature.${code.replace(/\./g, "_")}`), code).toBeTruthy();
    for (const code of RESOURCE_CODES) {
      expect(t.dynamic(`usage.resource.${code}`), code).toBeTruthy();
      expect(t.dynamic(`usage.unit.${code}`), code).toBeTruthy();
    }
    for (const kind of CREDIT_KINDS) expect(t.dynamic(`plan.creditKind.${kind}`), kind).toBeTruthy();
  });
});

describe("error code → localized message", () => {
  const tEn = createTranslator("en");
  const tNe = createTranslator("ne");
  const err = (code: string, extra: Partial<ConstructorParameters<typeof ApiError>[0]> = {}) =>
    new ApiError({ status: 400, code, message: "developer text", ...extra });

  it.each(CONTRACT_CODES)("maps %s in both languages", (code) => {
    const enMsg = errorMessage(tEn, err(code));
    const neMsg = errorMessage(tNe, err(code));
    expect(enMsg).not.toBe(en.errors.unknown);
    expect(neMsg).not.toBe(ne.errors.unknown);
    expect(enMsg).not.toContain("developer text");
  });

  it("uses Retry-After for rate limits", () => {
    expect(errorMessage(tEn, err("rate_limited", { retryAfter: 30 }))).toBe("Too many attempts. Try again in 30 seconds.");
  });

  it("falls back for unknown codes and non-API errors", () => {
    expect(errorMessage(tEn, err("brand_new_code"))).toBe(en.errors.unknown);
    expect(errorMessage(tNe, new Error("boom"))).toBe(ne.errors.unknown);
  });

  it("maps network failures", () => {
    expect(errorMessage(tNe, new ApiError({ status: 0, code: "network_error", message: "" }))).toBe(ne.errors.network_error);
  });

  it("maps validation field types", () => {
    expect(fieldErrorMessages(tEn, { email: "value_error_email", password: "weird_type" })).toEqual({
      email: en.errors.field.email,
      password: en.errors.field.invalid,
    });
  });
});

describe("formatting", () => {
  it("formats NPR the way sellers write it", () => {
    expect(formatMoney(125000, "NPR", "ne")).toBe("रू 1,250");
    expect(formatMoney(125000, "NPR", "en")).toBe("Rs 1,250");
    expect(formatMoney(125050, "NPR", "en")).toBe("Rs 1,250.50");
    expect(formatMoney(12345600, "NPR", "ne")).toBe("रू 1,23,456");
  });

  it("uses Latin digits in Nepali", () => {
    expect(formatNumber(1234567, "ne")).toBe("12,34,567");
  });

  it("resolves locale from cookie, then Accept-Language", () => {
    expect(resolveLocale("en", "ne-NP")).toBe("en");
    expect(resolveLocale(undefined, "en-US,en;q=0.9")).toBe("en");
    expect(resolveLocale(undefined, "ne,en;q=0.5")).toBe("ne");
    expect(resolveLocale("fr", null)).toBe("ne");
  });
});
