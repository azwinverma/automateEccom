"use client";

import type { UsageLimit } from "@commerce-os/api-client";
import { useI18n } from "@/i18n/I18nProvider";
import { atLimitActions, meterState } from "@/lib/usage";
import { LimitActions, STATE_CLASS } from "./UsageMeter";
import styles from "./commerce.module.css";

const MAX_CELLS = 60;

function Cells({ used, reserved, limit, small }: { used: number; reserved: number; limit: number; small?: boolean }) {
  return (
    <div className={[styles.cells, small && styles.cellsSmall].filter(Boolean).join(" ")} aria-hidden="true">
      {Array.from({ length: limit }, (_, i) => (
        <span
          key={i}
          className={[styles.cell, i < used ? styles.cellUsed : i < used + reserved ? styles.cellReserved : null].filter(Boolean).join(" ")}
        />
      ))}
    </div>
  );
}

function Bar({ used, reserved, limit }: { used: number; reserved: number; limit: number }) {
  const u = Math.min(100, (used / limit) * 100);
  const r = Math.min(100 - u, (reserved / limit) * 100);
  return (
    <div className={[styles.track, styles.videoTrack].join(" ")} aria-hidden="true">
      <span className={styles.fill} style={{ width: `${u}%`, background: "var(--cell-fill)" }} />
      {r > 0 ? <span className={styles.reservedFill} style={{ left: `${u}%`, width: `${r}%` }} /> : null}
    </div>
  );
}

export interface VideoCreditMeterProps {
  /** Must be an included limit; the Plan page renders a "higher plans" note otherwise. */
  usage: UsageLimit;
  credits: number | null;
  periodEnd: string | null;
}

/**
 * Signature component: premium video quota as discrete clip cells (monthly) with the
 * daily burst cap shown separately, plus the credit balance that can extend it.
 */
export function VideoCreditMeter({ usage, credits, periodEnd }: VideoCreditMeterProps) {
  const { t, number } = useI18n();
  const state = meterState(usage);
  const actions = atLimitActions(usage);
  const { reserved, limit } = usage;
  const used = usage.used ?? 0;
  const burst = usage.burst ?? null;
  const burstHit = burst?.limit != null && burst.used >= burst.limit;
  const monthlyText =
    limit === null
      ? t("video.clipsUsedNoLimit", { used: number(used) })
      : t("video.clipsUsed", { used: number(used), limit: number(limit) });

  return (
    <section
      className={[styles.video, STATE_CLASS[state], actions.overageNote && styles.stateOverage].filter(Boolean).join(" ")}
      aria-label={t("video.title")}
      data-testid="video-credit-meter"
      data-state={state}
      data-policy={usage.overage_policy ?? "block"}
    >
      <div className={styles.videoMain}>
        <div className={styles.videoRowHead}>
          <span className={styles.videoKicker}>{t("video.monthly")}</span>
          {state === "100" ? (
            actions.overageNote ? (
              <span className={styles.videoNote}>{t("usage.overageState")}</span>
            ) : (
              <span className={styles.videoNoteStrong}>{t("usage.state100")}</span>
            )
          ) : null}
          {state === "85" ? <span className={styles.videoNote}>{t("usage.state85")}</span> : null}
        </div>
        <span className={styles.videoBig}>{monthlyText}</span>
        <div
          role="meter"
          aria-label={t("video.meterLabel")}
          aria-valuemin={0}
          aria-valuemax={limit ?? used}
          aria-valuenow={used}
          aria-valuetext={monthlyText}
        >
          {limit !== null && limit > 0 && limit <= MAX_CELLS ? (
            <Cells used={used} reserved={reserved} limit={limit} />
          ) : limit !== null && limit > 0 ? (
            <Bar used={used} reserved={reserved} limit={limit} />
          ) : null}
        </div>
        {reserved > 0 ? <span className={styles.videoNote}>{t("usage.reserved", { count: number(reserved) })}</span> : null}
        {state === "100" ? (
          <>
            <p className={styles.videoNote}>
              {actions.overageNote ? t("usage.overageNote") : actions.buyCredits ? t("video.atLimitCredits") : t("video.atLimitBlock")}
            </p>
            <LimitActions buyCredits={actions.buyCredits} upgrade={actions.upgrade} renewsOn={actions.buyCredits ? periodEnd : null} />
          </>
        ) : null}
      </div>

      <div className={styles.videoSide}>
        <div className={styles.videoRowHead}>
          <span className={styles.videoKicker}>{t("video.today")}</span>
        </div>
        {burst ? (
          <>
            <span className={styles.videoNote} data-testid="video-burst">
              {burst.limit === null
                ? t("video.todayNoLimit", { used: number(burst.used) })
                : t("video.todayUsed", { used: number(burst.used), limit: number(burst.limit) })}
            </span>
            {burst.limit !== null && burst.limit > 0 && burst.limit <= MAX_CELLS ? (
              <Cells used={burst.used} reserved={0} limit={burst.limit} small />
            ) : null}
            {burstHit ? <span className={styles.videoNoteStrong}>{t("video.dailyCapHit")}</span> : null}
          </>
        ) : (
          <span className={styles.videoNote}>{t("common.none")}</span>
        )}
        {credits !== null ? (
          <span className={styles.videoCredits}>{t("video.credits", { count: number(credits) })}</span>
        ) : null}
      </div>
    </section>
  );
}
