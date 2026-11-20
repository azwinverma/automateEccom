"use client";

import type { Supplier, SupplierInput } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { PageHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./procurement.module.css";
import { InventoryTabs, PurchasingGate } from "./shared";

export function SuppliersView() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("inventory.title")} subtitle={t("procurement.subtitle")} />
      <InventoryTabs />
      <PurchasingGate>
        <SuppliersList />
      </PurchasingGate>
    </>
  );
}

function pct(x: number | null | undefined, number: (v: number) => string): string {
  return x === null || x === undefined ? "–" : `${number(Math.round(x * 1000) / 10)}%`;
}

function SuppliersList() {
  const { t, number, money } = useI18n();
  const { can } = useAuth();
  const router = useRouter();
  const [archived, setArchived] = useState(false);
  const [adding, setAdding] = useState(false);
  const q = useApiQuery((a) => a.procurement.suppliers(archived), [archived]);
  const data = q.state.status === "success" ? q.state.data : null;
  const perf = Boolean(data?.performance_available);
  return (
    <>
      <div className={styles.toolbar}>
        <Checkbox label={t("procurement.showArchived")} checked={archived} onChange={(e) => setArchived(e.target.checked)} />
        {can("procurement.write") ? (
          <Button variant="primary" onClick={() => setAdding(true)}>
            {t("procurement.addSupplier")}
          </Button>
        ) : null}
      </div>
      {q.state.status === "loading" ? (
        <TableSkeleton columns="1.4fr 1fr 1fr" label={t("common.loading")} />
      ) : q.state.status === "error" ? (
        <QueryError error={q.state.error} onRetry={q.reload} />
      ) : q.state.data.items.length === 0 ? (
        <EmptyState title={t("procurement.suppliersEmpty")} body={t("procurement.suppliersEmptyBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-label={t("procurement.suppliersTitle")} data-testid="suppliers">
            <thead>
              <tr>
                <th scope="col">{t("procurement.name")}</th>
                <th scope="col">{t("procurement.colLead")}</th>
                {perf ? (
                  <>
                    <th scope="col" className={table.num}>{t("procurement.colQuality")}</th>
                    <th scope="col" className={table.num}>{t("procurement.colOnTime")}</th>
                    <th scope="col" className={table.num}>{t("procurement.colPerUnit")}</th>
                  </>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {q.state.data.items.map((s) => (
                <tr key={s.id} data-status={s.status}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <Link href={`/inventory/suppliers/${s.id}`}>{s.name}</Link>
                      </strong>
                      <span>{[s.phone, s.status === "archived" ? t("procurement.archived") : null].filter(Boolean).join(" · ")}</span>
                    </div>
                  </td>
                  <td>{s.default_lead_time_days != null ? t("procurement.leadDays", { n: s.default_lead_time_days }) : "–"}</td>
                  {perf ? (
                    <>
                      <td className={table.num}>{pct(s.performance?.defect_rate, number)}</td>
                      <td className={table.num}>{pct(s.performance?.on_time_rate, number)}</td>
                      <td className={table.num}>{s.performance?.contribution_per_unit_minor != null ? money(s.performance.contribution_per_unit_minor, data?.currency) : "–"}</td>
                    </>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Drawer open={adding} onOpenChange={setAdding} title={t("procurement.addSupplier")}>
        <SupplierForm
          onSaved={(s) => {
            setAdding(false);
            router.push(`/inventory/suppliers/${s.id}`);
          }}
        />
      </Drawer>
    </>
  );
}

/** Contact and terms. Creates a supplier, or updates one when `existing` is given. */
export function SupplierForm({ existing, onSaved }: { existing?: Supplier; onSaved: (s: Supplier) => void }) {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [f, setF] = useState({
    name: existing?.name ?? "",
    phone: existing?.phone ?? "",
    email: existing?.email ?? "",
    contact_name: existing?.contact_name ?? "",
    address: existing?.address ?? "",
    default_lead_time_days: existing?.default_lead_time_days != null ? String(existing.default_lead_time_days) : "",
    payment_terms: existing?.payment_terms ?? "",
    notes: existing?.notes ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));
  const readOnly = !can("procurement.write");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!f.name.trim()) errs.name = t("procurement.errName");
    const lead = f.default_lead_time_days.trim() ? Number(f.default_lead_time_days) : null;
    if (lead !== null && (!Number.isInteger(lead) || lead < 0 || lead > 365)) errs.lead = t("procurement.errLead");
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const body: SupplierInput = {
      name: f.name.trim(),
      phone: f.phone.trim() || null,
      email: f.email.trim() || null,
      contact_name: f.contact_name.trim() || null,
      address: f.address.trim() || null,
      default_lead_time_days: lead,
      payment_terms: f.payment_terms.trim() || null,
      notes: f.notes.trim() || null,
    };
    const saved = await action.run(() => (existing ? api.procurement.updateSupplier(existing.id, body) : api.procurement.createSupplier(body)));
    if (saved) {
      toast(t("procurement.supplierSaved"));
      onSaved(saved);
    }
  };
  return (
    <form onSubmit={submit} noValidate data-testid="supplier-form" style={{ display: "grid", gap: "var(--space-3)" }}>
      <ErrorAlert error={action.error} />
      <TextField label={t("procurement.name")} value={f.name} onChange={set("name")} error={errors.name} maxLength={160} required readOnly={readOnly} />
      <div className={styles.grid2}>
        <TextField label={t("procurement.phone")} value={f.phone} onChange={set("phone")} type="tel" maxLength={32} optionalLabel={t("common.optional")} readOnly={readOnly} />
        <TextField label={t("procurement.email")} value={f.email} onChange={set("email")} type="email" maxLength={254} optionalLabel={t("common.optional")} readOnly={readOnly} />
        <TextField label={t("procurement.contact")} value={f.contact_name} onChange={set("contact_name")} maxLength={120} optionalLabel={t("common.optional")} readOnly={readOnly} />
        <TextField
          label={t("procurement.leadTime")}
          value={f.default_lead_time_days}
          onChange={(e) => setF((s) => ({ ...s, default_lead_time_days: e.target.value.replace(/[^\d]/g, "") }))}
          inputMode="numeric"
          error={errors.lead}
          optionalLabel={t("common.optional")}
          readOnly={readOnly}
        />
      </div>
      <TextField label={t("procurement.address")} value={f.address} onChange={set("address")} maxLength={300} optionalLabel={t("common.optional")} readOnly={readOnly} />
      <TextField label={t("procurement.terms")} hint={t("procurement.termsHint")} value={f.payment_terms} onChange={set("payment_terms")} maxLength={120} optionalLabel={t("common.optional")} readOnly={readOnly} />
      <TextField label={t("procurement.notes")} value={f.notes} onChange={set("notes")} maxLength={1000} optionalLabel={t("common.optional")} readOnly={readOnly} />
      {readOnly ? null : (
        <div className={styles.row}>
          <Button type="submit" variant="primary" loading={action.pending}>
            {t("procurement.saveSupplier")}
          </Button>
        </div>
      )}
    </form>
  );
}
