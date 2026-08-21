import { test, expect } from "@playwright/test";
import {
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
  test.skip(skipUnlessLive, skipReason);

  test("login, create project, walk Phase 0-4", async ({ page }) => {
    test.setTimeout(180_000);
    await login(page);
    await saveEvidence(page, "02-dashboard");
    await createProjectAndOpenDraft(page);
    await walkFivePhases(page);
  });

  test("Phase 2 AI draft uses LM Studio Gemma", async ({ page }) => {
    test.setTimeout(900_000);
    await login(page);
    await createProjectAndOpenDraft(page);
    await walkLiveDraftToCompose(page);
    await expect(page.getByTestId("phase3-draft")).toBeVisible();
    await expect(page.getByTestId("draft-chat")).toBeVisible();
    await expect(page.getByTestId("section-preview-s1")).toContainText(/\S.{20,}/, {
      timeout: 360_000,
    });
    await expect(page.getByText("ร่างด้วย AI ไม่สำเร็จ")).toHaveCount(0);
    await saveEvidence(page, "08-phase-2-ai-draft");
  });
});
