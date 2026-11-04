"use client";

import type { Customer, CustomerSegment } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import products from "../products/products.module.css";

type Seg = "all" | CustomerSegment;
const SEGS: Seg[] = ["all", "new", "repeat", "inactive"];

export function CustomersList() {
  const { t, relative } = useI18n();
  const { api, merchantId } = useAuth();
  const [seg, setSeg] = useState<Seg>("all");
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [state, setState] = useState<{ status: "loading" } | { status: "error"; error: unknown } | { status: "ready"; items: Customer[] }>({ status: "loading" });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const id = setTimeout(() => setQ(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);
  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    api.customers.list({ q: q || undefined, segment: seg === "all" ? undefined : seg, limit: 100 }).then(
      (p) => live && setState({ status: "ready", items: p.items }),
      (error: unknown) => live && setState({ status: "error", error }),
    );
    return () => {
      live = false;
    };
  }, [api, merchantId, q, seg, nonce]);

  return (
    <>
      <PageHeader title={t("customers.title")} subtitle={t("customers.subtitle")} />
      <div className={products.toolbar}>
        <div role="tablist" aria-label={t("customers.filters")} className={products.tabs}>
          {SEGS.map((s) => (
            <button key={s} type="button" role="tab" aria-selected={seg === s} className={products.tab} onClick={() => setSeg(s)}>
              {t(`customers.segment.${s}`)}
            </button>
          ))}
        </div>
        <div className={products.search} role="search">
          <Icon name="search" />
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("customers.search")} aria-label={t("customers.search")} maxLength={100} />
        </div>
      </div>
      {state.status === "loading" ? (
        <TableSkeleton columns="1.4fr 1fr 1fr" label={t("common.loading")} />
      ) : state.status === "error" ? (
        <QueryError error={state.error} onRetry={() => setNonce((n) => n + 1)} />
      ) : state.items.length === 0 ? (
        <EmptyState title={t("customers.empty")} body={t("customers.emptyBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-label={t("customers.title")} data-testid="customers">
            <thead>
              <tr>
                <th scope="col">{t("customers.colName")}</th>
                <th scope="col">{t("customers.colPhone")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("customers.colSeen")}
                </th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link href={`/customers/${c.id}`} className={products.titleLink}>
                      {c.display_name}
                    </Link>
                  </td>
                  <td>{c.phone ?? "–"}</td>
                  <td className={[table.hideSm, table.muted].join(" ")}>{c.last_seen_at ? relative(c.last_seen_at) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
