import { ApiError, type Api, type ExceptionRecord, type MediaAsset } from "@commerce-os/api-client";
import { describe, expect, it, vi } from "vitest";
import { connectFlow, normalizeStoreUrl, validateKeys } from "./channels/connect";
import { PENDING_TTL_MS, resolveCallback, stateFromAuthorizeUrl, type PendingConnect } from "./channels/oauth";
import { addMonths, dayKey, monthGrid, offsetMinutes, startOfWeek, timeOf, utcRange, weekDays, zonedToUtcIso } from "./content/calendar";
import { exceptionSummaryKey, exceptionTarget } from "./exceptions";
import { initialUpload, precheckPhoto, runUpload, uploadReducer, type UploadEvent } from "./media/upload";

/* ---------- calendar (Asia/Kathmandu, UTC+5:45) ---------- */
describe("calendar date math", () => {
  it("knows Kathmandu is UTC+5:45", () => {
    expect(offsetMinutes(new Date("2026-11-02T00:00:00Z"))).toBe(345);
  });
  it("puts late-UTC instants on the next Kathmandu day", () => {
    expect(dayKey("2026-11-02T18:14:00Z")).toBe("2026-11-02"); // 23:59 NPT
    expect(dayKey("2026-11-02T18:15:00Z")).toBe("2026-11-03"); // 00:00 NPT
    expect(timeOf("2026-11-02T18:20:00Z")).toBe("00:05");
  });
  it("converts Kathmandu wall time to UTC for scheduling", () => {
    expect(zonedToUtcIso("2026-11-03", "09:30")).toBe("2026-11-03T03:45:00.000Z");
    expect(zonedToUtcIso("2026-11-03", "00:00")).toBe("2026-11-02T18:15:00.000Z");
    expect(zonedToUtcIso("2026-11-03", "09:30", "Asia/Kolkata")).toBe("2026-11-03T04:00:00.000Z");
  });
  it("builds Sunday-first weeks and 6-week month grids", () => {
    expect(startOfWeek("2026-11-04")).toBe("2026-11-01"); // Wednesday → Sunday
    expect(weekDays("2026-11-04")).toHaveLength(7);
    const grid = monthGrid("2026-11-15");
    expect(grid).toHaveLength(42);
    expect(grid[0]).toBe("2026-11-01"); // 1 Nov 2026 is a Sunday
    expect(monthGrid("2026-12-10")[0]).toBe("2026-11-29");
    expect(addMonths("2026-12-15", 1)).toBe("2027-01-01");
  });
  it("asks the API for the UTC range covering whole Kathmandu days", () => {
    expect(utcRange(weekDays("2026-11-04"))).toEqual({ from: "2026-10-31T18:15:00.000Z", to: "2026-11-07T18:15:00.000Z" });
  });
});

/* ---------- OAuth callback ---------- */
describe("OAuth callback handling", () => {
  const pending: PendingConnect = { provider: "sandbox_channel", state: "s".repeat(32), reconnectId: null, returnTo: "/settings/channels", startedAt: 1_000 };
  const q = (s: string) => new URLSearchParams(s);

  it("exchanges a matching code", () => {
    expect(resolveCallback(q(`code=abc&state=${pending.state}`), pending, 2_000)).toEqual({
      kind: "exchange",
      provider: "sandbox_channel",
      state: pending.state,
      code: "abc",
      returnTo: "/settings/channels",
    });
  });
  it("reports a denied consent", () => {
    expect(resolveCallback(q(`error=access_denied&state=${pending.state}`), pending, 2_000).kind).toBe("denied");
  });
  it("rejects mismatched, missing or stale state and absent pending", () => {
    expect(resolveCallback(q("code=abc&state=other"), pending, 2_000)).toMatchObject({ kind: "invalid", reason: "state_mismatch" });
    expect(resolveCallback(q("code=abc"), pending, 2_000)).toMatchObject({ kind: "invalid", reason: "missing_params" });
    expect(resolveCallback(q(`state=${pending.state}`), pending, 2_000)).toMatchObject({ kind: "invalid", reason: "missing_params" });
    expect(resolveCallback(q(`code=abc&state=${pending.state}`), pending, 1_000 + PENDING_TTL_MS + 1)).toMatchObject({ reason: "expired" });
    expect(resolveCallback(q(`code=abc&state=${pending.state}`), null)).toMatchObject({ kind: "invalid", reason: "no_pending" });
  });
  it("never returns to an off-site URL", () => {
    expect(resolveCallback(q(`code=a&state=${pending.state}`), { ...pending, returnTo: "//evil.example" }, 2_000).returnTo).toBe("/settings/channels");
  });
  it("reads state from the authorize URL", () => {
    expect(stateFromAuthorizeUrl("http://api/_dev/channels/sandbox/authorize?state=xyz&redirect_uri=r")).toBe("xyz");
    expect(stateFromAuthorizeUrl("not a url")).toBeNull();
  });
});

