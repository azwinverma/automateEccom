/** Colour theme. Light is the default for everyone (specs/26 §16); dark and "follow device" are opt-in. */
export const THEMES = ["light", "dark", "system"] as const;
export type AppTheme = (typeof THEMES)[number];
export const THEME_COOKIE = "cos_theme";
export const DEFAULT_THEME: AppTheme = "light";

export function resolveTheme(v: string | undefined | null): AppTheme {
  return (THEMES as readonly string[]).includes(v ?? "") ? (v as AppTheme) : DEFAULT_THEME;
}
