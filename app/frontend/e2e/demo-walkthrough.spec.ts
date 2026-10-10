import { test, expect, type Page } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  ADMIN_EMAIL,
  DEMO_PASSWORD,
  LIVE_INTAKE_TEXT,
  createProjectAndOpenDraft,
  login,
  pauseLikeUser,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
  waitForLiveAssistant,
  walkLiveDraftToCompose,
  finishLivePhase3ToSubmit,
} from "./helpers";

/**
 * Headed/live walkthrough that records video of the four work tools plus admin AI.
 * Skipped unless E2E=1 so CI without a live stack does not fail.
 * Video is on for this file only — does not change other specs.
 */
test.use({ video: "on" });

test.describe.serial("Demo walkthrough video (draft, review, analyze, chat, admin AI)", () => {
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("1 ร่าง TOR ขั้นที่ 0–4 รวมคะแนนสามด้าน ใบประมาณ และขอบเขตอบรม", async ({
    page,
  }) => {
    test.setTimeout(12_600_000);
    await login(page);
    await expect(page.getByTestId("nav-draft")).toBeVisible();
    await expect(page.getByTestId("nav-analyze")).toBeVisible();
    await page.getByTestId("nav-draft").click();
    await pauseLikeUser(page, 700);
    await page.getByTestId("nav-projects").click();
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await createProjectAndOpenDraft(page);
    await walkLiveDraftToCompose(page);
    await expect(page.getByTestId("draft-chat")).toContainText("กำลังเริ่มร่างตามประเภทงาน", {
      timeout: 270_000,
    });
    await pauseLikeUser(page, 2500);
    await expect(page.getByText("ร่างด้วยระบบอัจฉริยะไม่สำเร็จ")).toHaveCount(0);
    await expect(page.getByTestId("draft-section-badge-s1")).toBeVisible({ timeout: 900_000 });
    await expect(page.getByTestId("phase3-all-drafted")).toBeVisible({ timeout: 10_800_000 });
    await expect(page.getByTestId("draft-chat-count")).toHaveText("16/16 หมวด");
    await showCostAndTrainingIfPresent(page);
    await finishLivePhase3ToSubmit(page);
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await saveEvidence(page, "demo-01-draft-done");
  });

  test("2 ตรวจสอบ TOR พร้อมคะแนนสามด้าน", async ({ page }) => {
    test.setTimeout(2_700_000);
    await login(page);
    await page.getByTestId("nav-review").click();
    await expect(page).toHaveURL(/\/review/);
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByTestId("review-stepper")).toBeVisible();
    await saveEvidence(page, "demo-02-review-start");
    const fileInput = page.locator("[data-testid=review-page] input[type=file]").first();
    await fileInput.setInputFiles({
      name: "tor-draft.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(LIVE_INTAKE_TEXT, "utf-8"),
    });
    await pauseLikeUser(page, 800);
    await expect(page.getByTestId("review-extract")).toBeEnabled();
    await page.getByTestId("review-extract").click();
    await expect(page.getByTestId("review-extract-preview")).toBeVisible({
      timeout: 120_000,
    });
    await saveEvidence(page, "demo-02-review-extract");
    await page.getByTestId("review-confirm-run").click();
    await expect(page.getByTestId("review-score")).toBeVisible({ timeout: 2_160_000 });
    await expect(page.getByTestId("review-result")).toContainText("คะแนนความพร้อม");
    const parts = page.getByTestId("review-part-scores");
    if (await parts.count()) {
      await expect(page.getByTestId("review-part-legal")).toBeVisible();
      await expect(page.getByTestId("review-part-lock-in")).toBeVisible();
      await expect(page.getByTestId("review-part-project")).toBeVisible();
      await pauseLikeUser(page, 900);
    }
    await saveEvidence(page, "demo-02-review-score");
  });

  test("3 วิเคราะห์ TOR สี่แผงในหน้า และแหล่งต่อหมวด", async ({ page }) => {
    test.setTimeout(1_260_000);
    await login(page);
    await page.getByTestId("nav-analyze").click();
    await expect(page).toHaveURL(/\/analyze/);
    await expect(page.getByTestId("analyze-page")).toBeVisible();
    await expect(page.getByTestId("analyze-panels")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-legal")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-lock_in")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-project")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-recommendations")).toBeVisible();
    await typeLikeUser(page.getByTestId("analyze-text"), LIVE_INTAKE_TEXT);
    await pauseLikeUser(page, 600);
    await page.getByTestId("analyze-run").click();
    await expect(page.getByTestId("analyze-summary")).toBeVisible({ timeout: 720_000 });
    await expect(page.getByTestId("analyze-panel-legal")).toBeVisible();
    await saveEvidence(page, "demo-03-analyze-legal");
    await page.getByTestId("analyze-tab-lock_in").click();
    await expect(page.getByTestId("analyze-panel-lock_in")).toBeVisible();
    await pauseLikeUser(page, 700);
    await saveEvidence(page, "demo-03-analyze-lock-in");
    await page.getByTestId("analyze-tab-project").click();
    await expect(page.getByTestId("analyze-panel-project")).toBeVisible();
    await pauseLikeUser(page, 700);
    await saveEvidence(page, "demo-03-analyze-project");
    await page.getByTestId("analyze-tab-recommendations").click();
    await expect(page.getByTestId("analyze-panel-recommendations")).toBeVisible();
    await pauseLikeUser(page, 900);
    const sourceLists = page.locator("[data-testid^=analyze-sources-]");
    if ((await sourceLists.count()) > 0) {
      const firstCount = await sourceLists.first().locator("li").count();
      expect(firstCount).toBeGreaterThan(0);
      expect(firstCount).toBeLessThanOrEqual(10);
    }
    await saveEvidence(page, "demo-03-analyze-recommendations");
  });

  test("4 ถาม-ตอบ คำตอบตรงคำถาม พร้อมแหล่งคลังและออนไลน์", async ({ page }) => {
    test.setTimeout(2_160_000);
    await login(page);
    await page.getByTestId("nav-chat").click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await page.getByTestId("chat-new-room").click();
    await expect(page.getByTestId("chat-input")).toBeVisible({ timeout: 10_000 });
    const question =
      "วิธีเฉพาะเจาะจงใช้งบประมาณวงเงินเท่าใด ตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560";
    await typeLikeUser(page.getByTestId("chat-input"), question);
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 600_000);
    const answer = page.getByTestId("chat-msg-assistant").last();
    await expect
      .poll(async () => (await answer.innerText()).trim().length, { timeout: 540_000 })
      .toBeGreaterThan(80);
    const body = (await answer.innerText()).toLowerCase();
    expect(body).toMatch(/เฉพาะเจาะจง|วงเงิน|บาท|มาตรา|พ\.ร\.บ|ระเบียบ/);
    expect(body).not.toMatch(/ชิ้นจำลอง|custom-rag-stub|mcp-retrieve-stub/);
    const oldTrio =
      /สรุปคำตอบ/.test(body) && /หลักที่เกี่ยวข้อง/.test(body) && /ข้อควรระวัง/.test(body);
    expect(oldTrio, "คำตอบไม่ควรล็อกหัวข้อสามชื่อแบบเดิม").toBeFalsy();
    const online = answer.getByTestId("chat-online-sources");
    const citations = answer.getByTestId("chat-citation");
    await expect(online.or(citations.first())).toBeVisible({ timeout: 30_000 });
    if (await online.count()) {
      const links = await online.locator("li").count();
      expect(links).toBeGreaterThan(0);
      expect(links).toBeLessThanOrEqual(10);
    }
    await saveEvidence(page, "demo-04-chat");
  });

  test("5 ตั้งค่า AI โดยไม่เปิดเผยโทเคน", async ({ page }) => {
    test.setTimeout(120_000);
    await login(page, ADMIN_EMAIL, DEMO_PASSWORD);
    await page.getByTestId("nav-admin-ai-settings").click();
    await expect(page).toHaveURL(/\/admin\/ai-settings/);
    await expect(page.getByTestId("admin-ai-settings-page")).toBeVisible();
    await expect(
      page.getByTestId("admin-ai-settings-page").getByRole("heading", { name: "การตั้งค่า AI" })
    ).toBeVisible();
    await expect(page.locator("#ai-mode")).toBeVisible();
    await expect(page.locator("#ai-llm")).toBeVisible();
    await expect(page.locator("#ai-embed")).toBeVisible();
    await expect(page.locator("#vector-store")).toBeVisible();
    const secretFields = page.locator(
      "#anthropic-key, #openai-key, #gemini-key, #aws-secret, #azure-key, #compat-key, #custom-rag-key"
    );
    const secretCount = await secretFields.count();
    for (let index = 0; index < secretCount; index += 1) {
      await expect(secretFields.nth(index)).toHaveAttribute("type", "password");
    }
    const visibleText = await page.getByTestId("admin-ai-settings-page").innerText();
    expect(visibleText).not.toMatch(/AWS_BEARER_TOKEN|sk-ant-|sk-proj-|AIza[0-9A-Za-z_-]{20,}/);
    await saveEvidence(page, "demo-05-admin-ai");
  });
});

