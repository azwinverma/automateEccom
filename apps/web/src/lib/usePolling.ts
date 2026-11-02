"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface PollingOptions<T> {
  /** Poll while non-null; changing it restarts polling. */
  key: string | null;
  isDone: (value: T) => boolean;
  /** Seed value (e.g. the POST response) so the first paint doesn't wait a full interval. */
  initial?: T | null;
  /** Delay before attempt n (0-based). Default 1s × 1.5ⁿ, capped at 5s. */
  delay?: (attempt: number) => number;
  maxFailures?: number;
}

export function backoff(attempt: number, base = 1000, cap = 5000): number {
  return Math.min(cap, Math.round(base * 1.5 ** attempt));
}

/**
 * Poll `load` until `isDone`. Stops on unmount, on key change, when done, or after
 * `maxFailures` consecutive errors (then `error` is set and `retry()` restarts).
 * `refresh()` fetches once more even after done (e.g. to renew signed URLs).
 */
export function usePolling<T>(load: () => Promise<T>, opts: PollingOptions<T>) {
  const { key, initial = null, maxFailures = 3 } = opts;
  const [data, setData] = useState<T | null>(initial);
  const [error, setError] = useState<unknown>(null);
  const [nonce, setNonce] = useState(0);
  const loadRef = useRef(load);
  const isDoneRef = useRef(opts.isDone);
  const delayRef = useRef(opts.delay ?? ((n: number) => backoff(n)));
  const initialRef = useRef(initial);
  loadRef.current = load;
  isDoneRef.current = opts.isDone;
  delayRef.current = opts.delay ?? ((n: number) => backoff(n));
  initialRef.current = initial;

  useEffect(() => {
    if (!key) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    let failures = 0;
    setError(null);

    const tick = async () => {
      try {
        const next = await loadRef.current();
        if (cancelled) return;
        failures = 0;
        setData(next);
        if (isDoneRef.current(next)) return;
      } catch (e) {
        if (cancelled) return;
        failures += 1;
        if (failures >= maxFailures) {
          setError(e);
          return;
        }
      }
      timer = setTimeout(tick, delayRef.current(attempt++));
    };

    const seed = initialRef.current;
    if (seed && nonce === 0) {
      setData(seed);
      if (isDoneRef.current(seed)) return;
      timer = setTimeout(tick, delayRef.current(attempt++));
    } else {
      void tick();
    }
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [key, nonce, maxFailures]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);
  return { data, setData, error, retry, refresh: retry, done: data !== null && opts.isDone(data) };
}
