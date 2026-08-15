import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/jornadas-e2e",
  globalSetup: "./tests/jornadas-e2e/real-stack.mjs",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  outputDir: "test-results/jornadas",
  reporter: [["line"], ["html", { open: "never", outputFolder: "playwright-report/jornadas" }]],
  use: { screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { height: 900, width: 1440 } } },
  ],
});
