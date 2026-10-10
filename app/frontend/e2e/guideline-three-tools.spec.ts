import { test } from "@playwright/test";
import {
  analyzeRealDraft,
  askGuidelineChat,
  openCalculatedWorksheet,
  reviewRealDraft,
} from "./guideline-flow";
import { CHAT_QUESTIONS } from "./guideline-questions";

export { CHAT_QUESTIONS };

test.use({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  video: { mode: "on", size: { width: 1920, height: 1080 } },
});

test.describe.serial("Guideline three tools at 1920x1080", () => {
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 so CI without the local stack does not fail.
  test.skip(process.env.E2E !== "1", "Set E2E=1 against the local stack");

  test("01 draft five-category worksheet", async ({ page }) => {
    test.setTimeout(14_400_000);
    await openCalculatedWorksheet(page);
  });

  test("02 review budget finding and risk panel", async ({ page }) => {
    test.setTimeout(900_000);
    await reviewRealDraft(page);
  });

  test("03 analyze budget finding and risk panel", async ({ page }) => {
    test.setTimeout(420_000);
    await analyzeRealDraft(page);
  });

  test("04 chat rate defaults and circulars", async ({ page }) => {
    test.setTimeout(4_800_000);
    await askGuidelineChat(page);
  });
});
