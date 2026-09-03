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

/** Separate process from the operator's daily Chrome/Edge windows. */
const headedChannel = process.env.E2E_CHANNEL || "";

function headedLaunchOptions() {
  return {
    slowMo: Number(process.env.E2E_SLOWMO_MS || "400"),
    args: [
      "--new-window",
      "--window-position=80,80",
      "--window-size=1280,860",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-session-crashed-bubble",
    ],
  };
}

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ignoredSpecs(),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // Shared demo officer account on the live Docker stack — parallel workers collide.
  workers: 1,
  timeout: headed ? 4_800_000 : 180_000,
  expect: { timeout: headed ? 30_000 : 15_000 },
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    locale: "th-TH",
    colorScheme: "light",
    viewport: { width: 1280, height: 800 },
    screenshot: headed ? "on" : "only-on-failure",
    video: process.env.E2E_VIDEO === "1" ? "on" : "off",
    trace: process.env.E2E_TRACE === "1" ? "on" : "retain-on-failure",
    actionTimeout: headed ? 60_000 : 20_000,
    navigationTimeout: 30_000,
    headless: !headed,
    launchOptions: headed ? headedLaunchOptions() : undefined,
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 800 },
        colorScheme: "light",
        // Default: Playwright Chromium (own binary + temp profile).
        // Do not default to channel "chrome" — that launches Google Chrome and
        // steals/mixes with the operator's everyday windows.
        // Override only when needed: E2E_CHANNEL=chrome
        ...(headed && headedChannel ? { channel: headedChannel } : {}),
      },
    },
  ],
  webServer: e2eEnabled
    ? {
        command: "npm run dev",
        url: process.env.E2E_BASE_URL || "http://localhost:3000",
        reuseExistingServer: true,
        timeout: 120_000,
      }
    : undefined,
});
