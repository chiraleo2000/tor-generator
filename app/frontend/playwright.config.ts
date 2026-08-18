import { defineConfig, devices } from "@playwright/test";

const e2eEnabled = process.env.E2E === "1";
const headed = process.env.HEADED === "1";
const captureReports = process.env.CAPTURE_REPORTS === "1";
const captureGuide = process.env.CAPTURE_GUIDE === "1";

function ignoredSpecs(): string[] {
  if (captureReports || captureGuide) return [];
  if (!e2eEnabled) return ["**/*.spec.ts"];
  return ["**/reports.spec.ts", "**/guide-shots.spec.ts"];
}

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ignoredSpecs(),
  fullyParallel: !headed,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: headed ? 1 : undefined,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    locale: "th-TH",
    colorScheme: "light",
    viewport: { width: 1440, height: 900 },
    screenshot: headed ? "on" : "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
    launchOptions: headed ? { slowMo: 250 } : undefined,
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        colorScheme: "light",
      },
    },
  ],
  webServer: e2eEnabled
    ? {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: true,
        timeout: 120_000,
      }
    : undefined,
});
