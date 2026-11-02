import { expect, test } from "@playwright/test";

test.skip(!process.env.E2E_BASE_URL, "Set E2E_BASE_URL to run against a live web + backend stack");

/** Owner creates a 2×2 product, publishes it, then archives it — all against the real catalog API. */
test("create a product with 2×2 variants, publish, archive", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}`;
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  const failures: string[] = [];
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 500) failures.push(`${r.status()} ${r.url()}`);
  });

  await page.goto("/register");
  await page.getByLabel("Full name").fill("Sita Gurung");
  await page.getByLabel("Email").fill(`e2e-catalog+${stamp}@example.com`);
  await page.getByLabel("Password").fill(`Patan-Durbar-${stamp}`);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByLabel("Business name").fill(`Thamel Threads ${stamp}`);
  await page.getByRole("button", { name: "Create business" }).click();
  await expect(page).toHaveURL(/\/home$/);

  await page.goto("/products");
  await expect(page.getByRole("heading", { name: "Products", level: 1 })).toBeVisible();
  await page.getByRole("link", { name: /Add (your first )?product/ }).first().click();
  await expect(page).toHaveURL(/\/products\/new$/);

  await page.getByLabel("Title", { exact: true }).fill(`Cotton Kurta ${stamp}`);
  await page.getByLabel("Title in Nepali").fill("सुती कुर्ता");
  // Price on the default row carries into every generated combination.
  await page.getByLabel("Price (रू) · Default").fill("1250.50");

  await page.getByRole("button", { name: "Add option" }).click();
  await page.getByLabel("Option name").nth(0).fill("Size");
  await page.getByLabel("Values").nth(0).fill("M");
  await page.getByLabel("Values").nth(0).press("Enter");
  await page.getByLabel("Values").nth(0).fill("L");
  await page.getByLabel("Values").nth(0).press("Enter");
  await page.getByRole("button", { name: "Add option" }).click();
  await page.getByLabel("Option name").nth(1).fill("Colour");
  await page.getByLabel("Values").nth(1).fill("Maroon");
  await page.getByLabel("Values").nth(1).press("Enter");
  await page.getByLabel("Values").nth(1).fill("Black");
  await page.getByLabel("Values").nth(1).press("Enter");

  const grid = page.getByTestId("variant-grid");
  await expect(grid.locator("tbody tr")).toHaveCount(4);
  await expect(grid.getByLabel("Price (रू) · L / Black")).toHaveValue("1250.50");

  await page.getByRole("button", { name: "Save as draft" }).click();
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]{36}$/);
  const status = page.getByTestId("status-control");
  await expect(status.getByText("Draft", { exact: true })).toBeVisible();
  await expect(page.getByTestId("variant-grid").locator("tbody tr")).toHaveCount(4);

  await status.getByRole("button", { name: "Publish" }).click();
  await expect(status.getByText("Active", { exact: true })).toBeVisible();
  await expect(status.getByRole("button", { name: "Move to draft" })).toBeVisible();

  await status.getByRole("button", { name: "Archive" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Archive" }).click();
  await expect(status.getByText("Archived", { exact: true })).toBeVisible();
  await expect(status.getByRole("button", { name: "Restore as draft" })).toBeVisible();

  // It now lives under the Archived tab only.
  await page.goto("/products");
  await page.getByRole("tab", { name: "Archived" }).click();
  await expect(page.getByRole("link", { name: `Cotton Kurta ${stamp}` })).toBeVisible();
  expect(failures).toEqual([]);
});
