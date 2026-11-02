import { isApiError } from "@commerce-os/api-client";
import type { Translate } from "./types";

/** Localized, user-facing message for any thrown value. API `message` is never shown. */
export function errorMessage(t: Translate, error: unknown): string {
  if (!isApiError(error)) return t("errors.unknown");
  if (error.code === "rate_limited" && error.retryAfter) {
    return t("errors.rateLimitedSeconds", { seconds: error.retryAfter });
  }
  return t.dynamic(`errors.${error.code}`) ?? t("errors.unknown");
}

const FIELD_TYPE_MAP: Record<string, string> = {
  missing: "errors.field.required",
  value_error_missing: "errors.field.required",
  required: "errors.field.required",
  string_too_short: "errors.field.tooShort",
  too_short: "errors.field.tooShort",
  password_too_short: "errors.field.passwordShort",
  password_too_weak: "errors.field.passwordShort",
  value_error_email: "errors.field.email",
  email: "errors.field.email",
  invalid_email: "errors.field.email",
  string_pattern_mismatch: "errors.field.slug",
};

/** Map `validation_error` field `type`s to localized copy. */
export function fieldErrorMessages(t: Translate, fields: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [field, type] of Object.entries(fields)) {
    out[field] = t.dynamic(FIELD_TYPE_MAP[type] ?? "") ?? t("errors.field.invalid");
  }
  return out;
}
