import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import fs from "node:fs";
import path from "node:path";
import {
  createProjectAndOpenDraft,
  headedRun,
  login,
  pauseLikeUser,
  saveEvidence,
  skipMockedInHeadedReason,
  skipReason,
  skipUnlessLive,
} from "./helpers";

const ECT_PACK = fs.readFileSync(
  path.resolve(__dirname, "../../backend/tests/fixtures/ect_ai_chatbot_pack.txt"),
  "utf-8"
);

test.describe("ECT AI Chatbot live pack", () => {
  test.skip(skipUnlessLive, skipReason);
  test.skip(!headedRun, skipMockedInHeadedReason);

  test("Phase 0–1 coverage from ECT TOR then standalone review", async ({ page }) => {
    test.setTimeout(420_000);
    await login(page);
    await createProjectAndOpenDraft(page, `ECT AI Chatbot UI ${Date.now()}`);
    await page.getByTestId("intake-paste").fill(ECT_PACK);
    await pauseLikeUser(page, 400);
    await page.getByTestId("intake-upload").setInputFiles({
      name: "ect-ai-chatbot-tor.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(ECT_PACK, "utf-8"),
    });
    await expect(page.getByTestId("phase0-file-list")).toContainText("ect-ai-chatbot-tor.txt", {
      timeout: 30_000,
    });
    await saveEvidence(page, "ect-phase-0-pack");
    await page.getByTestId("intake-start-analyze").click();
    await page.getByTestId("confirm-phase-ok").click();
    await expect(page.getByTestId("phase1-coverage")).toBeVisible({ timeout: 240_000 });
    await expect(page.getByTestId("coverage-row-s1")).toHaveAttribute("data-status", "filled");
    await expect(page.getByTestId("coverage-row-s5")).toHaveAttribute("data-status", "filled");
    await expect(page.getByTestId("coverage-row-s6")).toHaveAttribute("data-status", "filled");
    await expect(page.getByTestId("coverage-row-s4.1")).toHaveAttribute("data-status", "filled");
    await expect(page.getByTestId("coverage-row-s1")).toContainText(/ECT|กกต|Chatbot/);
    await expect(page.getByTestId("coverage-row-s6")).toContainText("15,000,000");
    await saveEvidence(page, "ect-phase-1-coverage");

    await page.getByTestId("nav-review").click();
    await expect(page.getByTestId("review-page")).toBeVisible();
    const fileInput = page.locator("[data-testid=review-page] input[type=file]").first();
    await fileInput.setInputFiles({
      name: "ect-ai-chatbot-tor.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(ECT_PACK, "utf-8"),
    });
    await expect(page.getByTestId("review-extract")).toBeEnabled();
    await page.getByTestId("review-extract").click();
    await expect(page.getByTestId("review-extract-preview")).toBeVisible({ timeout: 120_000 });
    await expect(page.getByTestId("review-extract-preview")).toContainText(/กกต|Chatbot|15,000,000/);
    await saveEvidence(page, "ect-standalone-extract");
    await page.getByTestId("review-confirm-run").click();
    await expect(page.getByTestId("review-score")).toBeVisible({ timeout: 180_000 });
    await expect(page.getByTestId("review-result")).toContainText("คะแนนความพร้อม");
    await saveEvidence(page, "ect-standalone-score");
  });
});
