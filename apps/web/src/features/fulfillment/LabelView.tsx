"use client";

import Link from "next/link";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import products from "../products/products.module.css";
import styles from "./fulfillment.module.css";

/** FUL-004: Nivaro's printable label (A6-ish), or the courier's own label when it provides one. */
export function LabelView({ id }: { id: string }) {
  const { t, money, number } = useI18n();
  const label = useApiQuery((a) => a.shipments.label(id), [id]);
  if (label.state.status === "loading") return <TableSkeleton columns="1fr" rows={6} label={t("common.loading")} />;
  if (label.state.status === "error") return <QueryError error={label.state.error} onRetry={label.reload} />;
  const l = label.state.data;
  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <div className={products.editorHeader}>
        <div className={products.editorTitle}>
          <Link href="/fulfillment" className={products.backLink}>
            ← {t("fulfillment.title")}
          </Link>
          <h1>{t("label.title", { number: l.order_number })}</h1>
        </div>
        <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
          {l.provider_label_url ? (
            <ButtonLink href={l.provider_label_url} target="_blank" rel="noopener noreferrer">
              {t("fulfillment.panel.courierLabel")}
            </ButtonLink>
          ) : null}
          <Button variant="primary" onClick={() => window.print()}>
            <Icon name="print" />
            {t("label.print")}
          </Button>
        </div>
      </div>
      <article className={styles.labelSheet} data-testid="label" data-print-only>
        <div className={styles.labelHead}>
          <strong>{l.courier}</strong>
          <span>
            {t("label.order")} #{l.order_number}
          </span>
        </div>
        {l.tracking_number ? (
          <div className={styles.labelBlock}>
            <h2>{t("label.tracking")}</h2>
            <span className={styles.labelTracking}>{l.tracking_number}</span>
          </div>
        ) : null}
        <div className={[styles.labelBlock, styles.labelTo].join(" ")}>
          <h2>{t("label.to")}</h2>
          <strong>{l.to.name}</strong>
          <span>{l.to.phone}</span>
          <span>{l.to.address}</span>
          {l.to.landmark ? <span>{l.to.landmark}</span> : null}
        </div>
        <div className={styles.labelCod}>
          {l.cod_amount.amount_minor ? `${t("label.cod")}: ${money(l.cod_amount.amount_minor, l.cod_amount.currency)}` : t("label.prepaid")}
        </div>
        <div className={styles.labelBlock}>
          <h2>{t("label.from")}</h2>
          <span>
            {l.from.name}
            {l.from.phone ? ` · ${l.from.phone}` : ""}
          </span>
          <span>{l.from.address}</span>
        </div>
        <div className={styles.labelBlock}>
          <h2>{t("label.contents")}</h2>
          <span>{l.contents || "–"}</span>
          <span>
            {t("label.weight")}: {t("label.grams", { n: number(l.weight_grams) })}
          </span>
        </div>
      </article>
    </div>
  );
}
