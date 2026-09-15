import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  LIVE_INTAKE_TEXT,
  createProjectAndOpenDraft,
  login,
  pauseLikeUser,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
  waitForLiveAssistant,
  walkLiveFivePhases,
} from "./helpers";

function citationBlob(texts: string[]): string {
  return texts.join(" | ").toLowerCase();
}

test.describe.serial("Three tools live UI (chat, draft, review)", () => {
  test.skip(skipUnlessLive, skipReason);

  test("1 ถาม-ตอบ บนหน้าเว็บ", async ({ page }) => {
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
    const chips = answer.getByTestId("chat-citation");
    await expect(chips.first()).toBeVisible({ timeout: 30_000 });
    const chipText = citationBlob(await chips.allInnerTexts());
    expect(chipText).not.toMatch(/stub/);
    expect(chipText).toMatch(/document:|mcp:|พรบ|ระเบียบ|คู่มือ/);
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

  test("3 ตรวจสอบ TOR บนหน้าเว็บ", async ({ page }) => {
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
    await expect(page.getByTestId("review-page")).not.toContainText(
      /ชิ้นจำลอง|custom-rag-stub|mcp-retrieve-stub/
    );
    await saveEvidence(page, "serial-05-review-score");
  });
});
