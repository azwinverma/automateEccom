"use client";

import type { LedgerEntry, VariantStock } from "@commerce-os/api-client";
import { useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import ordersCss from "../orders/orders.module.css";
import wf from "../shared/workflow.module.css";

type Mode = "receive" | "adjust" | "count" | "alert";

/** Per-variant stock with receive / adjust / count / alert level and the immutable history. */
export function StockSection({ productId }: { productId: string }) {
  const { t, number } = useI18n();
  const { can } = useAuth();
  const stock = useApiQuery((a) => a.inventory.productStock(productId), [productId]);
  const [editing, setEditing] = useState<{ v: VariantStock; mode: Mode } | null>(null);
  const [history, setHistory] = useState<VariantStock | null>(null);
  const canAdjust = can("inventory.adjust");

  if (stock.state.status === "loading") return <TableSkeleton columns="1.4fr 1fr 1fr 1fr" rows={2} label={t("common.loading")} />;
  if (stock.state.status === "error") return <QueryError error={stock.state.error} onRetry={stock.reload} />;
  return (
    <div className={wf.stack} data-testid="stock">
      <div className={table.wrap}>
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">{t("inventory.colVariant")}</th>
              <th scope="col" className={table.num}>
                {t("inventory.colAvailable")}
              </th>
              <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                {t("inventory.colOnHand")}
              </th>
              <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                {t("inventory.colReserved")}
              </th>
              <th scope="col" className={table.actions}>
                <span className="srOnly">{t("common.actions")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {stock.state.data.variants.map((v) => {
              const low = v.locations.some((l) => l.low);
              return (
                <tr key={v.variant_id} data-variant={v.sku ?? v.title}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{v.title === "Default" ? (v.sku ?? v.title) : v.title}</strong>
                      {v.sku && v.title !== "Default" ? <span>{v.sku}</span> : null}
                    </div>
                  </td>
                  <td className={table.num}>
                    {v.tracked ? (
                      <>
                        {number(v.available)} {low ? <Badge tone="warning">{t("inventory.lowStock")}</Badge> : null}
                      </>
                    ) : (
                      <Badge tone="neutral" dot={false}>
                        {t("inventory.untracked")}
                      </Badge>
                    )}
                  </td>
                  <td className={[table.num, table.hideSm].join(" ")}>{v.tracked ? number(v.on_hand) : "–"}</td>
                  <td className={[table.num, table.hideSm].join(" ")}>{v.tracked ? number(v.reserved) : "–"}</td>
                  <td className={table.actions}>
                    <div className={wf.rowActions}>
                      {canAdjust ? (
                        <Button size="sm" onClick={() => setEditing({ v, mode: "receive" })} aria-label={`${t("inventory.receive")}: ${v.title}`}>
                          {t("inventory.receive")}
                        </Button>
                      ) : null}
                      {canAdjust && v.tracked ? (
                        <>
                          <Button size="sm" variant="ghost" onClick={() => setEditing({ v, mode: "adjust" })}>
                            {t("inventory.adjust")}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditing({ v, mode: "count" })}>
                            {t("inventory.count")}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditing({ v, mode: "alert" })}>
                            {t("inventory.alert")}
                          </Button>
                        </>
                      ) : null}
                      {v.tracked ? (
                        <Button size="sm" variant="ghost" onClick={() => setHistory(v)}>
                          {t("inventory.history")}
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {editing ? <StockForm key={`${editing.v.variant_id}:${editing.mode}`} variant={editing.v} mode={editing.mode} onClose={() => setEditing(null)} onSaved={stock.reload} /> : null}
      {history ? <History variant={history} onClose={() => setHistory(null)} /> : null}
    </div>
  );
}

function StockForm({ variant, mode, onClose, onSaved }: { variant: VariantStock; mode: Mode; onClose: () => void; onSaved: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const idem = useIdempotencyKey();
  const [value, setValue] = useState(mode === "count" ? String(variant.on_hand) : mode === "alert" ? String(variant.locations[0]?.low_stock_threshold ?? "") : "");
  const [reason, setReason] = useState("");
  const n = Number(value);
  const valid = mode === "alert" ? value === "" || n >= 0 : mode === "adjust" ? Number.isInteger(n) && n !== 0 && reason.trim().length >= 2 : Number.isInteger(n) && (mode === "count" ? n >= 0 : n > 0);
  const submit = async () => {
    const vid = variant.variant_id;
    const run =
      mode === "receive"
        ? () => api.inventory.receive(vid, { quantity: n, reason: reason.trim() || null }, { idempotencyKey: idem.keyFor({ vid, n, reason }) })
        : mode === "adjust"
          ? () => api.inventory.adjust(vid, { delta: n, reason: reason.trim() }, { idempotencyKey: idem.keyFor({ vid, n, reason }) })
          : mode === "count"
            ? () => api.inventory.count(vid, { counted: n })
            : () => api.inventory.setThreshold(vid, value === "" ? null : n);
    if (await action.run(run)) {
      toast(t("inventory.saved"));
      onSaved();
      onClose();
    }
  };
  const label = { receive: "inventory.quantity", adjust: "inventory.delta", count: "inventory.counted", alert: "inventory.threshold" } as const;
  return (
    <Drawer
      open
      onOpenChange={(o) => !o && onClose()}
      title={`${t(`inventory.${mode === "alert" ? "alert" : mode}`)}: ${variant.title === "Default" ? (variant.sku ?? "") : variant.title}`}
      footer={
        <Button variant="primary" disabled={!valid} loading={action.pending} onClick={submit}>
          {t("inventory.save")}
        </Button>
      }
    >
      <div className={ordersCss.side}>
        <ErrorAlert error={action.error} />
        <TextField label={t(label[mode])} type="number" inputMode="numeric" value={value} onChange={(e) => setValue(e.target.value)} min={mode === "adjust" ? undefined : 0} autoFocus />
        {mode === "receive" || mode === "adjust" ? <TextField label={t("inventory.reason")} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} required={mode === "adjust"} /> : null}
      </div>
    </Drawer>
  );
}

function History({ variant, onClose }: { variant: VariantStock; onClose: () => void }) {
  const { t, relative, dateTime } = useI18n();
  const entries = useApiQuery((a) => a.inventory.ledger(variant.variant_id, { limit: 100 }), [variant.variant_id]);
  const delta = (e: LedgerEntry) => (e.on_hand_delta ? `${e.on_hand_delta > 0 ? "+" : ""}${e.on_hand_delta}` : e.reserved_delta ? `${e.reserved_delta > 0 ? "+" : ""}${e.reserved_delta}` : "0");
  return (
    <Drawer open onOpenChange={(o) => !o && onClose()} title={t("inventory.historyTitle", { title: variant.title === "Default" ? (variant.sku ?? "") : variant.title })} wide>
      {entries.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr" label={t("common.loading")} />
      ) : entries.state.status === "error" ? (
        <QueryError error={entries.state.error} onRetry={entries.reload} />
      ) : entries.state.data.items.length === 0 ? (
        <p className={ordersCss.meta}>{t("inventory.noHistory")}</p>
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="ledger">
            <tbody>
              {entries.state.data.items.map((e) => (
                <tr key={e.id}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{t(`inventory.kind.${e.kind}`)}</strong>
                      {e.reason ? <span>{e.reason}</span> : null}
                    </div>
                  </td>
                  <td className={table.num}>{delta(e)}</td>
                  <td className={table.num}>
                    {t("inventory.colOnHand")}: {e.on_hand_after}
                  </td>
                  <td className={table.muted}>
                    <time dateTime={e.created_at} title={dateTime(e.created_at)}>
                      {relative(e.created_at)}
                    </time>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Drawer>
  );
}
