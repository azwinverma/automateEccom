"use client";

import { useI18n } from "@/i18n/I18nProvider";
import styles from "./commerce.module.css";

export type AutopilotMode = "assisted" | "smart" | "autopilot";
const MODES: AutopilotMode[] = ["assisted", "smart", "autopilot"];

export interface AutopilotStatusStripProps {
  mode: AutopilotMode;
  /** null = not measured yet (renders an honest empty note, not a fake zero trend). */
  automatedCount: number | null;
  needsAttentionCount: number | null;
  /** Phase in which Smart/Autopilot become available; omit once they are. */
  lockedUntilPhase?: number;
}

export function AutopilotStatusStrip({ mode, automatedCount, needsAttentionCount, lockedUntilPhase }: AutopilotStatusStripProps) {
  const { t, number } = useI18n();
  const nothingYet = (automatedCount ?? 0) === 0 && (needsAttentionCount ?? 0) === 0;
  const modeLabel = t(`autopilot.${mode}`);

  return (
    <section className={styles.strip} aria-label={t("autopilot.label")} data-testid="autopilot-strip">
      <div className={styles.stripCell}>
        <span className={styles.stripLabel}>{t("autopilot.mode")}</span>
        <div className={styles.modeTrack} role="img" aria-label={t("autopilot.currentMode", { mode: modeLabel })}>
          {MODES.map((m) => (
            <span
              key={m}
              className={[styles.modeStep, m === mode && styles.modeStepActive].filter(Boolean).join(" ")}
              aria-hidden="true"
            >
              {t(`autopilot.${m}`)}
            </span>
          ))}
        </div>
      </div>

      <div className={styles.stripCell}>
        <span className={styles.stripLabel}>{t("autopilot.automated")}</span>
        <span className={styles.count}>
          <span className={[styles.countDot, automatedCount ? styles.dotAutomated : styles.dotIdle].join(" ")} aria-hidden="true" />
          <span className={styles.countValue} data-testid="automated-count">
            {automatedCount === null ? t("common.none") : number(automatedCount)}
          </span>
        </span>
      </div>

      <div className={styles.stripCell}>
        <span className={styles.stripLabel}>{t("autopilot.needsAttention")}</span>
        <span className={styles.count}>
          <span className={[styles.countDot, needsAttentionCount ? styles.dotAttention : styles.dotIdle].join(" ")} aria-hidden="true" />
          <span className={styles.countValue} data-testid="attention-count">
            {needsAttentionCount === null ? t("common.none") : number(needsAttentionCount)}
          </span>
        </span>
      </div>

      <div className={styles.stripCell}>
        <p className={styles.stripNote}>{nothingYet ? t("autopilot.emptyCounts") : t(`autopilot.${mode}Help`)}</p>
        {lockedUntilPhase ? <p className={styles.stripNote}>{t("autopilot.modeLocked", { phase: lockedUntilPhase })}</p> : null}
      </div>
    </section>
  );
}
