import { NextResponse, type NextRequest } from "next/server";
import { backendUrl } from "@/lib/server/backend";

/**
 * Same-origin proxy for `/api/v1/*` so the browser never needs CORS and the backend
 * URL stays runtime-configurable (BACKEND_URL). Endpoints that issue or consume
 * refresh tokens are blocked here: they must go through `/api/session/*`, which keeps
 * the refresh token in an httpOnly cookie.
 */
export const dynamic = "force-dynamic";

const BLOCKED = new Set(["auth/login", "auth/mfa/verify", "auth/refresh", "auth/logout"]);
const FORWARD_REQUEST_HEADERS = [
  "authorization",
  "content-type",
  "accept",
  "accept-language",
  "x-merchant-id",
  "idempotency-key",
  "x-request-id",
  "user-agent",
];
const FORWARD_RESPONSE_HEADERS = ["content-type", "x-request-id", "idempotent-replayed", "retry-after"];

function envelope(status: number, code: string, message: string, requestId: string | null) {
  return NextResponse.json({ error: { code, message, details: {}, request_id: requestId } }, { status });
}

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const joined = path.map(encodeURIComponent).join("/");
  const requestId = req.headers.get("x-request-id");
  if (BLOCKED.has(path.join("/"))) {
    return envelope(404, "not_found", "Use /api/session/* for token endpoints", requestId);
  }

  const headers = new Headers();
  for (const name of FORWARD_REQUEST_HEADERS) {
    const v = req.headers.get(name);
    if (v) headers.set(name, v);
  }
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) headers.set("x-forwarded-for", fwd);

  const target = `${backendUrl()}/api/v1/${joined}${req.nextUrl.search}`;
  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    return envelope(503, "dependency_unavailable", "Backend unreachable", requestId);
  }

  const outHeaders = new Headers({ "Cache-Control": "no-store" });
  for (const name of FORWARD_RESPONSE_HEADERS) {
    const v = upstream.headers.get(name);
    if (v) outHeaders.set(name, v);
  }
  const body = upstream.status === 204 || upstream.status === 304 ? null : await upstream.arrayBuffer();
  return new NextResponse(body, { status: upstream.status, headers: outHeaders });
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT, proxy as DELETE };
