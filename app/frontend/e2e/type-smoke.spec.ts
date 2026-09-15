import { test, expect } from "@playwright/test";
import {
  HIRE_MAINTAIN_INTAKE_TEXT,
  createProjectAndOpenDraft,
  login,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  walkLiveAnalyzeToPhase1,
} from "./helpers";

test.describe("hire_maintain smoke (Phase 0–1 only)", () => {
  test.skip(skipUnlessLive, skipReason);

  test("analyzes MA pack into asset_list and does not start Phase 3 compose", async ({
    page,
  }) => {
    test.setTimeout(420_000);
    await login(page);
    await createProjectAndOpenDraft(page, undefined, "hire_maintain");
    await walkLiveAnalyzeToPhase1(page, HIRE_MAINTAIN_INTAKE_TEXT);
    await expect(page.getByTestId("coverage-row-asset_list")).toBeVisible();
    await expect(page.getByTestId("coverage-row-asset_list")).toHaveAttribute(
      "data-status",
      "filled"
    );
    await expect(page.getByTestId("phase3-draft")).toHaveCount(0);
    await expect(page.getByTestId("draft-chat")).toHaveCount(0);
    await saveEvidence(page, "ui-workflow-ma-phase1");
  });
});
