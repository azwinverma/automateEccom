import type { Metadata } from "next";
import { cookies } from "next/headers";
import { SitePage } from "@/features/site/SitePage";
import { siteEn, siteNe } from "@/features/site/copy";
import { getLocale, getTranslator } from "@/i18n/server";
import { SESSION_MARKER_COOKIE } from "@/lib/session-constants";

/** Public landing page: visitors arrive here, then sign up or sign in (specs/26 §15, BRD-014). */
export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslator();
  return { title: { absolute: t("meta.titleFull") }, alternates: { canonical: "/" } };
}

export default async function Landing() {
  const [locale, jar] = await Promise.all([getLocale(), cookies()]);
  const signedIn = Boolean(jar.get(SESSION_MARKER_COOKIE)?.value);
  return <SitePage copy={locale === "ne" ? siteNe : siteEn} signedIn={signedIn} />;
}
