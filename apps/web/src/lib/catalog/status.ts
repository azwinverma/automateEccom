import type { ProductStatus, PublishProblem } from "@commerce-os/api-client";

/** Mirrors the backend lifecycle (CAT-007). The server still validates every move. */
export const TRANSITIONS: Record<ProductStatus, ProductStatus[]> = {
  draft: ["active", "archived"],
  active: ["draft", "archived"],
  archived: ["draft"],
};

export function allowedTransitions(from: ProductStatus): ProductStatus[] {
  return TRANSITIONS[from] ?? [];
}

export type TransitionAction = "publish" | "unpublish" | "archive" | "restore";

export function transitionAction(from: ProductStatus, to: ProductStatus): TransitionAction {
  if (to === "active") return "publish";
  if (to === "archived") return "archive";
  return from === "archived" ? "restore" : "unpublish";
}

/** Editor section each not_publishable problem links to. */
export const PROBLEM_SECTION: Record<PublishProblem, "basics" | "variants" | "attributes"> = {
  title_required: "basics",
  active_variant_required: "variants",
  price_required: "variants",
  unconfirmed_ai_attributes: "attributes",
};

export const PUBLISH_PROBLEMS = Object.keys(PROBLEM_SECTION) as PublishProblem[];

export function parseProblems(details: Record<string, unknown>): PublishProblem[] {
  const raw = details.problems;
  if (!Array.isArray(raw)) return [];
  return raw.filter((p): p is PublishProblem => typeof p === "string" && p in PROBLEM_SECTION);
}
