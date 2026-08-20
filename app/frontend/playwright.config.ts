import { defineConfig, devices } from "@playwright/test";

const e2eEnabled = process.env.E2E === "1";
const headed = process.env.HEADED === "1";
const captureReports = process.env.CAPTURE_REPORTS === "1";
const captureGuide = process.env.CAPTURE_GUIDE === "1";

/**
 * Optional suites stay ignored unless their own flag is set.
 * Never clear the whole ignore list when a capture flag leaks into the shell —
 * that used to pull reports/guide into `test:e2e:headed` and fail on missing :8765/:8766.
 */
function ignoredSpecs(): string[] {
  if (!e2eEnabled && !captureReports && !captureGuide) {
    return ["**/*.spec.ts"];
  }
  const ignore: string[] = [];
  if (!captureReports) ignore.push("**/reports.spec.ts");
  if (!captureGuide) ignore.push("**/guide-shots.spec.ts");
  return ignore;
}

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ignoredSpecs(),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // Shared demo officer account on the live Docker stack — parallel workers collide.
  workers: 1,
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
