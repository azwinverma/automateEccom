"use client";

import type { ManualPaymentMethod, OrderDetail as Order, OrderEvent, OrderStatus, Payment } from "@commerce-os/api-client";
import Link from "next/link";
import { useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import products from "../products/products.module.css";
import { ErrorAlert, OrderStatusBadge, PaymentBadge } from "./shared";
import styles from "./orders.module.css";

/** UX-008 Order Journey: the happy path, with branches shown as an alert instead of a step. */
const JOURNEY: { key: string; reached: OrderStatus[] }[] = [
  { key: "confirmed", reached: ["confirmed", "payment_pending", "cod_pending", "ready_to_ship", "shipped", "delivered", "completed", "delivery_failed", "returned"] },
  { key: "ready_to_ship", reached: ["ready_to_ship", "shipped", "delivered", "completed", "delivery_failed", "returned"] },
  { key: "shipped", reached: ["shipped", "delivered", "completed", "delivery_failed", "returned"] },
  { key: "delivered", reached: ["delivered", "completed", "returned"] },
];
const FORWARD: OrderStatus[] = ["confirmed", "ready_to_ship", "shipped", "delivered", "completed", "delivery_failed", "returned"];
const MANUAL_METHODS: ManualPaymentMethod[] = ["esewa", "khalti", "fonepay", "bank_transfer", "cash", "other"];

export function OrderDetailView({ id }: { id: string }) {
  const { t, money } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const order = useApiQuery((a) => a.orders.get(id), [id]);
  const timeline = useApiQuery((a) => a.orders.timeline(id), [id]);
  const payments = useApiQuery((a) => (can("payments.read") ? a.orders.payments(id) : Promise.resolve({ items: [] as Payment[] })), [id]);
  const action = useAction();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [partialOpen, setPartialOpen] = useState(false);
  const [note, setNote] = useState("");

  const refresh = (o?: Order) => {
    if (o) order.setData(() => o);
    else order.reload();
    timeline.reload();
    payments.reload();
  };
  const go = async (to: OrderStatus, opts: { reason?: string } = {}) => {
    if (order.state.status !== "success") return;
    const o = await action.run(() => api.orders.transition(id, to, { ...opts, expected_version: order.state.status === "success" ? order.state.data.version : undefined }));
    if (o) {
      toast(t("orders.actions.done"));
      refresh(o);
    }
    return o;
  };

  if (order.state.status === "loading") return <TableSkeleton columns="2fr 1fr" rows={6} label={t("common.loading")} />;
  if (order.state.status === "error") return <QueryError error={order.state.error} onRetry={order.reload} />;
  const o = order.state.data;
  const forward = o.allowed_transitions.filter((s) => FORWARD.includes(s));
  const canCancel = o.allowed_transitions.includes("cancelled") && can("orders.cancel");
  const editable = ["pending_confirmation", "confirmed", "payment_pending", "cod_pending", "ready_to_ship"].includes(o.status);

  return (
    <div data-testid="order-detail">
      <div className={products.editorHeader}>
        <div className={products.editorTitle}>
          <Link href="/orders" className={products.backLink}>
            ← {t("orders.detail.back")}
          </Link>
          <h1>
            #{o.number} <OrderStatusBadge status={o.status} />
          </h1>
          <p className={styles.meta}>
            {t(`orders.source.${o.source}`)}
            {o.external_number ? ` · ${o.external_number}` : ""}
          </p>
        </div>
        <div className={styles.actions}>
          {can("orders.write")
            ? forward.map((to, i) => (
                <Button key={to} variant={i === 0 ? "primary" : "secondary"} loading={action.pending} onClick={() => void go(to)} data-transition={to}>
                  {t.dynamic(`orders.actions.to.${to}`) ?? to}
                </Button>
              ))
            : null}
          {canCancel ? (
            <Button variant="ghost" onClick={() => setCancelOpen(true)}>
              {t("orders.actions.to.cancelled")}
            </Button>
          ) : null}
        </div>
      </div>
      <ErrorAlert error={action.error} />

      {o.status === "cancelled" ? (
        <InlineAlert tone="info" live={false}>
          {t("orders.detail.cancelled", { reason: o.cancel_reason ?? "" })}
        </InlineAlert>
      ) : o.status === "delivery_failed" || o.status === "returned" ? (
        <InlineAlert tone="warning" live={false}>
          {t(`orders.status.${o.status}`)}
        </InlineAlert>
      ) : (
        <ol className={styles.journey} aria-label={t("orders.detail.journey")}>
          {JOURNEY.map((step, i) => {
            const done = step.reached.includes(o.status);
            const next = !done && (i === 0 || JOURNEY[i - 1]!.reached.includes(o.status));
            return (
              <li key={step.key} className={[styles.step, done ? styles.stepDone : "", next ? styles.stepCurrent : ""].join(" ")} aria-current={next ? "step" : undefined}>
                {t(`orders.status.${step.key as OrderStatus}`)}
              </li>
            );
          })}
        </ol>
      )}
      {o.needs_review ? (
        <InlineAlert tone="warning" title={t("orders.detail.review")}>
          {t.dynamic(`orders.review.${o.needs_review}`) ?? o.needs_review}
        </InlineAlert>
      ) : null}

      <div className={styles.layout}>
        <div className={styles.side}>
          <section className={styles.panel} aria-labelledby="o-items">
            <div className={styles.actions} style={{ justifyContent: "space-between" }}>
              <h2 id="o-items">{t("orders.detail.items")}</h2>
              {editable && can("orders.cancel") && o.lines.some((l) => l.quantity > l.cancelled_quantity) && o.lines.length > 0 ? (
                <Button size="sm" variant="ghost" onClick={() => setPartialOpen(true)}>
                  {t("orders.actions.cancelItems")}
                </Button>
              ) : null}
            </div>
            <div className={table.wrap}>
              <table className={[table.table, table.dense].join(" ")}>
                <tbody>
                  {o.lines.map((l) => (
                    <tr key={l.id}>
                      <td>
                        <div className={table.primaryCell}>
                          <strong>
                            {l.product_id ? <Link href={`/products/${l.product_id}`}>{l.title}</Link> : l.title}
                            {l.variant_title ? ` (${l.variant_title})` : ""}
                          </strong>
                          <span>
                            {l.sku ?? ""}
                            {!l.matched ? <> · <Badge tone="warning">{t("orders.detail.unmatched")}</Badge></> : null}
                            {l.cancelled_quantity ? ` · ${t("orders.detail.cancelledQty", { n: l.cancelled_quantity })}` : ""}
                          </span>
                        </div>
                      </td>
                      <td className={table.num}>
                        {l.quantity - l.cancelled_quantity} × {money(l.unit_price.amount_minor, l.unit_price.currency)}
                      </td>
                      <td className={table.num}>{money(l.line_total.amount_minor, l.line_total.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <dl className={styles.totals}>
              <dt>{t("orders.detail.subtotal")}</dt>
              <dd>{money(o.totals.subtotal.amount_minor, o.currency)}</dd>
              {o.totals.discount.amount_minor ? (
                <>
                  <dt>{t("orders.detail.discount")}</dt>
                  <dd>−{money(o.totals.discount.amount_minor, o.currency)}</dd>
                </>
              ) : null}
              <dt>{t("orders.detail.deliveryFee")}</dt>
              <dd>{money(o.totals.delivery_fee.amount_minor, o.currency)}</dd>
              {o.totals.tax.amount_minor ? (
                <>
                  <dt>{t("orders.detail.tax")}</dt>
                  <dd>{money(o.totals.tax.amount_minor, o.currency)}</dd>
                </>
              ) : null}
              <dt className={styles.grand}>{t("orders.detail.total")}</dt>
              <dd className={styles.grand}>{money(o.totals.total.amount_minor, o.currency)}</dd>
            </dl>
          </section>

          <section className={styles.panel} aria-labelledby="o-history">
            <h2 id="o-history">{t("orders.detail.timeline")}</h2>
            <Timeline events={timeline.state.status === "success" ? timeline.state.data.items : []} />
            {can("orders.write") ? (
              <form
                className={styles.actions}
                style={{ marginTop: "var(--space-3)", alignItems: "flex-end" }}
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!note.trim()) return;
                  if (await action.run(() => api.orders.addNote(id, note.trim()))) {
                    setNote("");
                    toast(t("orders.detail.noteSaved"));
                    timeline.reload();
                  }
                }}
              >
                <div style={{ flex: 1, minWidth: 180 }}>
                  <TextField label={t("orders.detail.addNote")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} />
                </div>
                <Button type="submit" size="sm">
                  {t("orders.detail.addNote")}
                </Button>
              </form>
            ) : null}
          </section>
        </div>

        <aside className={styles.side}>
          <section className={styles.panel} aria-labelledby="o-customer">
            <h2 id="o-customer">{t("orders.detail.shipping")}</h2>
            {o.customer ? (
              <p style={{ margin: "0 0 var(--space-2)" }}>
                <Link href={`/customers/${o.customer.id}`}>{o.customer.display_name}</Link>
              </p>
            ) : null}
            <address className={styles.address}>
              {o.shipping.recipient_name}
              {o.shipping.phone ? <> · {o.shipping.phone}</> : null}
              <br />
              {o.shipping.municipality ? (
                <>
                  {[o.shipping.area, `${o.shipping.municipality}-${o.shipping.ward}`, o.shipping.district_name].filter(Boolean).join(", ")}
                  {o.shipping.landmark ? (
                    <>
                      <br />
                      {o.shipping.landmark}
                    </>
                  ) : null}
                </>
              ) : (
                <span className={styles.meta}>{o.shipping.text ?? t("orders.detail.noAddress")}</span>
              )}
            </address>
            {o.conversation_id ? (
              <div style={{ marginTop: "var(--space-3)" }}>
                <ButtonLink size="sm" href={`/inbox?c=${o.conversation_id}`}>
                  <Icon name="inbox" />
                  {t("orders.detail.openChat")}
                </ButtonLink>
              </div>
            ) : null}
          </section>
          <PaymentPanel order={o} payments={payments.state.status === "success" ? payments.state.data.items : []} onChanged={refresh} />
        </aside>
      </div>

      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={t("orders.actions.cancelTitle", { number: o.number })}
        body={t("orders.actions.cancelBody")}
        confirmLabel={t("orders.actions.to.cancelled")}
        destructive
        pending={action.pending}
        onConfirm={async () => {
          if (await go("cancelled", { reason: reason.trim() || undefined })) {
            setCancelOpen(false);
            setReason("");
          }
        }}
      >
        <TextField label={t("orders.actions.reason")} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} />
      </ConfirmDialog>
      <PartialCancel open={partialOpen} onOpenChange={setPartialOpen} order={o} onDone={refresh} />
    </div>
  );
}

function Timeline({ events }: { events: OrderEvent[] }) {
  const { t, dateTime, relative } = useI18n();
  return (
    <ol className={styles.timeline} data-testid="order-timeline">
      {[...events].reverse().map((e) => {
        const title =
          e.kind === "status_changed" && e.to_status
            ? t("orders.detail.event.status_changed", { from: e.from_status ? t(`orders.status.${e.from_status}`) : "", to: t(`orders.status.${e.to_status}`) })
            : (t.dynamic(`orders.detail.event.${e.kind}`) ?? e.kind);
        const note = typeof e.data.note === "string" ? e.data.note : typeof e.data.reason === "string" ? e.data.reason : null;
        return (
          <li key={e.id}>
            <span>{title}</span>
            {note ? <span>{note}</span> : null}
            <span className={styles.meta}>
              <time dateTime={e.at} title={dateTime(e.at)}>
                {relative(e.at)}
              </time>
              {" · "}
              {e.automated ? t("orders.detail.automated") : (e.actor.display ?? e.actor.type)}
              {e.provider ? ` · ${e.provider}` : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function PaymentPanel({ order: o, payments, onChanged }: { order: Order; payments: Payment[]; onChanged: (o?: Order) => void }) {
  const { t, money, relative } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [method, setMethod] = useState<ManualPaymentMethod>("esewa");
  const [reference, setReference] = useState("");
  const [key] = useState(() => crypto.randomUUID());
  const unpaid = o.payment_status !== "paid" && !["cancelled", "returned", "draft"].includes(o.status);
  const pendingLink = payments.find((p) => p.status === "pending" && p.redirect_url);

  return (
    <section className={styles.panel} aria-labelledby="o-payment">
      <h2 id="o-payment">{t("orders.detail.payment")}</h2>
      <p style={{ margin: "0 0 var(--space-3)" }}>
        <PaymentBadge status={o.payment_status} />
      </p>
      <ErrorAlert error={action.error} />
      {payments.length ? (
        <ul className={styles.timeline} style={{ marginBottom: "var(--space-3)" }}>
          {payments.map((p) => (
            <li key={p.id}>
              <span>
                {t.dynamic(`orders.pay.methods.${p.method ?? "wallet"}`) ?? p.method} · {money(p.paid_minor ?? p.amount.amount_minor, p.amount.currency)}
              </span>
              <span className={styles.meta}>
                {t(`orders.pay.statuses.${p.status}`)}
                {p.reference ? ` · ${p.reference}` : ""} · {relative(p.created_at)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.meta}>{t("orders.pay.none")}</p>
      )}
      {pendingLink ? (
        <div className={styles.actions} style={{ marginBottom: "var(--space-3)" }}>
          <Button
            size="sm"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(pendingLink.redirect_url!);
                toast(t("orders.pay.copied"));
              } catch {
                /* clipboard blocked: the link is still shown */
              }
            }}
          >
            {t("orders.pay.copy")}
          </Button>
          <Button size="sm" variant="ghost" loading={action.pending} onClick={async () => (await action.run(() => api.orders.verifyPayment(pendingLink.id))) && onChanged()}>
            {t("orders.pay.verify")}
          </Button>
        </div>
      ) : null}
      {unpaid && o.payment_method === "prepaid" && o.status === "payment_pending" && can("orders.write") ? (
        <div className={styles.actions} style={{ marginBottom: "var(--space-3)" }}>
          {!pendingLink ? (
            <Button size="sm" loading={action.pending} onClick={async () => (await action.run(() => api.orders.startOnlinePayment(o.id))) && onChanged()}>
              {t("orders.pay.createLink")}
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="ghost"
            loading={action.pending}
            onClick={async () => {
              const next = await action.run(() => api.orders.switchToCod(o.id));
              if (next) {
                toast(t("orders.pay.switched"));
                onChanged(next);
              }
            }}
          >
            {t("orders.pay.switchCod")}
          </Button>
        </div>
      ) : null}
      {unpaid && can("payments.write") ? (
        <form
          className={styles.side}
          aria-label={t("orders.pay.recordTitle")}
          onSubmit={async (e) => {
            e.preventDefault();
            const p = await action.run(() =>
              api.orders.recordPayment(o.id, { amount_minor: o.totals.total.amount_minor, method, reference: reference.trim() || null }, { idempotencyKey: key }),
            );
            if (p) {
              toast(t("orders.pay.recorded"));
              onChanged();
            }
          }}
        >
          <strong style={{ fontSize: "var(--font-size-sm)" }}>{t("orders.pay.recordTitle")}</strong>
          <p className={styles.meta}>{t("orders.pay.amountHint", { total: money(o.totals.total.amount_minor, o.currency) })}</p>
          <SelectField label={t("orders.pay.method")} value={method} onChange={(e) => setMethod(e.target.value as ManualPaymentMethod)}>
            {MANUAL_METHODS.map((m) => (
              <option key={m} value={m}>
                {t(`orders.pay.methods.${m}`)}
              </option>
            ))}
          </SelectField>
          <TextField label={t("orders.pay.reference")} value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} />
          <div>
            <Button type="submit" size="sm" variant="primary" loading={action.pending}>
              {t("orders.pay.record")}
            </Button>
          </div>
        </form>
      ) : null}
    </section>
  );
}

function PartialCancel({ open, onOpenChange, order: o, onDone }: { open: boolean; onOpenChange: (v: boolean) => void; order: Order; onDone: (o?: Order) => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [qty, setQty] = useState<Record<string, number>>({});
  const [reason, setReason] = useState("");
  const items = Object.entries(qty)
    .filter(([, n]) => n > 0)
    .map(([line_id, quantity]) => ({ line_id, quantity }));
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("orders.actions.cancelItemsTitle")}
      footer={
        <Button
          variant="dangerSolid"
          disabled={!items.length || reason.trim().length < 2}
          loading={action.pending}
          onClick={async () => {
            const next = await action.run(() => api.orders.cancelLines(o.id, items, reason.trim()));
            if (next) {
              toast(t("orders.actions.itemsCancelled"));
              setQty({});
              setReason("");
              onOpenChange(false);
              onDone(next);
            }
          }}
        >
          {t("orders.actions.cancelItems")}
        </Button>
      }
    >
      <div className={styles.side}>
        <ErrorAlert error={action.error} />
        {o.lines
          .filter((l) => l.quantity > l.cancelled_quantity)
          .map((l) => (
            <TextField
              key={l.id}
              label={t("orders.actions.cancelQty", { title: `${l.title}${l.variant_title ? ` (${l.variant_title})` : ""}` })}
              type="number"
              min={0}
              max={l.quantity - l.cancelled_quantity}
              value={qty[l.id] ?? 0}
              onChange={(e) => setQty((q) => ({ ...q, [l.id]: Math.min(l.quantity - l.cancelled_quantity, Math.max(0, Number(e.target.value) || 0)) }))}
            />
          ))}
        <TextField label={t("orders.actions.reason")} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} required />
      </div>
    </Drawer>
  );
}
