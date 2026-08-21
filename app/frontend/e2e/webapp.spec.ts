import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import { login, saveEvidence, skipReason, skipUnlessLive } from "./helpers";

test.describe("Help and standalone review", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  test.skip(skipUnlessLive, skipReason);

  test("help page tabs are usable", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-help").click();
    await expect(page).toHaveURL(/\/help/);
    await expect(page.getByTestId("help-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "ภาพรวมระบบ" })).toBeVisible();
    await page.getByTestId("help-tab-draft").click();
    await expect(page.getByRole("heading", { name: "กระบวนการร่าง 5 Phase" })).toBeVisible();
    await page.getByTestId("help-tab-chat").click();
    await expect(page.getByRole("heading", { name: "ถาม-ตอบ" })).toBeVisible();
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
    await saveEvidence(page, "12-standalone-review");
  });

  test("standalone review extract then confirm run", async ({ page }) => {
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
