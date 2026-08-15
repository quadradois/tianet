import { defineConfig, devices } from "@playwright/test";

const frontendPort = 3101;
const backendPort = 3201;
const baseURL = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./tests/session-e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  outputDir: "test-results/session",
  reporter: [["line"], ["html", { open: "never", outputFolder: "playwright-report/session" }]],
  use: {
    baseURL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { height: 900, width: 1440 } } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"], viewport: { height: 844, width: 390 } } },
  ],
  webServer: [
    {
      command: `node tests/session-e2e/backend-fixture.mjs --port ${backendPort}`,
      reuseExistingServer: false,
      timeout: 30_000,
      url: `http://127.0.0.1:${backendPort}/health`,
    },
    {
      command: `npm run dev -- --hostname 127.0.0.1 --port ${frontendPort}`,
      env: {
        FRONTEND_BACKEND_URL: `http://127.0.0.1:${backendPort}`,
        FRONTEND_ORIGIN: baseURL,
        FRONTEND_SESSION_KEY: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        FRONTEND_SESSION_KEY_ID: "e2e-current",
      },
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${baseURL}/login`,
    },
  ],
});
