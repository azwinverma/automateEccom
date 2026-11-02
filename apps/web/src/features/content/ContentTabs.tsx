"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/i18n/I18nProvider";
import settings from "../settings/settings.module.css";

export function ContentTabs() {
  const { t } = useI18n();
  const pathname = usePathname();
  const tabs = [
    { href: "/content", label: t("content.tabCalendar"), active: pathname === "/content" },
    { href: "/content/reels", label: t("content.tabReels"), active: pathname.startsWith("/content/reels") },
  ];
  return (
    <nav aria-label={t("content.sectionTabs")}>
      <ul className={settings.tabs}>
        {tabs.map((tb) => (
          <li key={tb.href}>
            <Link href={tb.href} className={settings.tab} aria-current={tb.active ? "page" : undefined}>
              {tb.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
