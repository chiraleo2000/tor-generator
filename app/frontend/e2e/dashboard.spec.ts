import { test, expect } from "@playwright/test";
import {
  login,
  pauseLikeUser,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
} from "./helpers";

test.describe("Dashboard", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("shows stat cards and creates a project from the intake dialog", async ({ page }) => {
    await login(page);
    await expect(page.getByText("ร่าง (Draft)")).toBeVisible();
    await expect(page.getByText("รายการโครงการ TOR")).toBeVisible();
    await saveEvidence(page, "02-dashboard");
    await page.getByTestId("new-project").click();
    await expect(page.getByTestId("new-project-dialog")).toBeVisible();
    await saveEvidence(page, "02b-create-dialog");
    await typeLikeUser(page.getByTestId("new-project-name"), "โครงการทดสอบ E2E");
    await pauseLikeUser(page, 300);
    await typeLikeUser(page.getByTestId("new-project-ministry"), "กรมบัญชีกลาง");
    await pauseLikeUser(page, 300);
    await typeLikeUser(page.getByTestId("new-project-budget"), "100000");
    await pauseLikeUser(page, 400);
    await page.getByTestId("create-project-submit").click();
    await expect(page.getByTestId("draft-page")).toBeVisible({ timeout: 20_000 });
  });
});
