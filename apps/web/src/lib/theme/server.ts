import { cookies } from "next/headers";
import { THEME_COOKIE, resolveTheme, type AppTheme } from "./config";

export async function getTheme(): Promise<AppTheme> {
  return resolveTheme((await cookies()).get(THEME_COOKIE)?.value);
}
