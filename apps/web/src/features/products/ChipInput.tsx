"use client";

import { useId, useState, type KeyboardEvent } from "react";
import { Icon } from "@/components/ui/Icon";
import { useI18n } from "@/i18n/I18nProvider";
import styles from "./products.module.css";

/** Free-text chips (tags, option values). Enter or comma adds; Backspace on empty removes the last. */
export function ChipInput({
  label,
  values,
  onChange,
  placeholder,
  error,
  max,
  hideLabel,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  error?: string | null;
  max?: number;
  hideLabel?: boolean;
}) {
  const { t } = useI18n();
  const id = useId();
  const [draft, setDraft] = useState("");

  const add = (raw: string) => {
    const parts = raw
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    if (!parts.length) return;
    const next = [...values];
    for (const p of parts) {
      if (!next.some((v) => v.toLowerCase() === p.toLowerCase()) && (!max || next.length < max)) next.push(p);
    }
    onChange(next);
    setDraft("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(draft);
    } else if (e.key === "Backspace" && !draft && values.length) {
      onChange(values.slice(0, -1));
    }
  };

  return (
    <div>
      <label htmlFor={id} className={hideLabel ? "srOnly" : styles.fieldLabel}>
        {label}
      </label>
      <div className={styles.chipField} data-invalid={error ? "true" : undefined}>
        {values.map((v) => (
          <span key={v} className={styles.chip}>
            {v}
            <button type="button" aria-label={t("products.editor.removeValue", { value: v })} onClick={() => onChange(values.filter((x) => x !== v))}>
              <Icon name="close" size={12} />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => add(draft)}
          placeholder={values.length ? undefined : placeholder}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-err` : undefined}
        />
      </div>
      {error ? (
        <p id={`${id}-err`} className={styles.cellError} style={{ maxWidth: "none" }}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
