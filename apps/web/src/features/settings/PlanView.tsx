"use client";

import type { UsageLimit } from "@commerce-os/api-client";
import { UsageMeter } from "@/components/commerce/UsageMeter";
import { VideoCreditMeter } from "@/components/commerce/VideoCreditMeter";
import { DegradedBanner, EmptyState, QueryError, TableSkeleton, isPermissionDenied } from "@/components/states/States";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, SectionHeader, Skeleton, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { creditKindLabel, featureLabel } from "@/i18n/labels";
import { useApiQuery } from "@/lib/api/hooks";
import { PLANS_HREF, isGauge, isIncluded, isPremiumVideoResource } from "@/lib/usage";
import styles from "./settings.module.css";

function statusTone(status: string): Tone {
  if (status === "active") return "success";
  if (status === "trialing") return "info";
  if (status === "past_due") return "warning";
  return "neutral";
}

/** Included limits first, then the ones not in this plan. */
function byIncluded(a: UsageLimit, b: UsageLimit): number {
  return Number(isIncluded(b)) - Number(isIncluded(a));
}

export function PlanView() {
  const { t, date, number } = useI18n();
  const subscription = useApiQuery((a) => a.billing.subscription());
  const entitlements = useApiQuery((a) => a.billing.entitlements());
  const credits = useApiQuery((a) => a.billing.credits());

  const states = [subscription.state, entitlements.state, credits.state];
  const errors = states.flatMap((s) => (s.status === "error" ? [s.error] : []));
  const retryAll = () => {
    if (subscription.state.status === "error") subscription.reload();
    if (entitlements.state.status === "error") entitlements.reload();
    if (credits.state.status === "error") credits.reload();
  };

  const header = <PageHeader level={2} title={t("plan.title")} subtitle={t("plan.subtitle")} />;

  if (errors.length === states.length) {
    return (
      <>
        {header}
        <QueryError error={errors[0]} onRetry={retryAll} />
      </>
    );
  }

  const sub = subscription.state.status === "success" ? subscription.state.data : null;
  const ent = entitlements.state.status === "success" ? entitlements.state.data : null;
  const cred = credits.state.status === "success" ? credits.state.data : null;
  const periodEnd = sub?.current_period_end ?? null;

  const videoLimit = ent?.limits.find((l) => isPremiumVideoResource(l.resource)) ?? null;
  const premiumVideo = Boolean(videoLimit && isIncluded(videoLimit) && ent?.features["video.premium"] !== false);
  const rest = ent?.limits.filter((l) => l !== videoLimit) ?? [];
  const consumable = rest.filter((l) => !isGauge(l)).sort(byIncluded);
  const capacity = rest.filter((l) => isGauge(l)).sort(byIncluded);

  const features = ent ? Object.entries(ent.features).sort(([a], [b]) => a.localeCompare(b)) : [];
  const included = features.filter(([, on]) => on).map(([code]) => code);
  const higher = features.filter(([, on]) => !on).map(([code]) => code);

  const limitRows = (list: UsageLimit[]) => (
    <div style={{ borderTop: "1px solid var(--border-default)" }}>
      {list.map((l) => (
        <UsageMeter key={`${l.resource}-${l.period}`} usage={l} periodEnd={periodEnd} />
      ))}
    </div>
  );

  return (
    <>
      {header}
      {errors.length > 0 && !errors.every(isPermissionDenied) ? <DegradedBanner errors={errors} onRetry={retryAll} /> : null}

      <section aria-label={t("plan.currentPlan")}>
        {subscription.state.status === "loading" ? (
          <div className={styles.planHead} role="status" aria-label={t("common.loading")}>
            <div className={styles.stack} style={{ gap: "var(--space-2)", flex: 1 }}>
              <Skeleton width={160} height={22} />
              <Skeleton width={260} />
            </div>
          </div>
        ) : sub ? (
          <div className={styles.planHead}>
            <div>
              <span className={styles.kicker}>{t("plan.currentPlan")}</span>
              <div className={styles.planName}>
                {sub.plan.name}
                <Badge tone={statusTone(sub.status)}>{t.dynamic(`plan.status.${sub.status}`) ?? sub.status}</Badge>
              </div>
              {sub.plan.tagline ? <p className={styles.planTagline}>{sub.plan.tagline}</p> : null}
            </div>
            <div className={styles.planDates}>
              {sub.status === "trialing" && sub.trial_ends_at ? <span>{t("plan.trialEnds", { date: date(sub.trial_ends_at) })}</span> : null}
              <span>{t("plan.period", { start: date(sub.current_period_start), end: date(sub.current_period_end) })}</span>
            </div>
          </div>
        ) : null}
      </section>

      <SectionHeader title={t("plan.videoHeading")} />
      {entitlements.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr" rows={2} label={t("common.loading")} />
      ) : premiumVideo && videoLimit ? (
        <VideoCreditMeter usage={videoLimit} credits={cred?.balance ?? null} periodEnd={periodEnd} />
      ) : ent ? (
        <div className={styles.calmNote} data-testid="video-unavailable">
          <p>{t("video.premiumUnavailable")}</p>
          <ButtonLink href={PLANS_HREF} size="sm" variant="ghost">
            {t("usage.seePlans")}
          </ButtonLink>
        </div>
      ) : null}

      <SectionHeader title={t("plan.usageHeading")} meta={periodEnd ? t("usage.renewsOn", { date: date(periodEnd) }) : undefined} />
      {entitlements.state.status === "loading" ? (
        <TableSkeleton columns="1fr 2fr 1fr" rows={4} label={t("common.loading")} />
      ) : entitlements.state.status === "error" ? (
        <QueryError error={entitlements.state.error} onRetry={entitlements.reload} />
      ) : consumable.length === 0 && capacity.length === 0 ? (
        <EmptyState title={t("plan.usageEmpty")} />
      ) : (
        <>
          {consumable.length ? limitRows(consumable) : null}
          {capacity.length ? (
            <>
              <SectionHeader title={t("plan.capacityHeading")} />
              {limitRows(capacity)}
            </>
          ) : null}
        </>
      )}

      <section id="credits" aria-labelledby="credits-heading">
        <SectionHeader title={t("plan.creditsHeading")} id="credits-heading" />
        {credits.state.status === "loading" ? (
          <TableSkeleton columns="1fr 2fr 1fr" rows={3} label={t("common.loading")} />
        ) : credits.state.status === "error" ? (
          <QueryError error={credits.state.error} onRetry={credits.reload} />
        ) : cred ? (
          <>
            <div className={styles.balance}>
              <span className={styles.kicker}>{t("plan.creditsBalance")}</span>
              <span className={styles.balanceValue}>{t("plan.creditsUnit", { count: number(cred.balance) })}</span>
            </div>
            {cred.transactions.length === 0 ? (
              <p className={table.empty}>{t("plan.creditsEmpty")}</p>
            ) : (
              <div className={table.wrap}>
                <table className={[table.table, table.dense].join(" ")} aria-labelledby="credits-heading">
                  <thead>
                    <tr>
                      <th scope="col">{t("plan.colWhen")}</th>
                      <th scope="col">{t("plan.colReason")}</th>
                      <th scope="col" className={table.num}>
                        {t("plan.colAmount")}
                      </th>
                      <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                        {t("plan.colBalance")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cred.transactions.map((tx) => (
                      <tr key={tx.id} data-kind={tx.kind ?? "other"}>
                        <td className={table.muted}>{tx.created_at ? date(tx.created_at) : t("common.none")}</td>
                        <td className={tx.kind === "hold" || tx.kind === "release" ? table.muted : undefined}>{creditKindLabel(t, tx.kind)}</td>
                        <td className={table.num}>{number(tx.amount, { signDisplay: "exceptZero" })}</td>
                        <td className={[table.num, table.hideSm, table.muted].join(" ")}>
                          {typeof tx.balance_after === "number" ? number(tx.balance_after) : t("common.none")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : null}
      </section>

      <section id="plans" aria-label={t("plan.featuresHeading")}>
        {included.length > 0 ? (
          <>
            <SectionHeader title={t("plan.featuresHeading")} id="features-included" />
            <ul className={styles.features} aria-labelledby="features-included" data-testid="features-included">
              {included.map((code) => (
                <li key={code}>
                  <Icon name="check" />
                  <span>{featureLabel(t, code)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : null}
        {higher.length > 0 ? (
          <>
            <SectionHeader title={t("plan.higherPlansHeading")} id="features-higher" />
            <ul
              className={[styles.features, styles.featuresHigher].join(" ")}
              aria-labelledby="features-higher"
              data-testid="features-higher"
            >
              {higher.map((code) => (
                <li key={code}>
                  <span>{featureLabel(t, code)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
    </>
  );
}