async function showCostAndTrainingIfPresent(page: Page) {
  const budgetCard = page.getByTestId("section-card-s6");
  if (await budgetCard.count()) {
    await budgetCard.click();
    await pauseLikeUser(page, 600);
    const sheet = page.getByTestId("cost-worksheet");
    if (await sheet.count()) {
      await expect(sheet).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-disclaimer")).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-personnel")).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-equipment")).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-procurement")).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-consultant")).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-training")).toBeVisible();
      await expect(page.getByTestId("cost-worksheet-save")).toBeVisible();
      await saveEvidence(page, "demo-01-cost-worksheet");
    }
  }
  const scopeHeader = page.getByRole("button", { name: /^ขอบเขตของงาน(\s|$)/ });
  if (await scopeHeader.count()) {
    await scopeHeader.click();
    await pauseLikeUser(page, 500);
  }
  const editor = page.getByTestId("scope-subsection-editor");
  if ((await editor.count()) === 0) {
    return;
  }
  const trainingChip = editor.getByRole("button", { name: /อบรม|training/i }).first();
  if ((await trainingChip.count()) === 0) {
    return;
  }
  await trainingChip.click();
  await pauseLikeUser(page, 500);
  const training = page.getByTestId("training-scope");
  if (await training.count()) {
    await expect(training).toBeVisible();
    await expect(page.getByTestId("training-scope-cohorts")).toBeVisible();
    await expect(page.getByTestId("training-scope-hours")).toBeVisible();
    await expect(page.getByTestId("training-scope-attendees")).toBeVisible();
    await expect(page.getByTestId("training-scope-documents")).toBeVisible();
    await saveEvidence(page, "demo-01-training-scope");
  }
}
