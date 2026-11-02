"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/i18n/I18nProvider";
import { SETTINGS_PAGES } from "@/lib/sections";
import styles from "./settings.module.css";

export function SettingsTabs() {
  const { t } = useI18n();
  const pathname = usePathname();
  return (
    <>
      <h1 className={styles.settingsTitle}>{t("settings.title")}</h1>
      <nav aria-label={t("settings.nav")}>
      <ul className={styles.tabs}>
        {SETTINGS_PAGES.map((p) => (
          <li key={p.key}>
            <Link href={p.href} className={styles.tab} aria-current={pathname.startsWith(p.href) ? "page" : undefined}>
              {t(`settings.${p.key}`)}
            </Link>
          </li>
        ))}
      </ul>
      </nav>
    </>
  );
}
