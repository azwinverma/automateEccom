"use client";

import type { AddressInput, Customer } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { NewOrderDrawer } from "../orders/NewOrderDrawer";
import { AddressFields, EMPTY_ADDRESS, ErrorAlert, fieldErrors, OrderStatusBadge } from "../orders/shared";
import ordersCss from "../orders/orders.module.css";
import products from "../products/products.module.css";

export function CustomerDetailView({ id }: { id: string }) {
  const { t, money, relative } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const cust = useApiQuery((a) => a.customers.get(id), [id]);
  const orders = useApiQuery((a) => (can("orders.read") ? a.orders.list({ customer_id: id, limit: 20 }) : Promise.resolve({ items: [], next_cursor: null })), [id]);
  const action = useAction();
  const [addOpen, setAddOpen] = useState(false);
  const [address, setAddress] = useState<AddressInput>(EMPTY_ADDRESS);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeQuery, setMergeQuery] = useState("");
  const [mergeResults, setMergeResults] = useState<Customer[]>([]);
  const [mergeSource, setMergeSource] = useState<Customer | null>(null);
  const [orderOpen, setOrderOpen] = useState(false);

  useEffect(() => {
    const q = mergeQuery.trim();
    if (q.length < 2) return setMergeResults([]);
    const tid = setTimeout(() => void api.customers.list({ q, limit: 6 }).then((p) => setMergeResults(p.items.filter((c) => c.id !== id))), 250);
    return () => clearTimeout(tid);
  }, [mergeQuery, api, id]);

  if (cust.state.status === "loading") return <TableSkeleton columns="2fr 1fr" rows={5} label={t("common.loading")} />;
  if (cust.state.status === "error") return <QueryError error={cust.state.error} onRetry={cust.reload} />;
  const c = cust.state.data;

  return (
    <div data-testid="customer-detail">
      <div className={products.editorHeader}>
        <div className={products.editorTitle}>
          <Link href="/customers" className={products.backLink}>
            ← {t("customers.back")}
          </Link>
          <h1>{c.display_name}</h1>
          <p className={ordersCss.meta}>
            {[c.phone, c.email].filter(Boolean).join(" · ")}
            {c.identities.map((i) => (
              <span key={`${i.provider}:${i.external_id}`}>
                {" "}
                <Badge tone="neutral" dot={false}>
                  {i.provider}
                </Badge>
              </span>
            ))}
          </p>
        </div>
        <div className={ordersCss.actions}>
          {can("orders.write") ? (
            <Button variant="primary" onClick={() => setOrderOpen(true)}>
              <Icon name="plus" />
              {t("orders.newOrder")}
            </Button>
          ) : null}
          {can("customers.merge") ? (
            <Button variant="ghost" onClick={() => setMergeOpen(true)}>
              {t("customers.merge")}
            </Button>
          ) : null}
        </div>
      </div>
      <ErrorAlert error={action.error} />
      <div className={ordersCss.layout}>
        <section className={ordersCss.panel} aria-labelledby="c-orders">
          <h2 id="c-orders">{t("customers.orders")}</h2>
          {orders.state.status === "success" && orders.state.data.items.length ? (
            <div className={table.wrap}>
              <table className={[table.table, table.dense].join(" ")}>
                <tbody>
                  {orders.state.data.items.map((o) => (
                    <tr key={o.id}>
                      <td>
                        <Link href={`/orders/${o.id}`}>#{o.number}</Link>
                      </td>
                      <td>
                        <OrderStatusBadge status={o.status} />
                      </td>
                      <td className={table.num}>{money(o.total.amount_minor, o.total.currency)}</td>
                      <td className={table.muted}>{relative(o.placed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className={ordersCss.meta}>{t("customers.noOrders")}</p>
          )}
        </section>
        <aside className={ordersCss.panel} aria-labelledby="c-addr">
          <div className={ordersCss.actions} style={{ justifyContent: "space-between" }}>
            <h2 id="c-addr">{t("customers.addresses")}</h2>
            {can("customers.write") ? (
              <Button size="sm" onClick={() => setAddOpen(true)}>
                {t("customers.addAddress")}
              </Button>
            ) : null}
          </div>
          {c.addresses.length === 0 ? <p className={ordersCss.meta}>{t("customers.noAddresses")}</p> : null}
          <ul className={ordersCss.timeline}>
            {c.addresses.map((a) => (
              <li key={a.id}>
                <address className={ordersCss.address}>
                  {a.recipient_name} · {a.phone}
                  <br />
                  {[a.area, `${a.municipality}-${a.ward}`, a.district_name].filter(Boolean).join(", ")}
                </address>
                <span className={ordersCss.meta}>
                  {a.is_default ? t("customers.default") : null}
                  {can("customers.write") ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={async () => (await action.run(() => api.customers.removeAddress(c.id, a.id))) !== undefined && cust.reload()}
                    >
                      {t("customers.removeAddress")}
                    </Button>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        </aside>
      </div>

      <Drawer
        open={addOpen}
        onOpenChange={setAddOpen}
        title={t("customers.addAddress")}
        footer={
          <Button
            variant="primary"
            loading={action.pending}
            onClick={async () => {
              if (await action.run(() => api.customers.addAddress(c.id, address))) {
                toast(t("customers.addressAdded"));
                setAddOpen(false);
                setAddress(EMPTY_ADDRESS);
                cust.reload();
              }
            }}
          >
            {t("customers.addAddress")}
          </Button>
        }
      >
        <ErrorAlert error={action.error} />
        <AddressFields value={{ ...address, recipient_name: address.recipient_name || c.display_name, phone: address.phone || (c.phone ?? "").replace("+977", "") }} onChange={setAddress} errors={fieldErrors(action.error)} />
      </Drawer>

      <ConfirmDialog
        open={mergeOpen}
        onOpenChange={(v) => {
          setMergeOpen(v);
          if (!v) setMergeSource(null);
        }}
        title={t("customers.merge")}
        body={t("customers.mergeHint")}
        confirmLabel={t("customers.mergeConfirm", { name: c.display_name })}
        pending={action.pending}
        onConfirm={async () => {
          if (!mergeSource) return;
          if (await action.run(() => api.customers.merge(c.id, mergeSource.id))) {
            toast(t("customers.merged"));
            setMergeOpen(false);
            setMergeSource(null);
            cust.reload();
            orders.reload();
          }
        }}
      >
        <TextField label={t("customers.search")} value={mergeSource ? mergeSource.display_name : mergeQuery} onChange={(e) => (setMergeSource(null), setMergeQuery(e.target.value))} type="search" />
        {!mergeSource && mergeResults.length ? (
          <ul className={ordersCss.results}>
            {mergeResults.map((m) => (
              <li key={m.id}>
                <button type="button" onClick={() => setMergeSource(m)}>
                  <span>{m.display_name}</span>
                  <span className={ordersCss.meta}>{m.phone}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </ConfirmDialog>
      <NewOrderDrawer open={orderOpen} onOpenChange={setOrderOpen} initialCustomerId={c.id} onCreated={(o) => router.push(`/orders/${o.id}`)} />
    </div>
  );
}
