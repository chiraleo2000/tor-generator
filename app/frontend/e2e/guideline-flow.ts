import { expect, type Locator, type Page } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  HIRE_MAINTAIN_INTAKE_TEXT,
  LIVE_INTAKE_TEXT,
  answerFactGapsViaIntakeChat,
  confirmPhase,
  createProjectAndOpenDraft,
  login,
  typeLikeUser,
} from "./helpers";
import { GUIDELINE_CHAT_TURNS } from "./guideline-questions";

const FROZEN_MS = 180_000;
const READ_MS = 6_000;

async function oneByOne<T>(items: readonly T[], visit: (item: T) => Promise<void>) {
  await items.reduce(async (previous, item) => {
    await previous;
    await visit(item);
  }, Promise.resolve());
}

async function watchUntil(
  page: Page,
  timeoutMs: number,
  timeoutMessage: string,
  read: () => Promise<{ done: boolean; marker: string; frozen: string }>
) {
  const started = Date.now();
  let last = "";
  let lastChange = started;
  await new Promise<void>((resolve, reject) => {
    const tick = () => {
      void (async () => {
        try {
          if (Date.now() - started >= timeoutMs) {
            reject(new Error(timeoutMessage));
            return;
          }
          const sample = await read();
          if (sample.done) {
            resolve();
            return;
          }
          if (sample.marker !== last) {
            last = sample.marker;
            lastChange = Date.now();
          } else if (Date.now() - lastChange > FROZEN_MS) {
            reject(new Error(sample.frozen));
            return;
          }
          await page.waitForTimeout(1_000);
          tick();
        } catch (error) {
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      })();
    };
    tick();
  });
}

const REVIEW_TEXTS = [
  { name: "tor-develop.txt", text: LIVE_INTAKE_TEXT },
  { name: "tor-maintain.txt", text: HIRE_MAINTAIN_INTAKE_TEXT || LIVE_INTAKE_TEXT },
];

async function dwell(page: Page, ms = READ_MS) {
  await page.waitForTimeout(ms);
}

async function showStep(page: Page, phase: number) {
  const step = page.getByTestId(`phase-${phase}`);
  await step.scrollIntoViewIfNeeded();
  await expect(step).toHaveAttribute("aria-current", "step");
  await dwell(page, 2_500);
}

/** Wait until `done` is visible. Throw if the status line stops changing for 3 minutes. */
async function untilVisible(page: Page, done: Locator, status: Locator, timeoutMs: number) {
  await watchUntil(page, timeoutMs, "ไม่เห็นผลบนหน้าเดิมภายในเวลาที่กำหนด", async () => {
    if (await done.isVisible().catch(() => false)) {
      return { done: true, marker: "", frozen: "" };
    }
    const text = (await status.innerText().catch(() => "")).trim();
    return {
      done: false,
      marker: text,
      frozen: text ? `สถานะค้าง: ${text}` : "หน้าจอค้างโดยไม่มีข้อความสถานะ",
    };
  });
}

async function uploadPhase0(page: Page, intakeText: string) {
  await page.getByTestId("intake-upload").setInputFiles({
    name: "pB0.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(`${intakeText}\nไฟล์แนบประกอบการวิเคราะห์โครงการทดสอบ`, "utf-8"),
  });
  await expect(page.getByTestId("phase0-file-list")).toContainText("pB0.txt", {
    timeout: 30_000,
  });
}

async function dwellOnRisk(page: Page) {
  const panel = page.getByTestId("bidder-risk-panel");
  await expect(panel).toBeVisible();
  const recommendation = page.getByTestId("bidder-risk-recommendation");
  await recommendation.scrollIntoViewIfNeeded();
  await expect(recommendation).toBeVisible();
  await dwell(page, 5_000);
  const penalty = page.getByTestId("bidder-risk-penalty");
  await penalty.scrollIntoViewIfNeeded();
  await expect(penalty).toBeVisible();
  await dwell(page, 5_000);
  const tables = panel.locator("[data-testid^='bidder-risk-table-']");
  await expect.poll(async () => tables.count()).toBeGreaterThan(1);
  const count = await tables.count();
  const indexes = Array.from({ length: count }, (_, index) => index);
  await oneByOne(indexes, async (index) => {
    await tables.nth(index).scrollIntoViewIfNeeded();
    await dwell(page, 3_000);
  });
}

async function showWorksheet(page: Page) {
  const budgetCard = page.getByTestId("section-card-s6");
  const sheet = page.getByTestId("cost-worksheet");
  await budgetCard.scrollIntoViewIfNeeded();
  if (!(await sheet.isVisible().catch(() => false))) {
    await budgetCard.getByRole("button").first().click();
  }
  await expect(sheet).toBeVisible();
  await oneByOne(
    ["ทรัพยากรบุคคล", "อุปกรณ์", "การจัดซื้อจัดจ้าง", "การจ้างที่ปรึกษา", "ค่าอบรม"],
    async (label) => {
      await expect(sheet).toContainText(label);
    }
  );
  await oneByOne(["personnel", "equipment", "procurement", "consultant", "training"], async (key) => {
    const row = page.getByTestId(`cost-worksheet-${key}`);
    await row.scrollIntoViewIfNeeded();
    await expect(row).toBeVisible();
    await dwell(page, 1_500);
  });
  await page.getByTestId("cost-worksheet-apply").click();
  await expect(page.getByTestId("cost-worksheet-info")).toContainText("ใช้ตัวเลขที่คำนวณแล้ว", {
    timeout: 60_000,
  });
  await expect(page.getByTestId("cost-worksheet-apply")).toBeEnabled();
  await sheet.scrollIntoViewIfNeeded();
  await dwell(page, 8_000);
}

export async function openCalculatedWorksheet(page: Page) {
  await login(page);
  await page.getByTestId("nav-projects").click();
  await expect(page.getByTestId("projects-page")).toBeVisible();
  await createProjectAndOpenDraft(page);
  await showStep(page, 0);

  await expect(page.getByTestId("intake-paste")).toBeVisible();
  await typeLikeUser(page.getByTestId("intake-paste"), LIVE_INTAKE_TEXT);
  await dwell(page, 1_000);
  await uploadPhase0(page, LIVE_INTAKE_TEXT);
  await dwell(page, 1_500);
  await page.getByTestId("intake-start-analyze").click();
  await confirmPhase(page);

  const analyzing = page.getByTestId("phase0-analyze-status");
  const coverage = page.getByTestId("phase1-coverage");
  await expect(analyzing.or(coverage)).toBeVisible({ timeout: 30_000 });
  await untilVisible(page, coverage, analyzing, 9_000_000);
  await showStep(page, 1);
  await expect(page.getByText("รายละเอียดที่จัดเข้าช่อง")).toBeVisible();
  await page.getByTestId("coverage-row-s1").scrollIntoViewIfNeeded();
  await dwell(page, READ_MS);

  await page.getByTestId("phase1-skip").click();
  await expect(page.getByTestId("phase2-qa")).toBeVisible({ timeout: 25_000 });
  await showStep(page, 2);
  await expect(page.getByTestId("chat-input")).toBeVisible();
  await dwell(page, READ_MS);
  await answerFactGapsViaIntakeChat(page);
  await expect(page.getByTestId("intake-confirm-ready")).toBeEnabled({ timeout: 30_000 });
  await dwell(page, 2_000);
  await page.getByTestId("intake-confirm-ready").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase3-draft")).toBeVisible({ timeout: 90_000 });
  await showStep(page, 3);

  const draftStatus = page.getByTestId("draft-chat-status");
  await expect(draftStatus).toBeVisible({ timeout: 90_000 });
  const draftingLine = (await draftStatus.innerText()).trim();
  await expect
    .poll(
      async () => {
        if (await page.getByTestId("phase3-all-drafted").isVisible().catch(() => false)) {
          return "draft-finished";
        }
        return (await draftStatus.innerText()).trim();
      },
      { timeout: 20_000 }
    )
    .not.toBe(draftingLine);
  await showWorksheet(page);
  await untilVisible(page, page.getByTestId("phase3-all-drafted"), draftStatus, 10_800_000);
  await expect(page.getByTestId("phase3-confirm")).toBeEnabled();
  await page.getByTestId("phase3-confirm").scrollIntoViewIfNeeded();
  await dwell(page, 2_000);
  await page.getByTestId("phase3-confirm").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase4-review")).toBeVisible({ timeout: 30_000 });
  await showStep(page, 4);

  const reviewStatus = page.getByTestId("phase4-review-status");
  const score = page.getByTestId("phase4-rule-score");
  await expect(reviewStatus.or(score)).toBeVisible({ timeout: 30_000 });
  await untilVisible(page, score, reviewStatus, 1_080_000);
  await expect(score).toContainText(/\d{1,3}\/100/);
  await score.scrollIntoViewIfNeeded();
  await dwell(page, READ_MS);
  const exportPanel = page.getByTestId("phase4-export");
  await exportPanel.scrollIntoViewIfNeeded();
  await expect(exportPanel).toBeVisible();
  await dwell(page, READ_MS);
}

async function showReviewBudget(page: Page) {
  const project = page.getByTestId("review-part-project");
  await expect(project).toBeVisible();
  await project.scrollIntoViewIfNeeded();
  await expect(project).toContainText(/จ้างที่ปรึกษา|ประเมินงบประมาณ|ค่าอบรม|ทรัพยากรบุคคล|งบประมาณ/);
  await dwell(page, 4_000);
  const buckets = page.getByTestId("review-finding-buckets");
  await buckets.scrollIntoViewIfNeeded();
  await dwell(page, 3_000);
}

async function reviewOneTor(page: Page, name: string, text: string) {
  await page.locator("[data-testid=review-page] input[type=file]").first().setInputFiles({
    name,
    mimeType: "text/plain",
    buffer: Buffer.from(text, "utf-8"),
  });
  await page.getByTestId("review-extract").click();
  await expect(page.getByTestId("review-status")).toContainText("สกัดข้อความ", {
    timeout: 120_000,
  });
  await expect(page.getByTestId("review-extract-preview")).toBeVisible({ timeout: 120_000 });
  await dwell(page, 2_000);
  const status = page.getByTestId("review-status");
  await status.scrollIntoViewIfNeeded();
  await page.getByTestId("review-confirm-run").click();
  await expect(status).toContainText(/กำลังตรวจ|ตรวจเสร็จ/, { timeout: 20_000 });
  const score = page.getByTestId("review-score");
  await untilVisible(page, score, status, 900_000);
  await expect(status).toContainText(/ตรวจเสร็จ/);
  await expect(score).toBeVisible();
  await score.scrollIntoViewIfNeeded();
  await dwell(page, 4_000);
  await showReviewBudget(page);
  await dwellOnRisk(page);
}

export async function reviewRealDraft(page: Page) {
  await login(page);
  await page.getByTestId("nav-review").click();
  await expect(page).toHaveURL(/\/review/);
  await expect(page.getByTestId("review-page")).toBeVisible();
  await reviewOneTor(page, REVIEW_TEXTS[0].name, REVIEW_TEXTS[0].text);
  await reviewOneTor(page, REVIEW_TEXTS[1].name, REVIEW_TEXTS[1].text);
}

async function analyzeOneTor(page: Page, text: string) {
  await page.locator("[data-testid=analyze-page] input[type=file]").first().setInputFiles({
    name: "tor-analyze.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(text.slice(0, 8_000), "utf-8"),
  });
  await page.getByTestId("analyze-extract").click();
  await expect(page.getByTestId("analyze-extract-preview")).toBeVisible({ timeout: 180_000 });
  const status = page.getByTestId("analyze-status");
  await page.getByTestId("analyze-run").click();
  await status.scrollIntoViewIfNeeded();
  await expect(status).toContainText(/กำลังวิเคราะห์|วิเคราะห์เสร็จ/, { timeout: 15_000 });
  const summary = page.getByTestId("analyze-summary");
  await untilVisible(page, summary, status, 900_000);
  await expect(status).toContainText("วิเคราะห์เสร็จ");
  await expect(summary).toBeVisible();
  await status.scrollIntoViewIfNeeded();
  await dwell(page, 4_000);
  await page.getByTestId("analyze-tab-project").click();
  await expect(page.getByTestId("analyze-panel-project")).toContainText(
    /จ้างที่ปรึกษา|ประเมินงบประมาณ|ค่าอบรม|ทรัพยากรบุคคล/
  );
  await page.getByTestId("analyze-panel-project").scrollIntoViewIfNeeded();
  await dwell(page, 4_000);
  await page.getByTestId("analyze-tab-bidder_risk").click();
  await dwellOnRisk(page);
}

export async function analyzeRealDraft(page: Page) {
  await login(page);
  await page.getByTestId("nav-analyze").click();
  await expect(page).toHaveURL(/\/analyze/);
  await expect(page.getByTestId("analyze-page")).toBeVisible();
  await analyzeOneTor(page, LIVE_INTAKE_TEXT);
  await analyzeOneTor(page, HIRE_MAINTAIN_INTAKE_TEXT || LIVE_INTAKE_TEXT.slice(0, 3_000));
}

async function askAndRead(page: Page, question: string) {
  await typeLikeUser(page.getByTestId("chat-input"), question);
  await page.getByTestId("chat-send").click();
  const answer = page.getByTestId("chat-msg-assistant").last();
  const status = page.getByTestId("chat-wait-status");
  let body = "";
  await watchUntil(page, 600_000, "ไม่ได้รับคำตอบจากคลัง", async () => {
    body = (await answer.innerText().catch(() => "")).trim();
    if (body.length > 40 && body.trim() !== question.trim()) {
      return { done: true, marker: "", frozen: "" };
    }
    const marker = `${(await status.innerText().catch(() => "")).trim()}|${body}`;
    return { done: false, marker, frozen: `แชทค้าง: ${marker}` };
  });
  return body;
}

export async function askGuidelineChat(page: Page) {
  await login(page);
  await page.getByTestId("nav-chat").click();
  await expect(page).toHaveURL(/\/chat/);
  await expect(page.getByTestId("chat-shell")).toBeVisible();
  await page.getByTestId("chat-new-room").click();
  await expect(page.getByTestId("chat-input")).toBeVisible();
  const bodies: string[] = [];
  await oneByOne(GUIDELINE_CHAT_TURNS, async (question) => {
    const body = await askAndRead(page, question);
    bodies.push(body);
    const user = page.getByTestId("chat-msg-user").last();
    const answer = page.getByTestId("chat-msg-assistant").last();
    await user.scrollIntoViewIfNeeded();
    await answer.scrollIntoViewIfNeeded();
    const cite = answer.getByTestId("chat-citation");
    if (await cite.count()) {
      await cite.first().scrollIntoViewIfNeeded();
      const lines = await cite.allInnerTexts();
      bodies[bodies.length - 1] = `${body}\n${lines.join(" ")}`;
    }
    await dwell(page, 8_000);
  });
  const rateText = `${bodies[0]}\n${bodies[1]}`;
  expect(rateText).toMatch(/อัตราค่าจ้างที่ปรึกษา/);
  expect(bodies).toHaveLength(GUIDELINE_CHAT_TURNS.length);
  const lengths = bodies.map((body) => body.length);
  expect(Math.max(...lengths)).toBeGreaterThan(40);
}
