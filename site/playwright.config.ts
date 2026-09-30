import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://127.0.0.1:4322",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    // Astro 7 otherwise auto-backgrounds in agent environments; Playwright owns lifecycle.
    command: "pnpm preview --port 4322 --ignore-lock",
    url: "http://127.0.0.1:4322/ftms/",
    reuseExistingServer: false,
  },
});
