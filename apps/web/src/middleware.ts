import { NextResponse, type NextRequest } from "next/server";
import { securityHeaders } from "@/lib/security-headers";
import { SESSION_MARKER_COOKIE } from "@/lib/session-constants";

// Email-link pages must open signed out (QA-001, QA-008).
const PUBLIC_PREFIXES = ["/login", "/register", "/forgot-password", "/reset-password", "/verify-email", "/invite", "/dev"];

function withSecurityHeaders(req: NextRequest, res: NextResponse): NextResponse {
  for (const [k, v] of Object.entries(securityHeaders(req))) res.headers.set(k, v);
  return res;
}

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  // "/" is the public website; the app lives under /home and the other section routes.
  if (pathname === "/" || PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return withSecurityHeaders(req, NextResponse.next());
  }
  if (!req.cookies.get(SESSION_MARKER_COOKIE)?.value) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }
  return withSecurityHeaders(req, NextResponse.next());
}

export const config = {
  // Pages only: skip API routes, Next internals and static files.
  matcher: ["/((?!api/|_next/|favicon.ico|icon.svg|manifest.webmanifest|robots.txt|.*\\.(?:svg|png|jpg|jpeg|webp|ico|txt)$).*)"],
};
