"use client";

import {
  ApiClient,
  createApi,
  isApiError,
  type Api,
  type Me,
  type Membership,
} from "@commerce-os/api-client";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { BrowserSession } from "../session-constants";
import { bffLogout, bffRefresh } from "./bff";

export type AuthStatus = "idle" | "loading" | "ready" | "unauthenticated" | "unreachable";

export interface AuthValue {
  status: AuthStatus;
  error: unknown;
  me: Me | null;
  api: Api;
  activeMemberships: Membership[];
  merchantId: string | null;
  membership: Membership | null;
  selectMerchant: (id: string) => void;
  /** Effective permissions for the current merchant; `null` = unknown (server still enforces). */
  permissions: Set<string> | null;
  can: (permission: string) => boolean;
  ensureSession: () => void;
  establishSession: (session: BrowserSession) => Promise<Me>;
  reloadMe: () => Promise<Me | null>;
  signOut: () => Promise<void>;
}

const MERCHANT_KEY = "cos.merchant";
const AuthContext = createContext<AuthValue | null>(null);

function readStoredMerchant(): string | null {
  try {
    return window.localStorage.getItem(MERCHANT_KEY);
  } catch {
    return null;
  }
}
function storeMerchant(id: string | null) {
  try {
    if (id) window.localStorage.setItem(MERCHANT_KEY, id);
    else window.localStorage.removeItem(MERCHANT_KEY);
  } catch {
    /* storage unavailable: selection just won't persist */
  }
}

function pickMerchant(memberships: Membership[], preferred: string | null): string | null {
  if (preferred && memberships.some((m) => m.merchant.id === preferred)) return preferred;
  return memberships[0]?.merchant.id ?? null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("idle");
  const [error, setError] = useState<unknown>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<Set<string> | null>(null);

  const tokenRef = useRef<string | null>(null);
  const merchantRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  merchantRef.current = merchantId;

  const clearTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
  };

  // The client is created once; it reads token/merchant from refs.
  const clientRef = useRef<ApiClient | null>(null);
  const applySessionRef = useRef<(s: BrowserSession) => void>(() => {});

  if (!clientRef.current) {
    clientRef.current = new ApiClient({
      baseUrl: "/api/v1",
      getAccessToken: () => tokenRef.current,
      getMerchantId: () => merchantRef.current,
      refreshAccessToken: async () => {
        try {
          const s = await bffRefresh();
          applySessionRef.current(s);
          return s.access_token;
        } catch (e) {
          if (isApiError(e) && e.status === 401) {
            tokenRef.current = null;
            setStatus("unauthenticated");
          }
          return null;
        }
      },
      onUnauthenticated: () => {
        tokenRef.current = null;
        setStatus("unauthenticated");
      },
    });
  }
  const client = clientRef.current;
  const api = useMemo(() => createApi(client), [client]);

  const applySession = useCallback(
    (s: BrowserSession) => {
      tokenRef.current = s.access_token;
      clearTimer();
      const ms = Math.max(30, s.expires_in - 60) * 1000;
      timerRef.current = setTimeout(() => {
        void client.refresh();
      }, ms);
    },
    [client],
  );
  applySessionRef.current = applySession;

  useEffect(() => clearTimer, []);

  const loadMe = useCallback(async (): Promise<Me> => {
    const next = await api.me.get();
    const active = next.memberships.filter((m) => m.status === "active" || !m.status);
    const chosen = pickMerchant(active, merchantRef.current ?? readStoredMerchant());
    setMe(next);
    setMerchantId(chosen);
    merchantRef.current = chosen;
    storeMerchant(chosen);
    return next;
  }, [api]);

  const bootstrap = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const s = await bffRefresh();
      applySession(s);
      await loadMe();
      setStatus("ready");
    } catch (e) {
      setError(e);
      setStatus(isApiError(e) && e.status === 401 ? "unauthenticated" : "unreachable");
    }
  }, [applySession, loadMe]);

  const ensureSession = useCallback(() => {
    if (status === "idle" || status === "unreachable") void bootstrap();
  }, [bootstrap, status]);

  const establishSession = useCallback(
    async (s: BrowserSession) => {
      applySession(s);
      const next = await loadMe();
      setError(null);
      setStatus("ready");
      return next;
    },
    [applySession, loadMe],
  );

  const reloadMe = useCallback(async () => {
    try {
      return await loadMe();
    } catch {
      return null;
    }
  }, [loadMe]);

  const selectMerchant = useCallback((id: string) => {
    merchantRef.current = id;
    setMerchantId(id);
    storeMerchant(id);
  }, []);

  const signOut = useCallback(async () => {
    clearTimer();
    try {
      await bffLogout();
    } finally {
      tokenRef.current = null;
      setMe(null);
      setPermissions(null);
      setStatus("unauthenticated");
    }
  }, []);

  // Effective permissions per merchant (used only to hide actions).
  useEffect(() => {
    if (status !== "ready" || !merchantId) return;
    let cancelled = false;
    setPermissions(null);
    api.me
      .permissions()
      .then((r) => {
        if (!cancelled && Array.isArray(r?.permissions)) setPermissions(new Set(r.permissions));
      })
      .catch(() => {
        /* unknown permissions: show actions, server enforces */
      });
    return () => {
      cancelled = true;
    };
  }, [api, merchantId, status]);

  const activeMemberships = useMemo(
    () => (me?.memberships ?? []).filter((m) => m.status === "active" || !m.status),
    [me],
  );
  const membership = activeMemberships.find((m) => m.merchant.id === merchantId) ?? null;

  const value = useMemo<AuthValue>(
    () => ({
      status,
      error,
      me,
      api,
      activeMemberships,
      merchantId,
      membership,
      selectMerchant,
      permissions,
      can: (p) => (permissions ? permissions.has(p) : true),
      ensureSession,
      establishSession,
      reloadMe,
      signOut,
    }),
    [status, error, me, api, activeMemberships, merchantId, membership, selectMerchant, permissions, ensureSession, establishSession, reloadMe, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
