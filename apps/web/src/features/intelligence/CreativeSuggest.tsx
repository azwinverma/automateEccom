"use client";

import type { CreativeSuggestions } from "@commerce-os/api-client";
import { Button } from "@/components/ui/Button";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { hourLabel, valueLabel } from "./creativeLabels";
import styles from "./intelligence.module.css";

/** Suggestions are optional help: no plan, no data or an error simply shows nothing. */
export function useCreativeSuggestions(enabled = true): CreativeSuggestions | null {
  const on = useAuth().feature("intelligence.creative_genome") === "yes" && enabled;
  const q = useApiQuery((a) => (on ? a.intelligence.creativeSuggestions().catch(() => null) : Promise.resolve(null)), [on]);
  return q.state.status === "success" ? q.state.data : null;
}

/**
 * CGN-004 posting time. `onUse(hour, genomeVersion)` schedules at that hour; the genome version is only
 * passed for a learned window (source "genome"), never for the order-time fallback.
 */
export function SuggestedTime({ suggestions, onUse, pending }: { suggestions: CreativeSuggestions | null; onUse: (hour: number, genomeVersion: number | null) => void; pending?: boolean }) {
  const { t, locale } = useI18n();
  const s = suggestions?.schedule;
  if (!s?.hours) return null;
  const [from, to] = s.hours;
  const fromGenome = s.source === "genome";
  return (
    <div className={styles.suggest} data-testid="suggested-time" data-source={s.source}>
      <span>
        <strong>{t("intel.creative.suggestTime", { from: hourLabel(locale, from), to: hourLabel(locale, to) })}</strong>
        <span className={styles.muted}> · {t(fromGenome ? "intel.creative.suggestGenome" : "intel.creative.suggestOrders")}</span>
      </span>
      <Button size="sm" variant="secondary" loading={pending} onClick={() => onUse(from, fromGenome ? (suggestions?.genome_version ?? null) : null)}>
        {t("intel.creative.useTime")}
      </Button>
    </div>
  );
}

/** CGN-004 Auto Reel settings ("8–11 second videos, price shown"). */
export function ReelBestSettings({ suggestions, applied, onApply }: { suggestions: CreativeSuggestions | null; applied: boolean; onApply: () => void }) {
  const { t, number } = useI18n();
  const r = suggestions?.reel;
  if (!suggestions?.genome_version || !r || (!r.target_seconds && r.show_price === undefined)) return null;
  const parts = [
    r.target_seconds ? t("intel.creative.reelSeconds", { from: number(r.target_seconds[0]), to: number(r.target_seconds[1]) }) : null,
    r.show_price ? t("intel.creative.reelPrice") : null,
    r.hook_type ? valueLabel(t, "hook_type", r.hook_type) : null,
  ].filter(Boolean);
  return (
    <div className={styles.suggest} data-testid="reel-best">
      <span>{applied ? t("intel.creative.bestApplied") : t("intel.creative.reelBest", { parts: parts.join(", ") })}</span>
      {applied ? null : (
        <Button size="sm" variant="secondary" onClick={onApply}>
          {t("intel.creative.useBest")}
        </Button>
      )}
    </div>
  );
}
