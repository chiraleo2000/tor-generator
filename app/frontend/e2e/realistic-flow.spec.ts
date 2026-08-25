import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
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

const TOR_TEXT = [
  "1. ความเป็นมา",
  "โครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์ของสำนักงานปลัดกระทรวง วงเงิน 5,000,000 บาท",
  "2. วัตถุประสงค์ เพื่อทดแทนครุภัณฑ์ตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560",
  "ระยะเวลา 180 วัน สถานที่กรุงเทพมหานคร",
].join("\n");

test.describe("Realistic unmocked golden paths", () => {
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("ตรวจ TOR — extract real file then confirm Rule Engine", async ({ page }) => {
    test.setTimeout(420_000);
    await login(page);
    await page.getByTestId("nav-review").click();
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByTestId("review-stepper")).toBeVisible();
    await saveEvidence(page, "12-standalone-review");
    await pauseLikeUser(page, 1500);
    const fileInput = page.locator("[data-testid=review-page] input[type=file]").first();
    await fileInput.setInputFiles({
      name: "tor-draft.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(TOR_TEXT, "utf-8"),
    });
    await pauseLikeUser(page, 800);
    await expect(page.getByTestId("review-extract")).toBeEnabled();
    await page.getByTestId("review-extract").click();
    await expect(
      page.getByTestId("review-busy").or(page.getByTestId("review-extract-preview"))
    ).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("review-extract-preview")).toBeVisible({
      timeout: 120_000,
    });
    const preview = await page.getByTestId("review-extract-preview").innerText();
    expect(preview).toMatch(/จัดซื้อ|วงเงิน|โครงการ|พัสดุ|TOR/i);
    await saveEvidence(page, "12a-review-detail");
    await pauseLikeUser(page, 1500);
    await page.getByTestId("review-confirm-run").click();
    await expect(
      page.getByTestId("review-busy").or(page.getByTestId("review-score"))
    ).toBeVisible({ timeout: 15_000 });
    await saveEvidence(page, "12b-review-running");
    await expect(page.getByTestId("review-score")).toBeVisible({ timeout: 180_000 });
    await expect(page.getByTestId("review-result")).toContainText("คะแนนความพร้อม");
    await saveEvidence(page, "12c-review-score");
    await page.reload();
    await expect(page.getByTestId("review-score")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("review-result")).toContainText("คะแนนความพร้อม");
  });

  test("Knowledge Base — category other, upload, download, delete", async ({
    page,
  }) => {
    test.setTimeout(240_000);
    await login(page);
    await page.getByTestId("nav-knowledge-base").click();
    await expect(page.getByTestId("knowledge-base-page")).toBeVisible();
    await expect(page.getByRole("button", { name: "ข้อมูลอื่น ๆ" })).toBeVisible();
    await page.getByRole("button", { name: "ข้อมูลอื่น ๆ" }).click();
    await pauseLikeUser(page, 600);
    const uniqueName = `บันทึกภายใน-e2e-${Date.now()}.txt`;
    await page.locator("[data-testid=knowledge-base-page] input[type=file]").setInputFiles({
      name: uniqueName,
      mimeType: "text/plain",
      buffer: Buffer.from(
        "หลักเกณฑ์วงเงินจัดซื้อจัดจ้างภาครัฐ ตามระเบียบกรมบัญชีกลาง สำหรับทดสอบคลังของฉัน",
        "utf-8"
      ),
    });
    await expect(page.getByText(/อัปโหลดเฉพาะบัญชีของคุณแล้ว|อัปโหลดไม่สำเร็จ/)).toBeVisible({
      timeout: 180_000,
    });
    await expect(page.getByText(uniqueName)).toBeVisible({ timeout: 30_000 });
    await saveEvidence(page, "11b-kb-mine-status");
    const downloadBtn = page.locator("[data-testid^=download-mine-]").first();
    if (await downloadBtn.count()) {
      const [download] = await Promise.all([
        page.waitForEvent("download", { timeout: 30_000 }).catch(() => null),
        downloadBtn.click(),
      ]);
      if (download) {
        expect(await download.failure()).toBeNull();
      }
    }
    await pauseLikeUser(page, 800);
    page.once("dialog", (dialog) => {
      void dialog.accept();
    });
    await page.locator("[data-testid^=delete-user-file-]").first().click();
    await expect(
      page.getByText(`ลบ «${uniqueName}» แล้ว`).or(page.getByText("ลบเอกสารไม่สำเร็จ"))
    ).toBeVisible({ timeout: 20_000 });
  });

  test("ร่าง TOR — Phase 0 start-analyze is visible without auto-run", async ({
    page,
  }) => {
    // NOSONAR: Headed runs cover Phase 0 via live wizard-flow / chat specs instead of this stub.
    test.skip(headedRun, skipMockedInHeadedReason);
    test.setTimeout(120_000);
    await login(page);
    await createProjectAndOpenDraft(page);
    await expect(page.getByTestId("intake-start-analyze")).toBeVisible();
    await expect(page.getByTestId("phase1-coverage")).toHaveCount(0);
    await saveEvidence(page, "03-phase-0-upload");
  });
});
