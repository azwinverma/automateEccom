import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

test.skip(!process.env.E2E_BASE_URL, "Set E2E_BASE_URL to run against a live web + backend stack");

/**
 * QA-001 / QA-008: the links inside Nivaro's emails must work in the web app.
 * Reads the dev mailbox (.data/mailbox) the backend's console mailer writes to, so this needs the
 * backend + worker of the same checkout.
 */
const MAILBOX = join(import.meta.dirname, "..", "..", "..", ".data", "mailbox");
const PASSWORD = "Patan-Durbar-E2E-2026";

async function linkFromMail(to: string, path: string, timeoutMs = 20_000): Promise<string> {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const files = readdirSync(MAILBOX)
      .map((f) => join(MAILBOX, f))
      .filter((f) => Date.now() - statSync(f).mtimeMs < 5 * 60_000);
    for (const f of files) {
      const body = readFileSync(f, "utf8");
      if (body.includes(`To: ${to}`)) {
        const m = body.match(new RegExp(`https?://[^\\s]+${path.replace("?", "\\?")}[^\\s]+`));
        if (m) return new URL(m[0]).pathname + new URL(m[0]).search;
      }
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`no ${path} email for ${to}`);
}

async function signUp(page: Page, email: string, name = "Sita Gurung") {
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
}

test.beforeEach(async ({ page }) => {
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
});

test("forgot password → email link → new password → sign in", async ({ page }, info) => {
  const email = `e2e-reset+${Date.now()}${info.parallelIndex}@example.com`;
  await page.goto("/register");
  await signUp(page, email);
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.context().clearCookies();
  await page.context().addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);

  await page.goto("/login");
  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();

  await page.goto(await linkFromMail(email, "/reset-password?token="));
  await page.getByLabel("New password").fill("1234567890"); // ≥10 chars, but on the server's common list
  await page.getByRole("button", { name: "Save new password" }).click();
  await expect(page.getByText(/stronger password/)).toBeVisible();
  await page.getByLabel("New password").fill("Bhaktapur-Square-2027");
  await page.getByRole("button", { name: "Save new password" }).click();
  await expect(page.getByRole("heading", { name: "Password changed" })).toBeVisible();

  await page.getByRole("link", { name: "Sign in" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("Bhaktapur-Square-2027");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
});

test("team invitation email → sign up → accept → lands in the shop", async ({ page, browser }, info) => {
  const stamp = `${Date.now()}${info.parallelIndex}`;
  // Owner creates a shop and invites a staff member.
  await page.goto("/register");
  await signUp(page, `e2e-owner+${stamp}@example.com`);
  await page.getByLabel("Business name").fill(`Invite Shop ${stamp}`);
  await page.getByRole("button", { name: "Create business" }).click();
  await expect(page).toHaveURL(/\/home$/);
  const invitee = `e2e-invitee+${stamp}@example.com`;
  const res = await page.evaluate(async (email) => {
    // Use the app's own BFF session for the API call (same path the Team screen uses).
    const s = await fetch("/api/session/refresh", { method: "POST" }).then((r) => r.json());
    const me = await fetch("/api/v1/me", { headers: { Authorization: `Bearer ${s.access_token}` } }).then((r) => r.json());
    const mid = me.memberships[0].merchant.id;
    const r = await fetch("/api/v1/invitations", {
      method: "POST",
      headers: { Authorization: `Bearer ${s.access_token}`, "X-Merchant-Id": mid, "Content-Type": "application/json" },
      body: JSON.stringify({ email, role: "staff" }),
    });
    return r.status;
  }, invitee);
  expect(res).toBe(201);

  // Invitee opens the email link signed out, creates an account, accepts, and lands in the shop.
  const ctx = await browser.newContext();
  await ctx.addCookies([{ name: "cos_locale", value: "en", url: process.env.E2E_BASE_URL! }]);
  const p2 = await ctx.newPage();
  await p2.goto(await linkFromMail(invitee, "/invite?token="));
  await expect(p2.getByRole("heading", { name: "Join the team" })).toBeVisible();
  await p2.getByRole("link", { name: "Create an account" }).click();
  await expect(p2).toHaveURL(/\/register\?next=/);
  await signUp(p2, invitee, "Ram Thapa");
  await expect(p2).toHaveURL(/\/invite\?token=/);
  await p2.getByRole("button", { name: "Accept invitation" }).click();
  await expect(p2).toHaveURL(/\/home$/);
  // The shop switcher/top bar shows the shop the invitee just joined (sidebar is collapsed on mobile).
  await expect(p2.getByText(`Invite Shop ${stamp}`).filter({ visible: true }).first()).toBeVisible();
  await ctx.close();
});

test("email verification link confirms the address", async ({ page }, info) => {
  const email = `e2e-verify+${Date.now()}${info.parallelIndex}@example.com`;
  await page.goto("/register");
  await signUp(page, email);
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.goto(await linkFromMail(email, "/verify-email?token="));
  await expect(page.getByRole("heading", { name: "Email confirmed" })).toBeVisible();
  // Single use: opening it again explains instead of erroring.
  await page.reload();
  await expect(page.getByRole("heading", { name: "This link didn't work" })).toBeVisible();
});
