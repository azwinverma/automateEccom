import type { ReactNode } from "react";
import { getTranslator } from "@/i18n/server";
import { LanguageToggle } from "./LanguageToggle";
import styles from "./auth.module.css";

export default async function AuthLayout({ children }: { children: ReactNode }) {
  const t = await getTranslator();
  const steps = [
    t("auth.asideStep1"),
    t("auth.asideStep2"),
    t("auth.asideStep3"),
    t("auth.asideStep4"),
    t("auth.asideStep5"),
    t("auth.asideStep6"),
  ];
  return (
    <div className={styles.layout}>
      <aside className={styles.aside}>
        <div className={styles.wordmark}>
          <span className={styles.wordmarkMark} aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          {t("meta.title")}
        </div>
        <div className={styles.asideCopy}>
          <p className={styles.asideTitle}>{t("auth.asideTitle")}</p>
          <p className={styles.asideBody}>{t("auth.asideBody")}</p>
        </div>
        <ol className={styles.journey}>
          {steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </aside>
      <div className={styles.main}>
        <div className={styles.topRow}>
          <LanguageToggle />
        </div>
        <main className={styles.formWrap}>{children}</main>
      </div>
    </div>
  );
}
