"use client";

import Link from "next/link";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { PageHeader, SectionHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { InventoryTabs } from "../procurement/shared";

export function InventoryView() {
  const { t, number } = useI18n();
  const low = useApiQuery((a) => a.inventory.lowStock());
  return (
    <>
      <PageHeader title={t("inventory.title")} subtitle={t("inventory.subtitle")} />
      <InventoryTabs />
      <SectionHeader title={t("inventory.lowStock")} id="low-heading" />
      {low.state.status === "loading" ? (
        <TableSkeleton columns="1.6fr 1fr 1fr" label={t("common.loading")} />
      ) : low.state.status === "error" ? (
        <QueryError error={low.state.error} onRetry={low.reload} />
      ) : low.state.data.items.length === 0 ? (
        <EmptyState title={t("inventory.noLow")} body={t("inventory.noLowBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="low-heading" data-testid="low-stock">
            <thead>
              <tr>
                <th scope="col">{t("inventory.colProduct")}</th>
                <th scope="col" className={table.num}>
                  {t("inventory.colAvailable")}
                </th>
                <th scope="col" className={table.num}>
                  {t("inventory.colThreshold")}
                </th>
              </tr>
            </thead>
            <tbody>
              {low.state.data.items.map((i) => (
                <tr key={`${i.variant_id}:${i.location_id}`}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <Link href={`/products/${i.product_id}#stock`}>{i.product_title}</Link>
                      </strong>
                      <span>{[i.variant_title !== "Default" ? i.variant_title : null, i.sku].filter(Boolean).join(" · ")}</span>
                    </div>
                  </td>
                  <td className={table.num}>{number(i.available)}</td>
                  <td className={table.num}>{i.low_stock_threshold ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
