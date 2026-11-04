"use client";

import type { Shipment, ShipmentBucket } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import products from "../products/products.module.css";
import { FulfillmentTabs, ShipmentStatusBadge } from "./shared";
import styles from "./fulfillment.module.css";

const BUCKETS: ShipmentBucket[] = ["to_pickup", "in_transit", "attention", "delivered", "returned"];

type State =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: Shipment[]; counts: Record<ShipmentBucket, number> | null; next: string | null };

export function ShipmentsView() {
  const { t, money, relative, dateTime } = useI18n();
  const { api, merchantId, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const couriers = useApiQuery((a) => a.couriers.list());
  const [bucket, setBucket] = useState<ShipmentBucket>("to_pickup");
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [state, setState] = useState<State>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const [picked, setPicked] = useState<Set<string>>(new Set());

  useEffect(() => {
    const id = setTimeout(() => setQ(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);
  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    setPicked(new Set());
    api.shipments.list({ bucket: q ? undefined : bucket, q: q || undefined, limit: 100 }).then(
      (p) => live && setState({ status: "ready", items: p.items, counts: p.counts, next: p.next_cursor }),
      (error: unknown) => live && setState({ status: "error", error }),
    );
    return () => {
      live = false;
    };
  }, [api, merchantId, bucket, q, nonce]);

  const noCouriers = couriers.state.status === "success" && couriers.state.data.items.length === 0;
  const pickable = state.status === "ready" ? state.items.filter((s) => s.actions.includes("request_pickup")) : [];
  const toggle = (id: string) =>
    setPicked((p) => {
      const n = new Set(p);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <>
      <PageHeader
        title={t("fulfillment.title")}
        subtitle={t("fulfillment.subtitle")}
        actions={
          can("settings.manage") ? (
            <ButtonLink href="/settings/couriers" size="sm">
              <Icon name="settings" />
              {t("settings.couriers")}
            </ButtonLink>
          ) : null
        }
      />
      <FulfillmentTabs />
      {noCouriers ? (
        <EmptyState
          title={t("fulfillment.noCourier")}
          body={t("fulfillment.noCourierBody")}
          actions={
            can("settings.manage") ? (
              <ButtonLink href="/settings/couriers" variant="primary">
                {t("fulfillment.connectCourier")}
              </ButtonLink>
            ) : null
          }
        />
      ) : (
        <>
          <div className={products.toolbar}>
            <div role="tablist" aria-label={t("fulfillment.tabsLabel")} className={products.tabs}>
              {BUCKETS.map((b) => (
                <button key={b} type="button" role="tab" aria-selected={!q && bucket === b} className={products.tab} onClick={() => (setQuery(""), setQ(""), setBucket(b))} data-bucket={b}>
                  {t(`fulfillment.bucket.${b}`)}
                  {state.status === "ready" && state.counts && state.counts[b] ? (
                    <>
                      {" "}
                      <Badge tone={b === "attention" ? "danger" : "neutral"} dot={false}>
                        {state.counts[b]}
                      </Badge>
                    </>
                  ) : null}
                </button>
              ))}
            </div>
            <div className={products.search} role="search">
              <Icon name="search" />
              <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("fulfillment.search")} aria-label={t("fulfillment.search")} maxLength={80} />
            </div>
          </div>
          <ErrorAlert error={action.error} />
          {pickable.length && can("fulfillment.write") ? (
            <div className={styles.row} style={{ margin: "var(--space-3) 0" }}>
              <Button
                size="sm"
                variant="primary"
                disabled={!picked.size}
                loading={action.pending}
                onClick={async () => {
                  if (await action.run(() => api.shipments.requestPickup([...picked]))) {
                    toast(t("fulfillment.pickupRequested"));
                    setNonce((n) => n + 1);
                  }
                }}
              >
                {t("fulfillment.requestPickup", { n: picked.size })}
              </Button>
            </div>
          ) : null}
          {state.status === "loading" ? (
            <TableSkeleton columns="0.4fr 1.4fr 1fr 1fr 1fr" label={t("common.loading")} />
          ) : state.status === "error" ? (
            <QueryError error={state.error} onRetry={() => setNonce((n) => n + 1)} />
          ) : state.items.length === 0 ? (
            <EmptyState title={t("fulfillment.empty")} body={bucket === "to_pickup" && !q ? t("fulfillment.emptyBody") : undefined} />
          ) : (
            <div className={table.wrap}>
              <table className={table.table} aria-label={t("fulfillment.tabShipments")} data-testid="shipments">
                <thead>
                  <tr>
                    {pickable.length && can("fulfillment.write") ? (
                      <th scope="col" style={{ width: 36 }}>
                        <input
                          type="checkbox"
                          aria-label={t("fulfillment.selectAll")}
                          checked={picked.size > 0 && picked.size === pickable.length}
                          onChange={(e) => setPicked(e.target.checked ? new Set(pickable.map((s) => s.id)) : new Set())}
                        />
                      </th>
                    ) : null}
                    <th scope="col">{t("fulfillment.colOrder")}</th>
                    <th scope="col">{t("fulfillment.colStatus")}</th>
                    <th scope="col" className={table.hideSm}>
                      {t("fulfillment.colCourier")}
                    </th>
                    <th scope="col" className={table.num}>
                      {t("fulfillment.colCod")}
                    </th>
                    <th scope="col" className={table.hideSm}>
                      {t("fulfillment.colUpdated")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {state.items.map((s) => {
                    const at = s.last_event_at ?? s.created_at;
                    return (
                      <tr key={s.id} data-status={s.status}>
                        {pickable.length && can("fulfillment.write") ? (
                          <td>
                            {s.actions.includes("request_pickup") ? (
                              <input type="checkbox" checked={picked.has(s.id)} onChange={() => toggle(s.id)} aria-label={t("fulfillment.selectRow", { number: s.order_number ?? "" })} />
                            ) : null}
                          </td>
                        ) : null}
                        <td>
                          <div className={table.primaryCell}>
                            <strong>
                              <Link href={`/orders/${s.order_id}`} className={products.titleLink}>
                                #{s.order_number}
                              </Link>{" "}
                              {s.customer_name ?? ""}
                            </strong>
                            <span>
                              {s.destination_district_name ?? ""}
                              {s.tracking_number ? (
                                <>
                                  {" · "}
                                  <span className={styles.mono}>{s.tracking_number}</span>
                                </>
                              ) : null}
                            </span>
                          </div>
                        </td>
                        <td>
                          <ShipmentStatusBadge status={s.status} />
                          {s.stuck ? (
                            <div style={{ marginTop: 4 }}>
                              <Badge tone="warning">{t("fulfillment.stuck", { days: Math.floor((Date.now() - Date.parse(at)) / 86400000) })}</Badge>
                            </div>
                          ) : null}
                          {s.attempt_count ? <div className={styles.muted}>{t("fulfillment.panel.attemptN", { n: s.attempt_count })}</div> : null}
                        </td>
                        <td className={table.hideSm}>{s.courier_name}</td>
                        <td className={table.num}>{s.cod_amount.amount_minor ? money(s.cod_amount.amount_minor, s.cod_amount.currency) : "–"}</td>
                        <td className={[table.hideSm, table.muted].join(" ")}>
                          <time dateTime={at} title={dateTime(at)}>
                            {relative(at)}
                          </time>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  );
}
