import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import type { AppLocale } from "@/i18n/config";
import { I18nProvider } from "@/i18n/I18nProvider";

export function renderWithI18n(ui: ReactElement, { locale = "en", ...options }: { locale?: AppLocale } & RenderOptions = {}) {
  return render(<I18nProvider locale={locale}>{ui}</I18nProvider>, options);
}
