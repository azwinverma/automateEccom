export interface FieldChange {
  field: string;
  before: unknown;
  after: unknown;
}

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

const PAIRS: [string, string][] = [
  ["old", "new"],
  ["before", "after"],
  ["from", "to"],
];

/**
 * Normalise the audit `changes` payload (format not pinned by the contract) into rows.
 * Accepts `{before:{…}, after:{…}}`, `{field: {old,new}}`, `{field: [old,new]}` or `{field: value}`.
 */
export function normalizeChanges(changes: Record<string, unknown> | null | undefined): FieldChange[] {
  if (!isObj(changes)) return [];
  if (isObj(changes.before) || isObj(changes.after)) {
    const before = isObj(changes.before) ? changes.before : {};
    const after = isObj(changes.after) ? changes.after : {};
    const keys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)])).sort();
    return keys
      .filter((k) => JSON.stringify(before[k]) !== JSON.stringify(after[k]))
      .map((field) => ({ field, before: before[field], after: after[field] }));
  }
  return Object.entries(changes).map(([field, value]) => {
    if (Array.isArray(value) && value.length === 2) return { field, before: value[0], after: value[1] };
    if (isObj(value)) {
      for (const [a, b] of PAIRS) {
        if (a in value || b in value) return { field, before: value[a], after: value[b] };
      }
    }
    return { field, before: undefined, after: value };
  });
}

export function formatValue(v: unknown): string {
  if (v === undefined) return "";
  if (v === null) return "null";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

export function shortId(id: string | null | undefined): string {
  if (!id) return "";
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}
