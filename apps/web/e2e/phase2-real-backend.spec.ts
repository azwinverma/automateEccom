import { execFileSync } from "node:child_process";
import { createHmac } from "node:crypto";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 2 exit flow against the live API + worker: a customer messages the shop on a channel, the AI
 * Sales Agent answers from real stock and price, collects the details, the customer says YES, the
 * order appears with stock reserved, and the seller packs and ships it in the web app.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
const ROOT = API.replace(/\/api\/v1\/?$/, "");
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(120_000);

const PASSWORD = "Pokhara-Lakeside-2083!";
const SANDBOX_SECRET = "dev-sandbox-webhook-secret";

async function call(p: string, init: { method?: string; token?: string; merchant?: string; body?: unknown } = {}) {
  const res = await fetch(`${API}${p}`, {
    method: init.method ?? (init.body !== undefined ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}),
      ...(init.merchant ? { "X-Merchant-Id": init.merchant } : {}),
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    redirect: "manual",
  });
  const text = await res.text();
  return { status: res.status, json: text ? JSON.parse(text) : null };
}

test("customer message → AI → order → packed and shipped", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p2+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Sita Gurung" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Lakeside Kurta ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "growth"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });
  await call("/merchant", { ...H, method: "PATCH", body: { automation_mode: "smart" } });

  // Sandbox channel via the real OAuth shape.
  const start = await call("/channels/connect", { ...H, body: { provider: "sandbox_channel", redirect_uri: `${process.env.E2E_BASE_URL}/channels/callback` } });
  const consent = await fetch(start.json.authorize_url, { redirect: "manual" });
  const q = new URL(consent.headers.get("location")!).searchParams;
  const conn = (await call("/channels/oauth/callback", { ...H, body: { provider: "sandbox_channel", state: q.get("state"), code: q.get("code") } })).json;

  // A product with two sizes and real stock.
  const p = (
    await call("/catalog/products", {
      ...H,
      body: { title: "Dhaka Kurta", options: [{ name: "Size", values: ["M", "XL"] }], variants: ["M", "XL"].map((s) => ({ options: { Size: s }, price_minor: 245000, sku: `DHK-${s}-${stamp}` })) },
    })
  ).json;
  await call(`/catalog/products/${p.id}/status`, { ...H, body: { status: "active" } });
  for (const v of p.variants) await call(`/inventory/variants/${v.id}/receive`, { ...H, body: { quantity: v.options.Size === "XL" ? 2 : 5 } });

  let n = 0;
  const thread = `t-${stamp}`;
  const say = async (text: string) => {
    n += 1;
    const body = JSON.stringify({ id: `${thread}-e${n}`, type: "message.received", account_id: conn.external_account_id, data: { thread_id: thread, message_id: `${thread}-m${n}`, sender: { id: `psid-${stamp}`, name: "Bikash Rai" }, text } });
    const sig = createHmac("sha256", SANDBOX_SECRET).update(body).digest("hex");
    const r = await fetch(`${ROOT}/webhooks/sandbox_channel`, { method: "POST", body, headers: { "Content-Type": "application/json", "X-Sandbox-Signature": sig } });
    expect(r.status).toBe(200);
    // Wait for the worker: the AI's reply to this message is sent.
    await expect
      .poll(async () => {
        const convs = (await call("/conversations?status=all", H)).json.items;
        if (!convs.length) return 0;
        const msgs = (await call(`/conversations/${convs[0].id}/messages`, H)).json.items;
        return msgs.filter((x: { direction: string; status: string }) => x.direction === "out" && x.status === "sent").length;
      }, { timeout: 30_000 })
      .toBeGreaterThanOrEqual(n);
  };

  // The seller watches it in the web inbox.
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/inbox");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/inbox/);

  await say("Dhaka kurta XL cha? kati ho?");
  await page.getByTestId("conversations").getByRole("button", { name: /Bikash Rai/ }).click();
  const messages = page.getByTestId("messages");
  await expect(messages.getByText(/Rs 2,450/).first()).toBeVisible({ timeout: 15_000 });
  await expect(messages.getByText(/Looked up: .*price.*stock/).first()).toBeVisible();

  for (const text of ["XL 1 wota chahiyo", "9807654321", "Kaski", "Pokhara Metropolitan City ward 6", "Lakeside, near Fewa lake", "COD"]) await say(text);
  await expect(messages.getByText(/Please confirm your order/).first()).toBeVisible({ timeout: 15_000 });
  await say("YES");
  await expect(messages.getByText(/Order #1001 confirmed/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("order-draft")).toContainText("Order created");

  // The order is real: stock reserved, then packed and shipped by the seller.
  await page.getByTestId("order-draft").getByRole("link", { name: "View order" }).click();
  const detail = page.getByTestId("order-detail");
  await expect(detail.getByRole("heading", { level: 1 })).toContainText("#1001");
  await expect(detail.getByText("Pokhara Metropolitan City-6", { exact: false })).toBeVisible();
  await detail.getByRole("button", { name: "Mark packed" }).click();
  await expect(detail.getByRole("button", { name: "Mark shipped" })).toBeVisible();
  await detail.getByRole("button", { name: "Mark shipped" }).click();
  await expect(detail.getByRole("heading", { level: 1 })).toContainText("Shipped");
  const stock = (await call(`/catalog/products/${p.id}/stock`, H)).json.variants.find((v: { sku: string }) => v.sku.startsWith("DHK-XL"));
  expect(stock).toMatchObject({ on_hand: 1, reserved: 0, available: 1 });
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p2-order-${testInfo.project.name}.png`), fullPage: true });

  await page.goto(`/inbox?c=${(await call("/conversations?status=all", H)).json.items[0].id}`);
  if (process.env.E2E_SCREENSHOTS) {
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p2-inbox-${testInfo.project.name}.png`), fullPage: true });
  }
});
