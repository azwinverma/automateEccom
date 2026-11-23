import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * The round of seller connections against the live API + worker:
 * - Set up autopilot: the selling path checklist, then "Turn on" switches on Smart mode, the five
 *   recommended automations and a win-back campaign; posting is skipped because nothing can post;
 * - Campaigns shows the win-back campaign running;
 * - Content shows Automatic posting asking for a Facebook/Instagram connection first;
 * - Settings → Payments connects eSewa in test mode (eSewa keys can't be checked in advance), and a
 *   prepaid order's payment link opens Nivaro's checkout page with a signed form to eSewa's test
 *   site (not submitted: nothing leaves the machine).
 * Needs E2E_BASE_URL, E2E_API_URL (…/api/v1) and COS_DATABASE_URL (for the set-plan ops CLI).
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");
test.setTimeout(150_000);

const PASSWORD = "Bhaktapur-Autopilot-2083!";

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

test("autopilot setup, campaigns, automatic posting and an eSewa checkout link", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  const email = `e2e-ap+${stamp}@example.com`;
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Ramesh Shakya" } })).status).toBe(201);
  const token: string = (await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } })).json.access_token;
  const shop = await call("/merchants", { token, body: { name: `Shakya Pottery ${stamp}`, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" } });
  const m = shop.json.merchant ?? shop.json;
  const H = { token, merchant: m.id as string };
  execFileSync("uv", ["run", "python", "-m", "app.cli", "set-plan", m.slug, "growth"], { cwd: path.resolve(import.meta.dirname, "../../backend"), env: process.env, stdio: "pipe" });

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/login?next=/automation/setup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL((u) => u.pathname === "/automation/setup");

  // The selling path, before anything is on.
  await expect(page.getByRole("heading", { name: "Set up autopilot" })).toBeVisible();
  await expect(page.getByText("Your selling path")).toBeVisible();
  await expect(page.getByText("Customers message you")).toBeVisible();
  await expect(page.getByText("Customers come back")).toBeVisible();

  // Turn on the recommended set in Smart mode.
  await page.getByRole("radio", { name: /Smart/ }).check();
  await page.getByRole("button", { name: "Turn on", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Turn on these automations?");
  await dialog.getByRole("button", { name: "Turn on", exact: true }).click();
  await expect(page.getByText("Switched on", { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Mode set to Smart")).toBeVisible();
  await expect(page.getByText("No connected account can post yet")).toBeVisible();
  await expect(page.getByText("Book the courier when an order is packed").first()).toBeVisible();
  if (process.env.E2E_SCREENSHOTS) await page.screenshot({ path: path.join(process.env.E2E_SCREENSHOTS, `ap-setup-${testInfo.project.name}.png`), fullPage: true });

  // The API agrees: five automations on, a win-back campaign running.
  const wfs = (await call("/automation/workflows", H)).json.items as { status: string }[];
  expect(wfs.filter((w) => w.status === "active")).toHaveLength(5);

  await page.goto("/campaigns");
  await expect(page.getByText("Win back quiet customers")).toBeVisible();
  await expect(page.getByText("Running").first()).toBeVisible();

  await page.goto("/content");
  await expect(page.getByText("Automatic posting")).toBeVisible();
  await expect(page.getByRole("link", { name: /Connect Facebook & Instagram/ })).toBeVisible();

  // eSewa in test mode: connected, keys unproven until the first payment.
  await page.goto("/settings/payments");
  await page.getByRole("button", { name: "Connect eSewa" }).click();
  await page.getByLabel("Merchant (product) code").fill("EPAYTEST");
  await page.getByLabel("Secret key").fill(`e2e-esewa-test-key-${stamp}`);
  await page.getByRole("dialog").getByRole("button", { name: /^Connect/ }).click();
  await expect(page.getByText("Confirmed by your first payment").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(`e2e-esewa-test-key-${stamp}`)).toHaveCount(0); // the key is never shown

  // A prepaid order's payment link opens Nivaro's checkout page with a signed form for eSewa.
  const p = (await call("/catalog/products", { ...H, body: { title: `Clay Pot ${stamp}`, variants: [{ price_minor: 120000, sku: `POT-${stamp}` }] } })).json;
  await call(`/inventory/variants/${p.variants[0].id}/receive`, { ...H, body: { quantity: 5 } });
  const address = { recipient_name: "Customer", phone: "9841000022", district: "Bhaktapur", municipality: "Bhaktapur Municipality", ward: 4, area: "Taumadhi" };
  const o = (await call("/orders", { ...H, body: { lines: [{ variant_id: p.variants[0].id, quantity: 1 }], address, payment_method: "prepaid" } })).json;
  const pay = await call(`/orders/${o.id}/payments/online`, { ...H, body: {} });
  expect(pay.status).toBe(201);
  expect(pay.json.provider).toBe("esewa");
  await page.goto(pay.json.redirect_url);
  await expect(page.getByRole("heading", { name: /Pay Rs 1,200/ })).toBeVisible();
  await expect(page.locator('form[action="https://rc-epay.esewa.com.np/api/epay/main/v2/form"]')).toHaveCount(1);
  await expect(page.locator('input[name="signature"]')).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Continue to eSewa" })).toBeVisible();
  // A tampered link is refused.
  await page.goto(pay.json.redirect_url.replace(/t=[^&]+/, "t=forged"));
  await expect(page.getByText(/not.?found/i).first()).toBeVisible();
});
