import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 8 against the live API:
 * - a seller with a supplier creates a purchase order in the UI with freight and sees the landed cost;
 * - the default PO limit is 0, so submitting waits for approval; the owner approves, marks it sent;
 * - a first delivery arrives with one damaged unit (partly received), then the rest (received);
 * - the product's stock went up by the good units only.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(150_000);

const PASSWORD = "Bhaktapur-Stock-2083!";

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

test("purchase order: landed cost → approval → sent → partial and full receipt → stock", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p8+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Ram Shakya" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Shakya Pottery ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "pro"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });

  const title = `Clay Pot ${stamp}`;
  const p = (await call("/catalog/products", { ...H, body: { title, variants: [{ price_minor: 120000, sku: `POT-${stamp}` }] } })).json;
  const vid: string = p.variants[0].id;
  await call(`/inventory/variants/${vid}/receive`, { ...H, body: { quantity: 2 } });
  const sup = (await call("/procurement/suppliers", { ...H, body: { name: `Thimi Potters ${stamp}`, default_lead_time_days: 7 } })).json;
  expect((await call(`/procurement/suppliers/${sup.id}/products/${vid}`, { ...H, method: "PUT", body: { cost_minor: 50000, moq: 10 } })).status).toBe(200);

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto(`/login?next=/inventory/purchase-orders/new`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/inventory/purchase-orders/new");

  // New PO: supplier, the pot (price prefilled from the supplier), 10 pieces, Rs 1,000 freight.
  const form = page.getByTestId("po-form");
  await form.getByLabel("Supplier").selectOption(sup.id);
  await form.getByLabel("Find a product").fill(title);
  await form.getByRole("button", { name: title }).click();
  const line = form.getByTestId("po-line");
  await expect(line.getByLabel("Price per unit (Rs)")).toHaveValue("500");
  await line.getByLabel("Quantity").fill("10");
  await form.getByLabel("Freight (Rs)").fill("1000");
  await expect(line.getByTestId("po-landed")).toContainText("600"); // 500 + 1,000 / 10
  await expect(form.getByTestId("po-totals")).toContainText("6,000");
  await form.getByRole("button", { name: "Save draft" }).click();
  await expect(page).toHaveURL(/\/inventory\/purchase-orders\/[0-9a-f-]+$/);
  const detail = page.getByTestId("po-detail");
  await expect(detail).toHaveAttribute("data-status", "draft");
  await expect(detail.getByTestId("line-landed")).toContainText("600");

  // Default limit 0: every PO waits for an explicit approval.
  await page.getByRole("button", { name: "Send for approval" }).click();
  await expect(detail).toHaveAttribute("data-status", "pending_approval");
  await expect(detail.getByTestId("po-approval-reason")).toContainText("every purchase order needs one");
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(detail).toHaveAttribute("data-status", "approved");
  await expect(detail.getByTestId("po-share")).toContainText("Purchase order PO-1001");
  await page.getByRole("button", { name: "Mark as sent" }).click();
  await expect(detail).toHaveAttribute("data-status", "sent");

  // First delivery: 6 good + 1 damaged.
  const receive = page.getByTestId("receive-form");
  await receive.getByLabel(`Good units of ${title}`).fill("6");
  await receive.getByLabel(`Damaged units of ${title}`).fill("1");
  await receive.getByLabel(/Lot or batch code/).fill("THIMI-A");
  await receive.getByRole("button", { name: "Receive" }).click();
  await expect(detail).toHaveAttribute("data-status", "partially_received");
  await expect(page.getByTestId("po-receipts")).toContainText("THIMI-A");
  await expect(page.getByTestId("po-receipts")).toContainText("6 good, 1 damaged");

  // The rest: 3 good.
  await page.getByTestId("receive-form").getByLabel(`Good units of ${title}`).fill("3");
  await page.getByTestId("receive-form").getByRole("button", { name: "Receive" }).click();
  await expect(detail).toHaveAttribute("data-status", "received");
  await expect(page.getByTestId("receive-form")).toHaveCount(0);
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p8-po-${testInfo.project.name}.png`), fullPage: true });

  // Stock: 2 before + 9 good units; the damaged one never went in.
  const stock = (await call(`/catalog/products/${p.id}/stock`, H)).json;
  expect(stock.variants[0].on_hand).toBe(11);
  const pos = (await call("/procurement/purchase-orders", H)).json.items;
  expect(pos[0].lines[0]).toMatchObject({ received_quantity: 10, defective_quantity: 1, remaining: 0 });
});
