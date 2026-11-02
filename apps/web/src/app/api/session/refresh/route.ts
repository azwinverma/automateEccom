import { ApiError, isApiError } from "@commerce-os/api-client";
import type { NextRequest } from "next/server";
import { backendApi } from "@/lib/server/backend";
import { REFRESH_COOKIE } from "@/lib/session-constants";
import { assertSameOrigin, clearSessionCookies, errorResponse, forwardHeaders, sessionResponse } from "@/lib/server/session";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const blocked = assertSameOrigin(req);
  if (blocked) return blocked;
  const refreshToken = req.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    const res = errorResponse(new ApiError({ status: 401, code: "not_authenticated", message: "No session" }));
    clearSessionCookies(res);
    return res;
  }
  try {
    const pair = await backendApi().auth.refresh(refreshToken, forwardHeaders(req));
    return sessionResponse(pair); // rotated refresh token replaces the old cookie
  } catch (e) {
    const res = errorResponse(e);
    // Only drop the cookie when the backend says the session is gone; keep it on outages.
    if (isApiError(e) && e.status === 401) clearSessionCookies(res);
    return res;
  }
}
