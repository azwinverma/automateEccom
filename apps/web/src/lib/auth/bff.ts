import { ApiError, errorFromResponse } from "@commerce-os/api-client";
import type { BrowserMfaChallenge, BrowserSession } from "../session-constants";

async function post<T>(path: string, body?: unknown): Promise<T> {
  const requestId = crypto.randomUUID();
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json", "X-Request-ID": requestId },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch (e) {
    throw new ApiError({ status: 0, code: "network_error", message: String(e), requestId });
  }
  if (!res.ok) throw await errorFromResponse(res, requestId);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function bffLogin(email: string, password: string) {
  return post<BrowserSession | BrowserMfaChallenge>("/api/session/login", { email, password });
}

export function bffMfaVerify(mfaToken: string, code: string) {
  return post<BrowserSession>("/api/session/mfa-verify", { mfa_token: mfaToken, code });
}

export function bffLogout() {
  return post<void>("/api/session/logout");
}

/**
 * Refresh via the httpOnly cookie. Refresh tokens rotate on every use and reuse
 * revokes the whole session family, so tabs must not refresh concurrently: the
 * Web Locks API serialises refreshes across tabs of this origin.
 */
export async function bffRefresh(): Promise<BrowserSession> {
  const run = () => post<BrowserSession>("/api/session/refresh");
  if (typeof navigator !== "undefined" && navigator.locks?.request) {
    return await navigator.locks.request("cos-session-refresh", run);
  }
  return run();
}

export function isBrowserSession(v: unknown): v is BrowserSession {
  return typeof v === "object" && v !== null && typeof (v as BrowserSession).access_token === "string";
}

/** Only allow same-site relative redirects (prevents open redirects via ?next=). */
export function safeNext(next: string | null | undefined, fallback = "/home"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return fallback;
  if (next.startsWith("/login") || next.startsWith("/register")) return fallback;
  return next;
}
