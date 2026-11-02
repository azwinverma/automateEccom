import "@commerce-os/design-system/tokens.css";
import "./globals.css";
import { tokens } from "@commerce-os/design-system/tokens";
import type { Metadata, Viewport } from "next";
import { Inter, Noto_Sans_Devanagari } from "next/font/google";
import type { ReactNode } from "react";
import { I18nProvider } from "@/i18n/I18nProvider";
import { getLocale, getTranslator } from "@/i18n/server";
import { AuthProvider } from "@/lib/auth/AuthProvider";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600", "700"],
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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Browser chrome colour must be a literal; values are the canvas tokens (light/dark).
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: tokens.semantic.light["surface-canvas"] },
    { media: "(prefers-color-scheme: dark)", color: tokens.semantic.dark["surface-canvas"] },
  ],
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  return (
    <html lang={locale} className={`${inter.variable} ${devanagari.variable}`}>
      <body>
        <I18nProvider locale={locale}>
          <AuthProvider>{children}</AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
