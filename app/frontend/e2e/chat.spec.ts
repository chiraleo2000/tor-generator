import { test, expect } from "@playwright/test";
import {
  createProjectAndOpenDraft,
  login,
  saveEvidence,
  skipReason,
  skipUnlessLive,
} from "./helpers";

test.describe("Chat Q&A and draft intake", () => {
  // NOSONAR: Playwright E2E spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("ถาม-ตอบ opens Open WebUI-like rooms", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-chat").click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.getByTestId("chat-page")).toBeVisible();
    await expect(page.getByTestId("chat-shell")).toBeVisible();
    await expect(page.getByTestId("chat-room-list")).toBeVisible();
    await expect(page.getByTestId("chat-new-room")).toBeVisible();
    await expect(page.getByTestId("chat-input")).toBeVisible();
    await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
    await saveEvidence(page, "13-kb-chat");
  });

  test("Phase 0–1 is intake chat; upload then confirm-ready", async ({ page }) => {
    await login(page);

    const envelope = (data: unknown) => ({
      ok: true,
      data,
      meta: { request_id: "e2e", timestamp: new Date().toISOString() },
    });
    const filledSlot = {
      content: "ข้อมูลข้อเท็จจริงของโครงการทดสอบ",
      status: "filled",
      sources: ["ผู้ใช้"],
    };
    const slotMap: Record<string, typeof filledSlot> = {
      s1: filledSlot,
      s2: filledSlot,
      s5: filledSlot,
      s6: filledSlot,
      s7: filledSlot,
      "s4.1": filledSlot,
    };
    const coverage = Object.entries(slotMap).map(([key, slot]) => ({
      key,
      label: key,
      status: slot.status,
      filled: true,
      fact_required: true,
    }));
    const room = {
      id: "11111111-1111-1111-1111-111111111111",
      kind: "draft_intake",
      project_id: null,
      title: "แชทร่าง TOR",
      updated_at: new Date().toISOString(),
      last_message: "",
      last_role: null,
    };

    await page.route("**/api/v1/chat/rooms**", async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await route.fulfill({ json: envelope({ rooms: [room] }) });
        return;
      }
      await route.fulfill({ json: envelope(room) });
    });
    await page.route("**/api/v1/chat/prompts**", async (route) => {
      await route.fulfill({
        json: envelope({
          prompts: [{ id: "p1", title: "จัดเข้า 13 หมวด", body: "จัดเข้า 13 หมวด" }],
        }),
      });
    });
    await page.route("**/api/v1/chat/rooms/*/messages", async (route) => {
      await route.fulfill({ json: envelope({ messages: [] }) });
    });
    await page.route("**/intake/coverage", async (route) => {
      await route.fulfill({
        json: envelope({
          coverage: [],
          gap_questions: [],
          ready_to_compose: false,
          slot_map: {},
        }),
      });
    });

    await createProjectAndOpenDraft(page);
    await expect(page.getByTestId("intake-chat-panel")).toBeVisible();
    await expect(page.getByText("Phase 0: อัปโหลดชุดเอกสาร")).toBeVisible();
    await expect(page.getByTestId("intake-upload")).toBeAttached();
    await saveEvidence(page, "03-phase-0-upload");

    await page.route("**/intake/coverage", async (route) => {
      await route.fulfill({
        json: envelope({
          coverage,
          gap_questions: [],
          ready_to_compose: false,
          slot_map: slotMap,
        }),
      });
    });
    await page.route("**/intake/upload", async (route) => {
      await route.fulfill({ json: envelope({ files: ["pack.txt"], count: 1 }) });
    });
    await page.route("**/intake/analyze", async (route) => {
      await route.fulfill({
        json: envelope({
          slot_map: slotMap,
          gap_questions: [],
          coverage,
          ready_to_compose: false,
        }),
      });
    });
    await page.route("**/intake/confirm-ready", async (route) => {
      await route.fulfill({
        json: envelope({ ready_to_compose: true, phase: 2 }),
      });
    });
    await page.route("**/projects/*/phase", async (route) => {
      await route.fulfill({ json: envelope({ phase: 2 }) });
    });

    await page.getByTestId("intake-upload").setInputFiles({
      name: "pack.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("โครงการทดสอบ วงเงิน 100000 บาท"),
    });
    await expect(page.getByText("แกะเอกสารแล้ว")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("intake-confirm-ready")).toBeVisible();
    await saveEvidence(page, "04b-phase-1-coverage");
    await page.getByTestId("intake-confirm-ready").click();
    await expect(page.getByText("Phase 2: ร่างเนื้อหา TOR")).toBeVisible({
      timeout: 20_000,
    });
  });
});
