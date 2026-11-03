import { expect, test as base } from "@playwright/test";

/**
 * Every E2E test fails if the page reports a Content-Security-Policy violation (QA-009):
 * a too-strict policy silently breaks uploads, images or scripts in production.
 */
export const test = base.extend<{ cspGuard: void }>({
  cspGuard: [
    async ({ page }, use) => {
      const violations: string[] = [];
      page.on("console", (m) => {
        if (/Content Security Policy|Refused to (load|connect|execute|apply)/i.test(m.text())) violations.push(m.text());
      });
      await use();
      expect(violations, "CSP violations").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
