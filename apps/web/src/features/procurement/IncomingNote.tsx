"use client";

import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./procurement.module.css";

/** "Incoming: N on order" on the product page (approved/sent purchase orders not yet received). */
export function IncomingNote({ variants }: { variants: { id: string; title: string }[] }) {
  const { t, number } = useI18n();
  const { feature, can } = useAuth();
  const on = feature("procurement") === "yes" && can("procurement.read");
  const q = useApiQuery((a) => (on ? a.procurement.incoming() : Promise.resolve({ items: [] })), [on]);
  if (q.state.status !== "success") return null;
  const by = new Map(q.state.data.items.map((i) => [i.variant_id, i.quantity]));
  const mine = variants.filter((v) => (by.get(v.id) ?? 0) > 0);
  if (!mine.length) return null;
  const total = mine.reduce((s, v) => s + (by.get(v.id) ?? 0), 0);
  return (
    <p className={styles.muted} data-testid="incoming-note" style={{ margin: "var(--space-2) 0 0" }}>
      {t("inventory.incoming", { n: number(total) })}
      {mine.length > 1 || mine[0]!.title !== "Default"
        ? ` · ${mine.map((v) => t("inventory.incomingVariant", { variant: v.title, n: number(by.get(v.id) ?? 0) })).join(", ")}`
        : ""}
    </p>
  );
}
