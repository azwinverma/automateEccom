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
  | "reply"
  | "check_payment"
  | "fix_stock"
  | "review_order"
  | "remove_file"
  | "call_customer"
  | "request_reattempt"
  | "contact_courier"
  | "confirm_received_back"
  | "review_settlement"
  | "reconnect_courier"
  | "review_return"
  | "inspect_return"
  | "issue_refund"
  | "approve_refund"
  | "retry_refund"
  | "review_automation"
  | "open_workflow";

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
    case "reply":
      return { kind: "link", href: `/inbox?c=${enc(id)}`, label: "reply" };
    case "check_payment":
    case "fix_stock":
    case "review_order":
      return { kind: "link", href: `/orders/${enc(id)}`, label: item.action as "check_payment" | "fix_stock" | "review_order" };
    case "call_customer":
    case "request_reattempt":
    case "contact_courier":
    case "confirm_received_back": {
      // Fixed on the order page, where the Delivery panel has the shipment's actions.
      const order = str(details.order_id);
      return { kind: "link", href: order ? `/orders/${enc(order)}#delivery` : "/fulfillment", label: item.action as ExceptionActionLabel };
    }
    case "review_settlement":
      return { kind: "link", href: "/fulfillment/cod", label: "review_settlement" };
    case "review_return":
    case "inspect_return":
    case "issue_refund":
      return { kind: "link", href: `/returns/${enc(id)}`, label: item.action as ExceptionActionLabel };
    case "approve_refund":
    case "retry_refund": {
      const ret = str(details.return_id);
      return { kind: "link", href: ret ? `/returns/${enc(ret)}` : "/returns", label: item.action as ExceptionActionLabel };
    }
    case "review_automation":
      return { kind: "link", href: "/automation", label: "review_automation" };
    case "open_workflow":
      return { kind: "link", href: `/automation/${enc(id)}`, label: "open_workflow" };
    case "reconnect_courier":
      return { kind: "link", href: "/settings/couriers", label: "reconnect_courier" };
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
  if (item.type === "customer_escalation") {
    const reason = str(d.reason);
    return { key: "escalation", vars: { name: str(d.name) ?? "", reason: reason ?? "" } };
  }
  if (r === "order") return { key: "orderReview", vars: { number: Number(d.number ?? 0), reason: str(d.reason) ?? "" } };
  if (item.type === "usage_limit") {
    // `resource` is a code; the caller swaps it for the localized name (usage.resource.*).
    const vars = { resource: str(d.resource) ?? "", used: Number(d.used ?? 0), limit: Number(d.limit ?? 0) };
    return { key: Number(d.level) >= 100 ? "usageLimitReached" : "usageLimitNear", vars };
  }
  if (item.type === "delivery_failed") {
    const replied = str(d.recovery_status) === "customer_replied";
    return { key: replied ? "deliveryReplied" : "deliveryFailed", vars: { number: Number(d.number ?? 0), reason: str(d.reason) ?? "" } };
  }
  if (item.type === "shipment_stuck") return { key: "shipmentStuck", vars: { number: Number(d.number ?? 0), days: Number(d.days_since_update ?? 0) } };
  if (item.type === "shipment_lost") return { key: "shipmentLost", vars: { number: Number(d.number ?? 0) } };
  if (item.type === "return_to_receive") return { key: "returnToReceive", vars: { number: Number(d.number ?? 0) } };
  if (item.type === "cod_settlement_mismatch") return { key: "settlementMismatch", vars: { reference: str(d.reference) ?? "", count: Number(d.issues ?? 0) } };
  if (item.type === "courier_error") return { key: "courierError", vars: { name } };
  if (item.type === "automation_approval") return { key: "automationApproval", vars: { name, action: str(d.step_action) ?? "" } };
  if (item.type === "automation_paused") return { key: "automationPaused", vars: { name } };
  if (item.type === "return_requested") return { key: "returnRequested", vars: { number: str(d.return_number) ?? "", order: Number(d.number ?? 0) } };
  if (item.type === "return_to_inspect") return { key: "returnToInspect", vars: { number: str(d.return_number) ?? "" } };
  if (item.type === "refund_due") return { key: "refundDue", vars: { number: str(d.return_number) ?? "", amount: Number(d.amount_minor ?? 0) } };
  if (item.type === "refund_above_threshold") return { key: "refundToApprove", vars: { order: Number(d.number ?? 0), amount: Number(d.amount_minor ?? 0) } };
  if (item.type === "refund_failed") return { key: "refundFailed", vars: { order: Number(d.number ?? 0) } };
  if (item.type === "listing_drift") return { key: "listingDrift", vars: { name, channel: str(d.name) ?? "" } };
  if (item.type === "publish_failed" && r === "content_post") return { key: "postFailed", vars: {} };
  if (item.type === "low_confidence_ai" && r === "content_post") return { key: "postNeedsApproval", vars: { count: Number(d.issues ?? 0) } };
  if (item.type === "low_confidence_ai" && r === "studio_job") return { key: "draftReady", vars: {} };
  if (item.type === "low_confidence_ai" && r === "product") return { key: "attributesToConfirm", vars: { name } };
  if (item.type === "provider_failure" && r === "studio_job") return { key: "draftFailed", vars: {} };
  if (item.type === "provider_failure" && r === "media") return { key: "fileBlocked", vars: { name } };
  return { key: "generic", vars: {} };
}
