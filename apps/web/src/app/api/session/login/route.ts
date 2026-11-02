import { isMfaChallenge } from "@commerce-os/api-client";
import { NextResponse, type NextRequest } from "next/server";
import { backendApi } from "@/lib/server/backend";
import {
  assertSameOrigin,
  deviceName,
  errorResponse,
  forwardHeaders,
  readJson,
  sessionResponse,
  str,
} from "@/lib/server/session";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const blocked = assertSameOrigin(req);
  if (blocked) return blocked;
  const body = await readJson(req);
  try {
    const result = await backendApi().auth.login(
      { email: str(body.email), password: str(body.password), device_name: deviceName(req.headers.get("user-agent")) },
      forwardHeaders(req),
    );
    if (isMfaChallenge(result)) {
      return NextResponse.json(
        { mfa_required: true, mfa_token: result.mfa_token },
        { headers: { "Cache-Control": "no-store" } },
      );
    }
    return sessionResponse(result);
  } catch (e) {
    return errorResponse(e);
  }
}
