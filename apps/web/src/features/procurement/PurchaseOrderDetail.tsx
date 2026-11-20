"use client";

import { isApiError, type PurchaseOrder } from "@commerce-os/api-client";
import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./procurement.module.css";
import { PurchaseOrderForm } from "./PurchaseOrderForm";
import { InventoryTabs, itemLabel, PurchasingGate, STATUS_TONE } from "./shared";

const newIdem = () => `rcv-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

export function PurchaseOrderDetailView({ id }: { id: string }) {
  const { t } = useI18n();
  return (
    <PurchasingGate header={<PageHeader title={t("procurement.poTitle")} />}>
      <PurchaseOrderDetail id={id} />
    </PurchasingGate>
  );
}

function PurchaseOrderDetail({ id }: { id: string }) {
  const { t } = useI18n();
  const q = useApiQuery((a) => a.procurement.purchaseOrder(id), [id]);
  if (q.state.status === "loading") return <TableSkeleton columns="1fr 1fr" label={t("common.loading")} />;
  if (q.state.status === "error") {
    if (isApiError(q.state.error) && q.state.error.status === 404) return <EmptyState title={t("procurement.notFound")} />;
    return <QueryError error={q.state.error} onRetry={q.reload} />;
  }
  return <PurchaseOrderPage po={q.state.data} onChange={(next) => q.setData(() => next)} reload={q.reload} />;
}

export function PurchaseOrderPage({ po, onChange, reload }: { po: PurchaseOrder; onChange: (po: PurchaseOrder) => void; reload: () => void }) {
  const { t, money, date } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [editing, setEditing] = useState(false);
  const [dialog, setDialog] = useState<null | "return" | "cancel">(null);
  const [reason, setReason] = useState("");
  const canWrite = can("procurement.write");
  const canApprove = can("procurement.approve");
  const open = !["received", "cancelled"].includes(po.status);
  const receivable = ["approved", "sent", "partially_received"].includes(po.status);

  const run = async (fn: () => Promise<PurchaseOrder>, msg: string | ((po: PurchaseOrder) => string)) => {
    const next = await action.run(fn);
    if (next) {
      onChange(next);
      toast(typeof msg === "string" ? msg : msg(next));
    }
    return next;
  };

  return (
    <>
      <PageHeader
        title={po.number}
        subtitle={
          <span className={styles.row}>
            <Badge tone={STATUS_TONE[po.status]}>{t.dynamic(`procurement.status_${po.status}`) ?? po.status}</Badge>
            <span>{po.supplier.name}</span>
            {po.source === "recommendation" ? <span className={styles.muted}>{t("procurement.fromSuggestion")}</span> : null}
          </span>
        }
      />
      <InventoryTabs />
      <p style={{ margin: "0 0 var(--space-4)" }}>
        <Link href="/inventory/purchase-orders">← {t("procurement.back")}</Link>
      </p>
      <div data-testid="po-detail" data-status={po.status}>
        <ErrorAlert error={action.error} />
        <Timeline po={po} />
        {po.status === "pending_approval" ? <ApprovalCallout po={po} /> : null}
        {po.status === "cancelled" || (po.status === "received" && po.cancel_reason) ? (
          <InlineAlert tone="info" live={false}>
            {t("procurement.cancelledNote", { reason: po.cancel_reason ?? "" })}
          </InlineAlert>
        ) : null}

        <div className={styles.row} style={{ marginBottom: "var(--space-4)" }}>
          {po.status === "draft" && canWrite ? (
            <>
              <Button
                variant="primary"
                loading={action.pending}
                onClick={() =>
                  run(
                    () => api.procurement.submit(po.id),
                    (next) => t(next.status === "approved" ? "procurement.submittedApproved" : "procurement.submittedPending"),
                  )
                }
              >
                {t("procurement.submit")}
              </Button>
              <Button onClick={() => setEditing((e) => !e)}>{t("procurement.edit")}</Button>
            </>
          ) : null}
          {po.status === "pending_approval" && canApprove ? (
            <>
              <Button variant="primary" loading={action.pending} onClick={() => run(() => api.procurement.approve(po.id), t("procurement.approved"))}>
                {t("procurement.approve")}
              </Button>
              <Button onClick={() => setDialog("return")}>{t("procurement.returnForChanges")}</Button>
            </>
          ) : null}
          {po.status === "pending_approval" && !canApprove ? <span className={styles.muted}>{t("procurement.approverOnly")}</span> : null}
          {po.status === "approved" && canWrite ? (
            <Button variant="primary" loading={action.pending} onClick={() => run(() => api.procurement.markSent(po.id), t("procurement.sentDone"))}>
              {t("procurement.markSent")}
            </Button>
          ) : null}
          {open && canWrite ? (
            <Button variant="danger" onClick={() => setDialog("cancel")}>
              {po.lines.some((l) => l.received_quantity > 0) ? t("procurement.close") : t("procurement.cancel")}
            </Button>
          ) : null}
        </div>

        {editing && po.status === "draft" ? (
          <PurchaseOrderForm
            suppliers={[{ id: po.supplier.id, name: po.supplier.name ?? "", status: "active" }]}
            existing={po}
            onSaved={(next) => {
              onChange(next);
              setEditing(false);
              toast(t("procurement.saved"));
            }}
          />
        ) : null}

        {["approved", "sent", "partially_received"].includes(po.status) ? <ShareBox text={po.share_text} /> : null}

        <section className={styles.card} aria-labelledby="po-lines-title">
          <div className={styles.head}>
            <h2 id="po-lines-title">{t("procurement.lines")}</h2>
            {po.expected_at ? <span className={styles.muted}>{t("procurement.expected")}: {date(po.expected_at)}</span> : null}
          </div>
          {po.warnings.map((w) => {
            const l = po.lines.find((x) => x.variant_id === w.variant_id);
            return (
              <span key={w.variant_id} className={styles.warn} role="status">
                <Icon name="alert" /> {itemLabel(l?.title, l?.variant)}: {t("procurement.belowMoq", { moq: w.moq })}
              </span>
            );
          })}
          <div className={table.wrap}>
            <table className={table.table} data-testid="po-lines">
              <thead>
                <tr>
                  <th scope="col">{t("procurement.item")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colOrdered")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colReceived")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colDefective")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colRemaining")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colUnit")}</th>
                  <th scope="col" className={table.num}>{t("procurement.colLanded")}</th>
                </tr>
              </thead>
              <tbody>
                {po.lines.map((l) => (
                  <tr key={l.id}>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>{l.product_id ? <Link href={`/products/${l.product_id}`}>{itemLabel(l.title, l.variant)}</Link> : itemLabel(l.title, l.variant)}</strong>
                        <span>{l.sku}</span>
                      </div>
                    </td>
                    <td className={table.num}>{l.quantity}</td>
                    <td className={table.num}>{l.received_quantity - l.defective_quantity}</td>
                    <td className={table.num}>{l.defective_quantity}</td>
                    <td className={table.num}>{l.remaining}</td>
                    <td className={table.num}>{money(l.unit_cost_minor, po.currency)}</td>
                    <td className={table.num} data-testid="line-landed">
                      {l.landed_unit_cost_minor != null ? money(l.landed_unit_cost_minor, po.currency) : "–"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <dl className={styles.totals}>
            <dt>{t("procurement.subtotal")}</dt>
            <dd>{money(po.subtotal_minor, po.currency)}</dd>
            {po.freight_minor ? (
              <>
                <dt>{t("procurement.freight")}</dt>
                <dd>{money(po.freight_minor, po.currency)}</dd>
              </>
            ) : null}
            {po.duty_minor ? (
              <>
                <dt>{t("procurement.duty")}</dt>
                <dd>{money(po.duty_minor, po.currency)}</dd>
              </>
            ) : null}
            {po.other_minor ? (
              <>
                <dt>{t("procurement.other")}</dt>
                <dd>{money(po.other_minor, po.currency)}</dd>
              </>
            ) : null}
            <dt className={styles.grand}>{t("procurement.total")}</dt>
            <dd className={styles.grand} data-testid="po-total">
              {money(po.total_minor, po.currency)}
            </dd>
          </dl>
          {po.notes ? <p className={styles.muted} style={{ whiteSpace: "pre-wrap", margin: 0 }}>{po.notes}</p> : null}
        </section>

        {receivable && canWrite ? <ReceiveForm po={po} onReceived={(next) => { onChange(next); toast(t("procurement.receivedDone")); }} /> : null}
        <Receipts po={po} />
      </div>

      <ConfirmDialog
        open={dialog !== null}
        onOpenChange={(v) => !v && setDialog(null)}
        title={
          dialog === "return"
            ? t("procurement.returnTitle")
            : po.lines.some((l) => l.received_quantity > 0)
              ? t("procurement.closeTitle")
              : t("procurement.cancelTitle")
        }
        confirmLabel={dialog === "return" ? t("procurement.returnForChanges") : po.lines.some((l) => l.received_quantity > 0) ? t("procurement.close") : t("procurement.cancel")}
        pending={action.pending}
        onConfirm={async () => {
          if (reason.trim().length < 3) return;
          const next =
            dialog === "return"
              ? await run(() => api.procurement.reject(po.id, reason.trim()), t("procurement.returned"))
              : await run(() => api.procurement.cancel(po.id, reason.trim()), t(po.lines.some((l) => l.received_quantity > 0) ? "procurement.closedDone" : "procurement.cancelled"));
          if (next) {
            setDialog(null);
            setReason("");
          } else reload();
        }}
      >
        <TextField
          label={dialog === "return" ? t("procurement.returnReason") : t("procurement.cancelReason")}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          minLength={3}
          maxLength={300}
          required
        />
      </ConfirmDialog>
    </>
  );
}

function Timeline({ po }: { po: PurchaseOrder }) {
  const { t, date } = useI18n();
  const order = ["draft", "pending_approval", "approved", "sent", "partially_received", "received"];
  const at = order.indexOf(po.status);
  const steps = [
    { key: "draft", label: t("procurement.step_draft"), when: po.created_at, done: at >= 1 || po.submitted_at !== null, current: po.status === "draft" },
    { key: "approval", label: t("procurement.step_approval"), when: po.approved_at, done: at >= 2, current: po.status === "pending_approval" },
    { key: "sent", label: t("procurement.step_sent"), when: po.sent_at, done: at >= 3 && po.sent_at !== null, current: po.status === "approved" },
    { key: "received", label: t("procurement.step_received"), when: po.received_at, done: po.status === "received", current: po.status === "sent" || po.status === "partially_received" },
  ];
  return (
    <ol className={styles.steps} aria-label={t("procurement.timeline")} style={{ marginBottom: "var(--space-4)" }}>
      {steps.map((s) => (
        <li key={s.key} className={styles.step} data-state={s.done ? "done" : s.current && po.status !== "cancelled" ? "current" : "todo"} aria-current={s.current ? "step" : undefined}>
          <span>{s.label}</span>
          <span className={styles.muted}>{s.when && (s.done || s.key === "draft") ? date(s.when) : "–"}</span>
        </li>
      ))}
    </ol>
  );
}

function ApprovalCallout({ po }: { po: PurchaseOrder }) {
  const { t, money } = useI18n();
  const { can } = useAuth();
  const policy = useApiQuery((a) => (can("automation.read") && po.approval_reason === "above_threshold" ? a.automation.policy() : Promise.resolve(null)), [po.approval_reason]);
  const limit = policy.state.status === "success" && policy.state.data ? policy.state.data.thresholds.po_minor : undefined;
  const text =
    po.approval_reason === "needs_approver"
      ? t("procurement.pending_needs_approver")
      : limit === 0
        ? t("procurement.pending_above_threshold_zero")
        : t("procurement.pending_above_threshold", { limit: limit !== undefined ? money(limit, po.currency) : "–" });
  return (
    <InlineAlert tone="warning" live={false}>
      <span data-testid="po-approval-reason">{text}</span>
    </InlineAlert>
  );
}

function ShareBox({ text }: { text: string }) {
  const { t } = useI18n();
  const toast = useToast();
  return (
    <section className={styles.card} aria-labelledby="share-title">
      <div className={styles.head}>
        <h2 id="share-title">{t("procurement.shareTitle")}</h2>
        <Button
          size="sm"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(text);
              toast(t("procurement.copied"));
            } catch {
              /* clipboard blocked: the text stays selectable */
            }
          }}
        >
          <Icon name="copy" /> {t("procurement.copy")}
        </Button>
      </div>
      <pre className={styles.share} data-testid="po-share">
        {text}
      </pre>
      <span className={styles.muted}>{t("procurement.shareHint")}</span>
    </section>
  );
}

export function ReceiveForm({ po, onReceived }: { po: PurchaseOrder; onReceived: (po: PurchaseOrder) => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const lines = po.lines.filter((l) => l.remaining > 0);
  const [good, setGood] = useState<Record<string, string>>({});
  const [bad, setBad] = useState<Record<string, string>>({});
  const [lot, setLot] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const idem = useRef(newIdem());
  const example = `${po.number}-${po.receipts.length + 1}`;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const items = lines.map((l) => ({ l, g: Number.parseInt(good[l.id] || "0", 10), b: Number.parseInt(bad[l.id] || "0", 10) }));
    if (items.some((x) => Number.isNaN(x.g) || Number.isNaN(x.b) || x.g < 0 || x.b < 0)) return setError(t("procurement.errReceiveNegative"));
    const over = items.find((x) => x.g + x.b > x.l.remaining);
    if (over) return setError(t("procurement.errReceiveOver", { item: itemLabel(over.l.title, over.l.variant), n: over.l.remaining }));
    const filled = items.filter((x) => x.g + x.b > 0);
    if (!filled.length) return setError(t("procurement.errReceiveEmpty"));
    setError(null);
    const next = await action.run(() =>
      api.procurement.receive(
        po.id,
        { lines: filled.map((x) => ({ po_line_id: x.l.id, quantity: x.g, defective_quantity: x.b })), lot_code: lot.trim() || null, note: note.trim() || null },
        { idempotencyKey: idem.current },
      ),
    );
    if (next) {
      idem.current = newIdem();
      setGood({});
      setBad({});
      setLot("");
      setNote("");
      onReceived(next);
    }
  };
  if (!lines.length) return null;
  return (
    <form className={styles.card} onSubmit={submit} noValidate aria-labelledby="receive-title" data-testid="receive-form">
      <div className={styles.head}>
        <h2 id="receive-title">{t("procurement.receiveTitle")}</h2>
      </div>
      <span className={styles.muted}>{t("procurement.receiveHint")}</span>
      {error ? <InlineAlert tone="danger">{error}</InlineAlert> : null}
      <ErrorAlert error={action.error} />
      {lines.map((l) => {
        const label = itemLabel(l.title, l.variant);
        return (
          <div key={l.id} className={styles.receiveGrid}>
            <div className={styles.itemCell}>
              <strong>{label}</strong>
              <span className={styles.muted}>{t("procurement.remainingOf", { n: l.remaining })}</span>
            </div>
            <TextField
              label={t("procurement.good")}
              aria-label={t("procurement.goodFor", { item: label })}
              inputMode="numeric"
              value={good[l.id] ?? ""}
              onChange={(e) => setGood((s) => ({ ...s, [l.id]: e.target.value.replace(/[^\d]/g, "") }))}
            />
            <TextField
              label={t("procurement.colDefective")}
              aria-label={t("procurement.defectiveFor", { item: label })}
              inputMode="numeric"
              value={bad[l.id] ?? ""}
              onChange={(e) => setBad((s) => ({ ...s, [l.id]: e.target.value.replace(/[^\d]/g, "") }))}
            />
          </div>
        );
      })}
      <div className={styles.grid2}>
        <TextField label={t("procurement.lot")} hint={t("procurement.lotHint", { example })} value={lot} onChange={(e) => setLot(e.target.value)} maxLength={40} optionalLabel={t("common.optional")} />
        <TextField label={t("procurement.receiveNote")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} optionalLabel={t("common.optional")} />
      </div>
      <div className={styles.row}>
        <Button type="submit" variant="primary" loading={action.pending}>
          {t("procurement.receive")}
        </Button>
      </div>
    </form>
  );
}

function Receipts({ po }: { po: PurchaseOrder }) {
  const { t, money, dateTime } = useI18n();
  const byLine = Object.fromEntries(po.lines.map((l) => [l.id, itemLabel(l.title, l.variant)]));
  return (
    <section className={styles.card} aria-labelledby="receipts-title" data-testid="po-receipts">
      <div className={styles.head}>
        <h2 id="receipts-title">{t("procurement.receipts")}</h2>
      </div>
      {po.receipts.length === 0 ? (
        <span className={styles.muted}>{t("procurement.receiptsEmpty")}</span>
      ) : (
        <ul className={styles.receipts}>
          {po.receipts.map((r) => (
            <li key={r.id}>
              <span className={styles.row}>
                <strong>{r.lot_code}</strong>
                <span className={styles.muted}>{dateTime(r.received_at)}</span>
              </span>
              {r.lines.map((rl) => (
                <span key={rl.po_line_id}>
                  {t("procurement.receiptLine", { item: byLine[rl.po_line_id] ?? "", good: rl.quantity, bad: rl.defective_quantity, landed: money(rl.landed_unit_cost_minor, po.currency) })}
                </span>
              ))}
              {r.note ? <span className={styles.muted}>{r.note}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
