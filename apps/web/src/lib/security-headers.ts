/**
 * Content-Security-Policy and HSTS for page responses (QA-009). Built at request time because the
 * browser talks to the API origin directly for signed uploads and media, and that origin differs per
 * environment (PUBLIC_API_ORIGIN, else the BACKEND_URL origin).
 */
export function apiOrigin(env: Record<string, string | undefined> = process.env): string {
  const raw = env.PUBLIC_API_ORIGIN || env.BACKEND_URL || "http://localhost:8000";
  try {
    return new URL(raw).origin;
  } catch {
    return "";
  }
}

export function contentSecurityPolicy(opts: { api: string; dev: boolean }): string {
  const api = opts.api ? ` ${opts.api}` : "";
  return [
    "default-src 'self'",
    // Next.js inlines its bootstrap scripts; nonces would need a per-request render (follow-up).
    `script-src 'self' 'unsafe-inline'${opts.dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' data: blob:${api}`,
    `media-src 'self' blob:${api}`,
    `connect-src 'self'${api}`,
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}

export function securityHeaders(
  req: { headers: Headers; url: string },
  env: Record<string, string | undefined> = process.env,
): Record<string, string> {
  const h: Record<string, string> = {
    "Content-Security-Policy": contentSecurityPolicy({ api: apiOrigin(env), dev: env.NODE_ENV !== "production" }),
  };
  const proto = req.headers.get("x-forwarded-proto") ?? new URL(req.url).protocol.replace(":", "");
  // HSTS only over HTTPS (never on localhost http, which would break local development).
  if (proto === "https") h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains";
  return h;
}
