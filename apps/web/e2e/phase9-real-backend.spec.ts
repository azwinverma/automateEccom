import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 9 against the live API + worker:
 * - Home shows "Store at a glance" from the Digital Store Twin (an open order counts);
 * - Analytics → What if: a discount estimate on a product whose sales are all from today can't be made
 *   (demand needs at least 7 selling days, and orders can't be backdated through the API), and the page
 *   says so plainly;
 * - a purchase-quantity estimate (needs only recent sales) runs on the worker and comes back as an
 *   "Estimate" with its assumptions, including the supplier's lead time; nothing is executed.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(150_000);

const PASSWORD = "Patan-WhatIf-2083!";

async function call(p: string, init: { method?: string; token?: string; merchant?: string; body?: unknown; key?: string } = {}) {
  const res = await fetch(`${API}${p}`, {
    method: init.method ?? (init.body !== undefined ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}),
      ...(init.merchant ? { "X-Merchant-Id": init.merchant } : {}),
      ...(init.key ? { "Idempotency-Key": init.key } : {}),
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  const text = await res.text();
  return { status: res.status, json: text ? JSON.parse(text) : null };
}

test("store at a glance; what-if estimates are labelled and never act", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p9+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Sabina Maharjan" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Maharjan Metalworks ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "business"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });

  const title = `Brass Bowl ${stamp}`;
  const p = (await call("/catalog/products", { ...H, body: { title, variants: [{ price_minor: 180000, cost_minor: 90000, sku: `BOWL-${stamp}` }] } })).json;
  const vid: string = p.variants[0].id;
  await call(`/inventory/variants/${vid}/receive`, { ...H, body: { quantity: 40 } });
  const sup = (await call("/procurement/suppliers", { ...H, body: { name: `Patan Brassworks ${stamp}`, default_lead_time_days: 9 } })).json;
  expect((await call(`/procurement/suppliers/${sup.id}/products/${vid}`, { ...H, method: "PUT", body: { cost_minor: 90000 } })).status).toBe(200);
  const address = { recipient_name: "Customer", phone: "9841000011", district: "Lalitpur", municipality: "Lalitpur Metropolitan City", ward: 3, area: "Mangal Bazaar" };
  for (let i = 0; i < 6; i++) {
    const o = (await call("/orders", { ...H, body: { lines: [{ variant_id: vid, quantity: 1 }], address } })).json;
    for (const to of ["ready_to_ship", "shipped", "delivered"]) expect((await call(`/orders/${o.id}/transition`, { ...H, body: { to } })).status).toBe(200);
  }
  // One order stays open, so the glance strip has something to say.
  expect((await call("/orders", { ...H, body: { lines: [{ variant_id: vid, quantity: 1 }], address } })).status).toBe(201);
  // The Twin updates from events on the worker: wait until it has counted the open order.
  await expect
    .poll(async () => (await call("/twin/summary?sections=orders", H)).json?.sections?.orders?.state?.open ?? 0, { timeout: 20_000 })
    .toBe(1);

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/home");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/home");

  const glance = page.getByTestId("store-glance");
  await expect(glance).toContainText("Store at a glance");
  await expect(glance.getByRole("link", { name: "Open orders: 1" })).toHaveAttribute("href", "/orders");
  await expect(glance).toContainText(/As of/);

  await page.goto("/analytics");
  await page.getByRole("tab", { name: "What if" }).click();
  const whatIf = page.getByTestId("what-if");
  await expect(whatIf.getByRole("radio", { name: "Moving ad budget" })).toBeDisabled();

  // Discount: all sales are from today, so demand can't be estimated yet, and the page says why.
  await whatIf.getByLabel("Find a product").fill(title);
  await whatIf.getByRole("button", { name: title }).click();
  await expect(whatIf.getByText(`Selected: ${title}`)).toBeVisible(); // the picker loads the product first
  await whatIf.getByLabel("Discount (%)").fill("20");
  await whatIf.getByRole("button", { name: "Estimate it" }).click();
  await expect(page.getByText(/Not enough sales yet to estimate demand/)).toBeVisible({ timeout: 30_000 });

  // Buying stock: recent sales are enough; the estimate comes back from the worker with its assumptions.
  await whatIf.getByRole("radio", { name: "Buying stock" }).check();
  await whatIf.getByLabel("Find a product").fill(title);
  await whatIf.getByRole("button", { name: title }).click();
  await expect(whatIf.getByText(`Selected: ${title}`)).toBeVisible(); // the picker loads the product first
  await whatIf.getByLabel("Quantity to buy").fill("30");
  await whatIf.getByRole("button", { name: "Estimate it" }).click();
  const result = page.getByTestId("sim-result");
  await expect(result).toHaveAttribute("data-kind", "purchase_quantity", { timeout: 30_000 });
  await expect(result).toContainText("Estimate");
  await expect(result).toContainText(`Buying 30 of ${title}`);
  await expect(result.getByTestId("sim-assumptions")).toContainText("Delivery takes about 9 days, from the supplier's terms.");
  await expect(result).toContainText("Nothing changes until you act.");
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p9-whatif-${testInfo.project.name}.png`), fullPage: true });

  // Nothing was bought: no purchase order exists.
  expect((await call("/procurement/purchase-orders", H)).json.items).toEqual([]);
});
