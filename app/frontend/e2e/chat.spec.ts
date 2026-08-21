import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  createProjectAndOpenDraft,
  login,
  pauseLikeUser,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
  waitForLiveAssistant,
  walkLiveAnalyzeToPhase1,
} from "./helpers";

test.describe("Chat Q&A and draft intake", () => {
  // NOSONAR: Playwright E2E spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("ถาม-ตอบ opens Open WebUI-like rooms", async ({ page }) => {
    test.setTimeout(300_000);
    await login(page);
    await page.getByTestId("nav-chat").click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await expect(page.getByTestId("chat-room-list")).toBeVisible();
    await expect(page.getByTestId("chat-new-room")).toBeVisible();
    await expect(page.getByTestId("chat-input")).toBeVisible();
    await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
    await typeLikeUser(
      page.getByTestId("chat-input"),
      "งวดจ่ายต้องวางหลักประกันสัญญาหรือไม่ ตามระเบียบพัสดุ"
    );
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 180_000);
    await saveEvidence(page, "13-kb-chat");
  });

  test("chat attach ingests into private KB list", async ({ page }) => {
    test.setTimeout(360_000);
    await login(page);
    await page.getByTestId("nav-chat").click();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await page.getByTestId("chat-attach").setInputFiles({
      name: "ระเบียบวงเงิน.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "หลักเกณฑ์วงเงินจัดซื้อจัดจ้างภาครัฐ ตามระเบียบกรมบัญชีกลาง สำหรับคลังส่วนตัวทดสอบ E2E",
        "utf-8"
      ),
    });
    await expect(page.getByTestId("chat-attach-feedback")).toContainText(
      "เพิ่มเข้าคลังของฉันแล้ว",
      { timeout: 120_000 }
    );
    await expect(page.getByTestId("chat-mine-files")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: "คลังของฉัน" })).toHaveAttribute(
      "href",
      "/knowledge-base"
    );
    await page.getByTestId("chat-scope-mine").click();
    await pauseLikeUser(page, 400);
    await typeLikeUser(page.getByTestId("chat-input"), "สรุปเอกสารของฉันเรื่องวงเงินจัดซื้อจัดจ้าง");
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 180_000);
  });

  test("Phase 0–1 is intake chat; upload then confirm-ready", async ({ page }) => {
    test.setTimeout(420_000);
    await login(page);
    await createProjectAndOpenDraft(page);
    await expect(page.getByTestId("intake-chat-panel")).toBeVisible();
    await expect(page.getByText("Phase 0: เตรียมข้อมูล")).toBeVisible();
    await expect(page.getByTestId("intake-paste")).toBeVisible();
    await expect(page.getByTestId("intake-upload")).toBeAttached();
    await expect(page.getByTestId("intake-start-analyze")).toBeVisible();
    await expect(page.getByTestId("phase1-coverage")).toHaveCount(0);
    await expect(page.getByTestId("intake-confirm-ready")).toHaveCount(0);
    await saveEvidence(page, "03-phase-0-upload");
    await walkLiveAnalyzeToPhase1(page);
  });
});
