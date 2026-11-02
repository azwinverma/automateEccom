import type { NextRequest } from "next/server";
import { backendApi } from "@/lib/server/backend";
import { assertSameOrigin, errorResponse, forwardHeaders, readJson, sessionResponse, str } from "@/lib/server/session";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const blocked = assertSameOrigin(req);
  if (blocked) return blocked;
  const body = await readJson(req);
  try {
    const pair = await backendApi().auth.mfaVerify(
      { mfa_token: str(body.mfa_token), code: str(body.code).replace(/\s+/g, "") },
      forwardHeaders(req),
    );
    return sessionResponse(pair);
  } catch (e) {
    return errorResponse(e);
  }
}
