/**
 * OAuth connect round-trip state. Before redirecting to the provider we remember what we
 * started (provider, the server's `state`, where to return) in sessionStorage; the callback
 * page only exchanges a code that matches. The server validates `state` again.
 */
export interface PendingConnect {
  provider: string;
  state: string;
  reconnectId: string | null;
  returnTo: string;
  startedAt: number;
}

export const PENDING_KEY = "cos.channels.pendingConnect";
export const PENDING_TTL_MS = 15 * 60 * 1000;

/** The provider's authorize URL carries the server-issued `state`. */
export function stateFromAuthorizeUrl(url: string): string | null {
  try {
    return new URL(url).searchParams.get("state");
  } catch {
    return null;
  }
}

export function callbackUrl(origin: string): string {
  return `${origin.replace(/\/+$/, "")}/channels/callback`;
}

/** One-click Facebook & Instagram returns here (it needs a Page picker, not the generic callback). */
export const META_CALLBACK_PATH = "/settings/channels/meta";
export const META_PENDING_PROVIDER = "meta";

export function metaCallbackUrl(origin: string): string {
  return `${origin.replace(/\/+$/, "")}${META_CALLBACK_PATH}`;
}

export type CallbackResolution =
  | { kind: "exchange"; provider: string; state: string; code: string; returnTo: string }
  | { kind: "denied"; returnTo: string }
  | { kind: "invalid"; reason: "missing_params" | "no_pending" | "state_mismatch" | "expired"; returnTo: string };

const FALLBACK_RETURN = "/settings/channels";

export function resolveCallback(
  query: URLSearchParams,
  pending: PendingConnect | null,
  now: number = Date.now(),
): CallbackResolution {
  const returnTo = pending?.returnTo && pending.returnTo.startsWith("/") && !pending.returnTo.startsWith("//") ? pending.returnTo : FALLBACK_RETURN;
  const state = query.get("state");
  const error = query.get("error");
  const code = query.get("code");
  if (!pending) return { kind: "invalid", reason: "no_pending", returnTo };
  if (!state || state !== pending.state) return { kind: "invalid", reason: state ? "state_mismatch" : "missing_params", returnTo };
  if (now - pending.startedAt > PENDING_TTL_MS) return { kind: "invalid", reason: "expired", returnTo };
  if (error) return { kind: "denied", returnTo };
  if (!code) return { kind: "invalid", reason: "missing_params", returnTo };
  return { kind: "exchange", provider: pending.provider, state, code, returnTo };
}

export function savePending(p: PendingConnect): void {
  try {
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify(p));
  } catch {
    /* storage blocked: callback will report no_pending */
  }
}

export function takePending(): PendingConnect | null {
  try {
    const raw = window.sessionStorage.getItem(PENDING_KEY);
    window.sessionStorage.removeItem(PENDING_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as PendingConnect;
    return typeof p?.provider === "string" && typeof p?.state === "string" ? p : null;
  } catch {
    return null;
  }
}
