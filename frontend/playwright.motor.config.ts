import { defineConfig, devices } from "@playwright/test";

const frontendPort = 3106;
const backendPort = 3206;
const baseURL = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./tests/motor-e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  outputDir: "test-results/motor",
  reporter: [["line"], ["html", { open: "never", outputFolder: "playwright-report/motor" }]],
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { height: 900, width: 1440 } } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"], deviceScaleFactor: 1, viewport: { height: 844, width: 390 } } },
  ],
  webServer: [
    { command: `node tests/motor-e2e/backend-fixture.mjs --port ${backendPort}`, reuseExistingServer: false, timeout: 30_000, url: `http://127.0.0.1:${backendPort}/health` },
    {
      command: `npm run build && npm run start -- --hostname 127.0.0.1 --port ${frontendPort}`,
      env: {
        FRONTEND_BACKEND_URL: `http://127.0.0.1:${backendPort}`,
        FRONTEND_ORIGIN: baseURL,
        FRONTEND_SESSION_KEY: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        FRONTEND_SESSION_KEY_ID: "motor-current",
      },
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${baseURL}/login`,
    },
  ],
});
