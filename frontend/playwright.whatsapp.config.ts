import { defineConfig, devices } from "@playwright/test";

const frontendPort = 3109;
const backendPort = 3209;
const baseURL = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  forbidOnly: true,
  fullyParallel: false,
  outputDir: "test-results/whatsapp",
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { height: 900, width: 1440 } } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"], deviceScaleFactor: 1, viewport: { height: 844, width: 390 } } },
  ],
  reporter: [["line"], ["html", { open: "never", outputFolder: "playwright-report/whatsapp" }]],
  retries: process.env.CI ? 1 : 0,
  testDir: "./tests/whatsapp-e2e",
  use: { baseURL, screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: [
    { command: `node tests/whatsapp-e2e/backend-fixture.mjs --port ${backendPort}`, reuseExistingServer: false, timeout: 30_000, url: `http://127.0.0.1:${backendPort}/health` },
    {
      command: `node scripts/require-build.mjs && npm run start -- --hostname 127.0.0.1 --port ${frontendPort}`,
      env: {
        FRONTEND_BACKEND_URL: `http://127.0.0.1:${backendPort}`,
        FRONTEND_ORIGIN: baseURL,
        FRONTEND_SESSION_KEY: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        FRONTEND_SESSION_KEY_ID: "whatsapp-current",
      },
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${baseURL}/login`,
    },
  ],
  workers: 1,
});
