import { expect, test } from "./fixtures";

test.skip(!process.env.E2E_BASE_URL, "Set E2E_BASE_URL to run against a live web + backend stack");

/**
 * register → (auto sign-in) → onboarding → home → sign out → sign in again.
 * Uses a unique email per run; requires the backend to be reachable from the web app.
 */
test("new seller registers, creates a business and signs back in", async ({ page }, testInfo) => {
  // Unique per project: desktop and mobile run in parallel and may share a millisecond.
  const stamp = `${Date.now()}${testInfo.parallelIndex}`;
  const email = `e2e+${stamp}@example.com`;
  const password = `Kathmandu-${stamp}`;

  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);

  // Middleware sends anonymous visitors to /login.
  await page.goto("/home");
  await expect(page).toHaveURL(/\/login/);

  await page.getByRole("link", { name: "Create an account" }).click();
  await page.getByLabel("Full name").fill("Sita Gurung");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByLabel("Business name").fill(`Thamel Threads ${stamp}`);
  await expect(page.getByLabel("Shop handle")).toHaveValue(`thamel-threads-${stamp}`);
  await page.getByRole("button", { name: "Create business" }).click();

  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByText("Nothing needs you right now")).toBeVisible();

  // Refresh token is httpOnly: not readable from page JS.
  const visibleCookies = await page.evaluate(() => document.cookie);
  expect(visibleCookies).not.toContain("cos_rt");

  // Reload restores the session from the cookie.
  await page.reload();
  await expect(page.getByText("Nothing needs you right now")).toBeVisible();

  // Sign out and back in.
  const accountButton = page.getByRole("button", { name: /^Account:/ });
  if (await accountButton.isHidden()) await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("button", { name: /^Account:/ }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/home$/);
});
