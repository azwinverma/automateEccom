import type { ExceptionRecord } from "@commerce-os/api-client";

/** What the "fix it" control on an exception does. */
export type ExceptionTarget =
  | { kind: "link"; href: string; label: ExceptionActionLabel }
  | { kind: "command"; command: "retry_publish" | "retry_draft" | "remove_file"; label: ExceptionActionLabel }
  | { kind: "none" };

export type ExceptionActionLabel =
  | "reconnect"
  | "retry_publish"
  | "reschedule"
  | "review_post"
  | "review_draft"
  | "retry_draft"
  | "confirm_attributes"
  | "resolve_drift"
  | "view_plan"
  | "remove_file";

const str = (v: unknown): string | null => (typeof v === "string" && v ? v : null);
const enc = encodeURIComponent;

/**
 * Route each backend `action` to a navigation or an in-place command.
 * `dismiss` has no endpoint; for blocked (malware) uploads removing the file is what clears it.
 */
export function exceptionTarget(item: ExceptionRecord): ExceptionTarget {
  const { resource, details } = item;
  const id = resource.id;
  switch (item.action) {
    case "reconnect": {
      const conn = resource.type === "channel_connection" ? id : str(details.connection_id);
      return { kind: "link", href: conn ? `/settings/channels?reconnect=${enc(conn)}` : "/settings/channels", label: "reconnect" };
    }
    case "retry_publish":
      return resource.type === "product" && str(details.connection_id)
        ? { kind: "command", command: "retry_publish", label: "retry_publish" }
        : { kind: "link", href: `/products/${enc(id)}#channels`, label: "retry_publish" };
    case "reschedule":
      return { kind: "link", href: `/content?post=${enc(id)}`, label: "reschedule" };
    case "review_post":
      return { kind: "link", href: `/content?post=${enc(id)}`, label: "review_post" };
    case "review_draft":
      return { kind: "link", href: `/products/studio/${enc(id)}`, label: "review_draft" };
    case "retry_draft":
      return { kind: "command", command: "retry_draft", label: "retry_draft" };
    case "resolve_drift":
      return { kind: "link", href: `/products/${enc(id)}#channels`, label: "resolve_drift" };
    case "view_plan":
      return { kind: "link", href: "/settings/plan", label: "view_plan" };
    case "confirm_attributes":
      return { kind: "link", href: `/products/${enc(id)}#attributes`, label: "confirm_attributes" };
    case "dismiss":
      return resource.type === "media" ? { kind: "command", command: "remove_file", label: "remove_file" } : { kind: "none" };
    default:
      return { kind: "none" };
  }
}

/** Dictionary key (under `exceptions.summary.*`) and variables for the one-line summary. */
export function exceptionSummaryKey(item: ExceptionRecord): { key: string; vars: Record<string, string | number> } {
  const d = item.details;
  const name = str(d.product_title) ?? str(d.name) ?? str(d.file_name) ?? "";
  const r = item.resource.type;
  if (item.type === "channel_expired") return { key: "channelExpired", vars: { name } };
  if (item.type === "publish_failed" && r === "product") return { key: "listingFailed", vars: { name } };
  if (item.type === "usage_limit") {
    // `resource` is a code; the caller swaps it for the localized name (usage.resource.*).
    const vars = { resource: str(d.resource) ?? "", used: Number(d.used ?? 0), limit: Number(d.limit ?? 0) };
    return { key: Number(d.level) >= 100 ? "usageLimitReached" : "usageLimitNear", vars };
  }
  if (item.type === "listing_drift") return { key: "listingDrift", vars: { name, channel: str(d.name) ?? "" } };
  if (item.type === "publish_failed" && r === "content_post") return { key: "postFailed", vars: {} };
  if (item.type === "low_confidence_ai" && r === "content_post") return { key: "postNeedsApproval", vars: { count: Number(d.issues ?? 0) } };
  if (item.type === "low_confidence_ai" && r === "studio_job") return { key: "draftReady", vars: {} };
  if (item.type === "low_confidence_ai" && r === "product") return { key: "attributesToConfirm", vars: { name } };
  if (item.type === "provider_failure" && r === "studio_job") return { key: "draftFailed", vars: {} };
  if (item.type === "provider_failure" && r === "media") return { key: "fileBlocked", vars: { name } };
  return { key: "generic", vars: {} };
}
