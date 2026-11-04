"use client";

import type { RefundMethod, RefundRecord, ReturnCondition, ReturnDetail as Detail } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ShipmentCard } from "../fulfillment/DeliveryPanel";
import orderStyles from "../orders/orders.module.css";
import { ErrorAlert } from "../orders/shared";
import products from "../products/products.module.css";
import { Checks, RefundStatusBadge, ReturnStatusBadge, Signals } from "./shared";
import styles from "./returns.module.css";

const CONDITIONS: ReturnCondition[] = ["resellable", "damaged", "used", "missing"];
const METHODS: RefundMethod[] = ["original_payment", "esewa", "khalti", "fonepay", "bank_transfer", "cash", "other"];
type Dialog = null | "approve" | "reject" | "cancel" | "received" | "pickup" | "inspect" | "refund";

export function ReturnDetailView({ id }: { id: string }) {
  const { t, money, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const detail = useApiQuery((a) => a.returns.get(id), [id]);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [text, setText] = useState("");

  const update = (next: Detail | undefined) => {
    if (!next) return;
    detail.setData(() => next);
    toast(t("returns.actions.done"));
    setDialog(null);
    setText("");
  };

  if (detail.state.status === "loading") return <TableSkeleton columns="2fr 1fr" rows={6} label={t("common.loading")} />;
  if (detail.state.status === "error") return <QueryError error={detail.state.error} onRetry={detail.reload} />;
  const r = detail.state.data;
  const acts = new Set(r.actions);
  const decide = can("returns.approve");
  const write = can("returns.write");

  return (
    <div data-testid="return-detail" data-status={r.status}>
      <div className={products.editorHeader}>
        <div className={products.editorTitle}>
          <Link href="/returns" className={products.backLink}>
            ← {t("returns.back")}
          </Link>
          <h1>
            {r.number} <ReturnStatusBadge status={r.status} />
          </h1>
          <p className={styles.muted}>
            <Link href={`/orders/${r.order_id}`}>#{r.order_number}</Link> · {r.customer_name ?? ""} · {t(`returns.resolution.${r.resolution}`)} ·{" "}
            <time dateTime={r.created_at}>{dateTime(r.created_at)}</time>
          </p>
        </div>
        <div className={styles.row}>
          {acts.has("approve") && decide ? (
            <Button variant="primary" loading={action.pending} onClick={() => (r.eligible ? void action.run(() => api.returns.approve(r.id)).then(update) : setDialog("approve"))}>
              {t("returns.actions.approve")}
            </Button>
          ) : null}
          {acts.has("book_pickup") && can("fulfillment.write") ? (
            <Button variant="primary" onClick={() => setDialog("pickup")}>
              {t("returns.actions.book_pickup")}
            </Button>
          ) : null}
          {acts.has("mark_received") && write ? (
            <Button variant={acts.has("book_pickup") ? "secondary" : "primary"} onClick={() => setDialog("received")}>
              {t("returns.actions.mark_received")}
            </Button>
          ) : null}
          {acts.has("inspect") && write ? (
            <Button variant="primary" onClick={() => setDialog("inspect")}>
              {t("returns.actions.inspect")}
            </Button>
          ) : null}
          {acts.has("refund") && can("refunds.create") ? (
            <Button variant="primary" onClick={() => setDialog("refund")}>
              {t("returns.actions.refund")}
            </Button>
          ) : null}
          {acts.has("reject") && decide ? (
            <Button variant="ghost" onClick={() => setDialog("reject")}>
              {t("returns.actions.reject")}
            </Button>
          ) : null}
          {acts.has("cancel") && write ? (
            <Button variant="ghost" onClick={() => setDialog("cancel")}>
              {t("returns.actions.cancel")}
            </Button>
          ) : null}
        </div>
      </div>
      <ErrorAlert error={action.error} />

      <div className={orderStyles.layout}>
        <div className={orderStyles.side}>
          <section className={orderStyles.panel} aria-labelledby="r-items">
            <h2 id="r-items">{t("returns.items")}</h2>
            <div className={table.wrap}>
              <table className={[table.table, table.dense].join(" ")}>
                <tbody>
                  {r.lines.map((ln) => (
                    <tr key={ln.id}>
                      <td>
                        <div className={table.primaryCell}>
                          <strong>
                            {ln.quantity} × {ln.title}
                            {ln.variant_title && ln.variant_title !== "Default" ? ` (${ln.variant_title})` : ""}
                          </strong>
                          <span>
                            {t(`returns.reason.${ln.reason}`)}
                            {ln.reason_note ? ` · “${ln.reason_note}”` : ""}
                            {ln.exchange ? ` · ${t("returns.exchangeFor")}: ${ln.exchange.title ?? ""}` : ""}
                          </span>
                          {ln.condition ? (
                            <span>
                              {t(`returns.condition.${ln.condition}`)}
                              {ln.restocked_quantity ? ` · ${t("returns.actions.restock")}: ${ln.restocked_quantity}` : ""}
                              {ln.inspection_note ? ` · ${ln.inspection_note}` : ""}
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className={table.num}>{money(ln.unit_refund_minor * ln.quantity, r.refund_due.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {r.resolution === "refund" ? (
              <dl className={styles.facts} style={{ marginTop: "var(--space-3)" }}>
                <dt>{t("returns.refundDue")}</dt>
                <dd className={styles.money}>{money(r.refund_due.amount_minor, r.refund_due.currency)}</dd>
                <dt>–</dt>
                <dd className={styles.muted}>
                  {r.customer_pays_shipping && r.return_shipping_fee_minor
                    ? t("returns.shippingFee", { amount: money(r.return_shipping_fee_minor, r.refund_due.currency) })
                    : !r.customer_pays_shipping
                      ? t("returns.shopPays")
                      : ""}
                </dd>
              </dl>
            ) : r.exchange_order_id ? (
              <p style={{ marginTop: "var(--space-3)" }}>
                <Link href={`/orders/${r.exchange_order_id}`}>{t("returns.openExchange")}</Link>
              </p>
            ) : null}
          </section>
          {r.pickup ? (
            <section className={orderStyles.panel} aria-labelledby="r-pickup">
              <h2 id="r-pickup">{t("returns.pickupTitle")}</h2>
              <ShipmentCard shipment={r.pickup} onChanged={() => detail.reload()} />
            </section>
          ) : null}
        </div>
        <aside className={orderStyles.side}>
          <section className={orderStyles.panel} aria-labelledby="r-checks">
            <h2 id="r-checks">{t("returns.checks")}</h2>
            <Checks checks={r.eligibility.checks} />
            {r.override_reason ? <p className={styles.muted}>{t("returns.overridden", { reason: r.override_reason })}</p> : null}
            {r.rejection_reason ? <p className={styles.muted}>{t("returns.rejectedBecause", { reason: r.rejection_reason })}</p> : null}
          </section>
          {r.signals.length ? <Signals signals={r.signals} /> : null}
          {r.refunds.length ? <RefundsList refunds={r.refunds} onChanged={() => detail.reload()} /> : null}
        </aside>
      </div>

      <ConfirmDialog
        open={dialog === "approve"}
        onOpenChange={(v) => setDialog(v ? "approve" : null)}
        title={t("returns.actions.approve")}
        body={t("returns.overrideHint")}
        confirmLabel={t("returns.actions.approve")}
        pending={action.pending}
        onConfirm={() => text.trim().length >= 3 && void action.run(() => api.returns.approve(r.id, text.trim())).then(update)}
      >
        <TextField label={t("returns.overrideReason")} value={text} onChange={(e) => setText(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === "reject"}
        onOpenChange={(v) => setDialog(v ? "reject" : null)}
        title={t("returns.actions.rejectTitle")}
        confirmLabel={t("returns.actions.reject")}
        destructive
        pending={action.pending}
        onConfirm={() => text.trim().length >= 3 && void action.run(() => api.returns.reject(r.id, text.trim())).then(update)}
      >
        <TextField label={t("returns.actions.rejectReason")} value={text} onChange={(e) => setText(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === "cancel"}
        onOpenChange={(v) => setDialog(v ? "cancel" : null)}
        title={t("returns.actions.cancelTitle")}
        body={t("returns.actions.cancelBody")}
        confirmLabel={t("returns.actions.cancel")}
        destructive
        pending={action.pending}
        onConfirm={() => void action.run(() => api.returns.cancel(r.id)).then(update)}
      />
      <ConfirmDialog
        open={dialog === "received"}
        onOpenChange={(v) => setDialog(v ? "received" : null)}
        title={t("returns.actions.receivedTitle")}
        body={t("returns.actions.receivedBody")}
        confirmLabel={t("returns.actions.mark_received")}
        pending={action.pending}
        onConfirm={() => void action.run(() => api.returns.received(r.id)).then(update)}
      />
      <PickupDrawer open={dialog === "pickup"} onOpenChange={(v) => setDialog(v ? "pickup" : null)} ret={r} onDone={update} />
      <InspectDrawer open={dialog === "inspect"} onOpenChange={(v) => setDialog(v ? "inspect" : null)} ret={r} onDone={update} />
      <RefundDrawer open={dialog === "refund"} onOpenChange={(v) => setDialog(v ? "refund" : null)} ret={r} onDone={() => (setDialog(null), detail.reload())} />
    </div>
  );
}

function PickupDrawer({ open, onOpenChange, ret, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; ret: Detail; onDone: (d?: Detail) => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const idem = useIdempotencyKey();
  const couriers = useApiQuery((a) => (open ? a.couriers.list() : Promise.resolve({ items: [] })), [open]);
  const [courier, setCourier] = useState("");
  const items = couriers.state.status === "success" ? couriers.state.data.items : [];
  const chosen = courier || items.find((c) => c.is_default)?.id || items[0]?.id || "";
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("returns.actions.pickupTitle")}
      footer={
        <Button
          variant="primary"
          disabled={!chosen}
          loading={action.pending}
          onClick={async () => {
            const body = { courier_account_id: chosen };
            const d = await action.run(() => api.returns.bookPickup(ret.id, body, { idempotencyKey: idem.keyFor({ ret: ret.id, ...body }) }));
            if (d) {
              idem.reset();
              onDone(d);
            }
          }}
        >
          {t("returns.actions.book_pickup")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }}>
        <ErrorAlert error={action.error} />
        <SelectField label={t("returns.actions.pickupCourier")} value={chosen} onChange={(e) => setCourier(e.target.value)}>
          {items.map((c) => (
            <option key={c.id} value={c.id}>
              {c.display_name}
            </option>
          ))}
        </SelectField>
      </div>
    </Drawer>
  );
}

function InspectDrawer({ open, onOpenChange, ret, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; ret: Detail; onDone: (d?: Detail) => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [rows, setRows] = useState<Record<string, { condition: ReturnCondition; restock: number; note: string }>>({});
  useEffect(() => {
    if (open) setRows(Object.fromEntries(ret.lines.map((l) => [l.id, { condition: "resellable" as ReturnCondition, restock: l.quantity, note: "" }])));
  }, [open, ret.lines]);
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      wide
      title={t("returns.actions.inspectTitle")}
      footer={
        <Button
          variant="primary"
          loading={action.pending}
          onClick={async () => {
            const items = ret.lines.map((l) => {
              const row = rows[l.id]!;
              return { line_id: l.id, condition: row.condition, restock: row.condition === "resellable" ? row.restock : 0, note: row.note.trim() || null };
            });
            onDone(await action.run(() => api.returns.inspect(ret.id, items)));
          }}
        >
          {t("returns.actions.saveInspection")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }} data-testid="inspect-form">
        <ErrorAlert error={action.error} />
        {ret.lines.map((l) => {
          const row = rows[l.id];
          if (!row) return null;
          const title = `${l.title ?? ""}${l.variant_title && l.variant_title !== "Default" ? ` (${l.variant_title})` : ""}`;
          return (
            <div key={l.id} className={styles.lineGrid}>
              <strong>
                {l.quantity} × {title}
              </strong>
              <div className={styles.split}>
                <SelectField
                  label={t("returns.actions.conditionOf", { title })}
                  value={row.condition}
                  onChange={(e) => setRows((rs) => ({ ...rs, [l.id]: { ...row, condition: e.target.value as ReturnCondition } }))}
                >
                  {CONDITIONS.map((c) => (
                    <option key={c} value={c}>
                      {t(`returns.condition.${c}`)}
                    </option>
                  ))}
                </SelectField>
                <TextField
                  label={t("returns.actions.restockOf", { title, max: l.quantity })}
                  type="number"
                  min={0}
                  max={l.quantity}
                  disabled={row.condition !== "resellable"}
                  value={row.condition === "resellable" ? row.restock : 0}
                  onChange={(e) => setRows((rs) => ({ ...rs, [l.id]: { ...row, restock: Math.max(0, Math.min(l.quantity, Number(e.target.value) || 0)) } }))}
                />
              </div>
              <TextField label={t("returns.actions.inspectNote")} value={row.note} onChange={(e) => setRows((rs) => ({ ...rs, [l.id]: { ...row, note: e.target.value } }))} maxLength={500} />
            </div>
          );
        })}
      </div>
    </Drawer>
  );
}

function RefundDrawer({ open, onOpenChange, ret, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; ret: Detail; onDone: () => void }) {
  const { t, money } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const idem = useIdempotencyKey();
  const cap = Math.min(ret.refund_due.amount_minor, ret.refundable_minor);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<RefundMethod>("esewa");
  const [reference, setReference] = useState("");
  useEffect(() => {
    if (open) {
      setAmount(String(cap / 100));
      action.clear();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, cap]);
  const minor = Math.round(Number(amount) * 100);
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("returns.refund.title")}
      footer={
        <Button
          variant="primary"
          disabled={!(minor > 0 && minor <= ret.refundable_minor) || (method !== "original_payment" && !reference.trim())}
          loading={action.pending}
          onClick={async () => {
            const body = { amount_minor: minor, method, return_id: ret.id, reference: reference.trim() || null };
            const ref = await action.run(() => api.refunds.create(ret.order_id, body, { idempotencyKey: idem.keyFor(body) }));
            if (ref) {
              toast(ref.status === "pending_approval" ? t("returns.refund.pending") : t("returns.refund.sent"));
              idem.reset();
              onDone();
            }
          }}
        >
          {t("returns.refund.send")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }} data-testid="refund-form">
        <ErrorAlert error={action.error} />
        <TextField
          label={t("returns.refund.amount")}
          hint={t("returns.refund.max", { amount: money(ret.refundable_minor, ret.refund_due.currency) })}
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <SelectField label={t("returns.refund.method")} value={method} onChange={(e) => setMethod(e.target.value as RefundMethod)}>
          {METHODS.map((m) => (
            <option key={m} value={m}>
              {t(`returns.refund.methods.${m}`)}
            </option>
          ))}
        </SelectField>
        {method !== "original_payment" ? (
          <TextField label={t("returns.refund.reference")} value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} required />
        ) : null}
      </div>
    </Drawer>
  );
}

export function RefundsList({ refunds, onChanged, title }: { refunds: RefundRecord[]; onChanged: () => void; title?: string }) {
  const { t, money, relative } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [rejecting, setRejecting] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const done = (r: RefundRecord | undefined) => {
    if (!r) return;
    toast(t("returns.actions.done"));
    onChanged();
  };
  return (
    <section className={orderStyles.panel} aria-labelledby="r-refunds" data-testid="refunds">
      <h2 id="r-refunds">{title ?? t("returns.refund.list")}</h2>
      <ErrorAlert error={action.error} />
      <ul className={styles.compact}>
        {refunds.map((x) => (
          <li key={x.id} data-status={x.status}>
            <span>
              <span className={styles.money}>{money(x.amount.amount_minor, x.amount.currency)}</span>{" "}
              <span className={styles.muted}>
                {x.order_number ? `${t("returns.refund.orderRef", { number: x.order_number })} · ` : ""}
                {t(`returns.refund.methods.${x.method}`)}
                {x.reference ? ` · ${x.reference}` : ""} · {relative(x.created_at)}
              </span>
            </span>
            <span className={styles.row}>
              <RefundStatusBadge status={x.status} />
              {x.status === "pending_approval" && can("refunds.approve") ? (
                <>
                  <Button size="sm" variant="primary" loading={action.pending} onClick={() => void action.run(() => api.refunds.approve(x.id)).then(done)}>
                    {t("returns.refund.approve")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setRejecting(x.id)}>
                    {t("returns.refund.reject")}
                  </Button>
                </>
              ) : null}
              {x.status === "failed" && can("refunds.create") ? (
                <Button size="sm" loading={action.pending} onClick={() => void action.run(() => api.refunds.retry(x.id)).then(done)}>
                  {t("returns.refund.retry")}
                </Button>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={rejecting !== null}
        onOpenChange={(v) => !v && setRejecting(null)}
        title={t("returns.refund.rejectTitle")}
        confirmLabel={t("returns.refund.reject")}
        destructive
        pending={action.pending}
        onConfirm={async () => {
          if (!rejecting || reason.trim().length < 3) return;
          done(await action.run(() => api.refunds.reject(rejecting, reason.trim())));
          setRejecting(null);
          setReason("");
        }}
      >
        <TextField label={t("returns.refund.rejectReason")} value={reason} onChange={(e) => setReason(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
    </section>
  );
}
