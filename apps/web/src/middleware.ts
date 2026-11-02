import { NextResponse, type NextRequest } from "next/server";
import { SESSION_MARKER_COOKIE } from "@/lib/session-constants";

const PUBLIC_PREFIXES = ["/login", "/register", "/dev"];

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }
  if (!req.cookies.get(SESSION_MARKER_COOKIE)?.value) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    if (pathname !== "/") url.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Pages only: skip API routes, Next internals and static files.
  matcher: ["/((?!api/|_next/|favicon.ico|icon.svg|robots.txt|.*\\.(?:svg|png|jpg|jpeg|webp|ico|txt)$).*)"],
};
