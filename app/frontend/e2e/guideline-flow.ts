import { expect, type Page } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  LIVE_INTAKE_TEXT,
  createProjectAndOpenDraft,
  login,
  pauseLikeUser,
  typeLikeUser,
  waitForLiveAssistant,
  walkLiveDraftToCompose,
} from "./helpers";
import { CHAT_QUESTIONS, RATE_QUESTIONS } from "./guideline-questions";

export async function openCalculatedWorksheet(page: Page) {
  await login(page);
  await page.getByTestId("nav-projects").click();
  await expect(page.getByTestId("projects-page")).toBeVisible();
  await createProjectAndOpenDraft(page);
  await walkLiveDraftToCompose(page);
  await expect(page.getByTestId("phase3-draft")).toBeVisible();
  const budgetCard = page.getByTestId("section-card-s6");
  await budgetCard.scrollIntoViewIfNeeded();
  await budgetCard.getByRole("button").first().click();
  const sheet = page.getByTestId("cost-worksheet");
  await expect(sheet).toBeVisible();
  await expect(page.getByTestId("cost-worksheet-rules")).toContainText("ปริญญาโทแล้วปริญญาเอก");
  await expect(page.getByTestId("cost-worksheet-rules")).toContainText("ภาคเอกชน");
  await expect(page.getByTestId("cost-worksheet-rules")).toContainText("โรงแรมหรือสถานที่เอกชน");
  const apply = page.getByTestId("cost-worksheet-apply");
  await apply.click();
  await expect(page.getByTestId("cost-worksheet-info")).toContainText("ใช้ตัวเลขที่คำนวณแล้ว", {
    timeout: 60_000,
  });
  await expect(apply).toBeEnabled();
  await expect(sheet).toContainText("ทรัพยากรบุคคล");
  await expect(sheet).toContainText("อุปกรณ์");
  await expect(sheet).toContainText("การจัดซื้อจัดจ้าง");
  await expect(sheet).toContainText("การจ้างที่ปรึกษา");
  await expect(sheet).toContainText("ค่าอบรม");
  await expect(page.getByTestId("cost-worksheet-personnel")).toBeVisible();
  await expect(page.getByTestId("cost-worksheet-equipment")).toBeVisible();
  await expect(page.getByTestId("cost-worksheet-procurement")).toBeVisible();
  await expect(page.getByTestId("cost-worksheet-consultant")).toBeVisible();
  await expect(page.getByTestId("cost-worksheet-training")).toBeVisible();
  await sheet.scrollIntoViewIfNeeded();
  await pauseLikeUser(page, 1200);
}

export async function reviewRealDraft(page: Page) {
  await login(page);
  await page.getByTestId("nav-review").click();
  await expect(page).toHaveURL(/\/review/);
  await expect(page.getByTestId("review-page")).toBeVisible();
  await page.locator("[data-testid=review-page] input[type=file]").first().setInputFiles({
    name: "tor-draft.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(LIVE_INTAKE_TEXT, "utf-8"),
  });
  await page.getByTestId("review-extract").click();
  await expect(page.getByTestId("review-status")).toContainText("สกัดข้อความ", {
    timeout: 120_000,
  });
  await expect(page.getByTestId("review-extract-preview")).toBeVisible({ timeout: 120_000 });
  await page.getByTestId("review-confirm-run").click();
  await expect(page.getByTestId("review-status")).toContainText(/กำลังตรวจ|ตรวจเสร็จ/, {
    timeout: 15_000,
  });
  await expect(page.getByTestId("review-score")).toBeVisible({ timeout: 600_000 });
  await expect(page.getByTestId("review-part-project")).toContainText(/จ้างที่ปรึกษา|ประเมินงบประมาณ|ค่าอบรม/);
  await expect(page.getByTestId("bidder-risk-panel")).toBeVisible();
  await expect(page.getByTestId("bidder-risk-recommendation")).toBeVisible();
  await page.getByTestId("bidder-risk-panel").scrollIntoViewIfNeeded();
  await pauseLikeUser(page, 1200);
}

export async function analyzeRealDraft(page: Page) {
  await login(page);
  await page.getByTestId("nav-analyze").click();
  await expect(page).toHaveURL(/\/analyze/);
  await expect(page.getByTestId("analyze-page")).toBeVisible();
  await typeLikeUser(page.getByTestId("analyze-text"), LIVE_INTAKE_TEXT.slice(0, 4000));
  await page.getByTestId("analyze-run").click();
  await expect(page.getByTestId("analyze-status")).toContainText("กำลังวิเคราะห์", {
    timeout: 5_000,
  });
  await expect(page.getByTestId("analyze-summary")).toBeVisible({ timeout: 180_000 });
  await expect(page.getByTestId("analyze-status")).not.toHaveText("กำลังวิเคราะห์");
  await page.getByTestId("analyze-tab-project").click();
  await expect(page.getByTestId("analyze-panel-project")).toContainText(
    /จ้างที่ปรึกษา|ประเมินงบประมาณ|ค่าอบรม/
  );
  await page.getByTestId("analyze-tab-bidder_risk").click();
  await expect(page.getByTestId("bidder-risk-panel")).toBeVisible();
  await expect(page.getByTestId("bidder-risk-recommendation")).toBeVisible();
  await page.getByTestId("bidder-risk-panel").scrollIntoViewIfNeeded();
  await pauseLikeUser(page, 1200);
}

async function askAndRead(page: Page, question: string) {
  await typeLikeUser(page.getByTestId("chat-input"), question);
  await page.getByTestId("chat-send").click();
  await waitForLiveAssistant(page, 600_000);
  const answer = page.getByTestId("chat-msg-assistant").last();
  await expect.poll(async () => (await answer.innerText()).trim().length, {
    timeout: 180_000,
  }).toBeGreaterThan(40);
  const body = await answer.innerText();
  expect(body.trim()).not.toBe(question.trim());
  return body;
}

export async function askGuidelineChat(page: Page) {
  await login(page);
  await page.getByTestId("nav-chat").click();
  await expect(page).toHaveURL(/\/chat/);
  await page.getByTestId("chat-new-room").click();
  await expect(page.getByTestId("chat-input")).toBeVisible();
  const rateAnswer = await askAndRead(page, RATE_QUESTIONS[0]);
  expect(rateAnswer).toMatch(/เอกชน|ปริญญา|บาท|อายุงาน|2 ปี|๒ ปี/);
  expect(rateAnswer).toMatch(/อัตราค่าจ้างที่ปรึกษา/);
  await pauseLikeUser(page, 800);
  const followUps = CHAT_QUESTIONS.slice(1, 6);
  await followUps.reduce(async (previous, question) => {
    await previous;
    await askAndRead(page, question);
    await pauseLikeUser(page, 600);
  }, Promise.resolve());
}
