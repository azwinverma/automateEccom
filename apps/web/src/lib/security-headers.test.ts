import { apiOrigin, contentSecurityPolicy, securityHeaders } from "./security-headers";

describe("security headers (QA-009)", () => {
  it("allows only self plus the API origin for network, images and media", () => {
    const csp = contentSecurityPolicy({ api: "https://api.nivaro.np", dev: false });
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("connect-src 'self' https://api.nivaro.np");
    expect(csp).toContain("img-src 'self' data: blob: https://api.nivaro.np");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).not.toContain("unsafe-eval");
    expect(contentSecurityPolicy({ api: "", dev: true })).toContain("'unsafe-eval'");
  });

  it("derives the API origin from PUBLIC_API_ORIGIN, else BACKEND_URL", () => {
    expect(apiOrigin({ PUBLIC_API_ORIGIN: "https://api.example.np/x" })).toBe("https://api.example.np");
    expect(apiOrigin({ BACKEND_URL: "http://localhost:8090/" })).toBe("http://localhost:8090");
    expect(apiOrigin({ BACKEND_URL: "not a url" })).toBe("");
  });

  it("sends HSTS only over HTTPS", () => {
    const https = securityHeaders({ headers: new Headers({ "x-forwarded-proto": "https" }), url: "http://x/" }, {});
    const http = securityHeaders({ headers: new Headers(), url: "http://localhost:3010/" }, {});
    expect(https["Strict-Transport-Security"]).toMatch(/max-age=\d+/);
    expect(http["Strict-Transport-Security"]).toBeUndefined();
  });
});
