"use client";

import type { Api, ImportJob, ImportStatus } from "@commerce-os/api-client";
import { useCallback, useEffect, useRef, useState } from "react";

export const TERMINAL_IMPORT: ReadonlySet<ImportStatus> = new Set(["completed", "completed_with_errors", "failed"]);
export const MAX_POLL_FAILURES = 3;

/** 1s, 1.5s, 2.25s … capped at 5s. */
export function pollDelay(attempt: number): number {
  return Math.min(5000, Math.round(1000 * 1.5 ** attempt));
}

/**
 * Poll an import job until it reaches a terminal status. Stops on unmount, on a
 * terminal status, or after MAX_POLL_FAILURES consecutive request failures.
 */
export function useImportJob(api: Api, id: string | null, initial: ImportJob | null = null) {
  const [job, setJob] = useState<ImportJob | null>(initial);
  const [error, setError] = useState<unknown>(null);
  const [nonce, setNonce] = useState(0);
  const initialRef = useRef(initial);
  initialRef.current = initial;

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    let failures = 0;
    setError(null);

    const tick = async () => {
      try {
        const next = await api.catalog.importJob(id);
        if (cancelled) return;
        failures = 0;
        setJob(next);
        if (TERMINAL_IMPORT.has(next.status)) return;
      } catch (e) {
        if (cancelled) return;
        failures += 1;
        if (failures >= MAX_POLL_FAILURES) {
          setError(e);
          return;
        }
      }
      timer = setTimeout(tick, pollDelay(attempt++));
    };

    const seed = initialRef.current;
    if (seed && seed.id === id && TERMINAL_IMPORT.has(seed.status)) {
      setJob(seed);
      return;
    }
    if (seed && seed.id === id) {
      setJob(seed);
      timer = setTimeout(tick, pollDelay(attempt++));
    } else {
      setJob(null);
      void tick();
    }
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [api, id, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);
  return { job, error, retry, done: job ? TERMINAL_IMPORT.has(job.status) : false };
}
