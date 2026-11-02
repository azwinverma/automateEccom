/**
 * Calendar date math in the merchant's time zone (default Asia/Kathmandu, UTC+5:45, no DST).
 * Day keys are "YYYY-MM-DD" in that zone. Weeks start on Sunday (Nepal's first working day).
 */
export const DEFAULT_TZ = "Asia/Kathmandu";

export interface ZonedParts {
  year: number;
  month: number; // 1-12
  day: number;
  hour: number;
  minute: number;
  weekday: number; // 0 = Sunday
}

const dtfCache = new Map<string, Intl.DateTimeFormat>();
function dtf(tz: string): Intl.DateTimeFormat {
  let f = dtfCache.get(tz);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      weekday: "short",
    });
    dtfCache.set(tz, f);
  }
  return f;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function zonedParts(instant: Date | string, tz = DEFAULT_TZ): ZonedParts {
  const d = typeof instant === "string" ? new Date(instant) : instant;
  const parts = Object.fromEntries(dtf(tz).formatToParts(d).map((p) => [p.type, p.value]));
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour) % 24,
    minute: Number(parts.minute),
    weekday: WEEKDAYS.indexOf(String(parts.weekday)),
  };
}

const pad = (n: number) => String(n).padStart(2, "0");

export function dayKey(instant: Date | string, tz = DEFAULT_TZ): string {
  const p = zonedParts(instant, tz);
  return `${p.year}-${pad(p.month)}-${pad(p.day)}`;
}

/** Offset of `tz` from UTC at `instant`, in minutes (Kathmandu → 345). */
export function offsetMinutes(instant: Date, tz = DEFAULT_TZ): number {
  const p = zonedParts(instant, tz);
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
  const floored = Math.floor(instant.getTime() / 60000) * 60000;
  return Math.round((asUtc - floored) / 60000);
}

/** Wall-clock time in `tz` ("2026-11-03", "09:30") → UTC ISO string. */
export function zonedToUtcIso(day: string, time: string, tz = DEFAULT_TZ): string {
  const [y, m, d] = day.split("-").map(Number) as [number, number, number];
  const [hh, mm] = time.split(":").map(Number) as [number, number];
  const guess = Date.UTC(y, m - 1, d, hh, mm);
  let utc = guess - offsetMinutes(new Date(guess), tz) * 60000;
  // Second pass corrects zones whose offset differs across the guess (DST edges).
  utc = guess - offsetMinutes(new Date(utc), tz) * 60000;
  return new Date(utc).toISOString();
}

/** Pure calendar arithmetic on day keys (no time zone involved). */
export function addDays(key: string, n: number): string {
  const [y, m, d] = key.split("-").map(Number) as [number, number, number];
  const t = new Date(Date.UTC(y, m - 1, d + n));
  return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}`;
}

export function weekdayOf(key: string): number {
  const [y, m, d] = key.split("-").map(Number) as [number, number, number];
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay();
}

export function startOfWeek(key: string): string {
  return addDays(key, -weekdayOf(key));
}

export function weekDays(key: string): string[] {
  const start = startOfWeek(key);
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

export function startOfMonth(key: string): string {
  return `${key.slice(0, 7)}-01`;
}

export function addMonths(key: string, n: number): string {
  const [y, m] = key.split("-").map(Number) as [number, number];
  const t = new Date(Date.UTC(y, m - 1 + n, 1));
  return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-01`;
}

/** 6 weeks × 7 days covering the month (leading/trailing days from adjacent months). */
export function monthGrid(key: string): string[] {
  const first = startOfMonth(key);
  const start = startOfWeek(first);
  return Array.from({ length: 42 }, (_, i) => addDays(start, i));
}

/** UTC range [from, to) for a list of day keys in `tz` — what the API's from/to expect. */
export function utcRange(days: string[], tz = DEFAULT_TZ): { from: string; to: string } {
  return { from: zonedToUtcIso(days[0]!, "00:00", tz), to: zonedToUtcIso(addDays(days[days.length - 1]!, 1), "00:00", tz) };
}

/** "HH:MM" wall time in tz for an instant. */
export function timeOf(instant: Date | string, tz = DEFAULT_TZ): string {
  const p = zonedParts(instant, tz);
  return `${pad(p.hour)}:${pad(p.minute)}`;
}
