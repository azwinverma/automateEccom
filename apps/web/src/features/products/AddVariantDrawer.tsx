"use client";

import { isApiError, type ProductDetail } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { SKU_RE, barcodeProblem, normalizeSku } from "@/lib/catalog/codes";
import { parseRupees } from "@/lib/money";

/** Add one variant to a saved product (POST …/variants with the product version). */
export function AddVariantDrawer({
  open,
  onOpenChange,
  product,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  product: ProductDetail;
  onAdded: (d: ProductDetail) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const [values, setValues] = useState<Record<string, string>>({});
  const [price, setPrice] = useState("");
  const [sku, setSku] = useState("");
  const [barcode, setBarcode] = useState("");
  const [errs, setErrs] = useState<Record<string, string>>({});
  const action = useAction();

  useEffect(() => {
    if (open) {
      setValues({});
      setPrice("");
      setSku("");
      setBarcode("");
      setErrs({});
      action.clear();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const err = (kind: string) => t.dynamic(`products.editor.err.${kind}`) ?? t("errors.field.invalid");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    for (const o of product.options) if (!values[o.name]?.trim()) next[`opt.${o.name}`] = err("required");
    const p = parseRupees(price);
    if (!p.ok) next.price = err(p.error);
    else if (p.minor === null) next.price = err("required");
    if (sku.trim() && !SKU_RE.test(normalizeSku(sku))) next.sku = err("invalid_sku");
    const bp = barcodeProblem(barcode);
    if (bp) next.barcode = err(bp === "checksum" ? "barcode_checksum" : "barcode_format");
    setErrs(next);
    if (Object.keys(next).length || !p.ok || p.minor === null) return;
    const options = Object.fromEntries(product.options.map((o) => [o.name, values[o.name]!.trim()]));
    const d = await action.run(() =>
      api.catalog.addVariant(product.id, product.version, {
        options,
        price_minor: p.minor!,
        ...(sku.trim() ? { sku: normalizeSku(sku) } : {}),
        ...(barcode.trim() ? { barcode: barcode.trim() } : {}),
      }),
    );
    if (d) onAdded(d);
  };

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("products.editor.addVariantTitle")}
      description={product.options.length ? t("products.editor.addVariantBody") : t("products.editor.noOptionsToAdd")}
      footer={
        <>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" form="add-variant-form" loading={action.pending} disabled={!product.options.length}>
            {t("products.editor.addVariantSave")}
          </Button>
        </>
      }
    >
      <form id="add-variant-form" onSubmit={submit} noValidate style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {action.error ? (
          <InlineAlert tone="danger">
            {errorMessage(t, action.error)}
            <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
          </InlineAlert>
        ) : null}
        {product.options.map((o) => (
          <div key={o.id}>
            <TextField
              label={o.name}
              value={values[o.name] ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [o.name]: e.target.value }))}
              list={`opt-values-${o.id}`}
              error={errs[`opt.${o.name}`]}
              autoComplete="off"
            />
            <datalist id={`opt-values-${o.id}`}>
              {o.values.map((v) => (
                <option key={v} value={v} />
              ))}
            </datalist>
          </div>
        ))}
        <TextField label={t("products.editor.colPrice")} value={price} onChange={(e) => setPrice(e.target.value)} inputMode="decimal" error={errs.price} />
        <TextField label={t("products.editor.colSku")} value={sku} onChange={(e) => setSku(e.target.value)} placeholder={t("products.editor.skuAuto")} error={errs.sku} mono />
        <TextField label={t("products.editor.colBarcode")} value={barcode} onChange={(e) => setBarcode(e.target.value)} error={errs.barcode} mono />
      </form>
    </Drawer>
  );
}
