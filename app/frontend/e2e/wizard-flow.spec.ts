import { test, expect } from "@playwright/test";
import {
  REVIEWER_EMAIL,
  DEMO_PASSWORD,
  confirmPhase,
  createProjectAndOpenDraft,
  finishLivePhase3ToSubmit,
  login,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  walkFivePhases,
} from "./helpers";

const RESUME_PROJECT_ID =
  process.env.E2E_RESUME_PROJECT_ID || "97101901-dbbc-4124-8b20-3900516b7678";
const RESUME_PHASE3_ID =
  process.env.E2E_RESUME_PHASE3_ID || "95168d5f-c9ec-4fc3-8fa1-f6c5d8ec9c37";

test.describe("TOR 5-phase draft", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("complete draft has no per-section HITL and re-enters review", async ({ page }) => {
    test.setTimeout(180_000);
    await login(page);
    const response = await page.goto(`/projects/${RESUME_PROJECT_ID}/draft`);
    expect(response?.ok(), `resume project ${RESUME_PROJECT_ID}`).toBeTruthy();
    await expect(page.getByTestId("draft-page")).toBeVisible();
    if ((await page.getByTestId("phase4-review").count()) > 0) {
      await expect(page.getByText("ยังไม่ได้ยืนยันหมวดที่เจ้าหน้าที่ต้องตรวจ")).toHaveCount(0);
      await expect(page.getByTestId("phase4-review")).toContainText(
        "เอกสารที่อัปโหลดในขั้นที่ ๐ ของโครงการนี้"
      );
      await expect(page.getByTestId("phase4-submit")).toBeEnabled();
      await saveEvidence(page, "resume-phase4-entered");
      await page.getByTestId("phase3-back").click();
    }
    await expect(page.getByTestId("phase3-draft")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("hitl-confirm-s3")).toHaveCount(0);
    await expect(page.getByText("ต้องให้เจ้าหน้าที่ยืนยัน")).toHaveCount(0);
    await expect(page.getByTestId("phase3-confirm")).toBeEnabled();
    await saveEvidence(page, "resume-phase3-fields");
    await page.getByTestId("phase3-confirm").click();
    await confirmPhase(page);
    await expect(page.getByTestId("phase4-review")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("phase4-review")).toContainText(
      "เอกสารที่อัปโหลดในขั้นที่ ๐ ของโครงการนี้"
    );
    await expect(page.getByTestId("phase4-submit")).toBeEnabled();
    await saveEvidence(page, "resume-phase4-entered");
  });

  test("resume live Phase 3 draft through review, export, submit, and approve", async ({
    page,
  }) => {
    test.setTimeout(600_000);
    await login(page);
    const response = await page.goto(`/projects/${RESUME_PHASE3_ID}/draft`);
    expect(response?.ok(), `resume phase3 ${RESUME_PHASE3_ID}`).toBeTruthy();
    await expect(page.getByTestId("phase3-draft")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("phase3-all-drafted")).toBeVisible();
    const projectName = (
      await page.getByTestId("draft-page").locator("p").first().innerText()
    ).trim();
    await finishLivePhase3ToSubmit(page);
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
