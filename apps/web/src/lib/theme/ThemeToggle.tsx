"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { useI18n } from "@/i18n/I18nProvider";
import { THEME_COOKIE, THEMES, resolveTheme, type AppTheme } from "./config";
import styles from "./theme.module.css";

export function applyTheme(theme: AppTheme) {
  document.documentElement.dataset.theme = theme;
  document.cookie = `${THEME_COOKIE}=${theme}; path=/; max-age=31536000; samesite=lax`;
}

export function useTheme(): [AppTheme, (t: AppTheme) => void] {
  const [theme, setTheme] = useState<AppTheme>("light");
  useEffect(() => setTheme(resolveTheme(document.documentElement.dataset.theme)), []);
  return [
    theme,
    (t) => {
      applyTheme(t);
      setTheme(t);
    },
  ];
}

const ICON: Record<AppTheme, "sun" | "moon" | "monitor"> = { light: "sun", dark: "moon", system: "monitor" };

/** Three-way segmented switch (Light · Dark · Device). Used on public pages and sign-in. */
export function ThemeToggle() {
  const { t } = useI18n();
  const [theme, set] = useTheme();
  return (
    <div className={styles.switch} role="group" aria-label={t("theme.label")}>
      {THEMES.map((th) => (
        <button key={th} type="button" aria-pressed={theme === th} title={t(`theme.${th}`)} onClick={() => set(th)}>
          <Icon name={ICON[th]} />
          <span className="srOnly">{t(`theme.${th}`)}</span>
        </button>
      ))}
    </div>
  );
}
