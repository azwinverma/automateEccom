"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { Icon } from "./Icon";
import styles from "./misc.module.css";

export function Skeleton({ width, height = 12, style }: { width?: number | string; height?: number | string; style?: CSSProperties }) {
  return <span className={styles.skeleton} style={{ width: width ?? "100%", height, ...style }} aria-hidden="true" />;
}

export type Tone = "neutral" | "success" | "warning" | "danger" | "info" | "automated";

export function Badge({ tone = "neutral", children, dot = true }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={[styles.badge, tone !== "neutral" && styles[tone]].filter(Boolean).join(" ")}>
      {dot ? <span className={styles.dot} aria-hidden="true" /> : null}
      {children}
    </span>
  );
}

export function RequestId({ id }: { id: string | null | undefined }) {
  const { t } = useI18n();
  if (!id) return null;
  return <span className={styles.requestId}>{t("common.requestId", { id })}</span>;
}

/** Inline alert. `live` announces it to screen readers (use for async errors). */
export function InlineAlert({
  tone = "danger",
  title,
  children,
  live = true,
  action,
}: {
  tone?: "danger" | "warning" | "info" | "success";
  title?: ReactNode;
  children?: ReactNode;
  live?: boolean;
  action?: ReactNode;
}) {
  return (
    <div
      className={[styles.alert, styles[tone]].join(" ")}
      role={live ? (tone === "danger" ? "alert" : "status") : undefined}
    >
      <Icon name={tone === "success" ? "check" : "alert"} />
      <div className={styles.alertBody}>
        {title ? <span className={styles.alertTitle}>{title}</span> : null}
        {children}
      </div>
      {action}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
  level = 1,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  level?: 1 | 2;
}) {
  const Heading = level === 1 ? "h1" : "h2";
  return (
    <header className={styles.pageHeader}>
      <div className={styles.pageHeaderText}>
        <Heading className={level === 2 ? styles.viewTitle : undefined}>{title}</Heading>
        {subtitle ? <p className={styles.pageSubtitle}>{subtitle}</p> : null}
      </div>
      {actions ? <div className={styles.pageActions}>{actions}</div> : null}
    </header>
  );
}

export function SectionHeader({ title, meta, id, action }: { title: ReactNode; meta?: ReactNode; id?: string; action?: ReactNode }) {
  return (
    <div className={styles.sectionHeader}>
      <h2 id={id}>{title}</h2>
      {meta ? <span className={styles.sectionMeta}>{meta}</span> : null}
      {action}
    </div>
  );
}

/* ---------- Toasts (polite live region) ---------- */

const ToastContext = createContext<(message: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<{ id: number; message: string }[]>([]);
  const seq = useRef(0);
  const show = useCallback((message: string) => {
    const id = ++seq.current;
    setItems((prev) => [...prev.slice(-2), { id, message }]);
    setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), 4000);
  }, []);
  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={styles.toastRegion} role="status" aria-live="polite">
        {items.map((i) => (
          <div key={i.id} className={styles.toast}>
            <Icon name="check" />
            {i.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
