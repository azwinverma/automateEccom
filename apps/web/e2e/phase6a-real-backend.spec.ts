import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 6 part A against the live API + worker:
 * - the seller books couriers by hand → the Autopilot Score shows the gap → a suggestion to turn on
 *   "Book a courier when an order is packed" is applied from Home (R3, by the owner);
 * - a customer whose last two COD parcels failed orders again → the order is held with reasons
 *   (never rejected) → the seller overrides with a reason and the hold clears.
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(150_000);

const PASSWORD = "Janakpur-Insight-2083!";

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

test("score gap → suggestion applied; risky COD order held → override", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p6+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Rita Yadav" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Yadav Sarees ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "pro"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });
  const c = (await call("/couriers", { ...H, body: { provider: "sandbox_courier", pickup: { name: "Yadav Sarees", phone: "9801234567", district: "kathmandu", municipality: "Kathmandu Metropolitan City" } } })).json;
  const p = (await call("/catalog/products", { ...H, body: { title: "Silk Saree", variants: [{ price_minor: 450000, sku: `SAR-${stamp}` }] } })).json;
  await call(`/inventory/variants/${p.variants[0].id}/receive`, { ...H, body: { quantity: 40 } });
  const order = async (phone: string) =>
    (
      await call("/orders", {
        ...H,
        body: {
          lines: [{ variant_id: p.variants[0].id, quantity: 1 }],
          address: { recipient_name: "Customer", phone, district: "Dhanusha", municipality: "Janakpurdham Sub-Metropolitan City", ward: 4, area: "Ramananda Chowk" },
        },
      })
    ).json;

  // 10 parcels booked by hand: a manual gap in "Booking couriers".
  for (let i = 0; i < 10; i++) {
    const o = await order(`98410000${String(10 + i)}`);
    expect((await call(`/orders/${o.id}/shipments`, { ...H, body: { courier_account_id: c.id }, key: `book-${stamp}-${i}` })).status).toBe(201);
  }
  // One customer's last two COD parcels failed.
  for (let i = 0; i < 2; i++) {
    const o = await order("9807654321");
    for (const to of ["ready_to_ship", "shipped", "delivery_failed", "returned"]) expect((await call(`/orders/${o.id}/transition`, { ...H, body: { to } })).status).toBe(200);
  }
  const risky = await order("9807654321");
  await expect.poll(async () => (await call(`/orders/${risky.id}`, H)).json.needs_review, { timeout: 20_000 }).toBe("cod_risk");

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/home");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/home");

  // Autopilot Score: booking couriers is 0% automatic, measured on 10 parcels.
  const score = page.getByTestId("autopilot-score");
  await expect(score.locator('[data-capability="shipment_creation"]')).toContainText("0%");
  await expect(score.locator('[data-capability="shipment_creation"]')).toContainText("By your team 10");

  // The suggestion exists once generated (nightly; here on demand) and is applied from Home.
  await call("/intelligence/recommendations/refresh", { ...H, method: "POST" });
  await page.reload();
  const recs = page.getByTestId("recommendations");
  const card = recs.locator('li[data-type="autopilot_improvement"]').filter({ hasText: "Book a courier when an order is packed" });
  await expect(card).toContainText("Your team did 10 of 10 by hand");
  await card.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("Done. We'll measure the result in 2 weeks.")).toBeVisible();
  const flows = (await call("/automation/workflows", H)).json.items;
  expect(flows.some((w: { template_code: string; status: string }) => w.template_code === "book_courier_when_packed" && w.status === "active")).toBe(true);
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p6-home-${testInfo.project.name}.png`), fullPage: true });

  // The risky order: held with reasons, never cancelled; the seller overrides after a call.
  await page.goto(`/orders/${risky.id}`);
  const risk = page.getByTestId("cod-risk");
  await expect(risk).toHaveAttribute("data-level", "HIGHER");
  await expect(risk).toContainText("Delivered 0, failed 2 before with you");
  await expect(risk).toContainText("Review before packing");
  await expect(risk).toContainText("Never on name, gender, religion, caste or ethnicity.");
  await expect(page.getByTestId("order-detail").getByRole("heading", { level: 1 })).toContainText("To pack");
  await risk.getByRole("button", { name: "Change" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Level").selectOption("LOW");
  await dialog.getByLabel("Reason (kept in the audit log)").fill("Called her: wrong landmark last time, now fixed");
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(risk).toHaveAttribute("data-level", "LOW");
  await expect(risk).toContainText("Changed by your team: Called her");
  expect((await call(`/orders/${risky.id}`, H)).json.needs_review).toBeNull();
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p6-order-${testInfo.project.name}.png`), fullPage: true });
});
