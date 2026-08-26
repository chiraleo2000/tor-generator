import { test, expect } from "@playwright/test";
import { Buffer } from "node:buffer";
import {
  login,
  pauseLikeUser,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
  waitForLiveAssistant,
} from "./helpers";

test.describe("Chat Q&A and draft intake", () => {
  // NOSONAR: Playwright E2E spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("ถาม-ตอบ opens Open WebUI-like rooms", async ({ page }) => {
    test.setTimeout(720_000);
    await login(page);
    await page.getByTestId("nav-chat").click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await expect(page.getByTestId("chat-room-list")).toBeVisible();
    await expect(page.getByTestId("chat-new-room")).toBeVisible();
    await expect(page.getByTestId("chat-input")).toBeVisible();
    await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
    await saveEvidence(page, "13a-chat-rooms");
    await typeLikeUser(
      page.getByTestId("chat-input"),
      "งวดจ่ายต้องวางหลักประกันสัญญาหรือไม่ ตามระเบียบพัสดุ"
    );
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 600_000);
    await expect.poll(
      async () =>
        (await page.getByTestId("chat-msg-assistant").last().innerText()).length,
      { timeout: 480_000 }
    ).toBeGreaterThan(1500);
    await saveEvidence(page, "13-kb-chat");
  });

  test("chat attach ingests into private KB list", async ({ page }) => {
    test.setTimeout(720_000);
    await login(page);
    await page.getByTestId("nav-chat").click();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await expect(page.getByTestId("chat-new-room")).toBeVisible();
    await expect(page.getByTestId("chat-room-item").first()).toBeVisible({
      timeout: 30_000,
    });
    const fileName = `ระเบียบวงเงิน-e2e-${Date.now()}.txt`;
    await page.getByTestId("chat-attach").setInputFiles({
      name: fileName,
      mimeType: "text/plain",
      buffer: Buffer.from(
        "หลักเกณฑ์วงเงินจัดซื้อจัดจ้างภาครัฐ ตามระเบียบกรมบัญชีกลาง สำหรับคลังส่วนตัวทดสอบ E2E",
        "utf-8"
      ),
    });
    await expect(page.getByTestId("chat-attach-feedback")).toBeVisible({
      timeout: 20_000,
    });
    await expect.poll(
      async () => {
        const err = page.getByTestId("chat-error");
        if (await err.count()) {
          throw new Error(await err.innerText());
        }
        return page.getByTestId("chat-attach-feedback").innerText();
      },
      { timeout: 180_000 }
    ).toMatch(/เพิ่มเข้าคลังของฉันแล้ว/);
    await expect(page.getByTestId("chat-error")).toHaveCount(0);
    await expect(page.getByTestId("chat-mine-files")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: "คลังของฉัน" })).toHaveAttribute(
      "href",
      "/knowledge-base"
    );
    await expect(page.getByTestId("chat-mine-files").getByText(fileName)).toBeVisible();
    await saveEvidence(page, "13b-chat-attach");
    await page.getByTestId("nav-knowledge-base").click();
    await expect(page.getByTestId("knowledge-base-page")).toBeVisible();
    await expect(page.getByTestId("knowledge-base-page").getByText(fileName)).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId("nav-chat").click();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await page.getByTestId("chat-scope-mine").click();
    await pauseLikeUser(page, 400);
    await typeLikeUser(page.getByTestId("chat-input"), "สรุปเอกสารของฉันเรื่องวงเงินจัดซื้อจัดจ้าง");
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 600_000);
    await saveEvidence(page, "13c-chat-attach-ask");
    const citation = page.getByTestId("chat-citation");
    if (await citation.count()) {
      await expect(citation.first()).toBeVisible();
    }
  });
});