/* ---------- WooCommerce keys ---------- */
describe("API-key connect", () => {
  it("picks the flow by provider code", () => {
    expect(connectFlow("woocommerce")).toBe("keys");
    expect(connectFlow("sandbox_channel")).toBe("oauth");
  });
  it("validates store URL and keys", () => {
    expect(validateKeys({ store_url: "", consumer_key: "", consumer_secret: "" })).toEqual({
      store_url: "required",
      consumer_key: "required",
      consumer_secret: "required",
    });
    expect(validateKeys({ store_url: "http://shop.np", consumer_key: "ck_1234567890", consumer_secret: "cs_123" })).toEqual({
      store_url: "https_required",
      consumer_secret: "too_short",
    });
    expect(validateKeys({ store_url: "https://localhost", consumer_key: "ck_1234567890", consumer_secret: "cs_1234567890" })).toEqual({
      store_url: "invalid_url",
    });
    expect(validateKeys({ store_url: "https://thamelthreads.com.np", consumer_key: "ck_1234567890", consumer_secret: "cs_1234567890" })).toEqual({});
    expect(normalizeStoreUrl(" https://shop.np/ ")).toBe("https://shop.np");
  });
});

/* ---------- exception routing ---------- */
describe("exception action routing", () => {
  const ex = (over: Partial<ExceptionRecord>): ExceptionRecord => ({
    id: "x",
    type: "publish_failed",
    severity: "high",
    resource: { type: "product", id: "p1" },
    occurred_at: null,
    action: "retry_publish",
    details: {},
    ...over,
  });
  it.each([
    [{ action: "reconnect", type: "channel_expired", resource: { type: "channel_connection", id: "c1" } }, { kind: "link", href: "/settings/channels?reconnect=c1" }],
    [{ action: "reconnect", details: { connection_id: "c2" } }, { kind: "link", href: "/settings/channels?reconnect=c2" }],
    [{ action: "retry_publish", details: { connection_id: "c1" } }, { kind: "command", command: "retry_publish" }],
    [{ action: "retry_publish" }, { kind: "link", href: "/products/p1#channels" }],
    [{ action: "reschedule", resource: { type: "content_post", id: "post1" } }, { kind: "link", href: "/content?post=post1" }],
    [{ action: "review_post", resource: { type: "content_post", id: "post1" } }, { kind: "link", href: "/content?post=post1" }],
    [{ action: "review_draft", resource: { type: "studio_job", id: "j1" } }, { kind: "link", href: "/products/studio/j1" }],
    [{ action: "retry_draft", resource: { type: "studio_job", id: "j1" } }, { kind: "command", command: "retry_draft" }],
    [{ action: "confirm_attributes" }, { kind: "link", href: "/products/p1#attributes" }],
    [{ action: "dismiss", resource: { type: "media", id: "m1" } }, { kind: "command", command: "remove_file" }],
    [{ action: "resolve_drift", type: "listing_drift" }, { kind: "link", href: "/products/p1#channels", label: "resolve_drift" }],
    [{ action: "view_plan", type: "usage_limit", resource: { type: "plan_resource", id: "ai_text_generations" } }, { kind: "link", href: "/settings/plan" }],
    [{ action: "reply", type: "customer_escalation", resource: { type: "conversation", id: "cv1" } }, { kind: "link", href: "/inbox?c=cv1" }],
    [{ action: "check_payment", type: "payment_mismatch", resource: { type: "order", id: "o1" } }, { kind: "link", href: "/orders/o1", label: "check_payment" }],
    [{ action: "fix_stock", type: "inventory_mismatch", resource: { type: "order", id: "o2" } }, { kind: "link", href: "/orders/o2" }],
    [{ action: "something_new" }, { kind: "none" }],
  ] as [Partial<ExceptionRecord>, object][])("%o", (over, expected) => {
    expect(exceptionTarget(ex(over))).toMatchObject(expected);
  });
  it("summarises from type, resource and safe details", () => {
    expect(exceptionSummaryKey(ex({ type: "channel_expired", resource: { type: "channel_connection", id: "c" }, details: { name: "Thamel FB" } }))).toEqual({
      key: "channelExpired",
      vars: { name: "Thamel FB" },
    });
    expect(exceptionSummaryKey(ex({ type: "low_confidence_ai", resource: { type: "content_post", id: "p" }, details: { issues: 2 } }))).toEqual({
      key: "postNeedsApproval",
      vars: { count: 2 },
    });
    expect(exceptionSummaryKey(ex({ type: "listing_drift", details: { product_title: "Pashmina", name: "Thamel Woo" } }))).toEqual({
      key: "listingDrift",
      vars: { name: "Pashmina", channel: "Thamel Woo" },
    });
    expect(exceptionSummaryKey(ex({ type: "usage_limit", details: { resource: "ai_text_generations", used: 270, limit: 300, level: 85 } }))).toEqual({
      key: "usageLimitNear",
      vars: { resource: "ai_text_generations", used: 270, limit: 300 },
    });
    expect(exceptionSummaryKey(ex({ type: "usage_limit", details: { resource: "auto_reels", used: 10, limit: 10, level: 100 } })).key).toBe("usageLimitReached");
    expect(exceptionSummaryKey(ex({ type: "customer_escalation", resource: { type: "conversation", id: "c" }, details: { name: "Bikash", reason: "complaint" } }))).toEqual({
      key: "escalation",
      vars: { name: "Bikash", reason: "complaint" },
    });
    expect(exceptionSummaryKey(ex({ type: "payment_mismatch", resource: { type: "order", id: "o" }, details: { number: 1007, reason: "payment_mismatch" } }))).toEqual({
      key: "orderReview",
      vars: { number: 1007, reason: "payment_mismatch" },
    });
    expect(exceptionSummaryKey(ex({ type: "mystery" })).key).toBe("generic");
  });
});

