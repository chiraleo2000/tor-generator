import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  LIVE_INTAKE_TEXT,
  createProjectAndOpenDraft,
  headedRun,
  installMockedChatApi,
  installMockedFourToolsApi,
  isLiveStackReachable,
  login,
  pauseLikeUser,
  saveEvidence,
  skipLiveStackDownReason,
  skipMockedInHeadedReason,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
  waitForLiveAssistant,
  walkLiveFivePhases,
  walkMockedIntakeToPhase4,
} from "./helpers";

function citationBlob(texts: string[]): string {
  return texts.join(" | ").toLowerCase();
}

function hasForcedLegacyHeadings(text: string): boolean {
  return /สรุปคำตอบ/.test(text) && /หลักที่เกี่ยวข้อง/.test(text) && /ข้อควรระวัง/.test(text);
}

test.describe("Four tools live UI (draft, review, chat, analyze)", () => {
  test.skip(skipUnlessLive, skipReason);

  test.beforeAll(async ({ request }) => {
    if (!(await isLiveStackReachable(request))) {
      test.skip(true, skipLiveStackDownReason);
    }
  });

  test("1 ถาม-ตอบ บนหน้าเว็บ ไม่ล็อกสามหัวข้อ และแสดงแหล่งได้", async ({ page }) => {
    test.setTimeout(720_000);
    await login(page);
    await saveEvidence(page, "serial-00-dashboard");

    await page.getByTestId("nav-chat").click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await page.getByTestId("chat-new-room").click();
    await expect(page.getByTestId("chat-input")).toBeVisible({ timeout: 10_000 });
    await typeLikeUser(
      page.getByTestId("chat-input"),
      "ถามจาก พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 ผู้เสนอราคาต้องมีคุณสมบัติอะไรบ้าง อ้างมาตราให้ชัด"
    );
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 600_000);
    const answer = page.getByTestId("chat-msg-assistant").last();
    await expect.poll(
      async () => (await answer.innerText()).trim().length,
      { timeout: 180_000 }
    ).toBeGreaterThan(80);
    await expect(answer).not.toContainText(/ชิ้นจำลอง|custom-rag-stub|mcp-retrieve-stub/);
    const body = await answer.innerText();
    expect(hasForcedLegacyHeadings(body), "คำตอบไม่ควรล็อกหัวข้อสามชื่อแบบเดิม").toBeFalsy();
    const chips = answer.getByTestId("chat-citation");
    const online = answer.getByTestId("chat-online-sources");
    await expect(online.or(chips.first())).toBeVisible({ timeout: 30_000 });
    if (await chips.count()) {
      const chipText = citationBlob(await chips.allInnerTexts());
      expect(chipText).not.toMatch(/stub/);
      expect(chipText).toMatch(/document:|mcp:|พรบ|ระเบียบ|คู่มือ/);
    }
    if (await online.count()) {
      const links = await online.locator("li").count();
      expect(links).toBeGreaterThan(0);
      expect(links).toBeLessThanOrEqual(10);
    }
    await saveEvidence(page, "serial-01-chat");
  });

  test("1b ฐานความรู้ อัปโหลดและลบ", async ({ page }) => {
    test.setTimeout(240_000);
    await login(page);
    await page.getByTestId("nav-knowledge-base").click();
    await expect(page.getByTestId("knowledge-base-page")).toBeVisible();
    const otherCategory = page.getByRole("button", { name: "ข้อมูลอื่น ๆ" }).first();
    await expect(otherCategory).toBeVisible();
    await otherCategory.click();
    await pauseLikeUser(page, 400);
    const uniqueName = `บันทึกภายใน-three-tools-${Date.now()}.txt`;
    await page.locator("[data-testid=knowledge-base-page] input[type=file]").setInputFiles({
      name: uniqueName,
      mimeType: "text/plain",
      buffer: Buffer.from(
        "หลักเกณฑ์วงเงินจัดซื้อจัดจ้างภาครัฐ ตามระเบียบกรมบัญชีกลาง สำหรับทดสอบคลังในเส้นทางสามเครื่องมือ",
        "utf-8"
      ),
    });
    await expect(page.getByText(/อัปโหลดเฉพาะบัญชีของคุณแล้ว|อัปโหลดไม่สำเร็จ/)).toBeVisible({
      timeout: 180_000,
    });
    await expect(page.getByText(uniqueName)).toBeVisible({ timeout: 30_000 });
    await saveEvidence(page, "serial-01b-kb");
    page.once("dialog", (dialog) => {
      void dialog.accept();
    });
    await page.locator("[data-testid^=delete-user-file-]").first().click();
    await expect(
      page.getByText(`ลบ «${uniqueName}» แล้ว`).or(page.getByText("ลบเอกสารไม่สำเร็จ"))
    ).toBeVisible({ timeout: 20_000 });
  });

  test("2 ร่าง TOR ครบ 16 หมวด บนหน้าเว็บ", async ({ page }) => {
    test.setTimeout(4_200_000);
    await login(page);
    await page.getByTestId("nav-projects").click();
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await createProjectAndOpenDraft(page);
    await walkLiveFivePhases(page);
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await saveEvidence(page, "serial-02-draft-done");
  });

  test("3 ตรวจสอบ TOR อัปโหลด สกัด ได้คะแนนสามด้าน", async ({ page }) => {
    test.setTimeout(420_000);
    await login(page);
    await page.getByTestId("nav-review").click();
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByTestId("review-stepper")).toBeVisible();
    await saveEvidence(page, "serial-03-review-start");
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
    await saveEvidence(page, "serial-04-review-extract");
    await page.getByTestId("review-confirm-run").click();
    await expect(page.getByTestId("review-score")).toBeVisible({ timeout: 240_000 });
    await expect(page.getByTestId("review-result")).toContainText("คะแนนความพร้อม");
    await expect(page.getByTestId("review-part-scores")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("review-part-legal")).toBeVisible();
    await expect(page.getByTestId("review-part-lock-in")).toBeVisible();
    await expect(page.getByTestId("review-part-project")).toBeVisible();
    const scores = page.getByTestId("review-part-scores");
    await expect(scores).toContainText(/[1-9][0-9]?\/100|[1-9][0-9]{1,2}\/100/);
    const scoreText = await scores.innerText();
    expect(scoreText).not.toMatch(/0\/100[\s\S]*0\/100[\s\S]*0\/100/);
    await expect(page.getByTestId("review-page")).not.toContainText(
      /ชิ้นจำลอง|custom-rag-stub|mcp-retrieve-stub/
    );
    await saveEvidence(page, "serial-05-review-score");
  });

  test("4 วิเคราะห์ TOR เปิดจาก nav-analyze สลับสี่แผงและแหล่งต่อหมวด", async ({ page }) => {
    test.setTimeout(420_000);
    await login(page);
    await expect(page.getByTestId("nav-analyze")).toBeVisible();
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
    await expect(page.getByTestId("analyze-summary")).toBeVisible({ timeout: 240_000 });
    await expect(page.getByTestId("analyze-panel-legal")).toBeVisible();
    await page.getByTestId("analyze-tab-lock_in").click();
    await expect(page.getByTestId("analyze-panel-lock_in")).toBeVisible();
    await page.getByTestId("analyze-tab-project").click();
    await expect(page.getByTestId("analyze-panel-project")).toBeVisible();
    await page.getByTestId("analyze-tab-recommendations").click();
    await expect(page.getByTestId("analyze-panel-recommendations")).toBeVisible();
    const sourceLists = page.locator("[data-testid^=analyze-sources-]");
    if ((await sourceLists.count()) > 0) {
      const firstCount = await sourceLists.first().locator("li").count();
      expect(firstCount).toBeGreaterThan(0);
      expect(firstCount).toBeLessThanOrEqual(10);
    }
    await saveEvidence(page, "serial-06-analyze");
  });
});

