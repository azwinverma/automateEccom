"use client";

import type { OrderDetail, ReturnLineInput, ReturnReason, Returnable } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import orderStyles from "../orders/orders.module.css";
import { ErrorAlert } from "../orders/shared";
import { Checks, RETURN_REASONS, ReturnStatusBadge } from "./shared";
import styles from "./returns.module.css";

const AFTER_DELIVERY = ["delivered", "completed", "returned"];

/** Order page → Returns: what's already coming back, and starting a new return. */
export function ReturnsPanel({ order, onChanged }: { order: OrderDetail; onChanged: () => void }) {
  const { t, money } = useI18n();
  const { can } = useAuth();
  const allowed = can("returns.read") && AFTER_DELIVERY.includes(order.status);
  const returns = useApiQuery((a) => (allowed ? a.returns.forOrder(order.id) : Promise.resolve({ items: [] })), [order.id, order.version, allowed]);
  const [starting, setStarting] = useState(false);
  if (!allowed) return null;
  const items = returns.state.status === "success" ? returns.state.data.items : [];
  return (
    <section className={orderStyles.panel} aria-labelledby="o-returns" data-testid="returns-panel">
      <div className={styles.lineHead}>
        <h2 id="o-returns">{t("returns.panelTitle")}</h2>
        {can("returns.write") && order.status !== "returned" ? (
          <Button size="sm" onClick={() => setStarting(true)}>
            <Icon name="returns" />
            {t("returns.start")}
          </Button>
        ) : null}
      </div>
      {returns.state.status === "error" ? <ErrorAlert error={returns.state.error} /> : null}
      {items.length ? (
        <ul className={styles.compact}>
          {items.map((r) => (
            <li key={r.id}>
              <Link href={`/returns/${r.id}`}>{r.number}</Link>
              <span className={styles.row}>
                <ReturnStatusBadge status={r.status} />
                <span className={styles.muted}>
                  {t(`returns.resolution.${r.resolution}`)}
                  {r.resolution === "refund" && r.refund_due.amount_minor ? ` · ${money(r.refund_due.amount_minor, r.refund_due.currency)}` : ""}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <StartReturn
        open={starting}
        onOpenChange={setStarting}
        order={order}
        onCreated={() => {
          returns.reload();
          onChanged();
        }}
      />
    </section>
  );
}

type Pick = { qty: number; reason: ReturnReason | ""; note: string; exchange: string };

function StartReturn({ open, onOpenChange, order, onCreated }: { open: boolean; onOpenChange: (v: boolean) => void; order: OrderDetail; onCreated: () => void }) {
  const { t, money, date } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const idem = useIdempotencyKey();
  const info = useApiQuery((a) => (open ? a.returns.returnable(order.id) : Promise.resolve(null as Returnable | null)), [open, order.id]);
  const [picks, setPicks] = useState<Record<string, Pick>>({});
  const [resolution, setResolution] = useState<"refund" | "exchange">("refund");
  const [checks, setChecks] = useState<{ eligible: boolean; can_request: boolean; checks: import("@commerce-os/api-client").ReturnCheck[] } | null>(null);
  const data = info.state.status === "success" ? info.state.data : null;

  useEffect(() => {
    if (!open) {
      setPicks({});
      setChecks(null);
      setResolution("refund");
      action.clear();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const lines: ReturnLineInput[] = useMemo(
    () =>
      Object.entries(picks)
        .filter(([, p]) => p.qty > 0 && p.reason)
        .map(([id, p]) => ({
          order_line_id: id,
          quantity: p.qty,
          reason: p.reason as ReturnReason,
          reason_note: p.note.trim() || null,
          ...(resolution === "exchange" ? { exchange_variant_id: p.exchange || null } : {}),
        })),
    [picks, resolution],
  );
  const body = { resolution, lines };

  // Live policy check while the seller fills the form.
  useEffect(() => {
    if (!open || !lines.length) return setChecks(null);
    let live = true;
    const id = setTimeout(() => {
      api.returns.check(order.id, body).then(
        (r) => live && setChecks(r),
        () => live && setChecks(null),
      );
    }, 300);
    return () => {
      live = false;
      clearTimeout(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, JSON.stringify(body)]);

  const set = (id: string, patch: Partial<Pick>) => setPicks((p) => ({ ...p, [id]: { qty: 0, reason: "", note: "", exchange: "", ...p[id], ...patch } }));
  const estimate = data ? lines.reduce((s, l) => s + (data.lines.find((x) => x.order_line_id === l.order_line_id)?.unit_refund_minor ?? 0) * l.quantity, 0) : 0;
  const returnable = data?.lines.filter((l) => l.returnable_quantity > 0) ?? [];

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      wide
      title={t("returns.startTitle", { number: order.number })}
      description={
        data?.deadline
          ? new Date(data.deadline) >= new Date()
            ? t("returns.deadline", { date: date(data.deadline) })
            : t("returns.deadlinePassed", { date: date(data.deadline) })
          : undefined
      }
      footer={
        <Button
          variant="primary"
          disabled={!lines.length || (checks !== null && !checks.can_request) || (resolution === "exchange" && lines.some((l) => !l.exchange_variant_id))}
          loading={action.pending}
          onClick={async () => {
            const r = await action.run(() => api.returns.create(order.id, body, { idempotencyKey: idem.keyFor({ order: order.id, ...body }) }));
            if (r) {
              toast(t("returns.created"));
              idem.reset();
              onOpenChange(false);
              onCreated();
            }
          }}
        >
          {t("returns.create")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }} data-testid="start-return">
        <ErrorAlert error={action.error ?? (info.state.status === "error" ? info.state.error : null)} />
        {data && returnable.length === 0 ? <p className={styles.muted}>{t("returns.nothingLeft")}</p> : null}
        {data && returnable.length ? (
          <>
            <SelectField label={t("returns.resolutionField")} value={resolution} onChange={(e) => setResolution(e.target.value as "refund" | "exchange")}>
              {data.policy.allow_refund ? <option value="refund">{t("returns.resolution.refund")}</option> : null}
              {data.policy.allow_exchange ? <option value="exchange">{t("returns.resolution.exchange")}</option> : null}
            </SelectField>
            {returnable.map((l) => {
              const p = picks[l.order_line_id];
              const title = `${l.title}${l.variant_title && l.variant_title !== "Default" ? ` (${l.variant_title})` : ""}`;
              return (
                <div key={l.order_line_id} className={styles.lineGrid} data-picked={Boolean(p?.qty)}>
                  <div className={styles.lineHead}>
                    <strong>{title}</strong>
                    <span className={styles.row}>
                      {l.final_sale ? <Badge tone="warning">{t("returns.finalSale")}</Badge> : null}
                      <span className={styles.money}>{money(l.unit_refund_minor, data.currency)}</span>
                    </span>
                  </div>
                  <div className={styles.split}>
                    <TextField
                      label={t("returns.qtyOf", { title, max: l.returnable_quantity })}
                      type="number"
                      min={0}
                      max={l.returnable_quantity}
                      value={p?.qty ?? 0}
                      onChange={(e) => set(l.order_line_id, { qty: Math.max(0, Math.min(l.returnable_quantity, Number(e.target.value) || 0)) })}
                    />
                    <SelectField label={t("returns.reasonField")} value={p?.reason ?? ""} onChange={(e) => set(l.order_line_id, { reason: e.target.value as ReturnReason, qty: p?.qty || 1 })}>
                      <option value="">–</option>
                      {RETURN_REASONS.map((r) => (
                        <option key={r} value={r}>
                          {t(`returns.reason.${r}`)}
                        </option>
                      ))}
                    </SelectField>
                    {resolution === "exchange" ? (
                      l.exchange_options.length ? (
                        <SelectField label={t("returns.exchangeFor")} value={p?.exchange ?? ""} onChange={(e) => set(l.order_line_id, { exchange: e.target.value })}>
                          <option value="">–</option>
                          {l.exchange_options.map((o) => (
                            <option key={o.variant_id} value={o.variant_id} disabled={o.available === 0}>
                              {o.title}
                              {o.available !== null ? ` · ${t("returns.inStock", { n: o.available })}` : ""}
                            </option>
                          ))}
                        </SelectField>
                      ) : (
                        <p className={styles.muted}>{t("returns.exchangeNone")}</p>
                      )
                    ) : null}
                  </div>
                  {p?.qty ? <TextField label={t("returns.reasonNote")} value={p.note} onChange={(e) => set(l.order_line_id, { note: e.target.value })} maxLength={500} /> : null}
                </div>
              );
            })}
            {checks ? <Checks checks={checks.checks} /> : null}
            {resolution === "refund" && estimate ? <p className={styles.muted}>{t("returns.estimate", { amount: money(estimate, data.currency) })}</p> : null}
          </>
        ) : null}
        {info.state.status === "loading" ? <p className={styles.muted}>{t("common.loading")}</p> : null}
      </div>
    </Drawer>
  );
}
