"use client";

import type { CourierAccount, CourierProvider, DeliveryFeeRule, FulfillmentSettings, PickupAddress } from "@commerce-os/api-client";
import { useEffect, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { Checkbox, SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, SectionHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert, useNepalReference } from "../orders/shared";
import fstyles from "../fulfillment/fulfillment.module.css";

const EMPTY_PICKUP: PickupAddress = { name: "", phone: "", district: "", municipality: "", area: "" };
const toRs = (minor: number | null | undefined) => (minor == null ? "" : String(minor / 100));
const toMinor = (rs: string): number | null => {
  const n = Number(rs.replace(/,/g, "").trim());
  return rs.trim() === "" || !Number.isFinite(n) || n < 0 ? null : Math.round(n * 100);
};

/** Settings → Couriers & delivery: who delivers, what customers pay, when customers hear from you. */
export function CouriersView() {
  const { t } = useI18n();
  const { can } = useAuth();
  const couriers = useApiQuery((a) => a.couriers.list());
  const providers = useApiQuery((a) => a.couriers.providers());
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<CourierAccount | null>(null);
  const [removing, setRemoving] = useState<CourierAccount | null>(null);
  const manage = can("settings.manage");
  const toast = useToast();
  const { api } = useAuth();
  const action = useAction();

  return (
    <>
      <PageHeader title={t("couriers.title")} subtitle={t("couriers.subtitle")} level={2} />
      <SectionHeader
        title={t("couriers.yours")}
        id="couriers-heading"
        action={
          manage ? (
            <Button size="sm" variant="primary" onClick={() => setAdding(true)}>
              <Icon name="plus" />
              {t("couriers.add")}
            </Button>
          ) : undefined
        }
      />
      <ErrorAlert error={action.error} />
      {couriers.state.status === "loading" ? (
        <TableSkeleton columns="1.4fr 1.4fr 1fr" rows={2} label={t("common.loading")} />
      ) : couriers.state.status === "error" ? (
        <QueryError error={couriers.state.error} onRetry={couriers.reload} />
      ) : couriers.state.data.items.length === 0 ? (
        <EmptyState title={t("couriers.empty")} body={t("couriers.emptyBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="couriers-heading" data-testid="couriers">
            <tbody>
              {couriers.state.data.items.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        {c.display_name}{" "}
                        {c.is_default ? (
                          <Badge tone="success" dot={false}>
                            {t("couriers.default")}
                          </Badge>
                        ) : null}{" "}
                        {c.status === "error" ? <Badge tone="danger">{t("errors.courier_reconnect_required")}</Badge> : null}
                      </strong>
                      <span>
                        {c.manual ? t("couriers.manual") : null}
                        {providers.state.status === "success" && providers.state.data.items.find((p) => p.code === c.provider)?.sandbox ? t("couriers.sandbox") : null}
                      </span>
                    </div>
                  </td>
                  <td className={table.hideSm}>
                    {c.pickup_complete ? (
                      <div className={table.primaryCell}>
                        <strong>{c.pickup.name}</strong>
                        <span>{[c.pickup.area, c.pickup.municipality, c.pickup.district_name].filter(Boolean).join(", ")}</span>
                      </div>
                    ) : c.manual ? (
                      "–"
                    ) : (
                      <Badge tone="warning">{t("couriers.pickupMissing")}</Badge>
                    )}
                  </td>
                  <td>
                    {manage ? (
                      <div className={fstyles.row} style={{ justifyContent: "flex-end" }}>
                        {!c.is_default ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            loading={action.pending}
                            onClick={async () => (await action.run(() => api.couriers.update(c.id, { is_default: true }))) && (toast(t("couriers.saved")), couriers.reload())}
                          >
                            {t("couriers.makeDefault")}
                          </Button>
                        ) : null}
                        <Button size="sm" variant="ghost" onClick={() => setEditing(c)}>
                          {t("couriers.edit")}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setRemoving(c)}>
                          {t("couriers.disconnect")}
                        </Button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DeliveryFees manage={manage} />
      <NotifySettings manage={manage} />

      <AddCourier
        open={adding}
        onOpenChange={setAdding}
        providers={providers.state.status === "success" ? providers.state.data.items : []}
        onAdded={() => (toast(t("couriers.added")), couriers.reload())}
      />
      <EditCourier courier={editing} onClose={() => setEditing(null)} onSaved={() => (toast(t("couriers.saved")), couriers.reload())} />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(v) => !v && setRemoving(null)}
        title={t("couriers.disconnectTitle", { name: removing?.display_name ?? "" })}
        body={t("couriers.disconnectBody")}
        confirmLabel={t("couriers.disconnect")}
        destructive
        pending={action.pending}
        onConfirm={async () => {
          if (!removing) return;
          const ok = await action.run(() => api.couriers.disconnect(removing.id).then(() => true));
          setRemoving(null);
          if (ok) couriers.reload();
        }}
      />
    </>
  );
}

function PickupFields({ value, onChange }: { value: PickupAddress; onChange: (p: PickupAddress) => void }) {
  const { t } = useI18n();
  const ref = useNepalReference();
  const set = (patch: Partial<PickupAddress>) => onChange({ ...value, ...patch });
  return (
    <fieldset style={{ border: 0, padding: 0, margin: 0, display: "grid", gap: "var(--space-3)" }}>
      <legend style={{ fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-1)" }}>{t("couriers.pickupTitle")}</legend>
      <p className={fstyles.muted} style={{ margin: 0 }}>
        {t("couriers.pickupHint")}
      </p>
      <TextField label={t("couriers.pickupName")} value={value.name ?? ""} onChange={(e) => set({ name: e.target.value })} maxLength={160} autoComplete="organization" />
      <TextField label={t("couriers.pickupPhone")} value={value.phone ?? ""} onChange={(e) => set({ phone: e.target.value })} inputMode="tel" maxLength={20} autoComplete="tel" />
      <SelectField label={t("couriers.pickupDistrict")} value={value.district ?? ""} onChange={(e) => set({ district: e.target.value })}>
        <option value="">{t("orders.address.pickDistrict")}</option>
        {(ref?.districts ?? []).map((d) => (
          <option key={d.code} value={d.code}>
            {d.name}
          </option>
        ))}
      </SelectField>
      <TextField label={t("couriers.pickupMunicipality")} value={value.municipality ?? ""} onChange={(e) => set({ municipality: e.target.value })} maxLength={120} />
      <TextField label={t("couriers.pickupArea")} value={value.area ?? ""} onChange={(e) => set({ area: e.target.value })} maxLength={160} />
    </fieldset>
  );
}

function clean(p: PickupAddress): Partial<PickupAddress> {
  return Object.fromEntries(Object.entries(p).map(([k, v]) => [k, typeof v === "string" && v.trim() ? v.trim() : null]));
}

function AddCourier({ open, onOpenChange, providers, onAdded }: { open: boolean; onOpenChange: (v: boolean) => void; providers: CourierProvider[]; onAdded: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [provider, setProvider] = useState("");
  const [name, setName] = useState("");
  const [creds, setCreds] = useState<Record<string, string>>({});
  const [pickup, setPickup] = useState<PickupAddress>(EMPTY_PICKUP);
  const chosen = providers.find((p) => p.code === (provider || providers[0]?.code)) ?? null;
  const manual = chosen?.capabilities.includes("manual_updates") ?? false;
  useEffect(() => {
    if (!open) {
      setProvider("");
      setName("");
      setCreds({});
      setPickup(EMPTY_PICKUP);
      action.clear();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("couriers.addTitle")}
      footer={
        <Button
          variant="primary"
          disabled={!chosen}
          loading={action.pending}
          onClick={async () => {
            if (!chosen) return;
            const a = await action.run(() =>
              api.couriers.connect({ provider: chosen.code, display_name: name.trim() || null, credentials: creds, pickup: manual ? {} : clean(pickup) }),
            );
            if (a) {
              onOpenChange(false);
              onAdded();
            }
          }}
        >
          {t("couriers.add")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }}>
        <ErrorAlert error={action.error} />
        <SelectField label={t("couriers.provider")} value={chosen?.code ?? ""} onChange={(e) => setProvider(e.target.value)}>
          {providers.map((p) => (
            <option key={p.code} value={p.code}>
              {p.name}
              {p.sandbox ? ` (${t("couriers.sandbox")})` : ""}
            </option>
          ))}
        </SelectField>
        <TextField label={t("couriers.displayName")} value={name} onChange={(e) => setName(e.target.value)} placeholder={chosen?.name} maxLength={120} />
        {chosen?.auth_fields?.length ? (
          <fieldset style={{ border: 0, padding: 0, margin: 0, display: "grid", gap: "var(--space-3)" }}>
            <legend style={{ fontWeight: "var(--font-weight-medium)" }}>{t("couriers.credentials")}</legend>
            {chosen.auth_fields.map((f) => (
              <TextField key={f} label={f} value={creds[f] ?? ""} onChange={(e) => setCreds((c) => ({ ...c, [f]: e.target.value }))} type="password" autoComplete="off" required />
            ))}
          </fieldset>
        ) : null}
        {!manual ? <PickupFields value={pickup} onChange={setPickup} /> : null}
      </div>
    </Drawer>
  );
}

function EditCourier({ courier, onClose, onSaved }: { courier: CourierAccount | null; onClose: () => void; onSaved: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [name, setName] = useState("");
  const [pickup, setPickup] = useState<PickupAddress>(EMPTY_PICKUP);
  useEffect(() => {
    if (courier) {
      setName(courier.display_name);
      setPickup({ name: courier.pickup.name ?? "", phone: courier.pickup.phone ?? "", district: courier.pickup.district ?? "", municipality: courier.pickup.municipality ?? "", area: courier.pickup.area ?? "" });
      action.clear();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courier]);
  return (
    <Drawer
      open={courier !== null}
      onOpenChange={(v) => !v && onClose()}
      title={t("couriers.editTitle", { name: courier?.display_name ?? "" })}
      footer={
        <Button
          variant="primary"
          disabled={!name.trim()}
          loading={action.pending}
          onClick={async () => {
            if (!courier) return;
            const a = await action.run(() => api.couriers.update(courier.id, { display_name: name.trim(), ...(courier.manual ? {} : { pickup: clean(pickup) }) }));
            if (a) {
              onClose();
              onSaved();
            }
          }}
        >
          {t("couriers.save")}
        </Button>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-3)" }}>
        <ErrorAlert error={action.error} />
        <TextField label={t("couriers.displayName")} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required />
        {courier && !courier.manual ? <PickupFields value={pickup} onChange={setPickup} /> : null}
      </div>
    </Drawer>
  );
}

type FeeRow = { scope: DeliveryFeeRule["scope"]; district: string; fee: string; freeOver: string };

function DeliveryFees({ manage }: { manage: boolean }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const ref = useNepalReference();
  const rules = useApiQuery((a) => a.couriers.feeRules());
  const [rows, setRows] = useState<FeeRow[] | null>(null);
  useEffect(() => {
    if (rules.state.status !== "success") return;
    const items = rules.state.data.items;
    const row = (r?: DeliveryFeeRule, scope: FeeRow["scope"] = "default"): FeeRow => ({
      scope: r?.scope ?? scope,
      district: r?.district ?? "",
      fee: toRs(r?.fee_minor),
      freeOver: toRs(r?.free_over_minor),
    });
    setRows([
      row(items.find((r) => r.scope === "default"), "default"),
      row(items.find((r) => r.scope === "inside_valley"), "inside_valley"),
      ...items.filter((r) => r.scope === "district").map((r) => row(r)),
    ]);
  }, [rules.state]);
  const set = (i: number, patch: Partial<FeeRow>) => setRows((rs) => rs && rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const payload: DeliveryFeeRule[] = (rows ?? [])
    .filter((r) => toMinor(r.fee) !== null && (r.scope !== "district" || r.district))
    .map((r) => ({ scope: r.scope, district: r.scope === "district" ? r.district : null, fee_minor: toMinor(r.fee)!, free_over_minor: toMinor(r.freeOver) || null }));

  return (
    <>
      <SectionHeader title={t("couriers.fees.title")} id="fees-heading" />
      <p className={fstyles.muted} style={{ marginTop: 0 }}>
        {t("couriers.fees.hint")}
      </p>
      {rules.state.status === "error" ? <QueryError error={rules.state.error} onRetry={rules.reload} /> : null}
      {rows ? (
        <form
          aria-labelledby="fees-heading"
          onSubmit={async (e) => {
            e.preventDefault();
            if (await action.run(() => api.couriers.saveFeeRules(payload))) {
              toast(t("couriers.fees.saved"));
              rules.reload();
            }
          }}
          style={{ display: "grid", gap: "var(--space-3)" }}
          data-testid="fee-rules"
        >
          <ErrorAlert error={action.error} />
          {payload.length === 0 ? <p className={fstyles.muted}>{t("couriers.fees.none")}</p> : null}
          <div className={table.wrap}>
            <table className={[table.table, table.dense].join(" ")}>
              <thead>
                <tr>
                  <th scope="col">{t("couriers.fees.area")}</th>
                  <th scope="col">{t("couriers.fees.fee")}</th>
                  <th scope="col">{t("couriers.fees.freeOver")}</th>
                  <th scope="col" />
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const area = r.scope === "district" ? t("couriers.fees.scope.district") : t(`couriers.fees.scope.${r.scope}`);
                  return (
                    <tr key={i}>
                      <td>
                        {r.scope === "district" ? (
                          <SelectField label={t("couriers.fees.scope.district")} value={r.district} onChange={(e) => set(i, { district: e.target.value })} disabled={!manage}>
                            <option value="">{t("orders.address.pickDistrict")}</option>
                            {(ref?.districts ?? []).map((d) => (
                              <option key={d.code} value={d.code}>
                                {d.name}
                              </option>
                            ))}
                          </SelectField>
                        ) : (
                          area
                        )}
                      </td>
                      <td>
                        <TextField label={`${t("couriers.fees.fee")} · ${area}`} inputMode="decimal" value={r.fee} onChange={(e) => set(i, { fee: e.target.value })} disabled={!manage} style={{ maxWidth: 120 }} />
                      </td>
                      <td>
                        <TextField label={`${t("couriers.fees.freeOver")} · ${area}`} inputMode="decimal" value={r.freeOver} onChange={(e) => set(i, { freeOver: e.target.value })} disabled={!manage} style={{ maxWidth: 140 }} />
                      </td>
                      <td>
                        {r.scope === "district" && manage ? (
                          <Button size="sm" variant="ghost" iconOnly aria-label={t("couriers.fees.remove")} onClick={() => setRows((rs) => rs && rs.filter((_, j) => j !== i))}>
                            <Icon name="close" />
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {manage ? (
            <div className={fstyles.row}>
              <Button size="sm" variant="ghost" onClick={() => setRows((rs) => [...(rs ?? []), { scope: "district", district: "", fee: "", freeOver: "" }])}>
                <Icon name="plus" />
                {t("couriers.fees.addDistrict")}
              </Button>
              <Button size="sm" type="submit" variant="primary" loading={action.pending}>
                {t("couriers.save")}
              </Button>
            </div>
          ) : null}
        </form>
      ) : rules.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr" rows={3} label={t("common.loading")} />
      ) : null}
    </>
  );
}

function NotifySettings({ manage }: { manage: boolean }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const settings = useApiQuery((a) => a.couriers.settings());
  const [form, setForm] = useState<FulfillmentSettings | null>(null);
  useEffect(() => {
    if (settings.state.status === "success") setForm(settings.state.data);
  }, [settings.state]);
  return (
    <>
      <SectionHeader title={t("couriers.notify.title")} id="notify-heading" />
      {settings.state.status === "error" ? <QueryError error={settings.state.error} onRetry={settings.reload} /> : null}
      {form ? (
        <form
          aria-labelledby="notify-heading"
          style={{ display: "grid", gap: "var(--space-3)", maxWidth: 520 }}
          onSubmit={async (e) => {
            e.preventDefault();
            const next = await action.run(() => api.couriers.updateSettings(form));
            if (next) {
              setForm(next);
              toast(t("couriers.notify.saved"));
            }
          }}
        >
          <ErrorAlert error={action.error} />
          <div>
            <Checkbox label={t("couriers.notify.label")} checked={form.notify_customers} disabled={!manage} onChange={(e) => setForm({ ...form, notify_customers: e.target.checked })} />
            <p className={fstyles.muted} style={{ margin: "var(--space-1) 0 0" }}>
              {t("couriers.notify.hint")}
            </p>
          </div>
          <TextField
            label={t("couriers.notify.wait")}
            type="number"
            min={1}
            max={168}
            value={form.recovery_wait_hours}
            disabled={!manage}
            onChange={(e) => setForm({ ...form, recovery_wait_hours: Math.max(1, Math.min(168, Number(e.target.value) || 1)) })}
          />
          <TextField
            label={t("couriers.notify.weight")}
            type="number"
            min={1}
            max={100000}
            value={form.default_weight_grams}
            disabled={!manage}
            onChange={(e) => setForm({ ...form, default_weight_grams: Math.max(1, Math.min(100000, Number(e.target.value) || 1)) })}
          />
          {manage ? (
            <div>
              <Button size="sm" type="submit" variant="primary" loading={action.pending}>
                {t("couriers.save")}
              </Button>
            </div>
          ) : null}
        </form>
      ) : null}
    </>
  );
}
