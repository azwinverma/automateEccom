"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import type { SectionDef, SectionKey } from "@/lib/sections";
import styles from "./home.module.css";

/** Honest placeholder for sections that are not built yet — no sample data. */
export function ComingSection({ section }: { section: SectionDef & { key: Exclude<SectionKey, "home">; phase: number } }) {
  const { t, number } = useI18n();
  return (
    <>
      <PageHeader title={t(`nav.${section.key}`)} />
      <div className={styles.coming}>
        <div>
          <span className={styles.phaseTag}>{t("sections.arrives", { phase: number(section.phase) })}</span>
          <p className={styles.comingBody}>{t(`sections.${section.key}`)}</p>
        </div>
        <nav className={styles.meanwhile} aria-labelledby="meanwhile-heading">
          <h2 id="meanwhile-heading">{t("sections.meanwhile")}</h2>
          <ul>
            <li>
              <Link href="/settings/team">
                {t("sections.meanwhileTeam")}
                <Icon name="arrowRight" />
              </Link>
            </li>
            <li>
              <Link href="/settings/security">
                {t("sections.meanwhileSecurity")}
                <Icon name="arrowRight" />
              </Link>
            </li>
            <li>
              <Link href="/settings/plan">
                {t("sections.meanwhilePlan")}
                <Icon name="arrowRight" />
              </Link>
            </li>
          </ul>
        </nav>
      </div>
    </>
  );
}
