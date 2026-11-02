import { expect, test } from "@playwright/test";

test.skip(!process.env.E2E_BASE_URL, "Set E2E_BASE_URL to run against a live web + backend stack");

/** Every settings screen renders real data from the backend without error states. */
test("settings screens load against the live API", async ({ page }, testInfo) => {
  const stamp = `${Date.now()}${testInfo.parallelIndex}`;
  const email = `e2e-settings+${stamp}@example.com`;
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  const failures: string[] = [];
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 400) failures.push(`${r.status()} ${r.url()}`);
  });

  await page.goto("/register");
  await page.getByLabel("Full name").fill("Ramesh Thapa");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(`Bhaktapur-${stamp}`);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByLabel("Business name").fill(`Bhaktapur Pottery ${stamp}`);
  await page.getByRole("button", { name: "Create business" }).click();
  await expect(page).toHaveURL(/\/home$/);

  for (const path of ["/settings/team", "/settings/security", "/settings/plan", "/settings/audit"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expect(page.locator("[role=alert]").filter({ hasText: /went wrong|couldn.t load|try again/i })).toHaveCount(0);
  }
  await page.goto("/settings/audit");
  await expect(page.getByText("merchants.merchant_created").or(page.getByText(/business created/i)).first()).toBeVisible();
  expect(failures).toEqual([]);
});
