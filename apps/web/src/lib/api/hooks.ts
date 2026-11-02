"use client";

import type { Api } from "@commerce-os/api-client";
import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import { useAuth } from "../auth/AuthProvider";

export type QueryState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: unknown };

export interface QueryResult<T> {
  state: QueryState<T>;
  reload: () => void;
  /** Optimistically replace data after a successful mutation. */
  setData: (updater: (prev: T) => T) => void;
}

/** Fetch on mount and whenever deps or the selected merchant change. */
export function useApiQuery<T>(fetcher: (api: Api) => Promise<T>, deps: DependencyList = []): QueryResult<T> {
  const { api, merchantId } = useAuth();
  const [state, setState] = useState<QueryState<T>>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetcherRef.current(api).then(
      (data) => !cancelled && setState({ status: "success", data }),
      (error: unknown) => !cancelled && setState({ status: "error", error }),
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, merchantId, nonce, ...deps]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const setData = useCallback(
    (updater: (prev: T) => T) =>
      setState((s) => (s.status === "success" ? { status: "success", data: updater(s.data) } : s)),
    [],
  );
  return { state, reload, setData };
}

/** Stable Idempotency-Key per logical submission: same body → same key, so retries replay. */
export function useIdempotencyKey() {
  const ref = useRef<{ body: string; key: string } | null>(null);
  const keyFor = useCallback((body: unknown) => {
    const serialized = JSON.stringify(body);
    if (!ref.current || ref.current.body !== serialized) {
      ref.current = { body: serialized, key: crypto.randomUUID() };
    }
    return ref.current.key;
  }, []);
  const reset = useCallback(() => {
    ref.current = null;
  }, []);
  return { keyFor, reset };
}

/** Track a single async action's pending/error state. */
export function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const run = useCallback(async <R,>(fn: () => Promise<R>): Promise<R | undefined> => {
    setPending(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e);
      return undefined;
    } finally {
      setPending(false);
    }
  }, []);
  const clear = useCallback(() => setError(null), []);
  return { pending, error, run, clear };
}
