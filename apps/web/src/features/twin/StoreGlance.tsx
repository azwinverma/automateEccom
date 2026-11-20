"use client";

import type { TwinSummary } from "@commerce-os/api-client";
import Link from "next/link";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./twin.module.css";

type T = ReturnType<typeof useI18n>["t"];
type Chip = { key: string; href: string; label: string; attention?: boolean };

const num = (state: Record<string, unknown> | undefined, key: string): number => {
  const v = state?.[key];
  return typeof v === "number" ? v : 0;
};

/** The chips worth showing: only what's non-zero, linked to where it's handled. */
export function glanceChips(t: T, money: (minor: number) => string, s: TwinSummary): Chip[] {
  const st = (n: keyof TwinSummary["sections"]) => s.sections[n]?.state;
  const out: Chip[] = [];
  const open = num(st("orders"), "open");
  const review = num(st("orders"), "needs_review");
  if (open) out.push({ key: "orders", href: "/orders", label: t("twin.orders", { n: open }) });
  if (review) out.push({ key: "review", href: "/orders", label: t("twin.review", { n: review }), attention: true });
  const oos = num(st("inventory"), "out_of_stock");
  const low = num(st("inventory"), "low_stock");
  if (oos) out.push({ key: "oos", href: "/inventory", label: t("twin.outOfStock", { n: oos }), attention: true });
  if (low) out.push({ key: "low", href: "/inventory", label: t("twin.lowStock", { n: low }) });
  const cash = num(st("cod"), "cash_with_courier_minor");
  if (cash) out.push({ key: "cash", href: "/fulfillment", label: t("twin.cash", { amount: money(cash) }) });
  const ret = num(st("returns"), "open");
  if (ret) out.push({ key: "returns", href: "/returns", label: t("twin.returns", { n: ret }) });
  const waiting = num(st("suppliers"), "awaiting_approval");
  const overdue = num(st("suppliers"), "overdue");
  if (waiting) out.push({ key: "pos", href: "/inventory/purchase-orders?status=pending_approval", label: t("twin.posWaiting", { n: waiting }), attention: true });
  if (overdue) out.push({ key: "overdue", href: "/inventory/purchase-orders", label: t("twin.posOverdue", { n: overdue }), attention: true });
  const ex = num(st("exceptions"), "total");
  if (ex) out.push({ key: "exceptions", href: "/home#exceptions", label: t("twin.exceptions", { n: ex }), attention: true });
  return out;
}

const SECTIONS = ["orders", "inventory", "cod", "returns", "suppliers", "exceptions"] as const;

/** Phase 9 (TWIN-005): one line of "how the shop is right now" from the Digital Store Twin.
 * Shop totals are for owners and managers (analytics.read); staff never fetch them. */
export function StoreGlance() {
  const { t, money, relative } = useI18n();
  const allowed = useAuth().can("analytics.read");
  const q = useApiQuery((a) => (allowed ? a.twin.summary([...SECTIONS]) : Promise.resolve(null)), [allowed]);
  if (q.state.status !== "success" || !q.state.data) return null; // optional help: no banner on errors
  const s = q.state.data;
  const shown = Object.values(s.sections);
  if (!shown.length) return null;
  const chips = glanceChips(t, (m) => money(m, s.currency), s);
  const oldest = shown.reduce((a, b) => (a.as_of < b.as_of ? a : b));
  const stale = shown.some((x) => x.stale);
  return (
    <section className={styles.glance} aria-labelledby="glance-title" data-testid="store-glance">
      <h2 id="glance-title" className={styles.glanceTitle}>
        {t("twin.title")}
      </h2>
      <ul className={styles.chips} aria-label={t("twin.listLabel")}>
        {chips.length ? (
          chips.map((c) => (
            <li key={c.key}>
              <Link href={c.href} className={[styles.chip, c.attention && styles.chipAttention].filter(Boolean).join(" ")} data-chip={c.key}>
                {c.label}
              </Link>
            </li>
          ))
        ) : (
          <li className={styles.chip}>{t("twin.allClear")}</li>
        )}
      </ul>
      <span className={styles.meta}>
        {t("twin.asOf", { time: relative(oldest.as_of) })}
        {stale ? (
          <>
            {" · "}
            <span className={styles.stale} data-testid="glance-stale">
              {t("twin.stale")}
            </span>
          </>
        ) : null}
      </span>
    </section>
  );
}
