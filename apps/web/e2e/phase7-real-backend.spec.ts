import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 7 against the live API + worker:
 * - the seller connects the sandbox channel and a post is published by the worker;
 * - the seller types in the post's results from the app's insights → shown as "You typed it";
 * - What sells shows the learning state with how many posts are measured;
 * - a test (experiment) is started and listed as collecting posts.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(180_000);

const PASSWORD = "Bhaktapur-Reels-2083!";

async function call(p: string, init: { method?: string; token?: string; merchant?: string; body?: unknown } = {}) {
  const res = await fetch(`${API}${p}`, {
    method: init.method ?? (init.body !== undefined ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}),
      ...(init.merchant ? { "X-Merchant-Id": init.merchant } : {}),
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  const text = await res.text();
  return { status: res.status, json: text ? JSON.parse(text) : null };
}

test("published post → typed-in results → What sells learning → test started", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p7+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Anita Shakya" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Shakya Crafts ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "pro"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/settings/channels");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/settings/channels");

  // 1. Connect the sandbox channel through the real OAuth round-trip.
  await page.getByTestId("providers").getByRole("button", { name: /^Connect: Sandbox channel/ }).click();
  await expect(page).toHaveURL(/\/settings\/channels$/, { timeout: 30_000 });
  await expect(page.getByTestId("connections").getByText("Connected", { exact: true })).toBeVisible();
  const conns = (await call("/channels", H)).json;
  const connectionId: string = (conns.items ?? conns)[0].id;

  // 2. A post, submitted and published now; the worker publishes due posts every 30 s.
  const post = await call("/content/posts", { ...H, body: { connection_id: connectionId, caption: `Handmade pottery from Bhaktapur. Message us to order. ${stamp}`, hashtags: ["pottery"] } });
  expect(post.status).toBe(201);
  expect((await call(`/content/posts/${post.json.id}/submit`, { ...H, method: "POST" })).status).toBe(200);
  expect((await call(`/content/posts/${post.json.id}/schedule`, { ...H, body: {} })).status).toBe(200);
  await expect.poll(async () => (await call(`/content/posts/${post.json.id}`, H)).json.status, { timeout: 90_000, intervals: [2_000] }).toBe("published");

  // 3. Results: typed in from the app's insights.
  await page.goto("/content/insights");
  const row = page.locator(`[data-testid="post-result"][data-post="${post.json.id}"]`);
  await expect(row).toBeVisible();
  await expect(row).toContainText("No views yet");
  await row.getByRole("button", { name: "Add results" }).click();
  const form = page.getByTestId("post-metrics-form");
  await form.getByLabel("Views").fill("1800");
  await form.getByLabel("Likes").fill("120");
  await page.getByRole("button", { name: "Save results" }).click();
  await expect(row).toContainText("You typed it");
  await expect(row).toContainText("1,800");

  // 4. What sells: still learning, with the measured count (the 7-day window isn't complete yet).
  const genome = page.getByTestId("creative-genome");
  await expect(genome).toHaveAttribute("data-status", "learning");
  await expect(page.getByTestId("genome-progress")).toContainText("0 of 20 posts measured");

  // 5. A test with a stopping rule set up front.
  await page.getByRole("button", { name: "New test" }).click();
  const exp = page.getByTestId("experiment-form");
  await exp.getByLabel("Name").fill("Price first?");
  await exp.getByLabel("What do you expect?").fill("Opening with the price brings more orders");
  await page.getByRole("button", { name: "Start test" }).click();
  const item = page.getByTestId("experiment").filter({ hasText: "Price first?" });
  await expect(item).toContainText("Collecting posts");
  await expect(item).toContainText("Opening with the price: 0 of 5 posts");
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p7-whatsells-${testInfo.project.name}.png`), fullPage: true });
});
