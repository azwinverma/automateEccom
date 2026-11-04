"use client";

import { isApiError, type CodAwaiting, type CodSettlement } from "@commerce-os/api-client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, SectionHeader, type Tone, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import { FulfillmentTabs, isDev } from "./shared";
import styles from "./fulfillment.module.css";

const STATUS_TONE: Record<CodSettlement["status"], Tone> = { needs_review: "warning", reconciled: "info", confirmed: "success" };
const AGES = ["d0_7", "d8_14", "d15_plus"] as const;

/** PAY-010: where the COD cash is, and the courier statements that move it to the merchant. */
export function CodView() {
  const { t, money, number } = useI18n();
  const { can } = useAuth();
  const overview = useApiQuery((a) => a.cod.overview());
  const awaiting = useApiQuery((a) => a.cod.awaiting());
  const settlements = useApiQuery((a) => a.cod.settlements());
  const couriers = useApiQuery((a) => a.couriers.list());
  const [open, setOpen] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const reloadAll = () => {
    overview.reload();
    awaiting.reload();
    settlements.reload();
  };

  if (!can("payments.read")) return null;
  const ov = overview.state.status === "success" ? overview.state.data : null;
  const currency = ov?.currency ?? "NPR";
  const withCouriers = ov ? AGES.reduce((sum, k) => sum + ov.awaiting_by_age[k].amount_minor, 0) : 0;
  return (
    <>
      <PageHeader
        title={t("fulfillment.title")}
        subtitle={t("cod.subtitle")}
        actions={
          can("payments.write") ? (
            <Button size="sm" onClick={() => setImporting(true)}>
              <Icon name="download" />
              {t("cod.import")}
            </Button>
          ) : null
        }
      />
      <FulfillmentTabs />
      {overview.state.status === "error" ? <QueryError error={overview.state.error} onRetry={overview.reload} /> : null}
      {ov ? (
        <div className={styles.cards} data-testid="cod-overview">
          <section className={[styles.card, styles.cardWide].join(" ")} aria-labelledby="cod-with">
            <h2 id="cod-with">{t("cod.withCouriers")}</h2>
            <span className={styles.big}>{money(withCouriers, currency)}</span>
            {withCouriers ? (
              <div className={styles.age} role="img" aria-label={AGES.map((k) => `${t(`cod.age.${k}`)}: ${money(ov.awaiting_by_age[k].amount_minor, currency)}`).join(", ")}>
                {AGES.map((k, i) =>
                  ov.awaiting_by_age[k].amount_minor ? <span key={k} className={styles[`age${i}`]} style={{ flexGrow: ov.awaiting_by_age[k].amount_minor }} /> : null,
                )}
              </div>
            ) : null}
            <ul className={styles.legend}>
              {AGES.map((k, i) => (
                <li key={k}>
                  <i className={styles[`age${i}`]} aria-hidden />
                  {t(`cod.age.${k}`)} · {money(ov.awaiting_by_age[k].amount_minor, currency)}
                </li>
              ))}
            </ul>
          </section>
          <section className={styles.card} aria-labelledby="cod-review">
            <h2 id="cod-review">{t("cod.needsReview")}</h2>
            <span className={styles.big}>{number(ov.settlements_needing_review)}</span>
          </section>
          <section className={styles.card} aria-labelledby="cod-30">
            <h2 id="cod-30">{t("cod.received30")}</h2>
            <span className={styles.big}>{money(ov.received_last_30_days.amount_minor, currency)}</span>
          </section>
          <section className={styles.card} aria-labelledby="cod-out">
            <h2 id="cod-out">{t("cod.outstanding")}</h2>
            <span className={styles.big}>{money(ov.outstanding.amount_minor, currency)}</span>
            <span className={styles.muted}>{t("cod.parcels", { n: ov.outstanding.count })}</span>
          </section>
        </div>
      ) : overview.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr" rows={2} label={t("common.loading")} />
      ) : null}

      <Awaiting
        rows={awaiting.state.status === "success" ? awaiting.state.data.items : null}
        error={awaiting.state.status === "error" ? awaiting.state.error : null}
        manualIds={new Set((couriers.state.status === "success" ? couriers.state.data.items : []).filter((c) => c.manual).map((c) => c.id))}
        sandboxIds={(couriers.state.status === "success" ? couriers.state.data.items : []).filter((c) => c.provider === "sandbox_courier").map((c) => c.id)}
        onChanged={reloadAll}
        onOpen={setOpen}
      />

      <SectionHeader title={t("cod.settlementsTitle")} id="cod-settlements" />
      {settlements.state.status === "loading" ? (
        <TableSkeleton columns="1.2fr 1fr 1fr 1fr" label={t("common.loading")} />
      ) : settlements.state.status === "error" ? (
        <QueryError error={settlements.state.error} onRetry={settlements.reload} />
      ) : settlements.state.data.items.length === 0 ? (
        <EmptyState title={t("cod.settlementsEmpty")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="cod-settlements" data-testid="settlements">
            <thead>
              <tr>
                <th scope="col">{t("cod.colReference")}</th>
                <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                  {t("cod.colCollected")}
                </th>
                <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                  {t("cod.colFees")}
                </th>
                <th scope="col" className={table.num}>
                  {t("cod.colNet")}
                </th>
              </tr>
            </thead>
            <tbody>
              {settlements.state.data.items.map((st) => (
                <tr key={st.id} data-status={st.status}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <button type="button" className={styles.linkButton} onClick={() => setOpen(st.id)}>
                          {st.reference}
                        </button>
                      </strong>
                      <span>
                        {st.courier_name} · {t(`cod.source.${st.source}`)}
                      </span>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      <Badge tone={STATUS_TONE[st.status]}>{t(`cod.status.${st.status}`)}</Badge>
                    </div>
                    {st.issue_count && st.status !== "confirmed" ? <div className={styles.muted}>{t("cod.issues", { n: st.issue_count })}</div> : null}
                  </td>
                  <td className={[table.num, table.hideSm].join(" ")}>{money(st.collected_minor, st.currency)}</td>
                  <td className={[table.num, table.hideSm].join(" ")}>{money(st.fees_minor, st.currency)}</td>
                  <td className={table.num}>
                    <strong>{money(st.net_minor, st.currency)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <SettlementDrawer id={open} onClose={() => setOpen(null)} onChanged={reloadAll} />
      <ImportDrawer open={importing} onOpenChange={setImporting} couriers={couriers.state.status === "success" ? couriers.state.data.items.filter((c) => !c.manual) : []} onImported={(id) => (reloadAll(), setOpen(id))} />
    </>
  );
}

function Awaiting({
  rows,
  error,
  manualIds,
  sandboxIds,
  onChanged,
  onOpen,
}: {
  rows: CodAwaiting[] | null;
  error: unknown;
  manualIds: Set<string>;
  sandboxIds: string[];
  onChanged: () => void;
  onOpen: (id: string) => void;
}) {
  const { t, money, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [recording, setRecording] = useState(false);
  const [reference, setReference] = useState("");
  const selected = useMemo(() => (rows ?? []).filter((r) => picked.has(r.shipment_id)), [rows, picked]);
  const couriersPicked = new Set(selected.map((r) => r.courier_account_id));
  const total = selected.reduce((s, r) => s + r.cod_amount.amount_minor, 0);
  const canRecord = can("payments.write");

  return (
    <>
      <SectionHeader title={t("cod.awaitingTitle")} id="cod-awaiting" meta={rows?.length ? t("cod.parcels", { n: rows.length }) : undefined} />
      <ErrorAlert error={error ?? action.error} />
      {rows === null && !error ? (
        <TableSkeleton columns="1fr 1fr 1fr 0.6fr" label={t("common.loading")} />
      ) : rows && rows.length === 0 ? (
        <EmptyState title={t("cod.awaitingEmpty")} />
      ) : rows ? (
        <>
          {canRecord && rows.some((r) => manualIds.has(r.courier_account_id)) ? (
            <div className={styles.row} style={{ margin: "var(--space-2) 0" }}>
              <Button size="sm" variant="primary" disabled={!selected.length || couriersPicked.size !== 1} onClick={() => setRecording(true)}>
                <Icon name="cash" />
                {t("cod.recordCash", { n: selected.length })}
              </Button>
              <span className={styles.muted}>{couriersPicked.size > 1 ? t("cod.oneCourier") : t("cod.recordHint")}</span>
            </div>
          ) : null}
          {isDev() && canRecord && sandboxIds.length && rows.some((r) => sandboxIds.includes(r.courier_account_id)) ? (
            <div className={styles.dev} style={{ marginBottom: "var(--space-3)" }}>
              <span className={styles.muted}>{t("fulfillment.dev.title")}</span>
              <div>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={action.pending}
                  data-testid="sandbox-statement"
                  onClick={async () => {
                    const r = await action.run(() => api.devCourier.settlement(sandboxIds[0]!, { fee_minor: 10000 }));
                    if (r?.settlement) {
                      onChanged();
                      onOpen(r.settlement.id);
                    }
                  }}
                >
                  {t("cod.devStatement")}
                </Button>
              </div>
            </div>
          ) : null}
          <div className={table.wrap}>
            <table className={table.table} aria-labelledby="cod-awaiting" data-testid="cod-awaiting">
              <thead>
                <tr>
                  {canRecord ? <th scope="col" style={{ width: 36 }} /> : null}
                  <th scope="col">{t("cod.colOrder")}</th>
                  <th scope="col" className={table.hideSm}>
                    {t("cod.colCourier")}
                  </th>
                  <th scope="col" className={table.num}>
                    {t("cod.colAmount")}
                  </th>
                  <th scope="col" className={table.num}>
                    {t("cod.colWaiting")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.shipment_id}>
                    {canRecord ? (
                      <td>
                        {manualIds.has(r.courier_account_id) ? (
                          <input
                            type="checkbox"
                            checked={picked.has(r.shipment_id)}
                            aria-label={t("cod.selectRow", { number: r.order_number })}
                            onChange={() =>
                              setPicked((p) => {
                                const n = new Set(p);
                                if (n.has(r.shipment_id)) n.delete(r.shipment_id);
                                else n.add(r.shipment_id);
                                return n;
                              })
                            }
                          />
                        ) : null}
                      </td>
                    ) : null}
                    <td>
                      <div className={table.primaryCell}>
                        <strong>
                          <Link href={`/orders/${r.order_id}`}>#{r.order_number}</Link> {r.customer_name ?? ""}
                        </strong>
                        {r.tracking_number ? <span className={styles.mono}>{r.tracking_number}</span> : null}
                      </div>
                    </td>
                    <td className={table.hideSm}>{r.courier_name}</td>
                    <td className={table.num}>{money(r.cod_amount.amount_minor, r.cod_amount.currency)}</td>
                    <td className={table.num}>
                      {r.delivered_at ? (
                        <time dateTime={r.delivered_at} title={dateTime(r.delivered_at)}>
                          <Badge tone={(r.days_waiting ?? 0) > 14 ? "danger" : (r.days_waiting ?? 0) > 7 ? "warning" : "neutral"} dot={false}>
                            {t("cod.days", { n: r.days_waiting ?? 0 })}
                          </Badge>
                        </time>
                      ) : (
                        "–"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      <ConfirmDialog
        open={recording}
        onOpenChange={setRecording}
        title={t("cod.recordTitle", { courier: selected[0]?.courier_name ?? "" })}
        body={t("cod.recordTotal", { n: selected.length, amount: money(total, selected[0]?.cod_amount.currency ?? "NPR") })}
        confirmLabel={t("cod.recordCash", { n: selected.length })}
        pending={action.pending}
        onConfirm={async () => {
          const st = await action.run(() =>
            api.cod.recordCash({ courier_account_id: selected[0]!.courier_account_id, shipment_ids: selected.map((r) => r.shipment_id), reference: reference.trim() || null }),
          );
          if (st) {
            toast(t("cod.recorded"));
            setRecording(false);
            setPicked(new Set());
            setReference("");
            onChanged();
          }
        }}
      >
        <TextField label={t("cod.recordReference")} value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} />
      </ConfirmDialog>
    </>
  );
}

function SettlementDrawer({ id, onClose, onChanged }: { id: string | null; onClose: () => void; onChanged: () => void }) {
  const { t, money } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const detail = useApiQuery((a) => (id ? a.cod.settlement(id) : Promise.resolve(null)), [id]);
  const [accepting, setAccepting] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [bankRef, setBankRef] = useState("");
  const st = detail.state.status === "success" ? detail.state.data : null;
  const write = can("payments.write");
  const update = (next: CodSettlement | undefined) => {
    if (!next) return;
    detail.setData(() => next);
    onChanged();
  };

  return (
    <Drawer
      open={id !== null}
      onOpenChange={(v) => !v && onClose()}
      wide
      title={st ? t("cod.detailTitle", { reference: st.reference }) : t("common.loading")}
      description={st ? t("cod.summaryLine", { courier: st.courier_name, lines: st.line_count }) : undefined}
      footer={
        st && write && st.status !== "confirmed" ? (
          <>
            <Button size="sm" variant="ghost" loading={action.pending} onClick={async () => update(await action.run(() => api.cod.recheck(st.id)))}>
              <Icon name="refresh" />
              {t("cod.recheck")}
            </Button>
            <Button variant="primary" disabled={st.issue_count > 0} onClick={() => setConfirming(true)} data-testid="confirm-settlement">
              {t("cod.confirm")}
            </Button>
          </>
        ) : undefined
      }
    >
      {detail.state.status === "error" ? <QueryError error={detail.state.error} onRetry={detail.reload} /> : null}
      {st ? (
        <div style={{ display: "grid", gap: "var(--space-3)" }} data-testid="settlement-detail">
          <ErrorAlert error={action.error} />
          <dl className={styles.sum}>
            <div>
              <dt>{t("cod.colCollected")}</dt>
              <dd>{money(st.collected_minor, st.currency)}</dd>
            </div>
            <div>
              <dt>{t("cod.colFees")}</dt>
              <dd>−{money(st.fees_minor, st.currency)}</dd>
            </div>
            <div>
              <dt>{t("cod.colNet")}</dt>
              <dd>{money(st.net_minor, st.currency)}</dd>
            </div>
            <div>
              <dt>{t("cod.colStatus")}</dt>
              <dd>
                <Badge tone={STATUS_TONE[st.status]}>{t(`cod.status.${st.status}`)}</Badge>
              </dd>
            </div>
          </dl>
          {st.issue_count && st.status !== "confirmed" ? <p className={styles.muted}>{t("cod.issues", { n: st.issue_count })}</p> : null}
          <div className={table.wrap}>
            <table className={[table.table, table.dense].join(" ")} aria-label={t("cod.detailTitle", { reference: st.reference })}>
              <thead>
                <tr>
                  <th scope="col">{t("cod.colTracking")}</th>
                  <th scope="col">{t("cod.colMatch")}</th>
                  <th scope="col" className={table.num}>
                    {t("cod.colCollected")}
                  </th>
                  <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                    {t("cod.colFees")}
                  </th>
                  <th scope="col" />
                </tr>
              </thead>
              <tbody>
                {(st.lines ?? []).map((ln) => {
                  const issue = ln.match_status !== "matched" && !ln.accepted;
                  return (
                    <tr key={ln.id} className={issue ? styles.lineIssue : ln.accepted ? styles.lineAccepted : undefined} data-match={ln.match_status}>
                      <td>
                        <div className={table.primaryCell}>
                          <strong className={styles.mono}>{ln.tracking_number}</strong>
                          {ln.order_id ? (
                            <span>
                              <Link href={`/orders/${ln.order_id}`}>#{ln.order_number}</Link>
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td>
                        <Badge tone={ln.match_status === "matched" ? "success" : ln.accepted ? "neutral" : "warning"} dot={false}>
                          {t(`cod.match.${ln.match_status}`)}
                        </Badge>
                        {ln.accepted && ln.accept_reason ? <div className={styles.muted}>{t("cod.accepted", { reason: ln.accept_reason })}</div> : null}
                      </td>
                      <td className={table.num}>
                        {money(ln.collected_minor, st.currency)}
                        {ln.expected_minor != null && ln.expected_minor !== ln.collected_minor ? (
                          <div className={styles.muted}>{t("cod.expected", { amount: money(ln.expected_minor, st.currency) })}</div>
                        ) : null}
                      </td>
                      <td className={[table.num, table.hideSm].join(" ")}>{money(ln.fee_minor, st.currency)}</td>
                      <td>
                        {issue && write && st.status !== "confirmed" ? (
                          <Button size="sm" variant="ghost" onClick={() => setAccepting(ln.id)}>
                            {t("cod.accept")}
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      <ConfirmDialog
        open={accepting !== null}
        onOpenChange={(v) => !v && (setAccepting(null), setReason(""))}
        title={t("cod.acceptTitle")}
        body={t("cod.acceptBody")}
        confirmLabel={t("cod.accept")}
        pending={action.pending}
        onConfirm={async () => {
          if (!accepting || reason.trim().length < 3) return;
          const next = await action.run(() => api.cod.acceptLine(accepting, reason.trim()));
          if (next) {
            update(next);
            setAccepting(null);
            setReason("");
          }
        }}
      >
        <TextField label={t("cod.acceptReason")} value={reason} onChange={(e) => setReason(e.target.value)} minLength={3} maxLength={300} required />
      </ConfirmDialog>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={st ? t("cod.confirmTitle", { amount: money(st.net_minor, st.currency) }) : ""}
        body={t("cod.confirmBody")}
        confirmLabel={t("cod.confirm")}
        pending={action.pending}
        onConfirm={async () => {
          if (!st) return;
          const next = await action.run(() => api.cod.confirm(st.id, bankRef.trim() || null));
          if (next) {
            toast(t("cod.confirmed"));
            update(next);
            setConfirming(false);
            setBankRef("");
          }
        }}
      >
        <TextField label={t("cod.bankReference")} value={bankRef} onChange={(e) => setBankRef(e.target.value)} maxLength={120} />
      </ConfirmDialog>
    </Drawer>
  );
}

function ImportDrawer({
  open,
  onOpenChange,
  couriers,
  onImported,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  couriers: { id: string; display_name: string }[];
  onImported: (id: string) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [courier, setCourier] = useState("");
  const [reference, setReference] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const courierId = courier || couriers[0]?.id || "";
  const rows = isApiError(action.error) ? ((action.error.details as { rows?: { row: number; field: string }[] } | undefined)?.rows ?? []) : [];
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("cod.importTitle")}
      footer={
        <Button
          variant="primary"
          disabled={!courierId || !reference.trim() || !file}
          loading={action.pending}
          onClick={async () => {
            if (!file) return;
            const before = Date.now();
            const st = await action.run(() => api.cod.importFile(courierId, reference.trim(), file, file.name));
            if (st) {
              toast(Date.parse(st.created_at) < before - 60000 ? t("cod.alreadyImported") : t("cod.imported"));
              onOpenChange(false);
              setReference("");
              setFile(null);
              onImported(st.id);
            }
          }}
        >
          {t("cod.import")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }}>
        <ErrorAlert error={action.error} />
        {rows.length ? (
          <ul className={styles.muted} style={{ margin: 0 }}>
            {rows.slice(0, 10).map((r) => (
              <li key={`${r.row}:${r.field}`}>{t("cod.rowErrors", { row: r.row, field: r.field })}</li>
            ))}
          </ul>
        ) : null}
        <SelectField label={t("cod.importCourier")} value={courierId} onChange={(e) => setCourier(e.target.value)}>
          {couriers.map((c) => (
            <option key={c.id} value={c.id}>
              {c.display_name}
            </option>
          ))}
        </SelectField>
        <TextField label={t("cod.importReference")} value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} required />
        <TextField label={t("cod.importFile")} hint={t("cod.importHint")} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
      </div>
    </Drawer>
  );
}
