import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "./client";
import { createApi, unwrap } from "./endpoints";
import { ApiError } from "./errors";

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function errorBody(code: string, extra: Record<string, unknown> = {}) {
  return { error: { code, message: code, details: {}, request_id: "req-server", ...extra } };
}

function headersOf(init: RequestInit): Record<string, string> {
  return init.headers as Record<string, string>;
}

function setup(handler: Handler, overrides: Partial<ConstructorParameters<typeof ApiClient>[0]> = {}) {
  let counter = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => handler(String(input), init ?? {}));
  const client = new ApiClient({
    baseUrl: "http://api.test/api/v1/",
    fetch: fetchMock as unknown as typeof fetch,
    generateId: () => `id-${++counter}`,
    ...overrides,
  });
  return { client, api: createApi(client), fetchMock };
}

describe("ApiClient request basics", () => {
  it("joins base URL, drops empty query params and sends X-Request-ID", async () => {
    const { client, fetchMock } = setup(() => json(200, { ok: true }));
    await client.request("/audit-logs", { query: { action: "member.invited", cursor: undefined, actor_id: "" } });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("http://api.test/api/v1/audit-logs?action=member.invited");
    expect(headersOf(init!)["X-Request-ID"]).toBe("id-1");
  });

  it("adds bearer token and X-Merchant-Id for tenant endpoints", async () => {
    const { api, fetchMock } = setup(() => json(200, { items: [] }), {
      getAccessToken: () => "access-1",
      getMerchantId: () => "m-1",
    });
    await api.team.members();
    const h = headersOf(fetchMock.mock.calls[0]![1]!);
    expect(h.Authorization).toBe("Bearer access-1");
    expect(h["X-Merchant-Id"]).toBe("m-1");
  });

  it("refuses tenant calls without a merchant", async () => {
    const { api, fetchMock } = setup(() => json(200, {}));
    await expect(api.billing.subscription()).rejects.toMatchObject({ code: "no_merchant_selected" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("generates an Idempotency-Key for idem endpoints and reuses a supplied one", async () => {
    const { api, fetchMock } = setup(() => json(201, { merchant: { id: "m" } }));
    const body = { name: "Kathmandu Kurta", country: "NP" as const, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "ne" as const };
    await api.merchants.create(body);
    await api.merchants.create(body, { idempotencyKey: "stable-key-123" });
    const h1 = headersOf(fetchMock.mock.calls[0]![1]!);
    const h2 = headersOf(fetchMock.mock.calls[1]![1]!);
    expect(h1["Idempotency-Key"]).toMatch(/^id-/);
    expect(h1["Idempotency-Key"]).not.toBe(h1["X-Request-ID"]);
    expect(h2["Idempotency-Key"]).toBe("stable-key-123");
  });

  it("does not send Idempotency-Key on non-idem endpoints", async () => {
    const { api, fetchMock } = setup(() => json(200, { items: [] }), { getMerchantId: () => "m" });
    await api.team.members();
    expect(headersOf(fetchMock.mock.calls[0]![1]!)["Idempotency-Key"]).toBeUndefined();
  });

  it("returns undefined for 204", async () => {
    const { api } = setup(() => new Response(null, { status: 204 }));
    await expect(api.auth.revokeOtherSessions()).resolves.toBeUndefined();
  });

  it("reports idempotent replays", async () => {
    const { client } = setup(() => json(201, { id: "x" }, { "Idempotent-Replayed": "true", "X-Request-ID": "r-9" }));
    const res = await client.requestWithMeta("/merchants", { method: "POST", body: {}, idempotent: true });
    expect(res.replayed).toBe(true);
    expect(res.requestId).toBe("r-9");
  });
});

describe("ApiError parsing", () => {
  it("parses the error envelope", async () => {
    const { api } = setup(() =>
      json(402, errorBody("usage_limit_reached", { details: { resource: "team_members", limit: 3, used: 3, options: ["upgrade"] } })),
      { getMerchantId: () => "m" },
    );
    const err = await api.team.invite({ email: "sita@example.com", role: "staff" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 402, code: "usage_limit_reached", requestId: "req-server" });
    expect((err as ApiError).details.limit).toBe(3);
  });

  it("falls back for non-envelope bodies and keeps the request id", async () => {
    const { client } = setup(() => new Response("<html>bad gateway</html>", { status: 502, headers: { "X-Request-ID": "edge-1" } }));
    await expect(client.request("/me", { auth: false })).rejects.toMatchObject({
      status: 502,
      code: "dependency_unavailable",
      requestId: "edge-1",
    });
  });

  it("parses Retry-After on 429", async () => {
    const { client } = setup(() => json(429, errorBody("rate_limited"), { "Retry-After": "30" }));
    await expect(client.request("/auth/login", { method: "POST", auth: false })).rejects.toMatchObject({ retryAfter: 30 });
  });

  it("maps fetch failures to network_error", async () => {
    const { client } = setup(() => {
      throw new TypeError("Failed to fetch");
    });
    await expect(client.request("/me")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });

  it("extracts field errors from validation_error", () => {
    const e = new ApiError({
      status: 400,
      code: "validation_error",
      message: "bad",
      details: { fields: [{ loc: ["body", "password"], msg: "too short", type: "too_short" }] },
    });
    expect(e.fieldErrors()).toEqual({ password: "too_short" });
  });
});

describe("401 token_expired refresh", () => {
  it("refreshes once for concurrent expired requests (single flight) and retries each", async () => {
    let token = "old";
    const refresh = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 10));
      token = "new";
      return token;
    });
    const { client, fetchMock } = setup(
      (_url, init) => {
        const auth = headersOf(init).Authorization;
        return auth === "Bearer new" ? json(200, { ok: true }) : json(401, errorBody("token_expired"));
      },
      { getAccessToken: () => token, refreshAccessToken: refresh },
    );

    const results = await Promise.all([client.request("/a"), client.request("/b"), client.request("/c")]);
    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(6);
  });

  it("skips refreshing when another request already rotated the token", async () => {
    let token = "old";
    const refresh = vi.fn(async () => "never");
    const { client } = setup(
      (_url, init) => {
        if (headersOf(init).Authorization === "Bearer old") {
          token = "rotated-elsewhere";
          return json(401, errorBody("token_expired"));
        }
        return json(200, { ok: true });
      },
      { getAccessToken: () => token, refreshAccessToken: refresh },
    );
    await expect(client.request("/a")).resolves.toEqual({ ok: true });
    expect(refresh).not.toHaveBeenCalled();
  });

  it("keeps the same Idempotency-Key when retrying after refresh", async () => {
    let token = "old";
    const { client, fetchMock } = setup(
      (_url, init) => (headersOf(init).Authorization === "Bearer new" ? json(201, {}) : json(401, errorBody("token_expired"))),
      { getAccessToken: () => token, refreshAccessToken: async () => (token = "new") },
    );
    await client.request("/invitations", { method: "POST", body: {}, idempotent: true });
    const k1 = headersOf(fetchMock.mock.calls[0]![1]!)["Idempotency-Key"];
    const k2 = headersOf(fetchMock.mock.calls[1]![1]!)["Idempotency-Key"];
    expect(k1).toBeDefined();
    expect(k1).toBe(k2);
  });

  it("propagates the error and notifies when refresh fails, without looping", async () => {
    const onUnauthenticated = vi.fn();
    const { client, fetchMock } = setup(() => json(401, errorBody("token_expired")), {
      getAccessToken: () => "old",
      refreshAccessToken: async () => null,
      onUnauthenticated,
    });
    await expect(client.request("/me")).rejects.toMatchObject({ code: "token_expired" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onUnauthenticated).toHaveBeenCalledTimes(1);
  });

  it("retries at most once even if the retried request is also expired", async () => {
    const refresh = vi.fn(async () => "new");
    const { client, fetchMock } = setup(() => json(401, errorBody("token_expired")), {
      getAccessToken: () => "old",
      refreshAccessToken: refresh,
    });
    await expect(client.request("/me")).rejects.toMatchObject({ code: "token_expired" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("treats a throwing refresher as a failed refresh", async () => {
    const { client } = setup(() => json(401, errorBody("token_expired")), {
      getAccessToken: () => "old",
      refreshAccessToken: async () => {
        throw new Error("boom");
      },
    });
    await expect(client.request("/me")).rejects.toMatchObject({ code: "token_expired" });
  });

  it("does not refresh on other 401 codes", async () => {
    const refresh = vi.fn(async () => "new");
    const { client } = setup(() => json(401, errorBody("invalid_credentials")), {
      getAccessToken: () => "old",
      refreshAccessToken: refresh,
    });
    await expect(client.request("/auth/login", { method: "POST", auth: false })).rejects.toMatchObject({
      code: "invalid_credentials",
    });
    expect(refresh).not.toHaveBeenCalled();
  });
});

describe("unwrap", () => {
  it("handles wrapped and bare payloads", () => {
    expect(unwrap({ merchant: { id: "1" } }, "merchant")).toEqual({ id: "1" });
    expect(unwrap({ id: "1" } as unknown as Record<string, { id: string }>, "merchant")).toEqual({ id: "1" });
  });
});

describe("multipart uploads", () => {
  it("sends FormData untouched and lets the browser set the multipart boundary", async () => {
    const { api, fetchMock } = setup(() => json(202, { id: "imp1", status: "queued" }), { getMerchantId: () => "m1" });
    await api.catalog.uploadImport(new Blob(["title,price\nKurta,1250\n"], { type: "text/csv" }), "kurta.csv");
    const init = fetchMock.mock.calls[0]![1]!;
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeInstanceOf(Blob);
    expect(headersOf(init)["Content-Type"]).toBeUndefined();
    expect(headersOf(init)["X-Merchant-Id"]).toBe("m1");
  });

  it("sends version with product patches", async () => {
    const { api, fetchMock } = setup(() => json(200, {}), { getMerchantId: () => "m1" });
    await api.catalog.updateProduct("p1", 4, { title: "Dhaka topi" });
    expect(JSON.parse(String(fetchMock.mock.calls[0]![1]!.body))).toEqual({ version: 4, title: "Dhaka topi" });
  });
});

describe("signed uploads", () => {
  it("PUTs with only the ticket headers — never Authorization", async () => {
    const { putToSignedUrl } = await import("./upload");
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    await putToSignedUrl(
      { method: "PUT", url: "http://api.test/_dev/objects/m/1/original?exp=1&sig=x", headers: { "Content-Type": "image/jpeg" }, expires_at: "" },
      new Blob(["x"]),
      fetchMock as unknown as typeof fetch,
    );
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toContain("/_dev/objects/");
    expect(init.method).toBe("PUT");
    expect(init.headers).toEqual({ "Content-Type": "image/jpeg" });
    expect(init.credentials).toBe("omit");
  });

  it("maps storage failures to codes", async () => {
    const { putToSignedUrl } = await import("./upload");
    const t = { method: "PUT" as const, url: "u", headers: {}, expires_at: "" };
    await expect(putToSignedUrl(t, new Blob([]), (async () => new Response(null, { status: 403 })) as unknown as typeof fetch)).rejects.toMatchObject({ code: "upload_url_expired" });
    await expect(putToSignedUrl(t, new Blob([]), (async () => { throw new TypeError("cors"); }) as unknown as typeof fetch)).rejects.toMatchObject({ code: "upload_failed", status: 0 });
  });
});
