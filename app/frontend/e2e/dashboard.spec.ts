import { test, expect } from "@playwright/test";
import { login, skipReason, skipUnlessLive } from "./helpers";

test.describe("Dashboard", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  test.skip(skipUnlessLive, skipReason);

  test("shows stat cards and creates a project from the intake dialog", async ({ page }) => {
    await login(page);
    await expect(page.getByText("ร่าง (Draft)")).toBeVisible();
    await expect(page.getByText("รายการโครงการ TOR")).toBeVisible();
    await page.getByTestId("new-project").click();
    await expect(page.getByTestId("new-project-dialog")).toBeVisible();
    await page.getByTestId("new-project-name").fill("โครงการทดสอบ E2E");
    await page.getByTestId("new-project-ministry").fill("กรมบัญชีกลาง");
    await page.getByTestId("new-project-budget").fill("100000");
    await page.getByTestId("create-project-submit").click();
    await expect(page.getByTestId("draft-page")).toBeVisible({ timeout: 20_000 });
  });
});
