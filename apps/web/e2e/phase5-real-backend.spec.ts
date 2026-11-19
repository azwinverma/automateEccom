import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 5 exit flow against the live API + worker: a workflow under the Decision Policy, with every
 * action recorded, and the Control Center showing real numbers.
 * The seller turns on "Book a courier when an order is packed" from a template (dry-run first). In
 * Assisted mode the booking waits for approval on Home; approved, it books. In Smart mode the next
 * packed order is booked and picked up automatically, and the Control Center feed says why.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(150_000);

const PASSWORD = "Pokhara-Autopilot-2083!";

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

test("template workflow → approval in Assisted → automatic in Smart → Control Center", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p5+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Sunita Thapa" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Thapa Crafts ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "growth"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });
  await call("/couriers", { ...H, body: { provider: "sandbox_courier", pickup: { name: "Thapa Crafts", phone: "9801234567", district: "kathmandu", municipality: "Kathmandu Metropolitan City" } } });
  const p = (await call("/catalog/products", { ...H, body: { title: "Singing Bowl", variants: [{ price_minor: 280000, sku: `BOWL-${stamp}` }] } })).json;
  await call(`/inventory/variants/${p.variants[0].id}/receive`, { ...H, body: { quantity: 5 } });
  const newOrder = async () =>
    (
      await call("/orders", {
        ...H,
        body: {
          lines: [{ variant_id: p.variants[0].id, quantity: 1 }],
          address: { recipient_name: "Bimal Gurung", phone: "9841234567", district: "Lalitpur", municipality: "Lalitpur Metropolitan City", ward: 2, area: "Kupondole" },
        },
      })
    ).json;
  const shipments = async (oid: string) => (await call(`/orders/${oid}/shipments`, H)).json.items;

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/automation");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/automation");

  // Template → builder → dry run on a real order → turn on.
  const o0 = await newOrder();
  await page.getByRole("button", { name: "Use: Book a courier when an order is packed" }).click();
  await expect(page).toHaveURL(/\/automation\/[0-9a-f-]{36}$/);
  const builder = page.getByTestId("workflow-builder");
  await expect(builder.getByText("Off", { exact: true })).toBeVisible();
  const dry = page.getByTestId("dry-run");
  await dry.getByLabel("Order").selectOption(o0.id);
  await dry.getByRole("button", { name: "Run the test" }).click();
  await expect(page.getByTestId("dry-run-trace")).toContainText("This record isn't at a status that starts the workflow");
  await expect(page.getByTestId("dry-run-trace")).toContainText("Your shop is in Assisted mode");
  expect(await shipments(o0.id)).toHaveLength(0); // a dry run changes nothing
  await page.getByTestId("toggle-workflow").click();
  await expect(builder.getByText("On", { exact: true })).toBeVisible();

  // Assisted: packing an order asks the seller first, on Home.
  const o1 = await newOrder();
  expect((await call(`/orders/${o1.id}/transition`, { ...H, body: { to: "ready_to_ship" } })).status).toBe(200);
  await expect.poll(async () => (await call("/automation/approvals", H)).json.items.length, { timeout: 20_000 }).toBe(1);
  await page.goto("/home");
  const approvals = page.getByTestId("automation-approvals");
  await expect(approvals).toContainText("Book a courier");
  await expect(approvals).toContainText("Your shop is in Assisted mode");
  await approvals.getByRole("button", { name: "Approve" }).first().click();
  await expect.poll(async () => (await shipments(o1.id)).length, { timeout: 20_000 }).toBe(1);
  await expect(approvals.getByText("Request pickup")).toBeVisible(); // the next step asks again
  await approvals.getByRole("button", { name: "Approve" }).first().click();
  await expect.poll(async () => (await shipments(o1.id))[0]?.status, { timeout: 20_000 }).toBe("pickup_requested");

  // Smart: the next packed order is booked and picked up automatically.
  await call("/merchant", { ...H, method: "PATCH", body: { automation_mode: "smart" } });
  const o2 = await newOrder();
  await call(`/orders/${o2.id}/transition`, { ...H, body: { to: "ready_to_ship" } });
  await expect.poll(async () => (await shipments(o2.id))[0]?.status, { timeout: 20_000 }).toBe("pickup_requested");

  await page.reload();
  const board = page.getByTestId("control-center");
  await expect(board.getByRole("heading", { name: /Your store is running\.|A few things are waiting for you\./ })).toBeVisible();
  await expect(board).toContainText("Smart");
  const feed = page.getByTestId("autopilot-feed");
  await expect(feed.getByText("Book a courier").first()).toBeVisible();
  await expect(feed.getByText(/Ran automatically \(Smart mode, low risk\)/).first()).toBeVisible();
  const cc = (await call("/control-center", H)).json;
  expect(cc.metrics.orders).toBe(3);
  expect(cc.automation.done_automatically).toBeGreaterThanOrEqual(2);
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p5-home-${testInfo.project.name}.png`), fullPage: true });

  // Every decision is on record.
  await page.goto("/automation?tab=activity");
  const decisions = page.getByTestId("decisions");
  await expect(decisions.locator('tr[data-decision="AUTO_EXECUTE"]').first()).toBeVisible();
  await expect(decisions.locator('tr[data-decision="REQUIRE_APPROVAL"]').first()).toBeVisible();
});
