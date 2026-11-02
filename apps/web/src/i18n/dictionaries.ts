import type { AppLocale } from "./config";
import { en } from "./messages/en";
import { ne } from "./messages/ne";
import type { Messages, MessageKey, Translate, Vars } from "./types";

export const dictionaries: Record<AppLocale, Messages> = { en, ne };

function lookup(messages: Messages, key: string): string | undefined {
  let node: unknown = messages;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null) return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : undefined;
}

export function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (m, name: string) => (name in vars ? String(vars[name]) : m));
}

export function createTranslator(locale: AppLocale): Translate {
  const messages = dictionaries[locale];
  const t = ((key: MessageKey, vars?: Vars) => {
    const value = lookup(messages, key) ?? lookup(dictionaries.en, key) ?? key;
    return interpolate(value, vars);
  }) as Translate;
  t.dynamic = (key: string, vars?: Vars) => {
    const value = lookup(messages, key) ?? lookup(dictionaries.en, key);
    return value === undefined ? undefined : interpolate(value, vars);
  };
  return t;
}
