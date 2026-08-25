import { test, expect } from "@playwright/test";
import {
  createProjectAndOpenDraft,
  headedRun,
  login,
  saveEvidence,
  skipMockedInHeadedReason,
  skipReason,
  skipUnlessLive,
  walkMockedIntakeToPhase4,
} from "./helpers";

test.describe("Intake wizard UI 0–4", () => {
  // NOSONAR: Playwright E2E spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);
  // NOSONAR: Headed runs walk live Phase 0–4 (wizard-flow) instead of mocked APIs.
  test.skip(headedRun, skipMockedInHeadedReason);

  test("walks Phase 0–4 with table, skip, chat, and review chat", async ({ page }) => {
    test.setTimeout(180_000);
    await login(page);
    await createProjectAndOpenDraft(page);
    await expect(page.getByTestId("phase0-upload")).toBeVisible();
    await expect(page.getByTestId("intake-paste")).toBeVisible();
    await expect(page.getByTestId("intake-upload")).toBeVisible();
    await expect(page.getByTestId("intake-start-analyze")).toBeVisible();
    await walkMockedIntakeToPhase4(page);
    await expect(page.getByTestId("intake-enter-qa")).toHaveCount(0);
    await expect(page.getByTestId("run-review")).toBeVisible();
    await expect(page.getByTestId("review-chat")).toBeVisible();
    await expect(page.getByTestId("review-chat-input")).toBeVisible();
    await expect(page.getByTestId("export-docx")).toBeVisible();
    await expect(page.getByTestId("export-pdf")).toBeVisible();
    await page.getByTestId("review-chat-input").fill("ตรวจอีกครั้ง");
    await page.getByTestId("review-chat-send").click();
    await expect(page.getByTestId("review-chat-messages")).toContainText("ตรวจอีกครั้ง");
    await saveEvidence(page, "e2e-phase-4-review-chat");
  });
});
