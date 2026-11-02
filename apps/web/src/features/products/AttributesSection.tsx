"use client";

import { isApiError, type ProductAttribute, type ProductDetail } from "@commerce-os/api-client";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./products.module.css";

/** Confidence may arrive as 0–1 or 0–100. */
function ratio(c: number): number {
  return c > 1 ? c / 100 : c;
}

function AttributeRow({
  attr,
  canWrite,
  busy,
  onConfirm,
  onSave,
}: {
  attr: ProductAttribute;
  canWrite: boolean;
  busy: boolean;
  onConfirm: (key: string) => void;
  onSave: (attr: ProductAttribute, value: string) => Promise<boolean>;
}) {
  const { t, percent } = useI18n();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(attr.value);
  const suggested = attr.source === "ai" && !attr.confirmed;

  return (
    <li className={[styles.attr, suggested && styles.attrSuggested].filter(Boolean).join(" ")} data-suggested={suggested || undefined}>
      <span className={styles.attrKey}>
        {attr.key}
        <span className={styles.localeTag}>{attr.locale}</span>
      </span>
      <div className={styles.attrValue}>
        {editing ? (
          <form
            className={styles.attrEdit}
            onSubmit={async (e) => {
              e.preventDefault();
              if (value.trim() && (await onSave(attr, value.trim()))) setEditing(false);
            }}
          >
            <input
              className={styles.cell}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              aria-label={`${t("products.editor.attrValue")} · ${attr.key}`}
              autoFocus
              lang={attr.locale}
            />
            <Button size="sm" type="submit" variant="primary" loading={busy}>
              {t("common.save")}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setEditing(false);
                setValue(attr.value);
              }}
            >
              {t("common.cancel")}
            </Button>
          </form>
        ) : (
          <span lang={attr.locale}>{attr.value}</span>
        )}
        {suggested ? (
          <span className={styles.aiTag}>
            {attr.confidence !== null
              ? t("products.editor.aiSuggested", { percent: percent(ratio(attr.confidence)) })
              : t("products.editor.aiSuggestedNoScore")}
          </span>
        ) : (
          <span className={styles.provenance}>{t(`products.editor.source.${attr.source}`)}</span>
        )}
      </div>
      <div className={styles.attrActions}>
        {canWrite && suggested && !editing ? (
          <Button size="sm" onClick={() => onConfirm(attr.key)} disabled={busy}>
            {t("products.editor.confirm")}
          </Button>
        ) : null}
        {canWrite && !editing ? (
          <Button size="sm" variant="ghost" onClick={() => setEditing(true)} aria-label={`${t("products.editor.edit")} · ${attr.key}`}>
            {t("products.editor.edit")}
          </Button>
        ) : null}
      </div>
    </li>
  );
}

/**
 * Attribute review. Saves immediately (independent of the main Save) because confirming
 * AI suggestions is a review step, not a form edit. Updates only `attributes` locally.
 */
export function AttributesSection({
  product,
  onAttributes,
  canWrite,
}: {
  product: ProductDetail;
  onAttributes: (next: Pick<ProductDetail, "attributes" | "needs_review">) => void;
  canWrite: boolean;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [locale, setLocale] = useState<"en" | "ne">("en");
  const [addErrors, setAddErrors] = useState<{ key?: string; value?: string }>({});
  const suggestedKeys = product.attributes.filter((a) => a.source === "ai" && !a.confirmed).map((a) => a.key);

  const adopt = (d: ProductDetail) => onAttributes({ attributes: d.attributes, needs_review: d.needs_review });

  const confirm = async (keys: string[]) => {
    const d = await action.run(() => api.catalog.confirmAttributes(product.id, keys));
    if (d) {
      adopt(d);
      toast(t("products.editor.attrConfirmed"));
    }
  };

  const save = async (attr: Pick<ProductAttribute, "key" | "locale">, next: string) => {
    const d = await action.run(() => api.catalog.setAttributes(product.id, [{ key: attr.key, value: next, locale: attr.locale }]));
    if (d) {
      adopt(d);
      toast(t("products.editor.attrSaved"));
      return true;
    }
    return false;
  };

  const add = async (e: FormEvent) => {
    e.preventDefault();
    const errs: typeof addErrors = {};
    if (!key.trim()) errs.key = t("errors.field.required");
    if (!value.trim()) errs.value = t("errors.field.required");
    setAddErrors(errs);
    if (Object.keys(errs).length) return;
    if (await save({ key: key.trim(), locale }, value.trim())) {
      setKey("");
      setValue("");
    }
  };

  return (
    <>
      {action.error ? (
        <InlineAlert tone="danger">
          {errorMessage(t, action.error)}
          <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
        </InlineAlert>
      ) : null}
      {suggestedKeys.length > 1 && canWrite ? (
        <div style={{ paddingBottom: "var(--space-3)" }}>
          <Button size="sm" onClick={() => confirm(suggestedKeys)} loading={action.pending}>
            {t("products.editor.confirmAll")}
          </Button>
        </div>
      ) : null}
      {product.attributes.length === 0 ? (
        <p className={styles.sectionHint}>{t("products.editor.attributesEmpty")}</p>
      ) : (
        <ul className={styles.attrList} data-testid="attributes">
          {product.attributes.map((a) => (
            <AttributeRow
              key={`${a.key}-${a.locale}-${a.value}`}
              attr={a}
              canWrite={canWrite}
              busy={action.pending}
              onConfirm={(k) => confirm([k])}
              onSave={save}
            />
          ))}
        </ul>
      )}
      {canWrite ? (
        <form className={styles.attrAdd} onSubmit={add} noValidate>
          <TextField
            label={t("products.editor.attrKey")}
            placeholder={t("products.editor.attrKeyPlaceholder")}
            value={key}
            onChange={(e) => setKey(e.target.value)}
            error={addErrors.key}
            mono
          />
          <TextField label={t("products.editor.attrValue")} value={value} onChange={(e) => setValue(e.target.value)} error={addErrors.value} lang={locale} />
          <SelectField label={t("products.editor.attrLocale")} value={locale} onChange={(e) => setLocale(e.target.value as "en" | "ne")}>
            <option value="en">{t("language.en")}</option>
            <option value="ne">{t("language.ne")}</option>
          </SelectField>
          <Button type="submit" loading={action.pending} style={{ marginBottom: 1 }}>
            {t("products.editor.addAttr")}
          </Button>
        </form>
      ) : null}
    </>
  );
}
