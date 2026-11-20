"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import styles from "./intelligence.module.css";
import { MemoryFacts } from "./MemoryFacts";
import { ProfitView } from "./ProfitView";
import { Freshness, WhatIf } from "../twin/WhatIf";
import { ReturnInsights } from "./ReturnInsights";

const TABS = ["profit", "learned", "returns", "whatif"] as const;
type Tab = (typeof TABS)[number];

/** Analytics: true profit (ANA-008), Commerce Memory (UX-021), Return Intelligence (UX-020), What if (SIM) + Twin freshness. */
export function AnalyticsView() {
  const { t } = useI18n();
  const [tab, setTab] = useState<Tab>("profit");
  const label = (x: Tab) =>
    t(x === "profit" ? "intel.analytics.tabProfit" : x === "learned" ? "intel.analytics.tabLearned" : x === "returns" ? "intel.analytics.tabReturns" : "intel.analytics.tabWhatIf");
  return (
    <>
      <PageHeader title={t("intel.analytics.title")} subtitle={t("intel.analytics.subtitle")} />
      <div role="tablist" aria-label={t("intel.analytics.tabsLabel")} className={styles.tabs}>
        {TABS.map((x) => (
          <button key={x} type="button" role="tab" id={`tab-${x}`} aria-controls={`panel-${x}`} aria-selected={tab === x} className={styles.tab} onClick={() => setTab(x)}>
            {label(x)}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "profit" ? (
          <ProfitView />
        ) : tab === "learned" ? (
          <MemoryFacts />
        ) : tab === "returns" ? (
          <ReturnInsights />
        ) : (
          <>
            <WhatIf />
            <Freshness />
          </>
        )}
      </div>
    </>
  );
}
