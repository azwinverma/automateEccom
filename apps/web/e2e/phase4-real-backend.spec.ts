import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 4 exit flow against the live API + worker: "delivered → return → refund".
 * The seller starts a return from a delivered COD order (live policy check), approves it, books a
 * return pickup with the sandbox courier (signed courier webhooks bring the parcel back), inspects it
 * (the item goes back in stock) and refunds the customer by eSewa. The order ends up returned.
 * Needs E2E_BASE_URL and E2E_API_URL (…/api/v1).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API, "Set E2E_BASE_URL and E2E_API_URL");
test.setTimeout(150_000);

const PASSWORD = "Dharan-Returns-2083!";

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

test("delivered → return → pickup → inspection → refund", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p4+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Maya Rai" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Rai Fashion ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };

  await call("/couriers", { ...H, body: { provider: "sandbox_courier", pickup: { name: "Rai Fashion", phone: "9801234567", district: "kathmandu", municipality: "Kathmandu Metropolitan City" } } });
  const p = (await call("/catalog/products", { ...H, body: { title: "Wool Jacket", variants: [{ price_minor: 450000, sku: `JKT-${stamp}` }] } })).json;
  await call(`/inventory/variants/${p.variants[0].id}/receive`, { ...H, body: { quantity: 2 } });
  const o = (
    await call("/orders", {
      ...H,
      body: {
        lines: [{ variant_id: p.variants[0].id, quantity: 1 }],
        address: { recipient_name: "Kamal Shrestha", phone: "9841234567", district: "Lalitpur", municipality: "Lalitpur Metropolitan City", ward: 5, area: "Jhamsikhel" },
        delivery_fee_minor: 10000,
      },
    })
  ).json;
  for (const to of ["ready_to_ship", "shipped", "delivered"]) expect((await call(`/orders/${o.id}/transition`, { ...H, body: { to } })).status).toBe(200);
  const stock = async () => (await call(`/catalog/products/${p.id}/stock`, H)).json.variants[0];
  expect(await stock()).toMatchObject({ on_hand: 1, available: 1 });

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto(`/login?next=/orders/${o.id}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(new RegExp(`/orders/${o.id}`));

  // Order page → Returns: start a return with the live policy check.
  const panel = page.getByTestId("returns-panel");
  await panel.getByRole("button", { name: "Start a return" }).click();
  const form = page.getByTestId("start-return");
  await form.getByLabel("Reason").selectOption("size_large");
  await form.getByLabel("Customer's words (optional)").fill("Too loose on the shoulders");
  await expect(form.locator('[data-check="within_window"]')).toHaveAttribute("data-ok", "true");
  await expect(form.getByText("Refund about Rs 4,500")).toBeVisible();
  await page.getByRole("button", { name: "Create return" }).click();
  await expect(panel.getByRole("link", { name: `R-${o.number}-1` })).toBeVisible();

  // Return page: approve, book the pickup, the sandbox courier brings it back.
  await panel.getByRole("link", { name: `R-${o.number}-1` }).click();
  const ret = page.getByTestId("return-detail");
  await expect(ret).toHaveAttribute("data-status", "requested");
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(ret).toHaveAttribute("data-status", "approved");
  await page.getByRole("button", { name: "Book pickup" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Book pickup" }).click();
  const card = page.getByTestId("shipment-card");
  await expect(card).toHaveAttribute("data-status", "booked");
  const retId = new URL(page.url()).pathname.split("/").pop()!;
  const status = async () => (await call(`/returns/${retId}`, H)).json.status as string;
  for (const [sim, expected] of [["picked_up", "in_transit"], ["delivered", "received"]] as const) {
    await page.getByTestId("sandbox-courier").locator(`[data-sim="${sim}"]`).click();
    await expect.poll(status, { timeout: 20_000 }).toBe(expected);
    await page.reload();
  }
  await expect(ret).toHaveAttribute("data-status", "received");
  // The return parcel never moved the order.
  expect((await call(`/orders/${o.id}`, H)).json.status).toBe("delivered");

  // Inspect: good to resell, back in stock.
  await page.getByRole("button", { name: "Inspect" }).click();
  await page.getByRole("button", { name: "Save inspection" }).click();
  await expect(ret).toHaveAttribute("data-status", "inspected");
  expect(await stock()).toMatchObject({ on_hand: 2, available: 2 });

  // Refund by eSewa with the transfer reference.
  await page.getByRole("button", { name: "Refund", exact: true }).click();
  const refund = page.getByTestId("refund-form");
  await expect(refund.getByLabel("Amount (Rs)")).toHaveValue("4500");
  await refund.getByLabel("Transfer reference").fill("ESW-20831104-77");
  await page.getByRole("button", { name: "Send refund" }).click();
  await expect(ret).toHaveAttribute("data-status", "refunded");
  await expect(page.getByTestId("refunds")).toContainText("Sent");
  await expect(page.getByTestId("refunds")).toContainText("ESW-20831104-77");
  const order = (await call(`/orders/${o.id}`, H)).json;
  expect(order.status).toBe("returned");
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p4-return-${testInfo.project.name}.png`), fullPage: true });

  // Returns list: it's done.
  await page.goto("/returns");
  await page.getByRole("tab", { name: /Done/ }).click();
  await expect(page.getByTestId("returns")).toContainText(`R-${o.number}-1`);
});
