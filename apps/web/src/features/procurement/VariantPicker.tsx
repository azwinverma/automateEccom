"use client";

import type { ProductDetail, ProductSummary } from "@commerce-os/api-client";
import { useEffect, useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./procurement.module.css";

export interface PickedVariant {
  variant_id: string;
  product_id: string;
  title: string;
  variant: string | null;
  sku: string | null;
  price_minor: number | null;
  cost_minor: number | null;
}

/** Search the catalog by name/SKU, then pick the exact variant (single-variant products pick directly). */
export function VariantPicker({ onPick, exclude = [] }: { onPick: (v: PickedVariant) => void; exclude?: string[] }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const listId = useId();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<ProductSummary[] | null>(null);
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setResults(null);
      return;
    }
    let cancelled = false;
    const h = setTimeout(() => {
      api.catalog.products({ q: term, limit: 8 }).then(
        (r) => !cancelled && setResults(r.items.filter((p) => p.status !== "archived")),
        () => !cancelled && setResults([]),
      );
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(h);
    };
  }, [api, q]);

  const pickVariant = (p: ProductDetail, v: ProductDetail["variants"][number]) => {
    onPick({
      variant_id: v.id,
      product_id: p.id,
      title: p.title,
      variant: v.title === "Default" ? null : v.title,
      sku: v.sku || null,
      price_minor: v.price?.amount_minor ?? null,
      cost_minor: v.cost?.amount_minor ?? null,
    });
    setProduct(null);
    setResults(null);
    setQ("");
  };

  const openProduct = async (id: string) => {
    setBusy(true);
    try {
      const p = await api.catalog.product(id);
      const variants = p.variants.filter((v) => v.status === "active" && !exclude.includes(v.id));
      if (variants.length === 1) pickVariant(p, variants[0]!);
      else setProduct({ ...p, variants });
    } finally {
      setBusy(false);
    }
  };

  if (product) {
    return (
      <div className={styles.picker}>
        <span className={styles.muted} id={`${listId}-v`}>
          {t("procurement.pickerVariants", { title: product.title })}
        </span>
        <ul className={styles.results} aria-labelledby={`${listId}-v`}>
          {product.variants.map((v) => (
            <li key={v.id}>
              <button type="button" className={styles.result} onClick={() => pickVariant(product, v)}>
                <span>{v.title}</span>
                <span className={styles.muted}>{v.sku}</span>
              </button>
            </li>
          ))}
        </ul>
        <Button size="sm" variant="ghost" onClick={() => setProduct(null)}>
          {t("procurement.pickerBack")}
        </Button>
      </div>
    );
  }
  return (
    <div className={styles.picker}>
      <TextField
        label={t("procurement.pickerLabel")}
        placeholder={t("procurement.pickerPlaceholder")}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-controls={results && results.length > 0 ? listId : undefined}
        autoComplete="off"
      />
      {results === null ? null : results.length === 0 ? (
        <span className={styles.muted} role="status">
          {t("procurement.pickerNone")}
        </span>
      ) : (
        <ul className={styles.results} id={listId} aria-busy={busy || undefined}>
          {results.map((p) => (
            <li key={p.id}>
              <button type="button" className={styles.result} onClick={() => openProduct(p.id)} disabled={busy}>
                <span>{p.title}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
