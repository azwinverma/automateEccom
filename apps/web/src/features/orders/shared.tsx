"use client";

import { isApiError, type AddressInput, type NepalReference, type OrderStatus, type PaymentStatusApi } from "@commerce-os/api-client";
import { useEffect, useState } from "react";
import { SelectField, TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, RequestId, type Tone } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./orders.module.css";

export const ORDER_TONE: Record<OrderStatus, Tone> = {
  draft: "neutral",
  pending_confirmation: "warning",
  confirmed: "info",
  payment_pending: "warning",
  cod_pending: "info",
  ready_to_ship: "info",
  shipped: "info",
  delivered: "success",
  completed: "success",
  cancelled: "neutral",
  delivery_failed: "danger",
  returned: "neutral",
};
export const PAYMENT_TONE: Record<PaymentStatusApi, Tone> = {
  unpaid: "neutral",
  pending: "warning",
  paid: "success",
  failed: "danger",
  refunded: "neutral",
  cod_pending: "neutral",
  cod_collected: "success",
};
/** Statuses the seller has to act on (packing, shipping, chasing payment). */
export const TODO_STATUSES: OrderStatus[] = ["pending_confirmation", "payment_pending", "cod_pending", "ready_to_ship", "delivery_failed"];

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useI18n();
  return <Badge tone={ORDER_TONE[status] ?? "neutral"}>{t(`orders.status.${status}`)}</Badge>;
}

export function PaymentBadge({ status }: { status: PaymentStatusApi }) {
  const { t } = useI18n();
  return (
    <Badge tone={PAYMENT_TONE[status] ?? "neutral"} dot={false}>
      {t(`orders.payment.${status}`)}
    </Badge>
  );
}

export function ErrorAlert({ error }: { error: unknown }) {
  const { t } = useI18n();
  if (!error) return null;
  return (
    <InlineAlert tone="danger">
      {errorMessage(t, error)}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  );
}

let referenceCache: Promise<NepalReference> | null = null;
export function useNepalReference(): NepalReference | null {
  const { api } = useAuth();
  const [ref, setRef] = useState<NepalReference | null>(null);
  useEffect(() => {
    referenceCache ??= api.reference.nepal();
    let live = true;
    referenceCache.then((r) => live && setRef(r)).catch(() => {
      referenceCache = null;
    });
    return () => {
      live = false;
    };
  }, [api]);
  return ref;
}

export const EMPTY_ADDRESS: AddressInput = { recipient_name: "", phone: "", district: "", municipality: "", ward: 1, area: "", landmark: "" };

/** Structured Nepal address (ORD-012): district list from the API, ward 1–35. Field errors come from the server. */
export function AddressFields({ value, onChange, errors = {} }: { value: AddressInput; onChange: (a: AddressInput) => void; errors?: Record<string, string> }) {
  const { t } = useI18n();
  const ref = useNepalReference();
  const set = (patch: Partial<AddressInput>) => onChange({ ...value, ...patch });
  const err = (f: string) => (errors[f] ? (t.dynamic(`errors.field.${errors[f]}`) ?? t("errors.field.invalid")) : undefined);
  return (
    <div className={styles.formGrid}>
      <TextField label={t("orders.address.recipient")} value={value.recipient_name} onChange={(e) => set({ recipient_name: e.target.value })} required maxLength={160} error={err("recipient_name")} autoComplete="name" />
      <TextField label={t("orders.address.phone")} value={value.phone} onChange={(e) => set({ phone: e.target.value })} required inputMode="tel" maxLength={24} error={err("phone")} autoComplete="tel" />
      <SelectField label={t("orders.address.district")} value={value.district} onChange={(e) => set({ district: e.target.value })} required error={err("district")}>
        <option value="">{t("orders.address.pickDistrict")}</option>
        {(ref?.districts ?? []).map((d) => (
          <option key={d.code} value={d.code}>
            {d.name}
          </option>
        ))}
      </SelectField>
      <TextField label={t("orders.address.municipality")} value={value.municipality} onChange={(e) => set({ municipality: e.target.value })} required maxLength={120} error={err("municipality")} />
      <TextField
        label={t("orders.address.ward")}
        type="number"
        inputMode="numeric"
        min={1}
        max={ref?.max_ward ?? 35}
        value={value.ward || ""}
        onChange={(e) => set({ ward: Number(e.target.value) })}
        required
        error={err("ward")}
      />
      <TextField label={t("orders.address.area")} value={value.area ?? ""} onChange={(e) => set({ area: e.target.value })} maxLength={160} />
      <TextField label={t("orders.address.landmark")} value={value.landmark ?? ""} onChange={(e) => set({ landmark: e.target.value })} maxLength={200} />
    </div>
  );
}

/** Server field errors (`details.fields[].loc[-1]` → type) for inline display. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!isApiError(error)) return {};
  const fields = (error.details as { fields?: { loc: (string | number)[]; type?: string }[] } | undefined)?.fields ?? [];
  return Object.fromEntries(fields.map((f) => [String(f.loc[f.loc.length - 1]), f.type ?? "invalid"]));
}
