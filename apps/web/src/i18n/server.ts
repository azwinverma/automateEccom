import { cookies, headers } from "next/headers";
import { LOCALE_COOKIE, resolveLocale, type AppLocale } from "./config";
import { createTranslator } from "./dictionaries";

export async function getLocale(): Promise<AppLocale> {
  const [c, h] = await Promise.all([cookies(), headers()]);
  return resolveLocale(c.get(LOCALE_COOKIE)?.value, h.get("accept-language"));
}

export async function getTranslator() {
  return createTranslator(await getLocale());
}
