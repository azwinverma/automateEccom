// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { POST as login } from "./login/route";
import { POST as refresh } from "./refresh/route";
import { POST as logout } from "./logout/route";
import { GET as proxyGet } from "../v1/[...path]/route";

const pair = { access_token: "acc", refresh_token: "ref-secret", token_type: "bearer", expires_in: 900, session_id: "s1" };

function mockBackend(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(body === null ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

function req(path: string, init: { body?: unknown; cookie?: string; origin?: string } = {}) {
  const headers = new Headers({ "content-type": "application/json", host: "app.test" });
  if (init.cookie) headers.set("cookie", init.cookie);
  if (init.origin) headers.set("origin", init.origin);
  return new NextRequest(`http://app.test${path}`, {
    method: "POST",
    headers,
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("BFF session routes", () => {
  it("login sets an httpOnly Secure SameSite=Lax refresh cookie and never returns the refresh token", async () => {
    const backend = mockBackend(200, pair);
    const res = await login(req("/api/session/login", { body: { email: "a@b.np", password: "x" } }));
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json).toEqual({ access_token: "acc", expires_in: 900, session_id: "s1" });
    expect(JSON.stringify(json)).not.toContain("ref-secret");
    const setCookie = res.headers.getSetCookie().join("\n");
    expect(setCookie).toMatch(/cos_rt=ref-secret;[^\n]*Path=\/api\/session/);
    expect(setCookie).toMatch(/cos_rt=[^\n]*HttpOnly/i);
    expect(setCookie).toMatch(/cos_rt=[^\n]*Secure/i);
    expect(setCookie).toMatch(/cos_rt=[^\n]*SameSite=lax/i);
    expect(setCookie).toMatch(/cos_auth=1;[^\n]*Path=\//);
    expect(backend).toHaveBeenCalledWith("http://localhost:8000/api/v1/auth/login", expect.anything());
  });

  it("login passes through an MFA challenge without setting cookies", async () => {
    mockBackend(200, { mfa_required: true, mfa_token: "mfa-1" });
    const res = await login(req("/api/session/login", { body: { email: "a@b.np", password: "x" } }));
    expect(await res.json()).toEqual({ mfa_required: true, mfa_token: "mfa-1" });
    expect(res.headers.getSetCookie()).toHaveLength(0);
  });

  it("login relays the backend error envelope", async () => {
    mockBackend(401, { error: { code: "invalid_credentials", message: "nope", details: {}, request_id: "r1" } });
    const res = await login(req("/api/session/login", { body: { email: "a@b.np", password: "x" } }));
    expect(res.status).toBe(401);
    expect((await res.json()).error).toMatchObject({ code: "invalid_credentials", request_id: "r1" });
  });

  it("rejects cross-origin posts", async () => {
    mockBackend(200, pair);
    const res = await login(req("/api/session/login", { body: {}, origin: "https://evil.example" }));
    expect(res.status).toBe(403);
  });

  it("refresh without a cookie is 401 not_authenticated", async () => {
    const backend = mockBackend(200, pair);
    const res = await refresh(req("/api/session/refresh"));
    expect(res.status).toBe(401);
    expect((await res.json()).error.code).toBe("not_authenticated");
    expect(backend).not.toHaveBeenCalled();
  });

  it("refresh rotates the cookie", async () => {
    mockBackend(200, { ...pair, refresh_token: "ref-2" });
    const res = await refresh(req("/api/session/refresh", { cookie: "cos_rt=ref-1" }));
    expect(res.status).toBe(200);
    expect(res.headers.getSetCookie().join("\n")).toContain("cos_rt=ref-2");
  });

  it("refresh clears cookies when the backend rejects the session", async () => {
    mockBackend(401, { error: { code: "refresh_token_reused", message: "", details: {}, request_id: null } });
    const res = await refresh(req("/api/session/refresh", { cookie: "cos_rt=old" }));
    expect(res.status).toBe(401);
    expect(res.headers.getSetCookie().join("\n")).toMatch(/cos_rt=;/);
  });

  it("refresh keeps cookies during a backend outage", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("ECONNREFUSED"))));
    const res = await refresh(req("/api/session/refresh", { cookie: "cos_rt=keep" }));
    expect(res.status).toBe(503);
    expect(res.headers.getSetCookie()).toHaveLength(0);
  });

  it("logout clears cookies even if the backend fails", async () => {
    mockBackend(500, null);
    const res = await logout(req("/api/session/logout", { cookie: "cos_rt=x" }));
    expect(res.status).toBe(204);
    expect(res.headers.getSetCookie().join("\n")).toMatch(/cos_auth=;/);
  });
});

describe("API proxy", () => {
  it("blocks token endpoints so refresh tokens never reach browser JS", async () => {
    const backend = mockBackend(200, pair);
    const res = await proxyGet(new NextRequest("http://app.test/api/v1/auth/refresh"), {
      params: Promise.resolve({ path: ["auth", "refresh"] }),
    });
    expect(res.status).toBe(404);
    expect(backend).not.toHaveBeenCalled();
  });

  it("forwards tenant and auth headers", async () => {
    const backend = mockBackend(200, { items: [] });
    const r = new NextRequest("http://app.test/api/v1/members?limit=5", {
      headers: { authorization: "Bearer a", "x-merchant-id": "m1", "x-request-id": "rq", cookie: "cos_auth=1" },
    });
    const res = await proxyGet(r, { params: Promise.resolve({ path: ["members"] }) });
    expect(res.status).toBe(200);
    const [url, init] = backend.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/members?limit=5");
    const h = new Headers(init.headers);
    expect(h.get("authorization")).toBe("Bearer a");
    expect(h.get("x-merchant-id")).toBe("m1");
    expect(h.get("cookie")).toBeNull();
  });
});
