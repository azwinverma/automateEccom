"use client";

import type { ReturnBucket, ReturnSummary } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import products from "../products/products.module.css";
import { RefundsList } from "./ReturnDetail";
import { ReturnStatusBadge } from "./shared";

const BUCKETS: ReturnBucket[] = ["to_decide", "in_progress", "to_refund", "done"];
type State = { status: "loading" } | { status: "error"; error: unknown } | { status: "ready"; items: ReturnSummary[]; counts: Record<ReturnBucket, number> };

export function ReturnsView() {
  const { t, money, relative, dateTime } = useI18n();
  const { api, merchantId, can } = useAuth();
  const [bucket, setBucket] = useState<ReturnBucket>("to_decide");
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [state, setState] = useState<State>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const pending = useApiQuery((a) => (can("refunds.read") ? a.refunds.list("pending_approval") : Promise.resolve({ items: [] })), [nonce]);

  useEffect(() => {
    const id = setTimeout(() => setQ(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);
  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    api.returns.list({ bucket: q ? undefined : bucket, q: q || undefined, limit: 100 }).then(
      (p) => live && setState({ status: "ready", items: p.items, counts: p.counts }),
      (error: unknown) => live && setState({ status: "error", error }),
    );
    return () => {
      live = false;
    };
  }, [api, merchantId, bucket, q, nonce]);

  const refunds = pending.state.status === "success" ? pending.state.data.items : [];
  return (
    <>
      <PageHeader title={t("returns.title")} subtitle={t("returns.subtitle")} />
      {refunds.length ? <RefundsList refunds={refunds} title={t("returns.refund.toApprove")} onChanged={() => setNonce((n) => n + 1)} /> : null}
      <div className={products.toolbar} style={{ marginTop: refunds.length ? "var(--space-4)" : 0 }}>
        <div role="tablist" aria-label={t("returns.title")} className={products.tabs}>
          {BUCKETS.map((b) => (
            <button key={b} type="button" role="tab" aria-selected={!q && bucket === b} className={products.tab} onClick={() => (setQuery(""), setQ(""), setBucket(b))} data-bucket={b}>
              {t(`returns.bucket.${b}`)}
              {state.status === "ready" && state.counts[b] && b !== "done" ? (
                <>
                  {" "}
                  <Badge tone={b === "to_decide" ? "warning" : "neutral"} dot={false}>
                    {state.counts[b]}
                  </Badge>
                </>
              ) : null}
            </button>
          ))}
        </div>
        <div className={products.search} role="search">
          <Icon name="search" />
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("returns.search")} aria-label={t("returns.search")} maxLength={80} />
        </div>
      </div>
      {state.status === "loading" ? (
        <TableSkeleton columns="1fr 1.4fr 1fr 1fr" label={t("common.loading")} />
      ) : state.status === "error" ? (
        <QueryError error={state.error} onRetry={() => setNonce((n) => n + 1)} />
      ) : state.items.length === 0 ? (
        <EmptyState title={t("returns.empty")} body={bucket === "to_decide" && !q ? t("returns.emptyBody") : undefined} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-label={t("returns.title")} data-testid="returns">
            <thead>
              <tr>
                <th scope="col">{t("returns.colReturn")}</th>
                <th scope="col">{t("returns.colStatus")}</th>
                <th scope="col" className={table.num}>
                  {t("returns.colDue")}
                </th>
                <th scope="col" className={table.hideSm}>
                  {t("returns.colCreated")}
                </th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((r) => (
                <tr key={r.id} data-status={r.status}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <Link href={`/returns/${r.id}`} className={products.titleLink}>
                          {r.number}
                        </Link>{" "}
                        {r.customer_name ?? ""}
                      </strong>
                      <span>
                        #{r.order_number} · {t(`returns.resolution.${r.resolution}`)}
                      </span>
                    </div>
                  </td>
                  <td>
                    <ReturnStatusBadge status={r.status} />
                    {r.status === "requested" && (!r.eligible || r.signals.length) ? (
                      <div style={{ marginTop: 4 }}>
                        <Badge tone="warning">{!r.eligible ? t("returns.outsidePolicy") : t("returns.signalsTitle")}</Badge>
                      </div>
                    ) : null}
                  </td>
                  <td className={table.num}>{r.resolution === "refund" ? money(r.refund_due.amount_minor, r.refund_due.currency) : "–"}</td>
                  <td className={[table.hideSm, table.muted].join(" ")}>
                    <time dateTime={r.created_at} title={dateTime(r.created_at)}>
                      {relative(r.created_at)}
                    </time>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
