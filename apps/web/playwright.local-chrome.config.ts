import base from "./playwright.config";
import { defineConfig } from "@playwright/test";

// Local-only: run E2E with the system Chrome instead of downloaded Playwright browsers.
export default defineConfig({
  ...base,
  projects: (base.projects ?? []).map((p) => ({ ...p, use: { ...p.use, channel: "chrome" } })),
});
