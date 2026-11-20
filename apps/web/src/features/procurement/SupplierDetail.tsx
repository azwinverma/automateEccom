"use client";

import { isApiError, type SupplierDetail as SupplierDetailT, type SupplierPerformance, type SupplierProduct } from "@commerce-os/api-client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, PageHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./procurement.module.css";
import { fromMinor, InventoryTabs, itemLabel, PurchasingGate, toMinor } from "./shared";
import { SupplierForm } from "./SuppliersView";
import { VariantPicker, type PickedVariant } from "./VariantPicker";

export function SupplierDetailView({ id }: { id: string }) {
  const { t } = useI18n();
  return (
    <PurchasingGate header={<PageHeader title={t("procurement.suppliersTitle")} />}>
      <SupplierDetail id={id} />
    </PurchasingGate>
  );
}

function SupplierDetail({ id }: { id: string }) {
  const { t } = useI18n();
  const { api, can, feature } = useAuth();
  const toast = useToast();
  const action = useAction();
  const q = useApiQuery((a) => a.procurement.supplier(id), [id]);
  const [adding, setAdding] = useState(false);
  if (q.state.status === "loading") return <TableSkeleton columns="1fr 1fr" label={t("common.loading")} />;
  if (q.state.status === "error") {
    if (isApiError(q.state.error) && q.state.error.status === 404) return <EmptyState title={t("procurement.supplierNotFound")} />;
    return <QueryError error={q.state.error} onRetry={q.reload} />;
  }
  const s = q.state.data;
  const canWrite = can("procurement.write");
  const setProducts = (items: SupplierProduct[]) => q.setData((prev) => ({ ...prev, products: items }));
  return (
    <>
      <PageHeader
        title={s.name}
        subtitle={s.status === "archived" ? <Badge>{t("procurement.archived")}</Badge> : (s.payment_terms ?? undefined)}
      />
      <InventoryTabs />
      <p style={{ margin: "0 0 var(--space-4)" }}>
        <Link href="/inventory/suppliers">← {t("procurement.back2")}</Link>
      </p>
      <ErrorAlert error={action.error} />
      <div className={styles.row} style={{ marginBottom: "var(--space-4)" }}>
        {canWrite && s.status === "active" ? (
          <ButtonLink variant="primary" href={`/inventory/purchase-orders/new?supplier=${s.id}`}>
            {t("procurement.poNew")}
          </ButtonLink>
        ) : null}
        {canWrite ? (
          <Button
            loading={action.pending}
            onClick={async () => {
              const next = await action.run(() => api.procurement.updateSupplier(s.id, { status: s.status === "active" ? "archived" : "active" }));
              if (next) {
                q.setData((prev) => ({ ...prev, status: next.status }));
                toast(t("procurement.supplierSaved"));
              }
            }}
          >
            {s.status === "active" ? t("procurement.archive") : t("procurement.restore")}
          </Button>
        ) : null}
      </div>

      <PerformanceSection supplier={s} available={feature("intelligence.supplier") === "yes"} onRefreshed={q.reload} />

      <section className={styles.card} aria-labelledby="sp-title" data-testid="supplier-products">
        <div className={styles.head}>
          <h2 id="sp-title">{t("procurement.products")}</h2>
          {canWrite ? (
            <Button size="sm" onClick={() => setAdding(true)}>
              {t("procurement.addProduct")}
            </Button>
          ) : null}
        </div>
        {s.products.length === 0 ? (
          <span className={styles.muted}>{t("procurement.productsEmpty")}</span>
        ) : (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">{t("procurement.item")}</th>
                  <th scope="col">{t("procurement.supplierSku")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colCost")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colMoq")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colLead")}</th>
                  <th scope="col">{t("procurement.preferred")}</th>
                  {canWrite ? <th scope="col"><span className="srOnly">{t("procurement.remove")}</span></th> : null}
                </tr>
              </thead>
              <tbody>
                {s.products.map((p) => (
                  <ProductRow key={p.variant_id} supplier={s} p={p} canWrite={canWrite} onChange={setProducts} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={styles.card} aria-labelledby="sc-title">
        <div className={styles.head}>
          <h2 id="sc-title">{t("procurement.contact")}</h2>
        </div>
        <SupplierForm existing={s} onSaved={(next) => q.setData((prev) => ({ ...prev, ...next }))} />
      </section>

      <Drawer open={adding} onOpenChange={setAdding} title={t("procurement.addProductTitle")}>
        <AddProductForm
          supplierId={s.id}
          exclude={s.products.map((p) => p.variant_id)}
          onSaved={(items) => {
            setProducts(items);
            setAdding(false);
          }}
        />
      </Drawer>
    </>
  );
}

function ProductRow({ supplier, p, canWrite, onChange }: { supplier: SupplierDetailT; p: SupplierProduct; canWrite: boolean; onChange: (items: SupplierProduct[]) => void }) {
  const { t, money: fmt } = useI18n();
  const money = (minor: number) => fmt(minor, supplier.currency);
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const label = itemLabel(p.title, p.variant);
  return (
    <tr>
      <td>
        <div className={table.primaryCell}>
          <strong>
            <Link href={`/products/${p.product_id}`}>{label}</Link>
          </strong>
          <span>{[p.sku, t("procurement.yourPrice", { price: money(p.price_minor) })].filter(Boolean).join(" · ")}</span>
        </div>
      </td>
      <td>{p.supplier_sku ?? "–"}</td>
      <td className={table.num}>{p.cost_minor != null ? money(p.cost_minor) : "–"}</td>
      <td className={table.num}>{p.moq ?? "–"}</td>
      <td className={table.num}>{p.lead_time_days != null ? t("procurement.leadDays", { n: p.lead_time_days }) : "–"}</td>
      <td>
        {canWrite ? (
          <Button
            size="sm"
            variant="ghost"
            className={styles.star}
            aria-pressed={p.is_preferred}
            aria-label={t("procurement.makePreferred", { to: supplier.name, item: label })}
            disabled={p.is_preferred}
            loading={action.pending}
            onClick={async () => {
              const r = await action.run(() => api.procurement.setSupplierProduct(supplier.id, p.variant_id, { is_preferred: true }));
              if (r) {
                onChange(r.items);
                toast(t("procurement.preferredSet"));
              }
            }}
          >
            {p.is_preferred ? "★" : "☆"}
          </Button>
        ) : p.is_preferred ? (
          "★"
        ) : (
          "–"
        )}
        {p.is_preferred ? <span className="srOnly">{t("procurement.preferred")}</span> : null}
      </td>
      {canWrite ? (
        <td>
          <Button
            size="sm"
            variant="ghost"
            aria-label={t("procurement.removeItem", { item: label })}
            onClick={async () => {
              const r = await action.run(() => api.procurement.removeSupplierProduct(supplier.id, p.variant_id));
              if (r) {
                onChange(r.items);
                toast(t("procurement.productRemoved"));
              }
            }}
          >
            {t("procurement.remove")}
          </Button>
        </td>
      ) : null}
    </tr>
  );
}

function AddProductForm({ supplierId, exclude, onSaved }: { supplierId: string; exclude: string[]; onSaved: (items: SupplierProduct[]) => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [picked, setPicked] = useState<PickedVariant | null>(null);
  const [f, setF] = useState({ sku: "", cost: "", moq: "", lead: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!picked) return;
    const cost = toMinor(f.cost);
    const errs: Record<string, string> = {};
    if (cost !== null && Number.isNaN(cost)) errs.cost = t("procurement.errAmount");
    const moq = f.moq ? Number.parseInt(f.moq, 10) : null;
    const lead = f.lead ? Number.parseInt(f.lead, 10) : null;
    if (lead !== null && lead > 365) errs.lead = t("procurement.errLead");
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const r = await action.run(() =>
      api.procurement.setSupplierProduct(supplierId, picked.variant_id, {
        supplier_sku: f.sku.trim() || null,
        cost_minor: cost,
        moq: moq && moq > 0 ? moq : null,
        lead_time_days: lead,
      }),
    );
    if (r) {
      toast(t("procurement.productSaved"));
      onSaved(r.items);
    }
  };
  return (
    <form onSubmit={submit} noValidate style={{ display: "grid", gap: "var(--space-3)" }}>
      <ErrorAlert error={action.error} />
      {picked ? (
        <div className={styles.chosen}>
          <strong>{itemLabel(picked.title, picked.variant)}</strong>
          <Button size="sm" variant="ghost" onClick={() => setPicked(null)}>
            {t("procurement.pickerBack")}
          </Button>
        </div>
      ) : (
        <VariantPicker
          exclude={exclude}
          onPick={(v) => {
            setPicked(v);
            setF((s) => ({ ...s, cost: fromMinor(v.cost_minor) }));
          }}
        />
      )}
      {picked ? (
        <>
          <div className={styles.grid2}>
            <TextField label={t("procurement.cost")} inputMode="decimal" value={f.cost} onChange={(e) => setF((s) => ({ ...s, cost: e.target.value }))} error={errors.cost} optionalLabel={t("common.optional")} />
            <TextField label={t("procurement.supplierSku")} value={f.sku} onChange={(e) => setF((s) => ({ ...s, sku: e.target.value }))} maxLength={80} optionalLabel={t("common.optional")} />
            <TextField label={t("procurement.moq")} inputMode="numeric" value={f.moq} onChange={(e) => setF((s) => ({ ...s, moq: e.target.value.replace(/[^\d]/g, "") }))} optionalLabel={t("common.optional")} />
            <TextField label={t("procurement.leadTimeItem")} inputMode="numeric" value={f.lead} onChange={(e) => setF((s) => ({ ...s, lead: e.target.value.replace(/[^\d]/g, "") }))} error={errors.lead} optionalLabel={t("common.optional")} />
          </div>
          <div className={styles.row}>
            <Button type="submit" variant="primary" loading={action.pending}>
              {t("procurement.addProduct")}
            </Button>
          </div>
        </>
      ) : null}
    </form>
  );
}

function PerformanceSection({ supplier, available, onRefreshed }: { supplier: SupplierDetailT; available: boolean; onRefreshed: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  if (!available)
    return (
      <InlineAlert tone="info" live={false}>
        {t("procurement.perfUpsell")}
      </InlineAlert>
    );
  return (
    <section className={styles.card} aria-labelledby="perf-title" data-testid="supplier-performance">
      <div className={styles.head}>
        <h2 id="perf-title">{t("procurement.perfTitle")}</h2>
        <Button
          size="sm"
          variant="ghost"
          loading={action.pending}
          onClick={async () => {
            if (await action.run(() => api.procurement.refreshPerformance())) {
              toast(t("procurement.perfRefreshed"));
              onRefreshed();
            }
          }}
        >
          {t("procurement.perfRefresh")}
        </Button>
      </div>
      <ErrorAlert error={action.error} />
      {supplier.performance ? <PerformanceCard p={supplier.performance} currency={supplier.currency} /> : <span className={styles.muted}>{t("procurement.perfEmpty")}</span>}
    </section>
  );
}

/** SPI-001: metric tiles + the per-unit economics (price − landed − defects − returns − fees). */
export function PerformanceCard({ p, currency }: { p: SupplierPerformance; currency?: string }) {
  const { t, money: fmt, number } = useI18n();
  const money = (minor: number) => fmt(minor, currency);
  const pct = (x: number | null) => (x === null ? "–" : `${number(Math.round(x * 1000) / 10)}%`);
  const neg = (x: number | null) => (x === null ? "–" : `−${money(x)}`);
  const c = p.components;
  const lead =
    p.lead_time_days_avg === null
      ? "–"
      : p.lead_time_days_sd === null
        ? t("procurement.mLeadValueOne", { avg: number(p.lead_time_days_avg) })
        : t("procurement.mLeadValue", { avg: number(p.lead_time_days_avg), sd: number(p.lead_time_days_sd) });
  return (
    <>
      <span className={styles.muted}>{t("procurement.perfHint", { days: p.window_days })}</span>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>{t("procurement.mReceived")}</dt>
          <dd>{number(p.received_units)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mLanded")}</dt>
          <dd>{p.avg_landed_cost_minor != null ? money(p.avg_landed_cost_minor) : "–"}</dd>
        </div>
        <div className={styles.metric} data-testid="perf-defect">
          <dt>{t("procurement.mDefect")}</dt>
          <dd>{pct(p.defect_rate)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mSold")}</dt>
          <dd>{number(p.sold_units)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mReturns")}</dt>
          <dd>{pct(p.return_rate)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mQuality")}</dt>
          <dd>{pct(p.quality_return_rate)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mOnTime")}</dt>
          <dd>{pct(p.on_time_rate)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mLead")}</dt>
          <dd>{lead}</dd>
        </div>
        <div className={styles.metric}>
          <dt>{t("procurement.mFill")}</dt>
          <dd>{pct(p.fill_rate)}</dd>
        </div>
      </dl>
      <h3 style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{t("procurement.econTitle")}</h3>
      {p.basis === "no_sales_yet" || p.contribution_per_unit_minor === null ? (
        <span className={styles.muted} data-testid="perf-no-sales">
          {t("procurement.noSalesYet")}
        </span>
      ) : null}
      <dl className={styles.econ} data-testid="perf-econ">
        <dt>{t("procurement.econPrice")}</dt>
        <dd>{c.price != null ? money(c.price) : "–"}</dd>
        <dt>{t("procurement.econLanded")}</dt>
        <dd>{neg(c.landed)}</dd>
        <dt>{t("procurement.econDefect")}</dt>
        <dd>{neg(c.defect_cost)}</dd>
        <dt>{t("procurement.econReturns")}</dt>
        <dd>{neg(c.return_cost)}</dd>
        <dt>{t("procurement.econFees")}</dt>
        <dd>{neg(c.fees_fulfilment)}</dd>
        <dt className={styles.result2}>{t("procurement.econResult")}</dt>
        <dd className={styles.result2} data-testid="perf-contribution">
          {p.contribution_per_unit_minor != null ? money(p.contribution_per_unit_minor) : "–"}
        </dd>
      </dl>
      {p.not_included.length ? (
        <div data-testid="perf-not-included">
          <span className={styles.muted}>{t("procurement.notIncludedTitle")}</span>
          <ul className={styles.niList}>
            {p.not_included.map((code) => (
              <li key={code}>{t.dynamic(`procurement.ni_${code}`) ?? code}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
