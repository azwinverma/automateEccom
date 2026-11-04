"use client";

import type { OrderSummary } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import products from "../products/products.module.css";
import { NewOrderDrawer } from "./NewOrderDrawer";
import { OrderStatusBadge, PaymentBadge, TODO_STATUSES } from "./shared";

type Tab = "todo" | "review" | "all";
const TABS: { key: Tab; label: "orders.tabAction" | "orders.tabReview" | "orders.tabAll" }[] = [
  { key: "todo", label: "orders.tabAction" },
  { key: "review", label: "orders.tabReview" },
  { key: "all", label: "orders.tabAll" },
];

type State = { status: "loading" } | { status: "error"; error: unknown } | { status: "ready"; items: OrderSummary[]; next: string | null; more: boolean };

export function OrdersList() {
  const { t, money, relative, dateTime } = useI18n();
  const { api, merchantId, can } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("todo");
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [state, setState] = useState<State>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setQ(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);

  const filter = () => ({
    status: tab === "todo" ? TODO_STATUSES.join(",") : undefined,
    needs_review: tab === "review" ? true : undefined,
    q: q || undefined,
  });

  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    api.orders.list({ ...filter(), limit: 50 }).then(
      (p) => live && setState({ status: "ready", items: p.items, next: p.next_cursor, more: false }),
      (error: unknown) => live && setState({ status: "error", error }),
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, merchantId, tab, q, nonce]);

  const loadMore = async () => {
    if (state.status !== "ready" || !state.next) return;
    setState({ ...state, more: true });
    const p = await api.orders.list({ ...filter(), limit: 50, cursor: state.next });
    setState({ status: "ready", items: [...state.items, ...p.items], next: p.next_cursor, more: false });
  };

  return (
    <>
      <PageHeader
        title={t("orders.title")}
        subtitle={t("orders.subtitle")}
        actions={
          can("orders.write") ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" />
              {t("orders.newOrder")}
            </Button>
          ) : null
        }
      />
      <div className={products.toolbar}>
        <div role="tablist" aria-label={t("orders.filters")} className={products.tabs}>
          {TABS.map((tb) => (
            <button key={tb.key} type="button" role="tab" aria-selected={tab === tb.key} className={products.tab} onClick={() => setTab(tb.key)}>
              {t(tb.label)}
            </button>
          ))}
        </div>
        <div className={products.search} role="search">
          <Icon name="search" />
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("orders.search")} aria-label={t("orders.search")} maxLength={100} />
        </div>
      </div>
      {state.status === "loading" ? (
        <TableSkeleton columns="0.6fr 1.4fr 1fr 1fr 1fr" label={t("common.loading")} />
      ) : state.status === "error" ? (
        <QueryError error={state.error} onRetry={() => setNonce((n) => n + 1)} />
      ) : state.items.length === 0 ? (
        <EmptyState title={q || tab !== "all" ? t("orders.emptyFiltered") : t("orders.empty")} body={q || tab !== "all" ? undefined : t("orders.emptyBody")} />
      ) : (
        <>
          <div className={table.wrap}>
            <table className={table.table} aria-label={t("orders.title")} data-testid="orders">
              <thead>
                <tr>
                  <th scope="col">{t("orders.colOrder")}</th>
                  <th scope="col">{t("orders.colCustomer")}</th>
                  <th scope="col">{t("orders.colStatus")}</th>
                  <th scope="col" className={table.hideSm}>
                    {t("orders.colPayment")}
                  </th>
                  <th scope="col" className={table.num}>
                    {t("orders.colTotal")}
                  </th>
                  <th scope="col" className={table.hideSm}>
                    {t("orders.colPlaced")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {state.items.map((o) => (
                  <tr key={o.id} data-status={o.status}>
                    <td>
                      <Link href={`/orders/${o.id}`} className={products.titleLink}>
                        #{o.number}
                      </Link>
                      <div className={table.muted} style={{ fontSize: "var(--font-size-xs)" }}>
                        {t(`orders.source.${o.source}`)}
                        {o.external_number ? ` · ${o.external_number}` : ""}
                      </div>
                    </td>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>{o.customer?.display_name ?? "–"}</strong>
                        {o.customer?.phone ? <span>{o.customer.phone}</span> : null}
                      </div>
                    </td>
                    <td>
                      <OrderStatusBadge status={o.status} />
                      {o.needs_review ? (
                        <div style={{ marginTop: 4 }}>
                          <Badge tone="warning">{t.dynamic(`orders.review.${o.needs_review}`) ?? o.needs_review}</Badge>
                        </div>
                      ) : null}
                    </td>
                    <td className={table.hideSm}>
                      <PaymentBadge status={o.payment_status} />
                    </td>
                    <td className={table.num}>{money(o.total.amount_minor, o.total.currency)}</td>
                    <td className={[table.hideSm, table.muted].join(" ")}>
                      <time dateTime={o.placed_at} title={dateTime(o.placed_at)}>
                        {relative(o.placed_at)}
                      </time>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {state.next ? (
            <div style={{ marginTop: "var(--space-3)" }}>
              <Button size="sm" loading={state.more} onClick={loadMore}>
                {t("orders.loadMore")}
              </Button>
            </div>
          ) : null}
        </>
      )}
      <NewOrderDrawer open={creating} onOpenChange={setCreating} onCreated={(o) => router.push(`/orders/${o.id}`)} />
    </>
  );
}
