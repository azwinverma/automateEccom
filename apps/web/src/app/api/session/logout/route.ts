import { NextResponse, type NextRequest } from "next/server";
import { backendApi } from "@/lib/server/backend";
import { REFRESH_COOKIE } from "@/lib/session-constants";
import { assertSameOrigin, clearSessionCookies, forwardHeaders } from "@/lib/server/session";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const blocked = assertSameOrigin(req);
  if (blocked) return blocked;
  const refreshToken = req.cookies.get(REFRESH_COOKIE)?.value;
  if (refreshToken) {
    try {
      await backendApi().auth.logout(refreshToken, forwardHeaders(req));
    } catch {
      // Best effort: the cookie is cleared regardless so this browser is signed out.
    }
  }
  const res = new NextResponse(null, { status: 204 });
  clearSessionCookies(res);
  return res;
}
