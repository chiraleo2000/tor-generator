import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  headedRun,
  LIVE_INTAKE_TEXT,
  login,
  pauseLikeUser,
  saveEvidence,
  skipMockedInHeadedReason,
  skipReason,
  skipUnlessLive,
} from "./helpers";

test.describe("Help and standalone review", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("help page tabs are usable", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-help").click();
    await expect(page).toHaveURL(/\/help/);
    await expect(page.getByTestId("help-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "ภาพรวมระบบ" })).toBeVisible();
    await saveEvidence(page, "10a-help-overview");
    const tabs: Array<{ id: string; heading: string }> = [
      { id: "login", heading: "เข้าสู่ระบบ" },
      { id: "dashboard", heading: "แดชบอร์ด" },
      { id: "draft", heading: "กระบวนการร่างห้าขั้น" },
      { id: "chat", heading: "ถาม-ตอบ" },
      { id: "kb", heading: "ฐานความรู้" },
      { id: "review", heading: "ตรวจสอบ TOR" },
      { id: "admin", heading: "ผู้ดูแลระบบ" },
      { id: "faq", heading: "คำถามที่พบบ่อย" },
    ];
    const tabShots: Record<string, string> = {
      login: "10g-help-login",
      dashboard: "10b-help-dashboard",
      draft: "10c-help-draft",
      chat: "10f-help-chat",
      kb: "10e-help-kb",
      review: "10d-help-review",
      admin: "10h-help-admin",
      faq: "10-help-faq",
    };
    for (const tab of tabs) {
      await page.getByTestId(`help-tab-${tab.id}`).click();
      await expect(page.getByRole("heading", { name: tab.heading })).toBeVisible();
      await pauseLikeUser(page, 500);
      await saveEvidence(page, tabShots[tab.id]);
    }
    await page.getByTestId("help-tab-draft").click();
    await expect(page.getByText("ไปขั้นที่ ๒").first()).toBeVisible();
    await expect(page.getByText("ไม่มีปุ่มต่อแถว")).toBeVisible();
    await expect(page.getByText("แชทรีวิวสรุปคะแนน")).toBeVisible();
    await page.getByTestId("help-tab-faq").click();
    await expect(page.getByText(/google\/gemma-4-e4b/)).toBeVisible();
    await expect(page.getByText(/text-embedding-embeddinggemma-300m/)).toBeVisible();
    await expect(page.getByText(/127\.0\.0\.1:1234/)).toBeVisible();
    await saveEvidence(page, "10-help-faq");
  });

  test("knowledge base is in the main menu", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-knowledge-base").click();
    await expect(page).toHaveURL(/\/knowledge-base/);
    await expect(page.getByTestId("knowledge-base-page")).toBeVisible();
    await expect(page.getByText("อัปโหลดเอกสารของฉัน")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "เอกสารที่ผู้ใช้อัปโหลด (เฉพาะบัญชีนี้)" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "พ.ร.บ. / กฎหมาย" })).toBeVisible();
    await expect(page.getByRole("button", { name: "หนังสือเวียนกรมบัญชีกลาง" })).toBeVisible();
    await expect(page.getByRole("button", { name: "ประกาศราคากลาง" })).toBeVisible();
    await expect(page.getByTestId("kb-mine-count")).toBeVisible();
    await saveEvidence(page, "11-knowledge-base");
  });

  test("standalone review page loads", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-review").click();
    await expect(page).toHaveURL(/\/review/);
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByText("อัปโหลด TOR ที่ต้องการตรวจสอบ")).toBeVisible();
    await expect(page.getByTestId("review-extract")).toBeDisabled();
    await expect(page.getByTestId("review-stepper")).toBeVisible();
    if (!headedRun) {
      await saveEvidence(page, "12-standalone-review");
    }
  });

  test("standalone review live run shows a rule score", async ({ page }) => {
    test.setTimeout(360_000);
    await login(page);
    await page.getByTestId("nav-review").click();
    await expect(page.getByTestId("review-page")).toBeVisible();
    await page.locator("[data-testid=review-page] input[type=file]").first().setInputFiles({
      name: "tor-e2e.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(LIVE_INTAKE_TEXT, "utf-8"),
    });
    await page.getByTestId("review-extract").click();
    await expect(page.getByTestId("review-extract-preview")).toBeVisible({ timeout: 120_000 });
    await page.getByTestId("review-confirm-run").click();
    await expect(page.getByTestId("review-error")).toHaveCount(0);
    await expect(page.getByTestId("review-score")).toContainText(/[0-9]{1,3}\/100/, {
      timeout: 180_000,
    });
    await saveEvidence(page, "12c-review-score");
  });

  test("standalone review extract then confirm run", async ({ page }) => {
    // NOSONAR: Headed runs use live Rule Engine in realistic-flow; this case is mocked APIs only.
    test.skip(headedRun, skipMockedInHeadedReason);
    const envelope = (data: unknown) => ({
      ok: true,
      data,
      meta: { request_id: "e2e", timestamp: new Date().toISOString() },
    });
    await page.route("**/api/v1/review/extract", async (route) => {
      await route.fulfill({
        json: envelope({ id: "job-1", extracted_text: "ร่าง TOR ทดสอบวงเงิน" }),
      });
    });
    await page.route("**/api/v1/review/run", async (route) => {
      await route.fulfill({
        json: envelope({ quality_score: 72, findings: [] }),
      });
    });
    await login(page);
    await page.getByTestId("nav-review").click();
    await page.locator("[data-testid=review-page] input[type=file]").first().setInputFiles({
      name: "tor.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 test"),
    });
    await page.getByTestId("review-extract").click();
    await expect(page.getByTestId("review-extract-preview")).toContainText("ร่าง TOR ทดสอบ");
    await page.getByTestId("review-back").click();
    await expect(page.getByTestId("review-extract")).toBeVisible();
    await page.getByTestId("review-extract").click();
    await expect(page.getByTestId("review-extract-preview")).toBeVisible();
    await page.getByTestId("review-confirm-run").click();
    await expect(page.getByTestId("review-result")).toContainText("คะแนนความพร้อม 72/100");
    await saveEvidence(page, "12a-review-detail");
  });
});
