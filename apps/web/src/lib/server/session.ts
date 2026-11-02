import { ApiError, isApiError, type TokenPair } from "@commerce-os/api-client";
import { NextResponse, type NextRequest } from "next/server";
import {
  REFRESH_COOKIE,
  REFRESH_COOKIE_PATH,
  REFRESH_MAX_AGE_SECONDS,
  SESSION_MARKER_COOKIE,
  type BrowserSession,
} from "../session-constants";

function secureCookies(): boolean {
  return process.env.SESSION_COOKIE_INSECURE !== "1";
}

export function setSessionCookies(res: NextResponse, refreshToken: string): void {
  const base = { httpOnly: true, secure: secureCookies(), sameSite: "lax" as const, maxAge: REFRESH_MAX_AGE_SECONDS };
  res.cookies.set(REFRESH_COOKIE, refreshToken, { ...base, path: REFRESH_COOKIE_PATH });
  res.cookies.set(SESSION_MARKER_COOKIE, "1", { ...base, path: "/" });
}

export function clearSessionCookies(res: NextResponse): void {
  const base = { httpOnly: true, secure: secureCookies(), sameSite: "lax" as const, maxAge: 0 };
  res.cookies.set(REFRESH_COOKIE, "", { ...base, path: REFRESH_COOKIE_PATH });
  res.cookies.set(SESSION_MARKER_COOKIE, "", { ...base, path: "/" });
}

export function toBrowserSession(pair: TokenPair): BrowserSession {
  return { access_token: pair.access_token, expires_in: pair.expires_in, session_id: pair.session_id };
}

export function sessionResponse(pair: TokenPair): NextResponse {
  const res = NextResponse.json(toBrowserSession(pair), { headers: { "Cache-Control": "no-store" } });
  setSessionCookies(res, pair.refresh_token);
  return res;
}

export function errorResponse(error: unknown): NextResponse {
  const e = isApiError(error)
    ? error
    : new ApiError({ status: 500, code: "unknown", message: "Unexpected error in session handler" });
  const status = e.status === 0 ? 503 : e.status;
  const code = e.status === 0 ? "dependency_unavailable" : e.code;
  const headers: Record<string, string> = { "Cache-Control": "no-store" };
  if (e.requestId) headers["X-Request-ID"] = e.requestId;
  if (e.retryAfter) headers["Retry-After"] = String(e.retryAfter);
  return NextResponse.json(
    { error: { code, message: e.message, details: e.details, request_id: e.requestId } },
    { status, headers },
  );
}

/** Reject cross-site POSTs (defence in depth on top of SameSite=Lax). */
export function assertSameOrigin(req: NextRequest): NextResponse | null {
  const origin = req.headers.get("origin");
  if (!origin) return null;
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  try {
    if (new URL(origin).host === host) return null;
  } catch {
    /* fall through */
  }
  return NextResponse.json(
    { error: { code: "permission_denied", message: "Cross-origin request rejected", details: {}, request_id: null } },
    { status: 403 },
  );
}

/** Headers forwarded to the backend so sessions record the real device and IP. */
export function forwardHeaders(req: NextRequest): Record<string, string> {
  const out: Record<string, string> = {};
  const ua = req.headers.get("user-agent");
  if (ua) out["User-Agent"] = ua;
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) out["X-Forwarded-For"] = fwd;
  const lang = req.headers.get("accept-language");
  if (lang) out["Accept-Language"] = lang;
  return out;
}

/** Short human device label from a User-Agent, e.g. "Chrome on Android". */
export function deviceName(ua: string | null): string {
  if (!ua) return "Web browser";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /OPR\//.test(ua)
      ? "Opera"
      : /Chrome\//.test(ua)
        ? "Chrome"
        : /Firefox\//.test(ua)
          ? "Firefox"
          : /Safari\//.test(ua)
            ? "Safari"
            : "Browser";
  const os = /Android/.test(ua)
    ? "Android"
    : /iPhone|iPad/.test(ua)
      ? "iOS"
      : /Mac OS X/.test(ua)
        ? "macOS"
        : /Windows/.test(ua)
          ? "Windows"
          : /Linux/.test(ua)
            ? "Linux"
            : "";
  return os ? `${browser} on ${os}` : browser;
}

export async function readJson(req: NextRequest): Promise<Record<string, unknown>> {
  try {
    const body: unknown = await req.json();
    return body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}
