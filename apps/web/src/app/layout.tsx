import "@commerce-os/design-system/tokens.css";
import "./globals.css";
import { tokens } from "@commerce-os/design-system/tokens";
import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";
import { I18nProvider } from "@/i18n/I18nProvider";
import { getLocale, getTranslator } from "@/i18n/server";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { getTheme } from "@/lib/theme/server";

// Fonts live in the repo (Fontsource 5.3.0 builds, SIL OFL; see ./fonts/*-OFL.txt), so builds never
// depend on downloading from Google Fonts.
const inter = localFont({
  src: "./fonts/inter-latin-wght-normal.woff2",
  weight: "100 900",
  variable: "--font-inter",
  display: "swap",
});
const devanagari = localFont({
  src: [
    { path: "./fonts/noto-sans-devanagari-devanagari-400-normal.woff2", weight: "400" },
    { path: "./fonts/noto-sans-devanagari-devanagari-500-normal.woff2", weight: "500" },
    { path: "./fonts/noto-sans-devanagari-devanagari-600-normal.woff2", weight: "600" },
    { path: "./fonts/noto-sans-devanagari-devanagari-700-normal.woff2", weight: "700" },
  ],
  variable: "--font-devanagari",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslator();
  const title = t("meta.titleFull");
  const description = t("meta.description");
  return {
    // Public origin for absolute OG URLs; falls back to localhost in dev.
    metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3010"),
    applicationName: t("brand.name"),
    title: { default: title, template: `%s · ${t("meta.title")}` },
    description,
    openGraph: { type: "website", siteName: t("brand.name"), title, description },
    twitter: { card: "summary_large_image", title, description },
    appleWebApp: { title: t("brand.name"), statusBarStyle: "default" },
    formatDetection: { telephone: false },
  };
}

export async function generateViewport(): Promise<Viewport> {
  const theme = await getTheme();
  // Browser chrome colour must be a literal; values are the canvas tokens for the chosen theme.
  const light = tokens.semantic.light["surface-canvas"];
  const dark = tokens.semantic.dark["surface-canvas"];
  return {
    width: "device-width",
    initialScale: 1,
    colorScheme: theme === "system" ? "light dark" : theme,
    themeColor:
      theme === "system"
        ? [
            { media: "(prefers-color-scheme: light)", color: light },
            { media: "(prefers-color-scheme: dark)", color: dark },
          ]
        : theme === "dark"
          ? dark
          : light,
  };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const [locale, theme] = await Promise.all([getLocale(), getTheme()]);
  return (
    // data-theme is set on the server from the cookie (light by default), so there is no theme flash.
    <html lang={locale} data-theme={theme} className={`${inter.variable} ${devanagari.variable}`}>
      <body>
        <I18nProvider locale={locale}>
          <AuthProvider>{children}</AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
