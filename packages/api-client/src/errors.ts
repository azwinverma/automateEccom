import type { ErrorEnvelope } from "./types";

/** Codes the client produces itself (no server response to parse). */
export const CLIENT_ERROR_CODES = {
  network: "network_error",
  invalidResponse: "invalid_response",
  aborted: "aborted",
} as const;

export interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  details?: Record<string, unknown>;
  requestId?: string | null;
  retryAfter?: number | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;
  /** Seconds, from the `Retry-After` header on 429/503. */
  readonly retryAfter: number | null;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.details = init.details ?? {};
    this.requestId = init.requestId ?? null;
    this.retryAfter = init.retryAfter ?? null;
  }

  /** Field errors from a 400 `validation_error`, keyed by the last `loc` segment. */
  fieldErrors(): Record<string, string> {
    const fields = this.details.fields;
    const out: Record<string, string> = {};
    if (!Array.isArray(fields)) return out;
    for (const f of fields) {
      if (!f || typeof f !== "object") continue;
      const loc = (f as { loc?: unknown }).loc;
      const type = (f as { type?: unknown }).type;
      const msg = (f as { msg?: unknown }).msg;
      const key = Array.isArray(loc) ? String(loc[loc.length - 1]) : typeof loc === "string" ? loc : "";
      if (key && !(key in out)) out[key] = typeof type === "string" ? type : String(msg ?? "invalid");
    }
    return out;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

function isEnvelope(v: unknown): v is ErrorEnvelope {
  if (typeof v !== "object" || v === null) return false;
  const err = (v as { error?: unknown }).error;
  return typeof err === "object" && err !== null && typeof (err as { code?: unknown }).code === "string";
}

function parseRetryAfter(h: string | null): number | null {
  if (!h) return null;
  const n = Number(h);
  if (Number.isFinite(n)) return n;
  const d = Date.parse(h);
  return Number.isNaN(d) ? null : Math.max(0, Math.round((d - Date.now()) / 1000));
}

/** Build an ApiError from a non-2xx Response, tolerating non-envelope bodies. */
export async function errorFromResponse(res: Response, fallbackRequestId: string | null): Promise<ApiError> {
  const headerRequestId = res.headers.get("X-Request-ID");
  const retryAfter = parseRetryAfter(res.headers.get("Retry-After"));
  let body: unknown = null;
  try {
    const text = await res.text();
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (isEnvelope(body)) {
    const e = body.error;
    return new ApiError({
      status: res.status,
      code: e.code,
      message: e.message ?? e.code,
      details: e.details ?? {},
      requestId: e.request_id ?? headerRequestId ?? fallbackRequestId,
      retryAfter,
    });
  }
  return new ApiError({
    status: res.status,
    code: statusFallbackCode(res.status),
    message: `HTTP ${res.status}`,
    requestId: headerRequestId ?? fallbackRequestId,
    retryAfter,
  });
}

function statusFallbackCode(status: number): string {
  if (status === 401) return "not_authenticated";
  if (status === 403) return "permission_denied";
  if (status === 404) return "not_found";
  if (status === 429) return "rate_limited";
  if (status === 502 || status === 503 || status === 504) return "dependency_unavailable";
  return CLIENT_ERROR_CODES.invalidResponse;
}
