"use client";

import type { PurchaseOrderStatus } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { ButtonLink } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/Field";
import { Badge, PageHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isPlanGate } from "../intelligence/ProfitView";
import styles from "./procurement.module.css";
import { PurchaseOrderForm } from "./PurchaseOrderForm";
import { InventoryTabs, PO_STATUSES, PurchasingGate, STATUS_TONE } from "./shared";

export function PurchaseOrdersView() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("inventory.title")} subtitle={t("procurement.subtitle")} />
      <InventoryTabs />
      <PurchasingGate>
        <PurchaseOrdersList />
      </PurchasingGate>
    </>
  );
}

function PurchaseOrdersList() {
  const { t, money, date } = useI18n();
  const { can } = useAuth();
  const params = useSearchParams();
  const router = useRouter();
  const raw = params.get("status");
  const status = PO_STATUSES.includes(raw as PurchaseOrderStatus) ? (raw as PurchaseOrderStatus) : undefined;
  const q = useApiQuery((a) => a.procurement.purchaseOrders({ status, limit: 100 }), [status]);
  return (
    <>
      <div className={styles.toolbar}>
        <SelectField
          label={t("procurement.filterStatus")}
          value={status ?? ""}
          onChange={(e) => router.replace(e.target.value ? `/inventory/purchase-orders?status=${e.target.value}` : "/inventory/purchase-orders")}
        >
          <option value="">{t("procurement.allStatuses")}</option>
          {PO_STATUSES.map((s) => (
            <option key={s} value={s}>
              {t.dynamic(`procurement.status_${s}`) ?? s}
            </option>
          ))}
        </SelectField>
        {can("procurement.write") ? (
          <ButtonLink variant="primary" href="/inventory/purchase-orders/new">
            {t("procurement.poNew")}
          </ButtonLink>
        ) : null}
      </div>
      {q.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1.4fr 1fr 1fr" label={t("common.loading")} />
      ) : q.state.status === "error" ? (
        isPlanGate(q.state.error) ? null : <QueryError error={q.state.error} onRetry={q.reload} />
      ) : q.state.data.items.length === 0 ? (
        <EmptyState title={t("procurement.poEmpty")} body={t("procurement.poEmptyBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-label={t("procurement.poTitle")} data-testid="po-list">
            <thead>
              <tr>
                <th scope="col">{t("procurement.colNumber")}</th>
                <th scope="col">{t("procurement.colSupplier")}</th>
                <th scope="col">{t("procurement.colStatus")}</th>
                <th scope="col" className={table.num}>
                  {t("procurement.colTotal")}
                </th>
                <th scope="col">{t("procurement.colExpected")}</th>
              </tr>
            </thead>
            <tbody>
              {q.state.data.items.map((po) => (
                <tr key={po.id} data-status={po.status}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <Link href={`/inventory/purchase-orders/${po.id}`}>{po.number}</Link>
                      </strong>
                      <span>{po.source === "recommendation" ? t("procurement.fromSuggestion") : date(po.created_at)}</span>
                    </div>
                  </td>
                  <td>{po.supplier.name}</td>
                  <td>
                    <Badge tone={STATUS_TONE[po.status]}>{t.dynamic(`procurement.status_${po.status}`) ?? po.status}</Badge>
                  </td>
                  <td className={table.num}>{money(po.total_minor, po.currency)}</td>
                  <td>{po.expected_at ? date(po.expected_at) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export function NewPurchaseOrderView() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("procurement.formTitleNew")} subtitle={t("procurement.subtitle")} />
      <InventoryTabs />
      <PurchasingGate>
        <NewPurchaseOrder />
      </PurchasingGate>
    </>
  );
}

function NewPurchaseOrder() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const suppliers = useApiQuery((a) => a.procurement.suppliers());
  if (suppliers.state.status === "loading") return <TableSkeleton columns="1fr" label={t("common.loading")} />;
  if (suppliers.state.status === "error") return <QueryError error={suppliers.state.error} onRetry={suppliers.reload} />;
  return (
    <PurchaseOrderForm
      suppliers={suppliers.state.data.items}
      initialSupplierId={params.get("supplier") ?? undefined}
      onSaved={(po) => router.push(`/inventory/purchase-orders/${po.id}`)}
    />
  );
}
