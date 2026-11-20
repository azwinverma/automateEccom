"use client";

import type { PurchaseOrderStatus } from "@commerce-os/api-client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { InlineAlert, Skeleton, type Tone } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import settings from "../settings/settings.module.css";

export const PO_STATUSES: PurchaseOrderStatus[] = ["draft", "pending_approval", "approved", "sent", "partially_received", "received", "cancelled"];

export const STATUS_TONE: Record<PurchaseOrderStatus, Tone> = {
  draft: "neutral",
  pending_approval: "warning",
  approved: "info",
  sent: "info",
  partially_received: "automated",
  received: "success",
  cancelled: "neutral",
};

/** "1,250.50" → 125050 paisa. Empty → null; invalid or negative → NaN (caller reports it). */
export function toMinor(value: string): number | null {
  const v = value.trim().replace(/,/g, "");
  if (!v) return null;
  if (!/^\d+(\.\d{0,2})?$/.test(v)) return Number.NaN;
  return Math.round(Number(v) * 100);
}

export function fromMinor(minor: number | null | undefined): string {
  if (minor === null || minor === undefined) return "";
  return minor % 100 === 0 ? String(minor / 100) : (minor / 100).toFixed(2);
}

/** Same allocation as the server (PRO-006): extras shared by line value, per unit. */
export function landedUnitCosts(lines: { quantity: number; unit_cost_minor: number }[], extrasMinor: number): number[] {
  const value = lines.reduce((s, l) => s + l.unit_cost_minor * l.quantity, 0);
  return lines.map((l) => {
    if (l.quantity <= 0) return l.unit_cost_minor;
    const share = value ? (l.unit_cost_minor * l.quantity) / value : 1 / lines.length;
    return Math.round(l.unit_cost_minor + (extrasMinor * share) / l.quantity);
  });
}

export function itemLabel(title: string | null | undefined, variant: string | null | undefined): string {
  return [title ?? "", variant ? `(${variant})` : ""].filter(Boolean).join(" ");
}

/** Stock | Purchase orders | Suppliers. Purchasing tabs show only when the plan and role allow them. */
export function InventoryTabs() {
  const { t } = useI18n();
  const pathname = usePathname();
  const { feature, can } = useAuth();
  if (feature("procurement") !== "yes" || !can("procurement.read")) return null;
  const tabs = [
    { href: "/inventory", label: t("inventory.tabStock"), active: pathname === "/inventory" },
    { href: "/inventory/purchase-orders", label: t("inventory.tabPurchaseOrders"), active: pathname.startsWith("/inventory/purchase-orders") },
    { href: "/inventory/suppliers", label: t("inventory.tabSuppliers"), active: pathname.startsWith("/inventory/suppliers") },
  ];
  return (
    <nav aria-label={t("inventory.sectionTabs")}>
      <ul className={settings.tabs}>
        {tabs.map((tb) => (
          <li key={tb.href}>
            <Link href={tb.href} className={settings.tab} aria-current={tb.active ? "page" : undefined}>
              {tb.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Never calls the purchasing API when the plan or role doesn't allow it (ADR-072). */
export function PurchasingGate({ children, header }: { children: ReactNode; header?: ReactNode }) {
  const { t } = useI18n();
  const { feature, can } = useAuth();
  const f = feature("procurement");
  if (f === "pending")
    return (
      <>
        {header}
        <Skeleton height={120} />
      </>
    );
  if (f === "no")
    return (
      <>
        {header}
        <InlineAlert tone="info" title={t("procurement.upsell")}>
          <LimitActions buyCredits={false} upgrade />
        </InlineAlert>
      </>
    );
  if (!can("procurement.read"))
    return (
      <>
        {header}
        <InlineAlert tone="info">{t("procurement.noAccess")}</InlineAlert>
      </>
    );
  return <>{children}</>;
}
