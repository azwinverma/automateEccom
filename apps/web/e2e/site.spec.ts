import { expect, test } from "@playwright/test";

test.skip(!process.env.E2E_BASE_URL, "Set E2E_BASE_URL to run against a live web + backend stack");

/** Public website → sign-up and sign-in entry points; light theme by default, dark on request. */
test("landing page leads to sign-up and sign-in, light by default", async ({ page }) => {
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Your store, on autopilot.");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  // Theme switch persists across navigation (desktop header; on mobile it lives in the menu).
  const menu = page.getByRole("button", { name: "Menu" });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("button", { name: "Dark" }).first().click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("button", { name: "Light" }).first().click();

  if (await menu.isVisible()) await menu.click();
  await page.getByRole("link", { name: "Start free" }).first().click();
  await expect(page).toHaveURL(/\/register$/);
  await page.goto("/");
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("link", { name: "Sign in" }).first().click();
  await expect(page).toHaveURL(/\/login$/);
});
