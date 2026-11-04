"use client";

import type { CourierOptions, FailureReason, OrderDetail, Shipment, ShipmentStatus } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import orderStyles from "../orders/orders.module.css";
import { FAILURE_REASONS, MANUAL_STATUSES, ROUTE, ShipmentStatusBadge, isDev } from "./shared";
import styles from "./fulfillment.module.css";

const BOOKABLE = ["cod_pending", "ready_to_ship"];
const BEFORE_PACKED = ["draft", "pending_confirmation", "confirmed", "payment_pending"];

/** Order page → Delivery: pick a courier (rules-based recommendation), then follow the parcel. */
export function DeliveryPanel({ order, onChanged }: { order: OrderDetail; onChanged: () => void }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const allowed = can("fulfillment.read");
  const shipments = useApiQuery((a) => (allowed ? a.shipments.forOrder(order.id) : Promise.resolve({ items: [] as Shipment[] })), [order.id, order.version, allowed]);
  // Return pickups are shown on their return, not here.
  const items = shipments.state.status === "success" ? shipments.state.data.items.filter((s) => s.direction !== "return") : [];
  const live = items.find((s) => s.status !== "cancelled");
  const earlier = items.filter((s) => s.status === "cancelled");
  const changed = () => {
    shipments.reload();
    onChanged();
  };

  if (!allowed) return null;
  return (
    <section id="delivery" className={orderStyles.panel} aria-labelledby="o-delivery" data-testid="delivery-panel">
      <h2 id="o-delivery">{t("fulfillment.panel.title")}</h2>
      {shipments.state.status === "loading" ? (
        <p className={styles.muted}>{t("common.loading")}</p>
      ) : shipments.state.status === "error" ? (
        <ErrorAlert error={shipments.state.error} />
      ) : live ? (
        <ShipmentCard shipment={live} onChanged={changed} />
      ) : BOOKABLE.includes(order.status) && can("fulfillment.write") ? (
        <BookCourier order={order} onBooked={changed} />
      ) : (
        <p className={styles.muted}>{BEFORE_PACKED.includes(order.status) ? t("fulfillment.panel.notReady") : "–"}</p>
      )}
      {earlier.length ? (
        <details style={{ marginTop: "var(--space-3)" }}>
          <summary className={styles.muted}>{t("fulfillment.panel.history")}</summary>
          <ul className={styles.events} style={{ marginTop: "var(--space-2)" }}>
            {earlier.map((s) => (
              <li key={s.id}>
                <span>
                  {s.courier_name} · <span className={styles.mono}>{s.tracking_number ?? "–"}</span>
                </span>
                <span className={styles.muted}>{t("fulfillment.status.cancelled")}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

// ----------------------------------------------------------------------------- booking
function BookCourier({ order, onBooked }: { order: OrderDetail; onBooked: () => void }) {
  const { t, money } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const idem = useIdempotencyKey();
  const couriers = useApiQuery((a) => a.couriers.list());
  const [weight, setWeight] = useState<number | null>(null);
  const [weightInput, setWeightInput] = useState("");
  const rates = useApiQuery((a) => a.couriers.rates(order.id, weight), [order.id, weight]);
  const [pick, setPick] = useState<string | null>(null);
  const [courierName, setCourierName] = useState("");
  const [tracking, setTracking] = useState("");

  const data: CourierOptions | null = rates.state.status === "success" ? rates.state.data : null;
  const keyOf = (o: { courier_account_id: string; service_code: string | null }) => `${o.courier_account_id}:${o.service_code ?? ""}`;
  useEffect(() => {
    if (data && weightInput === "") setWeightInput(String(data.weight_grams));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // The recommendation is selected until the seller picks something else (and that option still exists).
  const fallback = data ? (data.options.find((o) => o.recommended) ?? data.options[0] ?? null) : null;
  const chosen = data?.options.find((o) => keyOf(o) === pick) ?? fallback;
  const chosenKey = chosen ? keyOf(chosen) : null;
  if (couriers.state.status === "success" && couriers.state.data.items.length === 0) {
    return (
      <div className={styles.row} style={{ alignItems: "flex-start", flexDirection: "column" }}>
        <strong style={{ fontSize: "var(--font-size-sm)" }}>{t("fulfillment.noCourier")}</strong>
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("fulfillment.noCourierBody")}
        </p>
        <ButtonLink size="sm" href="/settings/couriers">
          {t("fulfillment.connectCourier")}
        </ButtonLink>
      </div>
    );
  }
  const body = chosen
    ? {
        courier_account_id: chosen.courier_account_id,
        service_code: chosen.service_code,
        weight_grams: weight ?? data?.weight_grams ?? null,
        ...(chosen.manual ? { courier_name: courierName.trim() || null, tracking_number: tracking.trim() || null } : {}),
      }
    : null;
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        if (!body) return;
        const s = await action.run(() => api.shipments.book(order.id, body, { idempotencyKey: idem.keyFor({ order: order.id, ...body }) }));
        if (s) {
          toast(t("fulfillment.panel.booked"));
          idem.reset();
          onBooked();
        }
      }}
      style={{ display: "grid", gap: "var(--space-3)" }}
    >
      <ErrorAlert error={action.error ?? (rates.state.status === "error" ? rates.state.error : null)} />
      <div className={styles.row} style={{ alignItems: "flex-end" }}>
        <div style={{ flex: 1, minWidth: 140 }}>
          <TextField
            label={t("fulfillment.panel.weight")}
            type="number"
            inputMode="numeric"
            min={1}
            max={100000}
            value={weightInput}
            onChange={(e) => setWeightInput(e.target.value)}
            onBlur={() => {
              const n = Number(weightInput);
              if (n > 0 && n <= 100000 && n !== (weight ?? data?.weight_grams)) setWeight(Math.round(n));
            }}
          />
        </div>
      </div>
      {data ? (
        <>
          <fieldset className={styles.options}>
            <legend className={styles.muted} style={{ marginBottom: "var(--space-2)" }}>
              {t("fulfillment.panel.options")}
            </legend>
            {data.options.map((o) => (
              <label key={keyOf(o)} className={styles.option}>
                <input type="radio" name="courier" value={keyOf(o)} checked={chosenKey === keyOf(o)} onChange={() => setPick(keyOf(o))} />
                <span className={styles.optionMain}>
                  <strong>
                    {o.display_name}
                    {o.service_code && o.service_code !== "standard" ? ` · ${o.service_code}` : ""}
                  </strong>
                  <span className={styles.muted}>
                    {o.manual
                      ? t("fulfillment.panel.ownRider")
                      : o.eta_days_max === 0 || (o.eta_days_min === 0 && o.eta_days_max === 1)
                        ? t("fulfillment.panel.etaSame")
                        : o.eta_days_min != null && o.eta_days_max != null
                          ? t("fulfillment.panel.eta", { min: o.eta_days_min, max: o.eta_days_max })
                          : ""}
                  </span>
                  {o.recommended && data.recommendation ? (
                    <span className={styles.why}>
                      <Badge tone="automated" dot={false}>
                        {t("fulfillment.panel.recommended")}
                      </Badge>{" "}
                      {t(`fulfillment.panel.why.${data.recommendation.reason}`)}
                    </span>
                  ) : null}
                </span>
                <span className={styles.optionPrice}>{o.price ? money(o.price.amount_minor, o.price.currency) : ""}</span>
              </label>
            ))}
          </fieldset>
          {data.unavailable.map((u) => (
            <p key={u.courier_account_id} className={styles.muted} style={{ margin: 0 }}>
              {t(`fulfillment.panel.unavailable.${u.reason}`, { name: u.display_name })}
            </p>
          ))}
          {data.recommendation ? <p className={styles.muted} style={{ margin: 0 }}>{t("fulfillment.panel.rulesNote")}</p> : null}
          {chosen?.manual ? (
            <>
              <TextField label={t("fulfillment.panel.courierName")} value={courierName} onChange={(e) => setCourierName(e.target.value)} maxLength={80} placeholder={chosen.display_name} />
              <TextField label={t("fulfillment.panel.tracking")} value={tracking} onChange={(e) => setTracking(e.target.value)} maxLength={80} />
            </>
          ) : null}
          <p className={styles.muted} style={{ margin: 0 }}>
            {data.cod_amount_minor ? t("fulfillment.panel.collect", { amount: money(data.cod_amount_minor, order.currency) }) : t("fulfillment.panel.noCollect")}
          </p>
          <div>
            <Button type="submit" variant="primary" disabled={!chosen} loading={action.pending}>
              <Icon name="fulfillment" />
              {t("fulfillment.panel.book")}
            </Button>
          </div>
        </>
      ) : rates.state.status === "loading" ? (
        <p className={styles.muted}>{t("common.loading")}</p>
      ) : null}
    </form>
  );
}

// ----------------------------------------------------------------------------- the parcel
export function RouteLine({ status }: { status: ShipmentStatus }) {
  const { t } = useI18n();
  const failed = ["delivery_failed", "returning", "returned_to_origin", "lost", "reattempt_requested"].includes(status);
  const lastDone = ROUTE.reduce((acc, step, i) => (step.reached.includes(status) ? i : acc), -1);
  return (
    <ol className={[styles.route, failed ? styles.routeFailed : ""].join(" ")} aria-label={t("fulfillment.panel.events")}>
      {ROUTE.map((step, i) => {
        const done = i <= lastDone;
        const current = i === lastDone;
        return (
          <li
            key={step.key}
            className={[styles.stop, done ? styles.stopDone : "", i < lastDone ? styles.stopLink : "", current ? styles.stopCurrent : ""].join(" ")}
            aria-current={current ? "step" : undefined}
          >
            {current && failed ? t(`fulfillment.status.${status}`) : t(`fulfillment.status.${step.key}`)}
          </li>
        );
      })}
    </ol>
  );
}

type Dialog = null | "cancel" | "reattempt" | "return" | "received" | "status" | "tracking";

export function ShipmentCard({ shipment: s, onChanged }: { shipment: Shipment; onChanged: (s?: Shipment) => void }) {
  const { t, money, relative, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<ShipmentStatus>("picked_up");
  const [reason, setReason] = useState<FailureReason | "">("");
  const [tracking, setTracking] = useState(s.tracking_number ?? "");
  const write = can("fulfillment.write");

  const done = async (fn: () => Promise<Shipment>) => {
    const next = await action.run(fn);
    if (next) {
      toast(t("fulfillment.actions.done"));
      setDialog(null);
      setNote("");
      setReason("");
      onChanged(next);
    }
    return next;
  };
  const acts = useMemo(() => new Set(s.actions), [s.actions]);
  const openAttempt = s.attempts?.find((a) => a.recovery_status !== "resolved");

  return (
    <div data-testid="shipment-card" data-status={s.status}>
      <div className={styles.row} style={{ justifyContent: "space-between" }}>
        <ShipmentStatusBadge status={s.status} />
        {s.stuck ? <Badge tone="warning">{t("fulfillment.stuck", { days: Math.max(4, Math.floor((Date.now() - Date.parse(s.last_event_at ?? s.created_at)) / 86400000)) })}</Badge> : null}
      </div>
      <RouteLine status={s.status} />
      <dl className={styles.facts}>
        <dt>{t("fulfillment.colCourier")}</dt>
        <dd>{s.courier_name}</dd>
        <dt>{t("fulfillment.colTracking")}</dt>
        <dd>
          {s.tracking_number ? (
            <span className={styles.row} style={{ gap: "var(--space-1)" }}>
              <span className={styles.mono} data-testid="tracking-number">
                {s.tracking_number}
              </span>
              <Button
                size="sm"
                variant="ghost"
                iconOnly
                aria-label={t("fulfillment.panel.copyTracking")}
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(s.tracking_number!);
                    toast(t("fulfillment.panel.copied"));
                  } catch {
                    /* clipboard blocked: the number is on screen */
                  }
                }}
              >
                <Icon name="copy" />
              </Button>
            </span>
          ) : (
            "–"
          )}
        </dd>
        {s.direction !== "return" ? (
          <>
            <dt>{t("fulfillment.colCod")}</dt>
            <dd>{s.cod_amount.amount_minor ? money(s.cod_amount.amount_minor, s.cod_amount.currency) : t("fulfillment.panel.noCollect")}</dd>
          </>
        ) : null}
        {s.charge ? (
          <>
            <dt>{t("fulfillment.panel.chargeLabel")}</dt>
            <dd>{money(s.charge.amount_minor ?? 0, s.charge.currency)}</dd>
          </>
        ) : null}
      </dl>
      <ErrorAlert error={action.error} />
      {write ? (
        <div className={styles.row} style={{ marginBottom: "var(--space-3)" }}>
          {acts.has("request_pickup") ? (
            <Button size="sm" variant="primary" loading={action.pending} onClick={() => void action.run(() => api.shipments.requestPickup([s.id])).then((r) => r && (toast(t("fulfillment.pickupRequested")), onChanged()))}>
              {t("fulfillment.actions.request_pickup")}
            </Button>
          ) : null}
          {acts.has("reattempt") ? (
            <Button size="sm" variant="primary" onClick={() => setDialog("reattempt")}>
              {t("fulfillment.actions.reattempt")}
            </Button>
          ) : null}
          {acts.has("update_status") ? (
            <Button size="sm" variant={acts.has("reattempt") ? "secondary" : "primary"} onClick={() => setDialog("status")}>
              {t("fulfillment.actions.update_status")}
            </Button>
          ) : null}
          {acts.has("confirm_received_back") && can("inventory.adjust") ? (
            <Button size="sm" variant="primary" onClick={() => setDialog("received")}>
              {t("fulfillment.actions.confirm_received_back")}
            </Button>
          ) : null}
          {acts.has("return_to_sender") ? (
            <Button size="sm" variant="ghost" onClick={() => setDialog("return")}>
              {t("fulfillment.actions.return_to_sender")}
            </Button>
          ) : null}
          {acts.has("set_tracking") && !s.tracking_number ? (
            <Button size="sm" variant="ghost" onClick={() => setDialog("tracking")}>
              {t("fulfillment.actions.set_tracking")}
            </Button>
          ) : null}
          {acts.has("refresh") ? (
            <Button size="sm" variant="ghost" loading={action.pending} onClick={() => void done(() => api.shipments.refresh(s.id))}>
              <Icon name="refresh" />
              {t("fulfillment.actions.refresh")}
            </Button>
          ) : null}
          {acts.has("cancel") ? (
            <Button size="sm" variant="ghost" onClick={() => setDialog("cancel")}>
              {t("fulfillment.actions.cancel")}
            </Button>
          ) : null}
        </div>
      ) : null}
      <div className={styles.row} style={{ marginBottom: "var(--space-3)" }}>
        <ButtonLink size="sm" variant="ghost" href={`/fulfillment/label/${s.id}`}>
          <Icon name="print" />
          {t("fulfillment.panel.printLabel")}
        </ButtonLink>
      </div>

      {s.attempts?.length ? (
        <div style={{ display: "grid", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
          <strong style={{ fontSize: "var(--font-size-sm)" }}>{t("fulfillment.panel.attempts")}</strong>
          {s.attempts.map((a) => (
            <div key={a.id} className={[styles.attempt, a.recovery_status === "resolved" ? styles.attemptResolved : ""].join(" ")} data-testid="delivery-attempt">
              <span>
                <strong>{t("fulfillment.panel.attemptN", { n: a.attempt_no })}</strong> · {t(`fulfillment.reason.${a.failure_reason}`)}
              </span>
              <span className={styles.muted}>
                {a.recovery_status === "resolved" && a.resolution ? t(`fulfillment.resolution.${a.resolution}`) : t(`fulfillment.recovery.${a.recovery_status}`)}
                {a.reattempt_by === "automation" ? ` · ${t("fulfillment.panel.auto")}` : ""}
              </span>
              {a.customer_contacted_at ? (
                <span className={styles.muted}>{t("fulfillment.panel.messaged", { time: relative(a.customer_contacted_at) })}</span>
              ) : a === openAttempt && a.recovery_status !== "reattempt_requested" ? (
                <span className={styles.muted}>{t("fulfillment.panel.noChat")}</span>
              ) : null}
              {a.customer_reply ? <p className={styles.quote}>{t("fulfillment.panel.customerSaid", { text: a.customer_reply })}</p> : null}
            </div>
          ))}
        </div>
      ) : null}

      {s.events?.length ? (
        <>
          <strong style={{ fontSize: "var(--font-size-sm)", display: "block", marginBottom: "var(--space-2)" }}>{t("fulfillment.panel.events")}</strong>
          <ol className={styles.events} data-testid="shipment-events">
            {s.events.map((e) => (
              <li key={e.id} className={e.applied ? undefined : styles.late}>
                <span>
                  {t(`fulfillment.status.${e.status}`)}
                  {e.failure_reason ? ` · ${t(`fulfillment.reason.${e.failure_reason}`)}` : ""}
                </span>
                {e.description || e.location ? <span className={styles.muted}>{[e.location, e.description].filter(Boolean).join(" · ")}</span> : null}
                <span className={styles.muted}>
                  <time dateTime={e.occurred_at} title={dateTime(e.occurred_at)}>
                    {relative(e.occurred_at)}
                  </time>
                  {" · "}
                  {t(`fulfillment.source.${e.source}`)}
                  {!e.applied ? ` · ${t("fulfillment.lateUpdate")}` : ""}
                </span>
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {isDev() && s.provider === "sandbox_courier" && write ? <SandboxCourier shipment={s} onChanged={() => onChanged()} /> : null}

      <ConfirmDialog
        open={dialog === "cancel"}
        onOpenChange={(v) => setDialog(v ? "cancel" : null)}
        title={t("fulfillment.actions.cancelTitle")}
        body={t("fulfillment.actions.cancelBody")}
        confirmLabel={t("fulfillment.actions.cancel")}
        destructive
        pending={action.pending}
        onConfirm={() => void done(() => api.shipments.cancel(s.id, note.trim() || null))}
      >
        <TextField label={t("fulfillment.actions.reason")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} />
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === "return"}
        onOpenChange={(v) => setDialog(v ? "return" : null)}
        title={t("fulfillment.actions.returnTitle")}
        body={t("fulfillment.actions.returnBody")}
        confirmLabel={t("fulfillment.actions.return_to_sender")}
        destructive
        pending={action.pending}
        onConfirm={() => void done(() => api.shipments.returnToSender(s.id, note.trim() || null))}
      >
        <TextField label={t("fulfillment.actions.reason")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} />
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === "received"}
        onOpenChange={(v) => setDialog(v ? "received" : null)}
        title={t("fulfillment.actions.receivedTitle")}
        body={t("fulfillment.actions.receivedBody")}
        confirmLabel={t("fulfillment.actions.confirm_received_back")}
        pending={action.pending}
        onConfirm={() => void done(() => api.shipments.receivedBack(s.id))}
      />
      <Drawer
        open={dialog === "reattempt"}
        onOpenChange={(v) => setDialog(v ? "reattempt" : null)}
        title={t("fulfillment.actions.reattemptTitle")}
        footer={
          <Button variant="primary" loading={action.pending} onClick={() => void done(() => api.shipments.reattempt(s.id, { note: note.trim() || null }))}>
            {t("fulfillment.actions.reattempt")}
          </Button>
        }
      >
        <div style={{ display: "grid", gap: "var(--space-3)" }}>
          <ErrorAlert error={action.error} />
          {openAttempt?.customer_reply ? <p className={styles.quote}>{t("fulfillment.panel.customerSaid", { text: openAttempt.customer_reply })}</p> : null}
          <TextField label={t("fulfillment.actions.reattemptNote")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </div>
      </Drawer>
      <Drawer
        open={dialog === "status"}
        onOpenChange={(v) => setDialog(v ? "status" : null)}
        title={t("fulfillment.actions.statusTitle")}
        footer={
          <Button
            variant="primary"
            loading={action.pending}
            disabled={status === "delivery_failed" && !reason}
            onClick={() => void done(() => api.shipments.setStatus(s.id, { status, failure_reason: status === "delivery_failed" ? (reason as FailureReason) : null, note: note.trim() || null }))}
          >
            {t("couriers.save")}
          </Button>
        }
      >
        <div style={{ display: "grid", gap: "var(--space-3)" }}>
          <ErrorAlert error={action.error} />
          <SelectField label={t("fulfillment.actions.statusField")} value={status} onChange={(e) => setStatus(e.target.value as ShipmentStatus)}>
            {MANUAL_STATUSES.map((st) => (
              <option key={st} value={st}>
                {t(`fulfillment.status.${st}`)}
              </option>
            ))}
          </SelectField>
          {status === "delivery_failed" ? (
            <SelectField label={t("fulfillment.actions.reasonField")} value={reason} onChange={(e) => setReason(e.target.value as FailureReason)} required>
              <option value="">–</option>
              {FAILURE_REASONS.map((r) => (
                <option key={r} value={r}>
                  {t(`fulfillment.reason.${r}`)}
                </option>
              ))}
            </SelectField>
          ) : null}
          <TextField label={t("fulfillment.actions.noteField")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </div>
      </Drawer>
      <Drawer
        open={dialog === "tracking"}
        onOpenChange={(v) => setDialog(v ? "tracking" : null)}
        title={t("fulfillment.actions.trackingTitle")}
        footer={
          <Button variant="primary" disabled={!tracking.trim()} loading={action.pending} onClick={() => void done(() => api.shipments.setTracking(s.id, { tracking_number: tracking.trim() }))}>
            {t("couriers.save")}
          </Button>
        }
      >
        <TextField label={t("fulfillment.actions.trackingTitle")} value={tracking} onChange={(e) => setTracking(e.target.value)} maxLength={80} />
      </Drawer>
    </div>
  );
}

/** Development only: play the sandbox courier (signed webhook through the real ingest path). */
function SandboxCourier({ shipment: s, onChanged }: { shipment: Shipment; onChanged: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  if (!s.tracking_number || ["delivered", "returned_to_origin", "cancelled", "lost"].includes(s.status)) return null;
  const send = async (status: ShipmentStatus, failure_reason?: FailureReason) => {
    const r = await action.run(() => api.devCourier.simulate(s.courier_account_id, { tracking_number: s.tracking_number!, status, failure_reason }));
    // The worker applies the webhook a moment later.
    if (r) window.setTimeout(onChanged, 1500);
  };
  const steps: ShipmentStatus[] = s.status === "returning" ? ["returned_to_origin"] : ["picked_up", "out_for_delivery", "delivered"];
  return (
    <div className={styles.dev} data-testid="sandbox-courier">
      <strong style={{ fontSize: "var(--font-size-xs)" }}>{t("fulfillment.dev.title")}</strong>
      <span className={styles.muted}>{t("fulfillment.dev.hint")}</span>
      <ErrorAlert error={action.error} />
      <div className={styles.row}>
        {steps.map((st) => (
          <Button key={st} size="sm" variant="secondary" loading={action.pending} onClick={() => void send(st)} data-sim={st}>
            {t(`fulfillment.status.${st}`)}
          </Button>
        ))}
        {s.status !== "returning" ? (
          <Button size="sm" variant="ghost" loading={action.pending} onClick={() => void send("delivery_failed", "customer_unreachable")} data-sim="delivery_failed">
            {t("fulfillment.dev.failed")}
          </Button>
        ) : null}
      </div>
      <Link href="/fulfillment" className={styles.muted}>
        {t("fulfillment.title")} →
      </Link>
    </div>
  );
}
