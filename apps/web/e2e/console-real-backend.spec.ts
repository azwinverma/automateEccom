import { execFileSync } from "node:child_process";
import { createHmac } from "node:crypto";
import path from "node:path";
import { expect, test } from "./fixtures";

/**
 * Nivaro Console against the live API: staff sign in with a TOTP code, find a shop, grant credits,
 * suspend (the seller is blocked) and reactivate, and the actions show in the audit log.
 * Needs E2E_API_URL (e.g. http://localhost:8190/api/v1) and COS_DATABASE_URL for the make-staff CLI.
 */
const API = process.env.E2E_API_URL ?? "";
test.skip(!process.env.E2E_BASE_URL || !API || !process.env.COS_DATABASE_URL, "Set E2E_BASE_URL, E2E_API_URL and COS_DATABASE_URL");

const PASSWORD = "Patan-Durbar-2083!";

function base32(s: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of s.replace(/=+$/, "").toUpperCase()) bits += alphabet.indexOf(c).toString(2).padStart(5, "0");
  const out: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(out);
}
function totp(secret: string, at = Date.now()): string {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / 30)));
  const h = createHmac("sha1", base32(secret)).update(counter).digest();
  const o = h[h.length - 1]! & 0xf;
  return String((h.readUInt32BE(o) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

async function call(pathname: string, init: { method?: string; token?: string; merchant?: string; body?: unknown } = {}) {
  const res = await fetch(`${API}${pathname}`, {
    method: init.method ?? (init.body ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}),
      ...(init.merchant ? { "X-Merchant-Id": init.merchant } : {}),
    },
    body: init.body ? JSON.stringify(init.body) : undefined,
  });
  const text = await res.text();
  return { status: res.status, json: text ? JSON.parse(text) : null };
}

async function registerAndLogin(email: string) {
  expect((await call("/auth/register", { body: { email, password: PASSWORD, full_name: "Console E2E" } })).status).toBe(201);
  const login = await call("/auth/login", { body: { email, password: PASSWORD, device_name: "e2e" } });
  return login.json.access_token as string;
}

test("staff manage a shop from the Console", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);

  // A seller with a shop.
  const sellerToken = await registerAndLogin(`e2e-shop+${stamp}@example.com`);
  const shopName = `Console Pottery ${stamp}`;
  const shop = await call("/merchants", {
    token: sellerToken,
    body: { name: shopName, currency: "NPR", timezone: "Asia/Kathmandu", default_locale: "en" },
  });
  const merchantId: string = shop.json.merchant?.id ?? shop.json.id;

  // A staff member with an authenticator app.
  const staffEmail = `e2e-ops+${stamp}@nivaro.example`;
  const staffToken = await registerAndLogin(staffEmail);
  const setup = await call("/auth/mfa/totp/setup", { token: staffToken, body: {} });
  const secret: string = setup.json.secret;
  expect((await call("/auth/mfa/totp/enable", { token: staffToken, body: { code: totp(secret, Date.now() - 30_000) } })).status).toBe(200);
  execFileSync("uv", ["run", "python", "-m", "app.cli", "make-staff", staffEmail], {
    cwd: path.resolve(import.meta.dirname, "../../backend"),
    env: process.env,
    stdio: "pipe",
  });

  // Sign in through the UI with the code: staff without a shop land in the Console.
  await page.goto("/login?next=/console");
  await page.getByLabel("Email").fill(staffEmail);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.getByLabel("6-digit code").fill(totp(secret));
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page).toHaveURL(/\/console\/merchants/);
  await expect(page.getByTestId("console-env")).toBeVisible();

  await page.getByLabel("Search by name or slug").fill(shopName);
  await page.getByLabel("Search by name or slug").press("Enter");
  await page.getByRole("button", { name: shopName }).click();
  const drawer = page.getByTestId("merchant-detail");
  await expect(drawer.getByText(`e2e-shop+${stamp}@example.com`)).toBeVisible();
  const shots = process.env.E2E_SCREENSHOTS;
  if (shots) await page.waitForTimeout(600);
  if (shots) await page.screenshot({ path: path.join(shots, `console-drawer-${testInfo.project.name}.png`) });

  const credits = drawer.getByRole("form", { name: "Grant credits" });
  await credits.getByLabel("Credits").fill("25");
  await credits.getByLabel("Reason").fill("E2E goodwill credit");
  await credits.getByRole("button", { name: "Grant credits" }).click();
  await expect(drawer.locator("dd").filter({ hasText: /^25$/ })).toBeVisible();

  const suspend = drawer.getByRole("form", { name: "Suspend shop" });
  await suspend.getByLabel("Reason").fill("E2E suspension check");
  await suspend.getByRole("button", { name: "Suspend shop" }).click();
  await expect(drawer.getByRole("heading", { level: 2 })).toContainText("suspended");
  const blocked = await call("/catalog/products", { token: sellerToken, merchant: merchantId });
  expect(blocked.status).toBe(403);
  expect(blocked.json.error.code).toBe("merchant_suspended");

  const reactivate = drawer.getByRole("form", { name: "Reactivate shop" });
  await reactivate.getByLabel("Reason").fill("E2E suspension cleared");
  await reactivate.getByRole("button", { name: "Reactivate shop" }).click();
  await expect(drawer.getByRole("heading", { level: 2 })).toContainText("active");
  expect((await call("/catalog/products", { token: sellerToken, merchant: merchantId })).status).toBe(200);

  await page.goto(`/console/audit?merchant_id=${merchantId}`);
  await expect(page.getByTestId("audit").getByText("admin.merchant_status_changed").first()).toBeVisible();
  await expect(page.getByTestId("audit").getByText("admin.credits_granted")).toBeVisible();
  await expect(page.getByTestId("audit").getByText(staffEmail).first()).toBeVisible();

  if (shots) await page.screenshot({ path: path.join(shots, `console-audit-${testInfo.project.name}.png`), fullPage: true });
  await page.goto("/console/outbox");
  await expect(page.getByRole("heading", { name: "Outbox" })).toBeVisible();
  await page.goto("/console/ai");
  await expect(page.getByTestId("providers")).toBeVisible();
});

test("the Console is invisible to sellers", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}${testInfo.project.name.length}`;
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  const email = `e2e-noconsole+${stamp}@example.com`;
  await registerAndLogin(email);
  await page.goto("/login?next=/console");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await page.goto("/console/merchants");
  await expect(page.getByText("Page not found")).toBeVisible();
  await expect(page.getByTestId("merchants")).toHaveCount(0);
});
