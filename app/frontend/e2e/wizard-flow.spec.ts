import { test, expect } from "@playwright/test";
import {
  REVIEWER_EMAIL,
  DEMO_PASSWORD,
  createProjectAndOpenDraft,
  login,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  walkFivePhases,
  walkLiveDraftToCompose,
} from "./helpers";

test.describe("TOR 5-phase draft", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("create project, enter Phase 3 with no per-section HITL", async ({ page }) => {
    test.setTimeout(1_800_000);
    await login(page);
    await createProjectAndOpenDraft(page);
    await walkLiveDraftToCompose(page);
    await expect(page.getByTestId("phase3-draft")).toBeVisible();
    await expect(page.getByTestId("phase3-heading")).toBeVisible();
    await expect(page.getByTestId("hitl-confirm-s3")).toHaveCount(0);
    await expect(page.getByText("ต้องให้เจ้าหน้าที่ยืนยัน")).toHaveCount(0);
    await saveEvidence(page, "resume-phase3-fields");
  });

  test("login, create project, walk live Phase 0-4 through AI draft, Rule Engine, and export", async ({
    page,
  }) => {
    test.setTimeout(4_800_000);
    await login(page);
    await saveEvidence(page, "02-dashboard");
    const projectName = await createProjectAndOpenDraft(page);
    await walkFivePhases(page);
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await page.getByTestId("logout").click();
    await expect(page.getByTestId("login-form")).toBeVisible();
    await login(page, REVIEWER_EMAIL, DEMO_PASSWORD);
    const row = page.getByRole("row", { name: projectName });
    await expect(row).toBeVisible();
    await row.getByTestId("approve-project").click();
    await expect(row.getByText("เสร็จแล้ว")).toBeVisible({ timeout: 20_000 });
    await saveEvidence(page, "02c-reviewer-dashboard");
  });
});