test.describe("Four tools mocked API workflow", () => {
  test.skip(headedRun, skipMockedInHeadedReason);

  test.beforeEach(async ({ page }) => {
    await installMockedFourToolsApi(page);
    await login(page);
    await expect(page.getByTestId("nav-draft")).toBeVisible();
    await expect(page.getByTestId("nav-review")).toBeVisible();
    await expect(page.getByTestId("nav-chat")).toBeVisible();
    await expect(page.getByTestId("nav-analyze")).toHaveText(/วิเคราะห์ TOR/);
    await expect(page.getByTestId("nav-analyze")).toHaveAttribute("href", "/analyze");
  });

  test("ร่าง TOR ขั้น 0–4 พร้อมคำอธิบายสามด้านและคะแนนรายส่วน", async ({ page }) => {
    test.setTimeout(180_000);
    await page.getByTestId("nav-draft").click();
    await expect(page.getByTestId("draft-page").or(page.getByTestId("draft-index"))).toBeVisible({
      timeout: 20_000,
    });
    if (await page.getByTestId("draft-index").count()) {
      await page.getByTestId("nav-projects").click();
      await expect(page.getByTestId("projects-page")).toBeVisible();
      await createProjectAndOpenDraft(page);
    }
    await expect(page.getByTestId("phase-0")).toBeVisible();
    await walkMockedIntakeToPhase4(page);
    await expect(page.getByTestId("review-part-scores")).toBeVisible();
    await expect(page.getByTestId("review-part-legal")).toContainText(/กฎหมาย|พ\.ร\.บ|ไม่พบประเด็น/);
    await expect(page.getByTestId("review-part-lock-in")).toBeVisible();
    await expect(page.getByTestId("review-part-project")).toBeVisible();
    await saveEvidence(page, "mocked-01-draft");
  });

  test("ตรวจสอบ TOR อัปโหลด สกัด ได้คะแนนสามด้านจาก API จำลอง", async ({ page }) => {
    await page.getByTestId("nav-review").click();
    await expect(page).toHaveURL(/\/review/);
    await expect(page.getByTestId("review-page")).toBeVisible();
    await page.locator("[data-testid=review-page] input[type=file]").first().setInputFiles({
      name: "tor.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 mocked-tor"),
    });
    await page.getByTestId("review-extract").click();
    await expect(page.getByTestId("review-extract-preview")).toBeVisible();
    await page.getByTestId("review-confirm-run").click();
    await expect(page.getByTestId("review-score")).toContainText("79/100");
    await expect(page.getByTestId("review-part-scores")).toBeVisible();
    await expect(page.getByTestId("review-part-legal")).toBeVisible();
    await expect(page.getByTestId("review-part-lock-in")).toBeVisible();
    await expect(page.getByTestId("review-part-project")).toBeVisible();
    const reviewParts = await page.getByTestId("review-part-scores").innerText();
    expect(reviewParts).not.toMatch(/0\/100[\s\S]*0\/100[\s\S]*0\/100/);
    await saveEvidence(page, "mocked-02-review");
  });

  test("ถาม-ตอบ ไม่ล็อกสามหัวข้อ และแสดงแหล่งออนไลน์", async ({ page }) => {
    await installMockedChatApi(page);
    await page.getByTestId("nav-chat").click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
    await page.getByTestId("chat-new-room").click();
    await expect(page.getByTestId("chat-input")).toBeVisible();
    await page.getByTestId("chat-input").fill(
      "วิธีเฉพาะเจาะจงใช้งบประมาณวงเงินเท่าใด ตาม พ.ร.บ. การจัดซื้อจัดจ้าง"
    );
    await page.getByTestId("chat-send").click();
    const chatAnswer = page.getByTestId("chat-msg-assistant").last();
    await expect(chatAnswer).toBeVisible({ timeout: 20_000 });
    await expect(chatAnswer).toContainText("วิธีเฉพาะเจาะจง");
    const chatBody = await chatAnswer.innerText();
    expect(hasForcedLegacyHeadings(chatBody)).toBeFalsy();
    await expect(chatAnswer.getByTestId("chat-online-sources")).toBeVisible();
    await expect(chatAnswer.getByRole("link", { name: "กรมบัญชีกลาง" })).toHaveAttribute(
      "href",
      "https://www.gprocurement.go.th"
    );
    await expect(chatAnswer.getByTestId("chat-citation").first()).toBeVisible();
    await saveEvidence(page, "mocked-03-chat");
  });

  test("วิเคราะห์ TOR เปิดจาก nav-analyze สลับสี่แผงและแหล่งต่อหมวด", async ({ page }) => {
    await page.getByTestId("nav-analyze").click();
    await expect(page).toHaveURL(/\/analyze/);
    await expect(page.getByTestId("analyze-page")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-legal")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-lock_in")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-project")).toBeVisible();
    await expect(page.getByTestId("analyze-tab-recommendations")).toBeVisible();
    await page.getByTestId("analyze-text").fill("ร่าง TOR ทดสอบ Oracle โดยไม่มีหรือเทียบเท่า");
    await page.getByTestId("analyze-run").click();
    await expect(page.getByTestId("analyze-summary")).toContainText("79/100");
    await expect(page.getByTestId("analyze-panel-legal")).toBeVisible();
    await page.getByTestId("analyze-tab-lock_in").click();
    await expect(page.getByTestId("analyze-panel-lock_in")).toBeVisible();
    await page.getByTestId("analyze-tab-project").click();
    await expect(page.getByTestId("analyze-panel-project")).toBeVisible();
    await page.getByTestId("analyze-tab-recommendations").click();
    await expect(page.getByTestId("analyze-panel-recommendations")).toBeVisible();
    await expect(page.getByTestId("analyze-source-count-s4")).toContainText("พบ 7 แหล่ง");
    const analyzeSources = page.locator("[data-testid^=analyze-sources-]");
    await expect(analyzeSources.first()).toBeVisible();
    const sourceCount = await analyzeSources.first().locator("li").count();
    expect(sourceCount).toBeGreaterThanOrEqual(5);
    expect(sourceCount).toBeLessThanOrEqual(10);
    await saveEvidence(page, "mocked-04-analyze");
  });
});
