import type { IconName } from "@/components/ui/Icon";

export type SectionKey =
  | "home"
  | "inbox"
  | "orders"
  | "products"
  | "content"
  | "customers"
  | "inventory"
  | "fulfillment"
  | "returns"
  | "automation"
  | "analytics";

export type NavGroup = "none" | "sell" | "catalog" | "deliver" | "grow";

export interface SectionDef {
  key: SectionKey;
  href: string;
  icon: IconName;
  group: NavGroup;
  /** Delivery phase for sections not built yet (Phase 0 = this foundation). */
  phase?: number;
}

/**
 * Nav grouped by the seller's workflow: sell → catalog → deliver → grow.
 * Phase numbers are the web team's working plan; the specs do not pin them yet.
 */
export const SECTIONS: SectionDef[] = [
  { key: "home", href: "/home", icon: "home", group: "none" },
  { key: "inbox", href: "/inbox", icon: "inbox", group: "sell", phase: 2 },
  { key: "orders", href: "/orders", icon: "orders", group: "sell", phase: 1 },
  { key: "customers", href: "/customers", icon: "customers", group: "sell", phase: 1 },
  { key: "products", href: "/products", icon: "products", group: "catalog", phase: 1 },
  { key: "content", href: "/content", icon: "content", group: "catalog", phase: 2 },
  { key: "inventory", href: "/inventory", icon: "inventory", group: "catalog", phase: 1 },
  { key: "fulfillment", href: "/fulfillment", icon: "fulfillment", group: "deliver", phase: 2 },
  { key: "returns", href: "/returns", icon: "returns", group: "deliver", phase: 3 },
  { key: "automation", href: "/automation", icon: "automation", group: "grow", phase: 3 },
  { key: "analytics", href: "/analytics", icon: "analytics", group: "grow", phase: 3 },
];

export const NAV_GROUPS: { group: NavGroup; labelKey?: "nav.groupSell" | "nav.groupCatalog" | "nav.groupDeliver" | "nav.groupGrow" }[] = [
  { group: "none" },
  { group: "sell", labelKey: "nav.groupSell" },
  { group: "catalog", labelKey: "nav.groupCatalog" },
  { group: "deliver", labelKey: "nav.groupDeliver" },
  { group: "grow", labelKey: "nav.groupGrow" },
];

export const AUTOMATION_PHASE = 3;

export type SettingsKey = "team" | "security" | "plan" | "audit";
export const SETTINGS_PAGES: { key: SettingsKey; href: string; icon: IconName }[] = [
  { key: "team", href: "/settings/team", icon: "customers" },
  { key: "security", href: "/settings/security", icon: "shield" },
  { key: "plan", href: "/settings/plan", icon: "analytics" },
  { key: "audit", href: "/settings/audit", icon: "clock" },
];

export function findSection(key: string): SectionDef | undefined {
  return SECTIONS.find((s) => s.key === key);
}
