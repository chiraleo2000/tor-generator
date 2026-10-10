import { test } from "@playwright/test";
import {
  analyzeRealDraft,
  askGuidelineChat,
  openCalculatedWorksheet,
  reviewRealDraft,
} from "./guideline-flow";

test.use({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  video: { mode: "on", size: { width: 1920, height: 1080 } },
});

test.describe("Guideline four tools at 1920x1080", () => {
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 so CI without the local stack does not fail.
  test.skip(process.env.E2E !== "1", "Set E2E=1 against the local stack");

  test("four tools draft review analyze chat", async ({ page }) => {
    test.setTimeout(4_800_000);
    await openCalculatedWorksheet(page);
    await reviewRealDraft(page);
    await analyzeRealDraft(page);
    await askGuidelineChat(page);
  });
});
