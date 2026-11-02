import Link from "next/link";
import type { ReactNode } from "react";
import { CommerceLoop, HandUnderline, NivaroLogo } from "@/components/brand/Brand";
import { getTranslator } from "@/i18n/server";
import { ThemeToggle } from "@/lib/theme/ThemeToggle";
import { LanguageToggle } from "./LanguageToggle";
import styles from "./auth.module.css";

/** Sign-in / sign-up / onboarding frame. Brand energy: medium-high (specs/26 §29). */
export default async function AuthLayout({ children }: { children: ReactNode }) {
  const t = await getTranslator();
  const stages = (["Create", "Sell", "Fulfill", "Learn"] as const).map((s) => ({
    key: s.toLowerCase(),
    label: t(`brand.stage${s}`),
    detail: t(`brand.stage${s}Detail`),
  }));
  return (
    <div className={styles.layout}>
      <aside className={styles.aside}>
        <Link href="/" className={styles.homeLink}>
          <NivaroLogo height={26} label={t("brand.name")} />
        </Link>
        <div className={styles.asideCopy}>
          <p className={styles.asideTitle}>
            {t("brand.taglineLead")}
            <br />
            <HandUnderline>{t("brand.taglineEmphasis")}</HandUnderline>
            {t("brand.taglineEnd")}
          </p>
          <p className={styles.asideBody}>{t("auth.asideBody")}</p>
        </div>
        <div className={styles.loopWrap}>
          <CommerceLoop label={t("brand.loopLabel")} stages={stages} />
        </div>
      </aside>
      <div className={styles.main}>
        <div className={styles.topRow}>
          <Link href="/" className={styles.mobileLogo}>
            <NivaroLogo height={22} label={t("brand.name")} />
          </Link>
          <ThemeToggle />
          <LanguageToggle />
        </div>
        <main className={styles.formWrap}>{children}</main>
      </div>
    </div>
  );
}
