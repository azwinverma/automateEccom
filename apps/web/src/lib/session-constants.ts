/** httpOnly refresh-token cookie, scoped to the BFF session routes only. */
export const REFRESH_COOKIE = "cos_rt";
/** httpOnly marker cookie (no secret) so middleware on page routes knows a session exists. */
export const SESSION_MARKER_COOKIE = "cos_auth";
export const REFRESH_COOKIE_PATH = "/api/session";
export const REFRESH_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

/** What the BFF returns to the browser — never the refresh token. */
export interface BrowserSession {
  access_token: string;
  expires_in: number;
  session_id: string;
}
export interface BrowserMfaChallenge {
  mfa_required: true;
  mfa_token: string;
}