/* ---------- upload state machine ---------- */
describe("photo upload state machine", () => {
  const asset = (status: MediaAsset["status"], over: Partial<MediaAsset> = {}): MediaAsset => ({
    id: "a1",
    status,
    kind: "image",
    purpose: "product",
    file_name: "kurta.jpg",
    width: 1200,
    height: 1600,
    size_bytes: 1000,
    quality_score: 0.9,
    quality_flags: [],
    stripped_location_metadata: true,
    scan_status: "clean",
    rejection_reason: null,
    source: "upload",
    created_at: "",
    derivatives: {},
    ...over,
  });

  it("ignores impossible transitions and stays terminal", () => {
    const events: UploadEvent[] = [{ type: "uploaded" }, { type: "request" }, { type: "ticket", assetId: "a1" }];
    const s = events.reduce(uploadReducer, initialUpload);
    expect(s.phase).toBe("uploading");
    const failed = uploadReducer(s, { type: "error", error: new Error("x") });
    expect(uploadReducer(failed, { type: "asset", asset: asset("ready") }).phase).toBe("failed");
  });

  it("pre-checks type and size like the server", () => {
    expect(precheckPhoto({ type: "image/gif", size: 10 })).toBe("unsupported_media_type");
    expect(precheckPhoto({ type: "image/jpeg", size: 21 * 1024 * 1024 })).toBe("file_too_large");
    expect(precheckPhoto({ type: "image/heic", size: 10 })).toBeNull();
  });

  function api(states: MediaAsset[]) {
    return {
      media: {
        createUpload: vi.fn(async () => ({ asset_id: "a1", upload: { method: "PUT", url: "http://api/_dev/objects/k?sig=1", headers: { "Content-Type": "image/jpeg" }, expires_at: "" } })),
        complete: vi.fn(async () => asset("processing")),
        get: vi.fn(async () => states.shift() ?? asset("ready")),
      },
    } as unknown as Api & { media: Record<string, ReturnType<typeof vi.fn>> };
  }
  const file = new File(["x"], "kurta.jpg", { type: "image/jpeg" });
  const sleep = async () => {};

  it("runs request → PUT (no auth) → complete → poll → ready", async () => {
    const a = api([asset("processing"), asset("ready", { quality_flags: ["too_dark"] })]);
    const fetchImpl = vi.fn(async () => new Response(null, { status: 200 }));
    const phases: string[] = [];
    let s = initialUpload;
    const result = await runUpload(a, file, "kurta.jpg", (e) => phases.push((s = uploadReducer(s, e)).phase), { fetchImpl: fetchImpl as unknown as typeof fetch, sleep });
    expect(result.phase).toBe("ready");
    expect(result.asset?.quality_flags).toEqual(["too_dark"]);
    expect(phases).toEqual(["requesting", "uploading", "completing", "processing", "processing", "ready"]);
    const init = (fetchImpl.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.headers).toEqual({ "Content-Type": "image/jpeg" });
    expect(JSON.stringify(init.headers)).not.toMatch(/authorization/i);
  });

  it("ends rejected with the server's reason", async () => {
    const a = api([asset("rejected", { rejection_reason: "not_an_image" })]);
    const r = await runUpload(a, file, "kurta.jpg", () => {}, { fetchImpl: (async () => new Response(null)) as unknown as typeof fetch, sleep });
    expect(r.phase).toBe("rejected");
    expect(r.asset?.rejection_reason).toBe("not_an_image");
  });

  it("fails cleanly when the storage PUT fails, without completing", async () => {
    const a = api([]);
    const r = await runUpload(a, file, "kurta.jpg", () => {}, { fetchImpl: (async () => new Response(null, { status: 403 })) as unknown as typeof fetch, sleep });
    expect(r.phase).toBe("failed");
    expect(r.error).toBeInstanceOf(ApiError);
    expect((r.error as ApiError).code).toBe("upload_url_expired");
    expect(a.media.complete).not.toHaveBeenCalled();
  });

  it("times out if processing never finishes", async () => {
    const a = api(Array.from({ length: 10 }, () => asset("processing")));
    const r = await runUpload(a, file, "kurta.jpg", () => {}, { fetchImpl: (async () => new Response(null)) as unknown as typeof fetch, sleep, maxPolls: 3 });
    expect(r.phase).toBe("failed");
    expect((r.error as ApiError).code).toBe("processing_timeout");
  });
});

