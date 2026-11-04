"use client";

import type { FailureReason, ShipmentStatus } from "@commerce-os/api-client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge, type Tone } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import styles from "./fulfillment.module.css";

export const SHIPMENT_TONE: Record<ShipmentStatus, Tone> = {
  booked: "neutral",
  pickup_requested: "info",
  picked_up: "info",
  in_transit: "info",
  out_for_delivery: "info",
  delivered: "success",
  delivery_failed: "danger",
  reattempt_requested: "warning",
  returning: "warning",
  returned_to_origin: "neutral",
  cancelled: "neutral",
  lost: "danger",
};

export const FAILURE_REASONS: FailureReason[] = [
  "customer_unreachable",
  "customer_unavailable",
  "customer_refused",
  "address_incorrect",
  "cod_not_ready",
  "rescheduled_by_customer",
  "other",
];

/** Statuses a seller can record for their own rider (no courier API). */
export const MANUAL_STATUSES: ShipmentStatus[] = ["picked_up", "in_transit", "out_for_delivery", "delivered", "delivery_failed", "returning", "returned_to_origin", "lost"];

/** The parcel's happy path, drawn as a route line: booked → handed over → out for delivery → delivered. */
export const ROUTE: { key: ShipmentStatus; reached: ShipmentStatus[] }[] = [
  { key: "booked", reached: ["booked", "pickup_requested", "picked_up", "in_transit", "out_for_delivery", "delivered", "delivery_failed", "reattempt_requested", "returning", "returned_to_origin", "lost"] },
  { key: "picked_up", reached: ["picked_up", "in_transit", "out_for_delivery", "delivered", "delivery_failed", "reattempt_requested", "returning", "returned_to_origin", "lost"] },
  { key: "out_for_delivery", reached: ["out_for_delivery", "delivered", "delivery_failed", "reattempt_requested"] },
  { key: "delivered", reached: ["delivered"] },
];

export function ShipmentStatusBadge({ status }: { status: ShipmentStatus }) {
  const { t } = useI18n();
  return <Badge tone={SHIPMENT_TONE[status] ?? "neutral"}>{t(`fulfillment.status.${status}`)}</Badge>;
}

export function FulfillmentTabs() {
  const { t } = useI18n();
  const path = usePathname();
  const tabs = [
    { href: "/fulfillment", label: t("fulfillment.tabShipments"), current: path === "/fulfillment" },
    { href: "/fulfillment/cod", label: t("fulfillment.tabCod"), current: path.startsWith("/fulfillment/cod") },
  ];
  return (
    <nav aria-label={t("fulfillment.tabsLabel")} className={styles.navTabs}>
      {tabs.map((tb) => (
        <Link key={tb.href} href={tb.href} className={styles.navTab} aria-current={tb.current ? "page" : undefined}>
          {tb.label}
        </Link>
      ))}
    </nav>
  );
}

export function isDev(): boolean {
  return (process.env.NEXT_PUBLIC_NIVARO_ENV ?? "development") === "development";
}
