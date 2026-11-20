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
  | "campaigns"
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
  { key: "inbox", href: "/inbox", icon: "inbox", group: "sell" },
  { key: "orders", href: "/orders", icon: "orders", group: "sell" },
  { key: "customers", href: "/customers", icon: "customers", group: "sell" },
  { key: "products", href: "/products", icon: "products", group: "catalog" },
  { key: "content", href: "/content", icon: "content", group: "catalog" },
  { key: "inventory", href: "/inventory", icon: "inventory", group: "catalog" },
  { key: "fulfillment", href: "/fulfillment", icon: "fulfillment", group: "deliver" },
  { key: "returns", href: "/returns", icon: "returns", group: "deliver" },
  { key: "campaigns", href: "/campaigns", icon: "customers", group: "grow" },
  { key: "automation", href: "/automation", icon: "automation", group: "grow" },
  { key: "analytics", href: "/analytics", icon: "analytics", group: "grow" },
];

export const NAV_GROUPS: { group: NavGroup; labelKey?: "nav.groupSell" | "nav.groupCatalog" | "nav.groupDeliver" | "nav.groupGrow" }[] = [
  { group: "none" },
  { group: "sell", labelKey: "nav.groupSell" },
  { group: "catalog", labelKey: "nav.groupCatalog" },
  { group: "deliver", labelKey: "nav.groupDeliver" },
  { group: "grow", labelKey: "nav.groupGrow" },
];

export const AUTOMATION_PHASE = 3;

export type SettingsKey = "team" | "channels" | "payments" | "ai" | "couriers" | "returns" | "security" | "plan" | "audit";
export const SETTINGS_PAGES: { key: SettingsKey; href: string; icon: IconName }[] = [
  { key: "team", href: "/settings/team", icon: "customers" },
  { key: "channels", href: "/settings/channels", icon: "store" },
  { key: "payments", href: "/settings/payments", icon: "cash" },
  { key: "ai", href: "/settings/ai", icon: "automation" },
  { key: "couriers", href: "/settings/couriers", icon: "fulfillment" },
  { key: "returns", href: "/settings/returns", icon: "returns" },
  { key: "security", href: "/settings/security", icon: "shield" },
  { key: "plan", href: "/settings/plan", icon: "analytics" },
  { key: "audit", href: "/settings/audit", icon: "clock" },
];

export function findSection(key: string): SectionDef | undefined {
  return SECTIONS.find((s) => s.key === key);
}
