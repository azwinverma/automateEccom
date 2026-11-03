import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

test.skip(!process.env.E2E_BASE_URL, "Set E2E_BASE_URL to run against a live web + backend stack");
test.setTimeout(180_000);

/** A real 900×900 JPEG drawn in the browser, so the image pipeline gets a genuine photo. */
async function productPhoto(page: Page): Promise<Buffer> {
  const dataUrl = await page.evaluate(() => {
    const c = document.createElement("canvas");
    c.width = 900;
    c.height = 900;
    const g = c.getContext("2d")!;
    g.fillStyle = "#f4efe6";
    g.fillRect(0, 0, 900, 900);
    g.fillStyle = "#7a1f2b";
    g.beginPath();
    g.moveTo(330, 160);
    g.lineTo(570, 160);
    g.lineTo(650, 760);
    g.lineTo(250, 760);
    g.closePath();
    g.fill();
    g.fillStyle = "#d4a24c";
    for (let y = 220; y < 740; y += 60) g.fillRect(300, y, 300, 8);
    return c.toDataURL("image/jpeg", 0.9);
  });
  return Buffer.from(dataUrl.split(",")[1]!, "base64");
}

/**
 * Seller uploads a photo, gets an AI draft (sandbox AI in dev), applies it with a price,
 * connects the sandbox channel via the OAuth round-trip, makes the product live and lists it.
 */
test("photo → AI draft → product → sandbox channel listing", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}`;
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  const serverErrors: string[] = [];
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 500) serverErrors.push(`${r.status()} ${r.url()}`);
  });

  await page.goto("/register");
  await page.getByLabel("Full name").fill("Sita Gurung");
  await page.getByLabel("Email").fill(`e2e-studio+${stamp}@example.com`);
  await page.getByLabel("Password").fill(`Patan-Durbar-${stamp}`);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByLabel("Business name").fill(`Thamel Threads ${stamp}`);
  await page.getByRole("button", { name: "Create business" }).click();
  await expect(page).toHaveURL(/\/home$/);

  // 1. Connect the sandbox channel (OAuth round-trip through the dev consent screen).
  await page.goto("/settings/channels");
  await page.getByTestId("providers").getByRole("button", { name: /^Connect: Sandbox channel/ }).click();
  await expect(page).toHaveURL(/\/settings\/channels$/, { timeout: 30_000 });
  await expect(page.getByTestId("connections").getByText("Connected", { exact: true })).toBeVisible();

  // 2. Upload a photo (signed PUT straight to storage, then processing).
  await page.goto("/products/studio");
  await page.locator("#studio-files").setInputFiles({ name: "kurta.jpg", mimeType: "image/jpeg", buffer: await productPhoto(page) });
  const tile = page.getByTestId("studio-photos").locator("li").first();
  await expect(tile).toHaveAttribute("data-phase", "ready", { timeout: 60_000 });
  await page.getByLabel("Notes for the AI").fill("Handloom cotton kurta from Bhaktapur. Sizes M and L.");
  await page.getByRole("button", { name: "Create draft" }).click();

  // 3. Review the AI draft and apply it with a seller-entered price.
  await expect(page).toHaveURL(/\/products\/studio\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Review AI draft" })).toBeVisible({ timeout: 90_000 });
  await page.getByLabel("Title", { exact: true }).fill(`Cotton Kurta ${stamp}`);
  const grid = page.getByTestId("variant-grid");
  const priceInputs = grid.locator('input[aria-label^="Price (रू)"]');
  for (let i = 0; i < (await priceInputs.count()); i++) await priceInputs.nth(i).fill("1250");
  for (const box of await page.getByTestId("needs-input").getByRole("checkbox").all()) await box.check();
  await page.getByRole("button", { name: "Save as product" }).click();
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]{36}$/, { timeout: 30_000 });

  // 4. Channels panel: listing needs a live product.
  const listings = page.getByTestId("listings");
  await expect(listings.getByText(/Publish this product/)).toBeVisible();
  await page.getByTestId("status-control").getByRole("button", { name: "Publish" }).click();
  await expect(page.getByTestId("status-control").getByText("Active", { exact: true })).toBeVisible();

  // 5. List on the sandbox channel and wait for the listing to reach published.
  const row = listings.locator('tr[data-connection="Sandbox channel"], tr').filter({ hasText: /Sandbox/ }).first();
  await row.getByRole("button", { name: /^List/ }).click();
  await expect(row).toHaveAttribute("data-status", "published", { timeout: 60_000 });
  await expect(row.getByText("Listed", { exact: true })).toBeVisible();
  expect(serverErrors).toEqual([]);
});
