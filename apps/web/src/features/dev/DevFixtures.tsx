"use client";

import { AutopilotStatusStrip } from "@/components/commerce/AutopilotStatusStrip";
import { ExceptionInbox } from "@/components/commerce/ExceptionInbox";
import { UsageMeter } from "@/components/commerce/UsageMeter";
import { VideoCreditMeter } from "@/components/commerce/VideoCreditMeter";
import { DegradedBanner, PermissionDenied, TableSkeleton } from "@/components/states/States";
import { PageHeader, SectionHeader } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { ERROR_FIXTURE, EXCEPTION_FIXTURES, USAGE_FIXTURES, VIDEO_FIXTURES } from "./fixtures";

/* Fixture labels below are developer annotations, not product UI. */
export function DevFixtures() {
  const { t } = useI18n();
  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "var(--space-8) var(--space-4) var(--space-16)", background: "var(--surface-raised)" }}>
      <PageHeader title={t("dev.title")} subtitle={t("dev.body")} />

      <SectionHeader title="AutopilotStatusStrip" meta="assisted · empty" />
      <AutopilotStatusStrip mode="assisted" automatedCount={0} needsAttentionCount={0} lockedUntilPhase={3} />
      <SectionHeader title="AutopilotStatusStrip" meta="smart · active" />
      <AutopilotStatusStrip mode="smart" automatedCount={128} needsAttentionCount={4} />
      <SectionHeader title="AutopilotStatusStrip" meta="autopilot · not measured" />
      <AutopilotStatusStrip mode="autopilot" automatedCount={null} needsAttentionCount={null} />

      <SectionHeader title="ExceptionInbox" meta="all 10 types" />
      <ExceptionInbox state="ready" items={EXCEPTION_FIXTURES} />
      <SectionHeader title="ExceptionInbox" meta="empty" />
      <ExceptionInbox state="ready" items={[]} />
      <SectionHeader title="ExceptionInbox" meta="loading" />
      <ExceptionInbox state="loading" />
      <SectionHeader title="ExceptionInbox" meta="error" />
      <ExceptionInbox state="error" error={ERROR_FIXTURE} onRetry={() => {}} />

      <SectionHeader title="VideoCreditMeter" />
      {VIDEO_FIXTURES.map((v) => (
        <div key={v.label}>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", marginTop: "var(--space-4)" }}>{v.label}</p>
          <VideoCreditMeter usage={v.usage} credits={v.credits} periodEnd={new Date(Date.now() + 9 * 86400000).toISOString()} />
        </div>
      ))}

      <SectionHeader title="UsageMeter" meta="policies · gauges · not included" />
      <div style={{ borderTop: "1px solid var(--border-default)" }}>
        {USAGE_FIXTURES.map((f) => (
          <div key={f.note}>
            <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", paddingTop: "var(--space-2)" }}>{f.note}</p>
            <UsageMeter usage={f.usage} periodEnd={new Date(Date.now() + 9 * 86400000).toISOString()} />
          </div>
        ))}
      </div>

      <SectionHeader title="States" meta="degraded · permission · skeleton" />
      <DegradedBanner errors={[ERROR_FIXTURE]} onRetry={() => {}} />
      <PermissionDenied permission="audit.read" />
      <TableSkeleton columns="2fr 1fr 1fr 1fr" rows={3} label="loading" />
    </main>
  );
}
