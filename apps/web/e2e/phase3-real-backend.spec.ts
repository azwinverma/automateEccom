import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Phase 3 exit flow against the live API + worker: "order → COD → delivered", then the courier's
 * cash statement is reconciled and the seller confirms the money arrived.
 * The seller adds a courier and delivery charges in Settings, books the courier from the order,
 * requests pickup; the sandbox courier pushes signed webhooks (through the public webhook endpoint,
 * the webhook inbox and the worker) for pickup, a failed attempt, the reattempt and delivery.
 * Needs E2E_BASE_URL and E2E_API_URL (…/api/v1).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API, "Set E2E_BASE_URL and E2E_API_URL");
test.setTimeout(150_000);

const PASSWORD = "Biratnagar-Delivery-2083!";

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

test("order → COD → courier → failed attempt → reattempt → delivered → cash settled", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-p3+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Anita Karki" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Karki Fabrics ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };

  // A product with stock and a COD order from the seller (Lalitpur, inside the valley).
  const p = (await call("/catalog/products", { ...H, body: { title: "Pashmina Shawl", variants: [{ price_minor: 320000, sku: `PSH-${stamp}` }] } })).json;
  const vid = p.variants[0].id;
  await call(`/inventory/variants/${vid}/receive`, { ...H, body: { quantity: 3 } });

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/settings/couriers");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/settings\/couriers/);

  // Settings → Couriers: add the courier with a pickup address, and the delivery charge table.
  await page.getByRole("button", { name: "Add courier" }).click();
  const add = page.getByRole("dialog");
  await add.getByLabel("Courier", { exact: true }).selectOption("sandbox_courier");
  await add.getByLabel("Contact name").fill("Karki Fabrics");
  await add.getByLabel("Contact phone").fill("9801234567");
  await add.getByLabel("District").selectOption("kathmandu");
  await add.getByLabel("Municipality").fill("Kathmandu Metropolitan City");
  await add.getByRole("button", { name: "Add courier" }).click();
  await expect(page.getByTestId("couriers")).toContainText("Sandbox courier");
  await expect(page.getByTestId("couriers")).toContainText("Default");
  const fees = page.getByTestId("fee-rules");
  await fees.getByLabel("Charge (Rs) · Everywhere else").fill("175");
  await fees.getByLabel("Charge (Rs) · Inside Kathmandu Valley").fill("100");
  await fees.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Delivery charges saved.")).toBeVisible();
  const quote = (await call("/fulfillment/delivery-fee?district=lalitpur&subtotal_minor=320000", H)).json.quote;
  expect(quote).toMatchObject({ fee_minor: 10000, rule: "inside_valley" });

  const o = (
    await call("/orders", {
      ...H,
      body: {
        lines: [{ variant_id: vid, quantity: 1 }],
        address: { recipient_name: "Ramesh Thapa", phone: "9841234567", district: "Lalitpur", municipality: "Lalitpur Metropolitan City", ward: 3, area: "Pulchowk" },
        delivery_fee_minor: quote.fee_minor,
      },
    })
  ).json;
  expect(o.status).toBe("cod_pending");

  // Order page → Delivery: the default courier is recommended; book it and request pickup.
  await page.goto(`/orders/${o.id}`);
  const detail = page.getByTestId("order-detail");
  const panel = page.getByTestId("delivery-panel");
  await expect(panel.getByRole("radio", { name: /Sandbox courier/ })).toBeChecked();
  await expect(panel.getByText("Your default courier")).toBeVisible();
  await expect(panel.getByText("Rider collects Rs 3,300")).toBeVisible();
  await panel.getByRole("button", { name: "Book courier" }).click();
  const card = panel.getByTestId("shipment-card");
  await expect(card).toHaveAttribute("data-status", "booked");
  await expect(detail.getByRole("heading", { level: 1 })).toContainText("Packed");
  const tracking = (await card.getByTestId("tracking-number").textContent())!.trim();
  expect(tracking).toMatch(/^SBX/);
  await card.getByRole("button", { name: "Request pickup" }).click();
  await expect(card).toHaveAttribute("data-status", "pickup_requested");

  const shipmentStatus = async () => (await call(`/orders/${o.id}/shipments`, H)).json.items[0].status as string;
  const courierDoes = async (sim: string, expected: string) => {
    await card.getByTestId("sandbox-courier").locator(`[data-sim="${sim}"]`).click();
    await expect.poll(shipmentStatus, { timeout: 20_000 }).toBe(expected);
    await page.reload();
    await expect(page.getByTestId("shipment-card")).toHaveAttribute("data-status", expected);
  };

  // The courier collects the parcel: the order is shipped and the stock leaves the shelf.
  await courierDoes("picked_up", "picked_up");
  await expect(detail.getByRole("heading", { level: 1 })).toContainText("Shipped");
  expect((await call(`/catalog/products/${p.id}/stock`, H)).json.variants[0]).toMatchObject({ on_hand: 2, reserved: 0 });

  // A failed attempt: no chat with this customer, so the seller is asked to call; then a reattempt.
  await courierDoes("out_for_delivery", "out_for_delivery");
  await courierDoes("delivery_failed", "delivery_failed");
  await expect(detail.getByRole("heading", { level: 1 })).toContainText("Delivery failed");
  const attempt = page.getByTestId("delivery-attempt");
  await expect(attempt).toContainText("Customer's phone unreachable");
  await expect(attempt).toContainText("No chat with this customer");
  const ex = (await call("/exceptions", H)).json.items;
  expect(ex.find((e: { type: string }) => e.type === "delivery_failed")).toMatchObject({ action: "call_customer" });
  await page.getByTestId("shipment-card").getByRole("button", { name: "Request reattempt" }).click();
  await page.getByRole("dialog").getByLabel("Note for the courier (good time, landmark)").fill("Called: after 4pm, opposite Labim Mall");
  await page.getByRole("dialog").getByRole("button", { name: "Request reattempt" }).click();
  await expect(page.getByTestId("shipment-card")).toHaveAttribute("data-status", "reattempt_requested");

  await courierDoes("out_for_delivery", "out_for_delivery");
  await courierDoes("delivered", "delivered");
  await expect(detail.getByRole("heading", { level: 1 })).toContainText("Delivered");
  await expect(page.getByTestId("delivery-attempt")).toContainText("Delivered on a later attempt");
  const events = page.getByTestId("shipment-events");
  for (const s of ["Booked", "With courier", "Delivery failed · Customer's phone unreachable", "Reattempt requested", "Delivered"]) await expect(events.getByText(s, { exact: true }).first()).toBeVisible();
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p3-order-${testInfo.project.name}.png`), fullPage: true });

  // The printable label carries the tracking number and the cash to collect.
  await page.goto(`/fulfillment/label/${(await call(`/orders/${o.id}/shipments`, H)).json.items[0].id}`);
  const label = page.getByTestId("label");
  await expect(label).toContainText(tracking);
  await expect(label).toContainText("Collect cash: Rs 3,300");
  await expect(label).toContainText("Ramesh Thapa");

  // Deliveries list: the parcel is under Delivered.
  await page.goto("/fulfillment");
  await page.getByRole("tab", { name: /Delivered/ }).click();
  await expect(page.getByTestId("shipments")).toContainText(`#${o.number}`);

  // COD cash: the courier holds Rs 3,300 → statement arrives → it matches → the seller confirms.
  await page.goto("/fulfillment/cod");
  await expect(page.getByTestId("cod-overview")).toContainText("Rs 3,300");
  await expect(page.getByTestId("cod-awaiting")).toContainText(`#${o.number}`);
  await page.getByTestId("sandbox-statement").click();
  const st = page.getByTestId("settlement-detail");
  await expect(st).toContainText("Matches");
  await expect(st).toContainText("Rs 3,200"); // Rs 3,300 collected − Rs 100 courier charge
  await page.getByTestId("confirm-settlement").click();
  const confirm = page.getByRole("dialog", { name: "Did Rs 3,200 reach your account?" });
  await confirm.getByLabel("Bank or wallet reference (optional)").fill("NIC-4471");
  await confirm.getByRole("button", { name: "Confirm money received" }).click();
  await expect(page.getByText("Marked as received.")).toBeVisible();
  const ov = (await call("/cod/overview", H)).json;
  expect(ov.settled.count).toBe(1);
  expect(ov.awaiting_by_age.d0_7.count).toBe(0);
  if (process.env.E2E_SCREENSHOTS) {
    await page.keyboard.press("Escape");
    await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `p3-cod-${testInfo.project.name}.png`), fullPage: true });
  }
});