/* ---------- content workflow ---------- */
import { canEditPost, editResetsApproval, isUnscheduledWork, postActions } from "./content/actions";
describe("content post actions", () => {
  const all = { write: true, approve: true, publish: true };
  it("mirrors the backend workflow", () => {
    expect(postActions("draft", all)).toEqual(["submit", "cancel"]);
    expect(postActions("pending_approval", all)).toEqual(["approve", "reject", "cancel"]);
    expect(postActions("approved", all)).toEqual(["schedule", "publishNow", "cancel"]);
    expect(postActions("scheduled", all)).toEqual(["unschedule", "cancel"]);
    expect(postActions("failed", all)).toEqual(["schedule", "publishNow", "cancel"]);
    expect(postActions("published", all)).toEqual([]);
    expect(postActions("cancelled", all)).toEqual([]);
  });
  it("hides approval from staff without content.approve", () => {
    expect(postActions("pending_approval", { write: true, approve: false, publish: false })).toEqual(["cancel"]);
  });
  it("knows what can be edited and when edits reset approval", () => {
    expect(canEditPost("approved")).toBe(true);
    expect(canEditPost("scheduled")).toBe(false);
    expect(editResetsApproval("approved")).toBe(true);
    expect(editResetsApproval("draft")).toBe(false);
    expect(isUnscheduledWork({ status: "draft", scheduled_at: null })).toBe(true);
    expect(isUnscheduledWork({ status: "scheduled", scheduled_at: "2026-11-03T03:45:00Z" })).toBe(false);
  });
});
