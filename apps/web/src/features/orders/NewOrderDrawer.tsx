"use client";

import type { AddressInput, Customer, CustomerDetail, OrderDetail, ProductSummary, VariantStock } from "@commerce-os/api-client";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { SectionHeader, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { AddressFields, EMPTY_ADDRESS, ErrorAlert, fieldErrors } from "./shared";
import styles from "./orders.module.css";

interface Choice {
  id: string;
  title: string;
  price_minor: number;
  stock: VariantStock | null;
}

interface Line {
  key: string;
  product_title: string;
  choices: Choice[];
  variant_id: string;
  quantity: number;
}

const chosen = (l: Line) => l.choices.find((c) => c.id === l.variant_id) ?? l.choices[0]!;

/** Seller-entered order (ORD-007): customer, items with live stock, structured address, payment. */
export function NewOrderDrawer({
  open,
  onOpenChange,
  onCreated,
  initialCustomerId,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onCreated: (o: OrderDetail) => void;
  initialCustomerId?: string;
}) {
  const { t, money } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const idem = useIdempotencyKey();
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [custQuery, setCustQuery] = useState("");
  const [custResults, setCustResults] = useState<Customer[]>([]);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [prodQuery, setProdQuery] = useState("");
  const [prodResults, setProdResults] = useState<ProductSummary[]>([]);
  const [lines, setLines] = useState<Line[]>([]);
  const [addressId, setAddressId] = useState<string>("new");
  const [address, setAddress] = useState<AddressInput>(EMPTY_ADDRESS);
  const [payment, setPayment] = useState<"cod" | "prepaid">("cod");
  const [fee, setFee] = useState("");
  const [feeTouched, setFeeTouched] = useState(false);
  const [feeFromTable, setFeeFromTable] = useState(false);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!open) return;
    action.clear();
    idem.reset();
    if (initialCustomerId) void api.customers.get(initialCustomerId).then(pickCustomer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    const q = custQuery.trim();
    if (q.length < 2) return setCustResults([]);
    const id = setTimeout(() => void api.customers.list({ q, limit: 6 }).then((p) => setCustResults(p.items)), 250);
    return () => clearTimeout(id);
  }, [custQuery, api]);

  useEffect(() => {
    const q = prodQuery.trim();
    if (q.length < 2) return setProdResults([]);
    const id = setTimeout(() => void api.catalog.products({ q, status: "active", limit: 6 }).then((p) => setProdResults(p.items)), 250);
    return () => clearTimeout(id);
  }, [prodQuery, api]);

  function pickCustomer(c: CustomerDetail) {
    setCustomer(c);
    setCustResults([]);
    setCustQuery("");
    const def = c.addresses.find((a) => a.is_default) ?? c.addresses[0];
    setAddressId(def ? def.id : "new");
    setAddress({ ...EMPTY_ADDRESS, recipient_name: c.display_name, phone: c.phone?.replace("+977", "") ?? "" });
  }

  const addProduct = async (p: ProductSummary) => {
    setProdQuery("");
    setProdResults([]);
    const [detail, stock] = await Promise.all([api.catalog.product(p.id), api.inventory.productStock(p.id)]);
    const byVariant = new Map(stock.variants.map((v) => [v.variant_id, v]));
    const choices: Choice[] = detail.variants
      .filter((v) => v.status === "active")
      .map((v) => ({ id: v.id, title: v.title, price_minor: v.price.amount_minor, stock: byVariant.get(v.id) ?? null }));
    if (!choices.length) return;
    // Default to the first option that can be sold (untracked counts as sellable).
    const first = choices.find((c) => !c.stock?.tracked || c.stock.available > 0) ?? choices[0]!;
    setLines((prev) => [...prev, { key: crypto.randomUUID(), product_title: detail.title, choices, variant_id: first.id, quantity: 1 }]);
  };

  const itemsTotal = useMemo(() => lines.reduce((sum, l) => sum + chosen(l).price_minor * l.quantity, 0), [lines]);
  const destDistrict = customer && addressId !== "new" ? (customer.addresses.find((a) => a.id === addressId)?.district ?? "") : address.district;

  // The merchant's delivery-charge table fills the fee until the seller types their own.
  useEffect(() => {
    if (!open || feeTouched || !destDistrict) return;
    let live = true;
    const id = setTimeout(() => {
      api.couriers.quoteFee(destDistrict, itemsTotal).then(
        (r) => {
          if (!live || !r.quote) return;
          setFee(String(r.quote.fee_minor / 100));
          setFeeFromTable(true);
        },
        () => undefined, // no table or no permission: the seller types the fee
      );
    }, 250);
    return () => {
      live = false;
      clearTimeout(id);
    };
  }, [open, feeTouched, destDistrict, itemsTotal, api]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (lines.length === 0) return;
    const body = {
      lines: lines.map((l) => ({ variant_id: l.variant_id, quantity: l.quantity })),
      customer_id: customer?.id ?? null,
      customer_name: customer ? null : newName.trim() || null,
      customer_phone: customer ? null : newPhone.trim() || null,
      address_id: customer && addressId !== "new" ? addressId : null,
      address: customer && addressId !== "new" ? null : { ...address, recipient_name: address.recipient_name || newName, phone: address.phone || newPhone },
      payment_method: payment,
      delivery_fee_minor: Math.round(Number(fee || 0) * 100),
      notes: notes.trim() || null,
    };
    const o = await action.run(() => api.orders.create(body, { idempotencyKey: idem.keyFor(body) }));
    if (o) {
      toast(t("orders.new.created", { number: o.number }));
      onOpenChange(false);
      setLines([]);
      setCustomer(null);
      onCreated(o);
    }
  };

  const errs = fieldErrors(action.error);
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("orders.new.title")}
      wide
      footer={
        <Button type="submit" form="new-order" variant="primary" loading={action.pending} disabled={lines.length === 0}>
          {t("orders.new.create")}
        </Button>
      }
    >
      <form id="new-order" onSubmit={submit} className={styles.side} noValidate={false}>
        <ErrorAlert error={action.error} />
        <section>
          <SectionHeader title={t("orders.new.customer")} />
          {customer ? (
            <div className={styles.actions}>
              <strong>{customer.display_name}</strong>
              <span className={styles.meta}>{customer.phone}</span>
              <Button size="sm" variant="ghost" onClick={() => setCustomer(null)}>
                {t("orders.new.change")}
              </Button>
            </div>
          ) : (
            <>
              <TextField label={t("orders.new.searchCustomer")} value={custQuery} onChange={(e) => setCustQuery(e.target.value)} type="search" />
              {custResults.length ? (
                <ul className={styles.results}>
                  {custResults.map((c) => (
                    <li key={c.id}>
                      <button type="button" onClick={() => void api.customers.get(c.id).then(pickCustomer)}>
                        <span>{c.display_name}</span>
                        <span className={styles.meta}>{c.phone}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
              <p className={styles.meta} style={{ marginTop: "var(--space-2)" }}>
                {t("orders.new.orNew")}
              </p>
              <div className={styles.formGrid}>
                <TextField label={t("orders.new.name")} value={newName} onChange={(e) => setNewName(e.target.value)} maxLength={160} />
                <TextField label={t("orders.new.phone")} value={newPhone} onChange={(e) => setNewPhone(e.target.value)} inputMode="tel" maxLength={24} />
              </div>
            </>
          )}
        </section>

        <section>
          <SectionHeader title={t("orders.new.items")} />
          <TextField label={t("orders.new.searchProduct")} value={prodQuery} onChange={(e) => setProdQuery(e.target.value)} type="search" />
          {prodResults.length ? (
            <ul className={styles.results}>
              {prodResults.map((p) => (
                <li key={p.id}>
                  <button type="button" onClick={() => void addProduct(p)}>
                    <span>{p.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          <div className={styles.side} style={{ marginTop: "var(--space-3)" }} data-testid="order-lines">
            {lines.map((l, i) => {
              const c = chosen(l);
              const label = c.title === "Default" ? l.product_title : `${l.product_title} (${c.title})`;
              return (
                <div key={l.key} className={styles.lineRow}>
                  <div>
                    {l.choices.length > 1 ? (
                      <SelectField
                        label={l.product_title}
                        value={l.variant_id}
                        onChange={(e) => setLines((prev) => prev.map((x, j) => (j === i ? { ...x, variant_id: e.target.value } : x)))}
                      >
                        {l.choices.map((ch) => (
                          <option key={ch.id} value={ch.id} disabled={!!ch.stock?.tracked && ch.stock.available <= 0}>
                            {ch.title} · {ch.stock?.tracked ? t("orders.new.stockLeft", { n: ch.stock.available }) : t("orders.new.untracked")}
                          </option>
                        ))}
                      </SelectField>
                    ) : (
                      <strong>{label}</strong>
                    )}
                    <div className={styles.meta}>
                      {money(c.price_minor)} · {c.stock?.tracked ? t("orders.new.stockLeft", { n: c.stock.available }) : t("orders.new.untracked")}
                    </div>
                  </div>
                  <TextField
                    label={t("orders.new.qty")}
                    type="number"
                    min={1}
                    max={c.stock?.tracked ? Math.max(1, c.stock.available) : 999}
                    value={l.quantity}
                    onChange={(e) => setLines((prev) => prev.map((x, j) => (j === i ? { ...x, quantity: Math.max(1, Number(e.target.value) || 1) } : x)))}
                  />
                  <Button size="sm" variant="ghost" aria-label={t("orders.new.remove", { title: label })} onClick={() => setLines((prev) => prev.filter((_, j) => j !== i))}>
                    ×
                  </Button>
                </div>
              );
            })}
            {lines.length === 0 ? <p className={styles.meta}>{t("orders.new.noItems")}</p> : <p className={styles.meta}>{t("orders.new.total")}: {money(itemsTotal)}</p>}
          </div>
        </section>

        <section>
          <SectionHeader title={t("orders.new.address")} />
          {customer && customer.addresses.length ? (
            <SelectField label={t("orders.new.savedAddress")} value={addressId} onChange={(e) => setAddressId(e.target.value)}>
              {customer.addresses.map((a) => (
                <option key={a.id} value={a.id}>
                  {[a.area, `${a.municipality}-${a.ward}`, a.district_name].filter(Boolean).join(", ")}
                </option>
              ))}
              <option value="new">{t("orders.new.newAddress")}</option>
            </SelectField>
          ) : null}
          {!customer || addressId === "new" ? <AddressFields value={address} onChange={setAddress} errors={errs} /> : null}
        </section>

        <section>
          <SectionHeader title={t("orders.new.payment")} />
          <div className={styles.formGrid}>
            <SelectField label={t("orders.new.payment")} value={payment} onChange={(e) => setPayment(e.target.value as "cod" | "prepaid")}>
              <option value="cod">{t("orders.new.cod")}</option>
              <option value="prepaid">{t("orders.new.prepaid")}</option>
            </SelectField>
            <TextField
              label={t("orders.new.deliveryFee")}
              hint={feeFromTable && !feeTouched ? t("orders.new.feeFromTable") : undefined}
              type="number"
              inputMode="decimal"
              min={0}
              step="1"
              value={fee}
              onChange={(e) => {
                setFeeTouched(true);
                setFee(e.target.value);
              }}
            />
          </div>
          <TextField label={t("orders.new.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={2000} />
        </section>
      </form>
    </Drawer>
  );
}
