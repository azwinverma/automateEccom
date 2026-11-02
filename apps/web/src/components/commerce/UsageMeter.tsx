"use client";

import type { UsageLimit } from "@commerce-os/api-client";
import { useI18n } from "@/i18n/I18nProvider";
import { resourceLabel, resourceUnit } from "@/i18n/labels";
import { CREDITS_HREF, PLANS_HREF, atLimitActions, isGauge, meterState, usageRatio, type MeterState } from "@/lib/usage";
import { ButtonLink } from "../ui/Button";
import styles from "./commerce.module.css";

export const STATE_CLASS: Record<MeterState, string | undefined> = {
  not_included: styles.stateNeutral,
  uncounted: styles.stateNeutral,
  unlimited: styles.stateUnlimited,
  ok: undefined,
  "70": styles.state70,
  "85": styles.state85,
  "100": styles.state100,
};

export interface UsageMeterProps {
  usage: UsageLimit;
  /** Defaults to the localized label for `usage.resource`. */
  label?: string;
  periodEnd?: string | null;
}

/**
 * One limit row. Rules:
 * - not included → calm "Not in your plan" + "See plans", never red.
 * - gauge with `used: null` → "Up to N", no bar, no percentage.
 * - gauges / lifetime limits never show "Renews".
 * - at limit, actions follow `overage_policy` (credits → Buy credits; overage → neutral note; block → Upgrade).
 */
export function UsageMeter({ usage, label: labelProp, periodEnd }: UsageMeterProps) {
  const { t, number, percent } = useI18n();
  const label = labelProp ?? resourceLabel(t, usage.resource);
  const unit = resourceUnit(t, usage.resource);
  const gauge = isGauge(usage);
  const state = meterState(usage);
  const actions = atLimitActions(usage);
  const used = usage.used ?? 0;
  const { limit, reserved } = usage;

  const periodText = gauge
    ? t("usage.current")
    : usage.period === "month"
      ? t("usage.perMonth")
      : usage.period === "day"
        ? t("usage.perDay")
        : t("usage.perPeriod", { period: usage.period });

  const rootClass = [styles.meter, STATE_CLASS[state], actions.overageNote && styles.stateOverage].filter(Boolean).join(" ");
  const head = (
    <div className={styles.meterLabel}>
      <strong>{label}</strong>
      {state === "not_included" ? null : <span>{periodText}</span>}
    </div>
  );

  if (state === "not_included") {
    return (
      <div className={rootClass} data-testid="usage-meter" data-state={state} data-resource={usage.resource}>
        {head}
        <span className={styles.meterNumbers}>{t("usage.notIncluded")}</span>
        <span className={styles.meterState}>
          <ButtonLink href={PLANS_HREF} size="sm" variant="ghost">
            {t("usage.seePlans")}
          </ButtonLink>
        </span>
      </div>
    );
  }

  if (state === "uncounted" || (state === "unlimited" && usage.used === null)) {
    return (
      <div className={rootClass} data-testid="usage-meter" data-state={state} data-resource={usage.resource}>
        {head}
        <span className={styles.meterNumbers}>
          {limit === null ? t("common.unlimited") : t("usage.upTo", { limit: number(limit), unit })}
        </span>
        <span />
      </div>
    );
  }

  const numbers =
    limit === null
      ? gauge
        ? t("usage.inUseNoLimit", { used: number(used), unit })
        : t("usage.usedNoLimit", { used: number(used) })
      : gauge
        ? t("usage.inUse", { used: number(used), limit: number(limit), unit })
        : t("usage.usedOf", { used: number(used), limit: number(limit) });

  const pctText = percent(Math.min(usageRatio(used, reserved, limit) ?? 0, 1));
  const stateText =
    state === "unlimited"
      ? t("common.unlimited")
      : state === "100"
        ? actions.overageNote
          ? t("usage.overageState")
          : t("usage.state100")
        : state === "85"
          ? t("usage.state85")
          : gauge
            ? "" // gauges read as counts ("1 of 2 seats in use"), not consumption percentages
            : t("usage.stateOk", { percent: pctText });

  const usedPct = limit ? Math.min(100, (used / limit) * 100) : 0;
  const reservedPct = limit ? Math.min(100 - usedPct, (reserved / limit) * 100) : 0;

  return (
    <div className={rootClass} data-testid="usage-meter" data-state={state} data-resource={usage.resource}>
      {head}
      <div className={styles.meterBarCol}>
        <div
          className={styles.track}
          role="meter"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={limit ?? used}
          aria-valuenow={used}
          aria-valuetext={`${numbers}. ${stateText}`}
        >
          <span className={styles.fill} style={{ width: `${limit === null ? 100 : usedPct}%` }} />
          {reservedPct > 0 ? <span className={styles.reservedFill} style={{ left: `${usedPct}%`, width: `${reservedPct}%` }} /> : null}
        </div>
        <span className={styles.meterNumbers}>
          {numbers}
          {reserved > 0 ? ` · ${t("usage.reserved", { count: number(reserved) })}` : ""}
        </span>
      </div>
      <span className={styles.meterState}>{stateText}</span>
      {state === "100" ? (
        <div className={styles.meterLimit}>
          {actions.overageNote ? <p className={styles.limitWait}>{t("usage.overageNote")}</p> : null}
          <LimitActions
            buyCredits={actions.buyCredits}
            upgrade={actions.upgrade}
            renewsOn={!gauge && actions.buyCredits ? (periodEnd ?? null) : null}
          />
        </div>
      ) : null}
    </div>
  );
}

/** At-limit choices. Callers decide which apply (policy or server `details.options`). */
export function LimitActions({ buyCredits, upgrade, renewsOn }: { buyCredits: boolean; upgrade: boolean; renewsOn?: string | null }) {
  const { t, date } = useI18n();
  if (!buyCredits && !upgrade && !renewsOn) return null;
  return (
    <div className={styles.limitActions} data-testid="limit-actions">
      {buyCredits ? (
        <ButtonLink href={CREDITS_HREF} size="sm" variant="primary">
          {t("usage.buyCredits")}
        </ButtonLink>
      ) : null}
      {upgrade ? (
        <ButtonLink href={PLANS_HREF} size="sm" variant={buyCredits ? "secondary" : "primary"}>
          {t("usage.upgrade")}
        </ButtonLink>
      ) : null}
      {renewsOn ? <span className={styles.limitWait}>{t("usage.renewsOn", { date: date(renewsOn) })}</span> : null}
    </div>
  );
}
