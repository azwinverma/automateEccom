"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Badge } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import {
  newRow,
  type ProductForm,
  type VariantRow,
} from "@/lib/catalog/editor";
import {
  MAX_OPTIONS,
  MAX_VARIANTS,
  cleanOptions,
  combinationCount,
  syncRows,
  variantTitle,
  type OptionDraft,
} from "@/lib/catalog/variants";
import { ChipInput } from "./ChipInput";
import styles from "./products.module.css";

/** Above this many raw combinations we stop generating rows and only show the limit error. */
const GENERATE_CAP = MAX_VARIANTS * 3;

type CellField = "price" | "compareAt" | "cost" | "sku" | "barcode";

export function VariantGrid({
  mode,
  form,
  setForm,
  errorText,
  readOnly,
}: {
  mode: "create" | "edit";
  form: ProductForm;
  setForm: (updater: (f: ProductForm) => ProductForm) => void;
  errorText: (key: string) => string | undefined;
  readOnly: boolean;
}) {
  const { t, number } = useI18n();
  const [bulk, setBulk] = useState("");
  const optionNames = cleanOptions(form.options).map((o) => o.name);
  const nameOptions =
    mode === "edit" ? form.options.map((o) => o.name) : optionNames;

  const setOptions = (options: OptionDraft[]) =>
    setForm((f) => {
      if (combinationCount(options) > GENERATE_CAP) return { ...f, options };
      // New combinations inherit prices when every existing row shares the same ones
      // (e.g. the price typed on the single default variant before adding options).
      const first = f.variants[0];
      const uniform =
        first &&
        f.variants.every(
          (v) =>
            v.price === first.price &&
            v.compareAt === first.compareAt &&
            v.cost === first.cost,
        );
      const seed = uniform ? first : null;
      const make = (combo: Record<string, string>, key: string): VariantRow =>
        seed
          ? {
              ...newRow(combo, key),
              price: seed.price,
              compareAt: seed.compareAt,
              cost: seed.cost,
            }
          : newRow(combo, key);
      return {
        ...f,
        options,
        variants: syncRows(f.variants, options, f.excluded, make),
      };
    });

  const updateRow = (key: string, field: CellField, value: string) =>
    setForm((f) => ({
      ...f,
      variants: f.variants.map((v) =>
        v.key === key ? { ...v, [field]: value } : v,
      ),
    }));

  const removeRow = (row: VariantRow) =>
    setForm((f) =>
      row.id
        ? {
            ...f,
            variants: f.variants.map((v) =>
              v.key === row.key ? { ...v, remove: !v.remove } : v,
            ),
          }
        : {
            ...f,
            excluded: [...f.excluded, row.key],
            variants: f.variants.filter((v) => v.key !== row.key),
          },
    );

  const restoreExcluded = () =>
    setForm((f) => ({
      ...f,
      excluded: [],
      variants: syncRows(f.variants, f.options, [], newRow),
    }));

  const applyBulk = () => {
    if (!bulk.trim()) return;
    setForm((f) => ({
      ...f,
      variants: f.variants.map((v) =>
        v.status === "active" && !v.remove ? { ...v, price: bulk } : v,
      ),
    }));
  };

  const title = (v: VariantRow) =>
    variantTitle(v.options, nameOptions) || t("products.editor.defaultVariant");
  const cols: {
    field: CellField;
    label: string;
    mono?: boolean;
    inputMode?: "decimal" | "text";
  }[] = [
    {
      field: "price",
      label: t("products.editor.colPrice"),
      inputMode: "decimal",
    },
    {
      field: "compareAt",
      label: t("products.editor.colCompareAt"),
      inputMode: "decimal",
    },
    {
      field: "cost",
      label: t("products.editor.colCost"),
      inputMode: "decimal",
    },
    { field: "sku", label: t("products.editor.colSku"), mono: true },
    { field: "barcode", label: t("products.editor.colBarcode"), mono: true },
  ];
  const active = form.variants.filter(
    (v) => v.status === "active" && !v.remove,
  ).length;

  return (
    <>
      {mode === "create" && !readOnly ? (
        <div>
          {form.options.map((o, i) => (
            <div key={i} className={styles.optionRow}>
              <div>
                <label className={styles.fieldLabel} htmlFor={`opt-name-${i}`}>
                  {t("products.editor.optionName")}
                </label>
                <input
                  id={`opt-name-${i}`}
                  className={styles.cell}
                  value={o.name}
                  placeholder={t("products.editor.optionNamePlaceholder")}
                  onChange={(e) =>
                    setOptions(
                      form.options.map((x, j) =>
                        j === i ? { ...x, name: e.target.value } : x,
                      ),
                    )
                  }
                  aria-invalid={
                    errorText(`options.${i}.name`) ? true : undefined
                  }
                />
                {errorText(`options.${i}.name`) ? (
                  <span className={styles.cellError}>
                    {errorText(`options.${i}.name`)}
                  </span>
                ) : null}
              </div>
              <ChipInput
                label={t("products.editor.optionValues")}
                values={o.values}
                onChange={(values) =>
                  setOptions(
                    form.options.map((x, j) =>
                      j === i ? { ...x, values } : x,
                    ),
                  )
                }
                placeholder={t("products.editor.optionValuesPlaceholder")}
                error={errorText(`options.${i}.values`)}
              />
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                style={{ marginTop: 22 }}
                aria-label={t("products.editor.removeOption", {
                  name: o.name || String(i + 1),
                })}
                onClick={() =>
                  setOptions(form.options.filter((_, j) => j !== i))
                }
              >
                <Icon name="close" />
              </Button>
            </div>
          ))}
          <div className={styles.optionActions}>
            <Button
              size="sm"
              disabled={form.options.length >= MAX_OPTIONS}
              onClick={() =>
                setOptions([...form.options, { name: "", values: [] }])
              }
            >
              <Icon name="plus" />
              {t("products.editor.addOption")}
            </Button>
            <span className={styles.gridMeta}>
              {t("products.editor.variantCount", { count: number(active) })}
            </span>
            {form.excluded.length ? (
              <span className={styles.gridMeta}>
                {t("products.editor.hiddenCombos", {
                  count: number(form.excluded.length),
                })}{" "}
                <Button size="sm" variant="ghost" onClick={restoreExcluded}>
                  {t("products.editor.restore")}
                </Button>
              </span>
            ) : null}
          </div>
        </div>
      ) : mode === "edit" ? (
        <p className={styles.sectionHint}>
          {t("products.editor.optionsLocked")}
        </p>
      ) : null}

      {errorText("variants") ? (
        <p
          className={styles.cellError}
          role="alert"
          style={{ maxWidth: "none", marginBottom: "var(--space-2)" }}
        >
          {errorText("variants")}
        </p>
      ) : null}

      {!readOnly && form.variants.length > 1 ? (
        <div className={styles.optionActions}>
          <div className={styles.bulk}>
            <div>
              <label className={styles.fieldLabel} htmlFor="bulk-price">
                {t("products.editor.setAllPrices")}
              </label>
              <input
                id="bulk-price"
                className={styles.cell}
                inputMode="decimal"
                value={bulk}
                onChange={(e) => setBulk(e.target.value)}
              />
            </div>
            <Button size="sm" onClick={applyBulk} style={{ marginBottom: 2 }}>
              {t("products.editor.applyAll")}
            </Button>
          </div>
        </div>
      ) : null}

      {/* Wide grids scroll inside their own box, never the page (QA-018). Focusable so keyboard users can scroll. */}
      <div
        className={styles.gridScroll}
        role="region"
        aria-label={t("products.editor.variants")}
        tabIndex={0}
      >
        <table className={styles.grid} data-testid="variant-grid">
          <thead>
            <tr>
              <th scope="col">{t("products.editor.colVariant")}</th>
              {cols.map((c) => (
                <th scope="col" key={c.field}>
                  {c.label}
                </th>
              ))}
              <th scope="col">
                <span className="srOnly">{t("common.actions")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {form.variants.map((v) => {
              const locked = readOnly || v.status === "archived" || v.remove;
              const name = title(v);
              return (
                <tr
                  key={v.key}
                  className={v.remove ? styles.rowRemoved : undefined}
                  data-variant={name}
                >
                  <th
                    scope="row"
                    className={styles.variantName}
                    style={{ textAlign: "left" }}
                  >
                    {name}
                    {v.status === "archived" ? (
                      <span className={styles.rowNote}>
                        <Badge>{t("products.editor.archivedVariant")}</Badge>
                      </span>
                    ) : null}
                    {v.remove ? (
                      <span className={styles.rowNote}>
                        {t("products.editor.willArchive")}
                      </span>
                    ) : null}
                  </th>
                  {cols.map((c) => {
                    const errKey = `variants.${v.key}.${c.field}`;
                    const err = errorText(errKey);
                    const id = `cell-${v.key}-${c.field}`;
                    return (
                      <td key={c.field} data-label={c.label}>
                        <div>
                          <input
                            id={id}
                            className={[styles.cell, c.mono && styles.cellMono]
                              .filter(Boolean)
                              .join(" ")}
                            value={v[c.field]}
                            onChange={(e) =>
                              updateRow(v.key, c.field, e.target.value)
                            }
                            inputMode={c.inputMode}
                            placeholder={
                              c.field === "sku" && !v.id
                                ? t("products.editor.skuAuto")
                                : undefined
                            }
                            aria-label={`${c.label} · ${name}`}
                            aria-invalid={err ? true : undefined}
                            aria-describedby={err ? `${id}-err` : undefined}
                            disabled={locked}
                            spellCheck={false}
                            autoComplete="off"
                          />
                          {err ? (
                            <span id={`${id}-err`} className={styles.cellError}>
                              {err}
                            </span>
                          ) : null}
                        </div>
                      </td>
                    );
                  })}
                  <td className={styles.rowAction}>
                    {!readOnly &&
                    v.status === "active" &&
                    (mode === "create" ? form.variants.length > 1 : true) ? (
                      v.remove ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeRow(v)}
                        >
                          {t("products.editor.undoRemove")}
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          iconOnly
                          aria-label={t("products.editor.removeVariant", {
                            name,
                          })}
                          onClick={() => removeRow(v)}
                        >
                          <Icon name="close" />
                        </Button>
                      )
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
