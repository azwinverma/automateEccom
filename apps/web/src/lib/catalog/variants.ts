/** Option → variant combination logic for the variant grid. */

export interface OptionDraft {
  name: string;
  values: string[];
}

export const MAX_OPTIONS = 3;
export const MAX_VALUES_PER_OPTION = 50;
export const MAX_VARIANTS = 100;

/** Trim names/values, drop empty values and case-insensitive duplicates; keep options with a name and values. */
export function cleanOptions(options: OptionDraft[]): OptionDraft[] {
  return options
    .map((o) => {
      const seen = new Set<string>();
      const values: string[] = [];
      for (const raw of o.values) {
        const v = raw.trim();
        if (v && !seen.has(v.toLowerCase())) {
          seen.add(v.toLowerCase());
          values.push(v);
        }
      }
      return { name: o.name.trim(), values };
    })
    .filter((o) => o.name && o.values.length > 0);
}

/** Cartesian product in option order. No options → one default combination `{}`. */
export function combinations(options: OptionDraft[]): Record<string, string>[] {
  const clean = cleanOptions(options);
  let out: Record<string, string>[] = [{}];
  for (const o of clean) {
    const next: Record<string, string>[] = [];
    for (const combo of out) for (const value of o.values) next.push({ ...combo, [o.name]: value });
    out = next;
  }
  return out;
}

export function combinationCount(options: OptionDraft[]): number {
  return cleanOptions(options).reduce((n, o) => n * o.values.length, 1);
}

/**
 * Stable key for a combination: the value tuple in option order (case-insensitive).
 * Using values, not names, keeps rows (and typed prices) when an option is renamed.
 */
export function comboKey(combo: Record<string, string>, optionNames: string[]): string {
  if (optionNames.length === 0) return "default";
  return optionNames.map((n) => (combo[n] ?? "").toLowerCase()).join(" / ");
}

export function variantTitle(combo: Record<string, string>, optionNames: string[]): string {
  return optionNames.map((n) => combo[n]).filter(Boolean).join(" / ");
}

/**
 * Rebuild grid rows for the current options, keeping what the seller typed into rows
 * whose combination still exists. `excluded` keys are combinations the seller removed.
 */
export function syncRows<T extends { key: string; options: Record<string, string> }>(
  rows: T[],
  options: OptionDraft[],
  excluded: string[],
  make: (combo: Record<string, string>, key: string) => T,
): T[] {
  const names = cleanOptions(options).map((o) => o.name);
  const byKey = new Map(rows.map((r) => [r.key, r]));
  const skip = new Set(excluded);
  return combinations(options)
    .map((combo) => ({ combo, key: comboKey(combo, names) }))
    .filter(({ key }) => !skip.has(key))
    .map(({ combo, key }) => {
      const existing = byKey.get(key);
      return existing ? { ...existing, options: combo } : make(combo, key);
    });
}
