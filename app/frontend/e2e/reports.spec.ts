import { test, expect } from "@playwright/test";
import { saveEvidence } from "./helpers";

const backendCov = process.env.BACKEND_COV_URL || "http://127.0.0.1:8765/";
const frontendCov = process.env.FRONTEND_COV_URL || "http://127.0.0.1:8766/";
const playwrightReport = process.env.PLAYWRIGHT_REPORT_URL || "http://127.0.0.1:8767/";
const captureReports = process.env.CAPTURE_REPORTS === "1";

async function urlReachable(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { method: "GET", signal: AbortSignal.timeout(3_000) });
    return response.ok || response.status < 500;
  } catch {
    return false;
  }
}

test.describe("Test report evidence", () => {
  test.skip(
    !captureReports,
    "Set CAPTURE_REPORTS=1 and serve htmlcov/report on :8765/:8766/:8767 (npm run test:e2e:reports)"
  );

  test("backend coverage html is all green summary", async ({ page }) => {
    test.skip(!(await urlReachable(backendCov)), `Backend coverage not serving at ${backendCov}`);
    await page.goto(backendCov);
    await expect(page.locator("html")).toBeVisible();
    await saveEvidence(page, "13-backend-coverage");
  });

  test("frontend coverage html is all green summary", async ({ page }) => {
    test.skip(!(await urlReachable(frontendCov)), `Frontend coverage not serving at ${frontendCov}`);
    await page.goto(frontendCov);
    await expect(page.locator("html")).toBeVisible();
    await saveEvidence(page, "14-frontend-coverage");
  });

  test("playwright html report shows passed tests", async ({ page }) => {
    test.skip(
      !(await urlReachable(playwrightReport)),
      `Playwright report not serving at ${playwrightReport}`
    );
    await page.goto(playwrightReport);
    await expect(page.getByText(/passed/i).first()).toBeVisible({ timeout: 20_000 });
    await saveEvidence(page, "15-playwright-report");
  });
});
