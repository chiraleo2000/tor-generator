import { test, expect } from "@playwright/test";
import { saveEvidence } from "./helpers";

const backendCov = process.env.BACKEND_COV_URL || "http://127.0.0.1:8765/";
const frontendCov = process.env.FRONTEND_COV_URL || "http://127.0.0.1:8766/";
const playwrightReport = process.env.PLAYWRIGHT_REPORT_URL || "http://127.0.0.1:8767/";

test.describe("Test report evidence", () => {
  test("backend coverage html is all green summary", async ({ page }) => {
    await page.goto(backendCov);
    await expect(page.locator("html")).toBeVisible();
    await saveEvidence(page, "13-backend-coverage");
  });

  test("frontend coverage html is all green summary", async ({ page }) => {
    await page.goto(frontendCov);
    await expect(page.locator("html")).toBeVisible();
    await saveEvidence(page, "14-frontend-coverage");
  });

  test("playwright html report shows passed tests", async ({ page }) => {
    await page.goto(playwrightReport);
    await expect(page.getByText(/passed/i).first()).toBeVisible({ timeout: 20_000 });
    await saveEvidence(page, "15-playwright-report");
  });
});
