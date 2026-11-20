"use client";

import type { PurchaseOrder, Supplier, SupplierProduct } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { SelectField, TextField } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./procurement.module.css";
import { fromMinor, itemLabel, landedUnitCosts, toMinor } from "./shared";
import { VariantPicker, type PickedVariant } from "./VariantPicker";

interface LineDraft {
  key: string;
  variant_id: string;
  title: string;
  variant: string | null;
  sku: string | null;
  quantity: string;
  unitCost: string;
}

let lineSeq = 0;
const newKey = () => `l${++lineSeq}`;
const newIdem = () => `po-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

/** Create a PO (new) or edit a draft (existing). Landed cost and the MOQ warning update as you type. */
export function PurchaseOrderForm({
  suppliers,
  existing,
  initialSupplierId,
  onSaved,
}: {
  suppliers: Supplier[];
  existing?: PurchaseOrder;
  initialSupplierId?: string;
  onSaved: (po: PurchaseOrder) => void;
}) {
  const { t, money: fmt } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const money = (minor: number) => fmt(minor, currency);
  const [supplierId, setSupplierId] = useState(existing?.supplier.id ?? initialSupplierId ?? "");
  const [lines, setLines] = useState<LineDraft[]>(
    () =>
      existing?.lines.map((l) => ({
        key: newKey(),
        variant_id: l.variant_id,
        title: l.title ?? "",
        variant: l.variant,
        sku: l.sku,
        quantity: String(l.quantity),
        unitCost: fromMinor(l.unit_cost_minor),
      })) ?? [],
  );
  const [freight, setFreight] = useState(fromMinor(existing?.freight_minor ?? 0) === "0" ? "" : fromMinor(existing?.freight_minor));
  const [duty, setDuty] = useState(existing?.duty_minor ? fromMinor(existing.duty_minor) : "");
  const [other, setOther] = useState(existing?.other_minor ? fromMinor(existing.other_minor) : "");
  const [expected, setExpected] = useState(existing?.expected_at ? existing.expected_at.slice(0, 10) : "");
  const [notes, setNotes] = useState(existing?.notes ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [catalog, setCatalog] = useState<Record<string, SupplierProduct>>({});
  const [currency, setCurrency] = useState<string | undefined>(existing?.currency);
  const idem = useRef(newIdem());

  // The supplier's own price, MOQ and lead time for each variant (prefills price, drives the MOQ warning).
  useEffect(() => {
    if (!supplierId) {
      setCatalog({});
      return;
    }
    let cancelled = false;
    api.procurement.supplier(supplierId).then(
      (s) => {
        if (cancelled) return;
        setCatalog(Object.fromEntries(s.products.map((p) => [p.variant_id, p])));
        if (s.currency) setCurrency(s.currency);
      },
      () => !cancelled && setCatalog({}),
    );
    return () => {
      cancelled = true;
    };
  }, [api, supplierId]);

  const parsed = lines.map((l) => ({ qty: Number.parseInt(l.quantity, 10), cost: toMinor(l.unitCost) }));
  const extras = [freight, duty, other].map((x) => toMinor(x) ?? 0).reduce((a, b) => a + (Number.isNaN(b) ? 0 : b), 0);
  const valid = parsed.map((p) => ({ quantity: Number.isFinite(p.qty) && p.qty > 0 ? p.qty : 0, unit_cost_minor: p.cost !== null && !Number.isNaN(p.cost) ? p.cost : 0 }));
  const landed = landedUnitCosts(valid, extras);
  const subtotal = valid.reduce((s, l) => s + l.quantity * l.unit_cost_minor, 0);

  const add = (v: PickedVariant) => {
    const known = catalog[v.variant_id];
    const cost = known?.cost_minor ?? v.cost_minor;
    setLines((ls) => [
      ...ls,
      {
        key: newKey(),
        variant_id: v.variant_id,
        title: v.title,
        variant: v.variant,
        sku: v.sku,
        quantity: known?.moq ? String(known.moq) : "1",
        unitCost: fromMinor(cost),
      },
    ]);
  };
  const update = (key: string, patch: Partial<LineDraft>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!supplierId) errs.supplier = t("procurement.errNoSupplier");
    if (!lines.length) errs.lines = t("procurement.errNoItems");
    lines.forEach((l, i) => {
      if (!(parsed[i]!.qty > 0)) errs[`qty-${l.key}`] = t("procurement.errQty");
      const c = parsed[i]!.cost;
      if (c === null || Number.isNaN(c)) errs[`cost-${l.key}`] = t("procurement.errCost");
    });
    for (const [k, v] of [["freight", freight], ["duty", duty], ["other", other]] as const) {
      const m = toMinor(v);
      if (m !== null && Number.isNaN(m)) errs[k] = t("procurement.errAmount");
    }
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const body = {
      lines: lines.map((l, i) => ({ variant_id: l.variant_id, quantity: parsed[i]!.qty, unit_cost_minor: parsed[i]!.cost })),
      freight_minor: toMinor(freight) ?? 0,
      duty_minor: toMinor(duty) ?? 0,
      other_minor: toMinor(other) ?? 0,
      expected_at: expected ? new Date(`${expected}T12:00:00Z`).toISOString() : null,
      notes: notes.trim() || null,
    };
    const saved = await action.run(() =>
      existing
        ? api.procurement.updatePurchaseOrder(existing.id, { ...body, version: existing.version })
        : api.procurement.createPurchaseOrder({ supplier_id: supplierId, ...body }, { idempotencyKey: idem.current }),
    );
    if (saved) {
      idem.current = newIdem(); // the next creation is a new purchase order
      onSaved(saved);
    }
  };

  const active = suppliers.filter((s) => s.status === "active" || s.id === supplierId);
  return (
    <form onSubmit={submit} noValidate data-testid="po-form" className={styles.card}>
      <ErrorAlert error={action.error} />
      {active.length === 0 ? (
        <InlineAlert tone="info">
          {t("procurement.noSuppliers")} <Link href="/inventory/suppliers">{t("procurement.addSupplierLink")}</Link>
        </InlineAlert>
      ) : null}
      <SelectField
        label={t("procurement.supplier")}
        value={supplierId}
        onChange={(e) => setSupplierId(e.target.value)}
        disabled={Boolean(existing)}
        error={errors.supplier}
        required
      >
        <option value="">{t("procurement.chooseSupplier")}</option>
        {active.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </SelectField>

      <div className={styles.head}>
        <h3>{t("procurement.items")}</h3>
      </div>
      {errors.lines ? <InlineAlert tone="danger">{errors.lines}</InlineAlert> : null}
      <ul className={styles.lines} aria-label={t("procurement.items")}>
        {lines.map((l, i) => {
          const label = itemLabel(l.title, l.variant);
          const moq = catalog[l.variant_id]?.moq;
          const qty = parsed[i]!.qty;
          return (
            <li key={l.key} className={styles.line} data-testid="po-line">
              <div className={styles.lineHead}>
                <strong>{label}</strong>
                <span className={styles.row}>
                  {l.sku ? <span className={styles.muted}>{l.sku}</span> : null}
                  <Button size="sm" variant="ghost" iconOnly aria-label={t("procurement.removeItem", { item: label })} onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))}>
                    <Icon name="close" />
                  </Button>
                </span>
              </div>
              <div className={styles.lineFields}>
                <TextField
                  label={t("procurement.quantity")}
                  inputMode="numeric"
                  value={l.quantity}
                  onChange={(e) => update(l.key, { quantity: e.target.value.replace(/[^\d]/g, "") })}
                  error={errors[`qty-${l.key}`]}
                />
                <TextField
                  label={t("procurement.unitCost")}
                  inputMode="decimal"
                  value={l.unitCost}
                  onChange={(e) => update(l.key, { unitCost: e.target.value })}
                  error={errors[`cost-${l.key}`]}
                />
                <div className={styles.landed} data-testid="po-landed">
                  <span className={styles.muted}>{t("procurement.landed")}</span>
                  <strong>{valid[i]!.unit_cost_minor ? money(landed[i]!) : "–"}</strong>
                </div>
              </div>
              {moq && Number.isFinite(qty) && qty > 0 && qty < moq ? (
                <span className={styles.warn} role="status" data-testid="po-moq-warning">
                  <Icon name="alert" /> {t("procurement.belowMoq", { moq })}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>
      <VariantPicker onPick={add} exclude={lines.map((l) => l.variant_id)} />
      <span className={styles.muted}>{t("procurement.landedHint")}</span>

      <div className={styles.head}>
        <h3>{t("procurement.costs")}</h3>
      </div>
      <span className={styles.muted}>{t("procurement.costsHint")}</span>
      <div className={styles.grid3}>
        <TextField label={t("procurement.freight")} inputMode="decimal" value={freight} onChange={(e) => setFreight(e.target.value)} error={errors.freight} />
        <TextField label={t("procurement.duty")} inputMode="decimal" value={duty} onChange={(e) => setDuty(e.target.value)} error={errors.duty} />
        <TextField label={t("procurement.other")} inputMode="decimal" value={other} onChange={(e) => setOther(e.target.value)} error={errors.other} />
      </div>
      <div className={styles.grid2}>
        <TextField label={t("procurement.expected")} type="date" value={expected} onChange={(e) => setExpected(e.target.value)} optionalLabel={t("common.optional")} />
        <TextField label={t("procurement.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={1000} optionalLabel={t("common.optional")} />
      </div>
      <dl className={styles.totals} data-testid="po-totals">
        <dt>{t("procurement.subtotal")}</dt>
        <dd>{money(subtotal)}</dd>
        <dt>{t("procurement.costs")}</dt>
        <dd>{money(extras)}</dd>
        <dt className={styles.grand}>{t("procurement.total")}</dt>
        <dd className={styles.grand}>{money(subtotal + extras)}</dd>
      </dl>
      <div className={styles.row}>
        <Button type="submit" variant="primary" loading={action.pending}>
          {t("procurement.saveDraft")}
        </Button>
      </div>
    </form>
  );
}
