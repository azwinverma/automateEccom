import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 6 part B against the live API + worker:
 * - a seller with a costed product delivers three orders and gets one sent back as too small;
 * - Analytics shows true profit with packaging "Not included" (never a silent zero); setting a packaging
 *   cost per order makes it included and lowers the contribution;
 * - the product page shows the Product Brain card.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(150_000);

const PASSWORD = "Pokhara-Profit-2083!";

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

test("true profit labels missing costs; packaging set → included; Product Brain on the product", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p6b+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Sabina Gurung" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Gurung Knits ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "pro"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });

  const p = (await call("/catalog/products", { ...H, body: { title: "Wool Sweater", variants: [{ price_minor: 245000, cost_minor: 100000, sku: `SWT-${stamp}` }] } })).json;
  expect(p.variants[0].id).toBeTruthy();
  await call(`/inventory/variants/${p.variants[0].id}/receive`, { ...H, body: { quantity: 20 } });

  const delivered: { id: string; lines: { id: string }[] }[] = [];
  for (let i = 0; i < 3; i++) {
    const o = (
      await call("/orders", {
        ...H,
        body: {
          lines: [{ variant_id: p.variants[0].id, quantity: 1 }],
          address: { recipient_name: "Customer", phone: `98410000${20 + i}`, district: "Kaski", municipality: "Pokhara Metropolitan City", ward: 6, area: "Lakeside" },
          delivery_fee_minor: 15000,
        },
      })
    ).json;
    for (const to of ["ready_to_ship", "shipped", "delivered"]) expect((await call(`/orders/${o.id}/transition`, { ...H, body: { to } })).status).toBe(200);
    delivered.push((await call(`/orders/${o.id}`, H)).json);
  }
  // One sweater comes back as too small (a real return request).
  const back = delivered[0]!;
  const ret = await call(`/orders/${back.id}/returns`, {
    ...H,
    key: `ret-${stamp}`,
    body: { resolution: "refund", lines: [{ order_line_id: back.lines[0]!.id, quantity: 1, reason: "size_small" }] },
  });
  expect(ret.status).toBe(201);

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/analytics");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/analytics");

  // Profit: packaging isn't set, so it's "Not included" with a sentence saying how to fix it.
  const card = page.getByTestId("profit-card");
  await expect(card).toBeVisible();
  const packaging = page.getByTestId("profit-waterfall").locator('tr[data-component="packaging"]');
  await expect(packaging).toHaveAttribute("data-status", "not_included");
  await expect(packaging).toContainText("Not included");
  await expect(packaging).toContainText("Set a packaging cost per order in Profit settings.");
  await expect(page.getByTestId("profit-waterfall").locator('tr[data-component="goods"]')).toContainText("7,350");
  await expect(page.getByTestId("profit-completeness")).toContainText("Some costs are missing");
  const before = (await page.getByTestId("profit-contribution").textContent()) ?? "";
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p6b-profit-${testInfo.project.name}.png`), fullPage: true });

  // The seller sets Rs 20 per order: packaging becomes included and the contribution drops.
  const settings = page.getByTestId("profit-settings");
  await settings.getByLabel("Packaging cost per order (Rs)").fill("20");
  await settings.getByRole("button", { name: "Save settings" }).click();
  await expect(packaging).toHaveAttribute("data-status", "included");
  await expect(packaging).toContainText("60");
  await expect(page.getByTestId("profit-contribution")).not.toHaveText(before);
  const s = (await call("/intelligence/profit/settings", H)).json;
  expect(s.packaging_cost_minor).toBe(2000);

  // What Nivaro learned + return patterns tabs render (thin data: nothing raised yet).
  await page.getByRole("tab", { name: "What Nivaro learned" }).click();
  await expect(page.getByTestId("memory-facts")).toBeVisible();
  await page.getByRole("tab", { name: "Return patterns" }).click();
  await expect(page.getByTestId("return-insights")).toContainText("No unusual return patterns.");

  // Product page: Product Brain with sales, stock and margin at today's cost.
  await page.goto(`/products/${p.id}`);
  const brain = page.getByTestId("product-brain");
  await expect(brain).toBeVisible();
  await expect(brain).toContainText("Product Brain");
  await expect(brain).toContainText("Sold 3 in 7 days");
  await expect(brain).toContainText("59.2% margin at today's price and cost");
  await expect(brain).toContainText("Not included yet");
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p6b-product-${testInfo.project.name}.png`), fullPage: true });
});
