import { ApiError, CLIENT_ERROR_CODES, errorFromResponse } from "./errors";

export type QueryValue = string | number | boolean | null | undefined;

export interface ApiClientOptions {
  /** Base URL including the API prefix, e.g. `http://localhost:8000/api/v1` or `/api/v1`. */
  baseUrl: string;
  fetch?: typeof fetch;
  /** Current in-memory access token (never persisted). */
  getAccessToken?: () => string | null;
  /**
   * Obtain a fresh access token after a `401 token_expired`. Called at most once
   * concurrently (single flight). Resolve `null` when the session is gone.
   */
  refreshAccessToken?: () => Promise<string | null>;
  /** Merchant used for `X-Merchant-Id` on tenant endpoints. */
  getMerchantId?: () => string | null;
  /** Called when a request fails auth and refreshing did not help. */
  onUnauthenticated?: (error: ApiError) => void;
  /** ID generator for `X-Request-ID` / `Idempotency-Key`. Defaults to crypto.randomUUID. */
  generateId?: () => string;
  defaultHeaders?: Record<string, string>;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  query?: Record<string, QueryValue>;
  body?: unknown;
  /** Send `X-Merchant-Id`. Throws `no_merchant_selected` if none is available. */
  tenant?: boolean;
  /** Override the merchant for this call. */
  merchantId?: string;
  /**
   * Mark as an *(idem)* endpoint. `true` generates a fresh key; a string reuses
   * that key (pass the same key when retrying the same logical submission).
   */
  idempotent?: boolean | string;
  /** Attach the bearer token (default true). */
  auth?: boolean;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  requestId: string | null;
  replayed: boolean;
}

function defaultId(): string {
  return globalThis.crypto.randomUUID();
}

export class ApiClient {
  private readonly opts: ApiClientOptions;
  private readonly fetchImpl: typeof fetch;
  private refreshInFlight: Promise<string | null> | null = null;

  constructor(opts: ApiClientOptions) {
    this.opts = opts;
    this.fetchImpl = opts.fetch ?? ((...args: Parameters<typeof fetch>) => globalThis.fetch(...args));
  }

  newId(): string {
    return (this.opts.generateId ?? defaultId)();
  }

  /** Single-flight refresh: concurrent callers share one refresh promise. */
  refresh(): Promise<string | null> {
    const refresher = this.opts.refreshAccessToken;
    if (!refresher) return Promise.resolve(null);
    if (!this.refreshInFlight) {
      this.refreshInFlight = refresher()
        .catch(() => null)
        .finally(() => {
          this.refreshInFlight = null;
        });
    }
    return this.refreshInFlight;
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return (await this.requestWithMeta<T>(path, options)).data;
  }

  async requestWithMeta<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    const idempotencyKey =
      typeof options.idempotent === "string" ? options.idempotent : options.idempotent ? this.newId() : null;
    const useAuth = options.auth !== false;

    let token = useAuth ? (this.opts.getAccessToken?.() ?? null) : null;
    let res = await this.send(path, options, token, idempotencyKey);

    if (res.ok) return this.parse<T>(res.response, res.requestId);

    let error = await errorFromResponse(res.response, res.requestId);
    if (useAuth && error.status === 401 && error.code === "token_expired") {
      // Another request may already have refreshed while this one was in flight.
      const current = this.opts.getAccessToken?.() ?? null;
      const fresh = current && current !== token ? current : await this.refresh();
      if (fresh) {
        token = fresh;
        res = await this.send(path, options, token, idempotencyKey);
        if (res.ok) return this.parse<T>(res.response, res.requestId);
        error = await errorFromResponse(res.response, res.requestId);
      }
    }
    if (useAuth && error.status === 401) this.opts.onUnauthenticated?.(error);
    throw error;
  }

  private buildUrl(path: string, query?: Record<string, QueryValue>): string {
    const base = this.opts.baseUrl.replace(/\/+$/, "");
    const p = path.startsWith("/") ? path : `/${path}`;
    let url = `${base}${p}`;
    if (query) {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(query)) {
        if (v === undefined || v === null || v === "") continue;
        params.set(k, String(v));
      }
      const qs = params.toString();
      if (qs) url += `?${qs}`;
    }
    return url;
  }

  private async send(
    path: string,
    options: RequestOptions,
    token: string | null,
    idempotencyKey: string | null,
  ): Promise<{ ok: boolean; response: Response; requestId: string }> {
    const requestId = this.newId();
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...this.opts.defaultHeaders,
      ...options.headers,
      "X-Request-ID": requestId,
    };
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Bearer ${token}`;
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    if (options.tenant) {
      const merchantId = options.merchantId ?? this.opts.getMerchantId?.() ?? null;
      if (!merchantId) {
        throw new ApiError({ status: 0, code: "no_merchant_selected", message: "No merchant selected", requestId });
      }
      headers["X-Merchant-Id"] = merchantId;
    }

    let response: Response;
    try {
      response = await this.fetchImpl(this.buildUrl(path, options.query), {
        method: options.method ?? "GET",
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal,
        credentials: "same-origin",
      });
    } catch (e) {
      const aborted = e instanceof Error && e.name === "AbortError";
      throw new ApiError({
        status: 0,
        code: aborted ? CLIENT_ERROR_CODES.aborted : CLIENT_ERROR_CODES.network,
        message: e instanceof Error ? e.message : "Network error",
        requestId,
      });
    }
    return { ok: response.ok, response, requestId };
  }

  private async parse<T>(response: Response, sentRequestId: string): Promise<ApiResponse<T>> {
    const requestId = response.headers.get("X-Request-ID") ?? sentRequestId;
    const replayed = response.headers.get("Idempotent-Replayed") === "true";
    if (response.status === 204) {
      return { data: undefined as T, status: response.status, requestId, replayed };
    }
    const text = await response.text();
    if (!text) return { data: undefined as T, status: response.status, requestId, replayed };
    try {
      return { data: JSON.parse(text) as T, status: response.status, requestId, replayed };
    } catch {
      throw new ApiError({
        status: response.status,
        code: CLIENT_ERROR_CODES.invalidResponse,
        message: "Response was not valid JSON",
        requestId,
      });
    }
  }
}
