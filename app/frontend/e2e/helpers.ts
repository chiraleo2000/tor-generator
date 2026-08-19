import { expect, type Page } from "@playwright/test";
import path from "node:path";

export const DEMO_EMAIL = process.env.E2E_EMAIL || "officer@example.go.th";
export const DEMO_PASSWORD = process.env.E2E_PASSWORD || "Passw0rd!";
export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@example.go.th";
export const REVIEWER_EMAIL = process.env.E2E_REVIEWER_EMAIL || "reviewer@example.go.th";

export const skipUnlessLive = process.env.E2E !== "1";
export const skipReason =
  "Set E2E=1 and run a live stack (compose + seed) to execute this spec";

export const evidenceDir = path.resolve(
  __dirname,
  "../../../discussions/test-evidence"
);

export async function saveEvidence(page: Page, name: string) {
  await page.screenshot({
    path: path.join(evidenceDir, `${name}.png`),
    fullPage: true,
  });
}

export async function login(
  page: Page,
  email = DEMO_EMAIL,
  password = DEMO_PASSWORD
) {
  await page.goto("/login");
  await expect(page.getByTestId("login-form")).toBeVisible();
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/projects/, { timeout: 20_000 });
  await expect(page.getByTestId("projects-page")).toBeVisible();
  await expect(page.getByTestId("login-error")).toHaveCount(0);
  await expect(page.getByTestId("toast-region")).toHaveCount(1);
}

export async function createProjectAndOpenDraft(page: Page) {
  await page.getByTestId("new-project").click();
  await expect(page.getByTestId("new-project-dialog")).toBeVisible();
  await page.getByTestId("new-project-name").fill("โครงการทดสอบ E2E");
  await page.getByTestId("new-project-ministry").fill("กรมบัญชีกลาง");
  await page.getByTestId("new-project-budget").fill("100000");
  await page.getByTestId("create-project-submit").click();
  await expect(page.getByTestId("draft-page")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("phase-0")).toBeVisible();
}

export async function walkFivePhases(page: Page) {
  await expect(page.getByTestId("draft-page")).toBeVisible();
  await expect(page.getByTestId("intake-chat-panel")).toBeVisible();
  await expect(page.getByText("Phase 0: อัปโหลดชุดเอกสาร")).toBeVisible();
  await expect(page.getByTestId("intake-paste")).toBeVisible();
  await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
  await page.getByTestId("phase-2").click({ force: true });
  await expect(page.getByText("Phase 0: อัปโหลดชุดเอกสาร")).toBeVisible();
  await expect(page.getByText("Phase 2: ร่างเนื้อหา TOR")).toHaveCount(0);
  await saveEvidence(page, "03-phase-0-upload");
}

export async function unlockPhase2ViaMockedIntake(page: Page) {
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
  const slotMap = {
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
  await page.route("**/intake/text", async (route) => {
    await route.fulfill({ json: envelope({ files: ["ข้อความผู้ใช้.txt"], count: 1 }) });
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
  await page.route("**/intake/confirm-ready", async (route) => {
    await route.fulfill({ json: envelope({ ready_to_compose: true, phase: 2 }) });
  });
  await page.route("**/projects/*/phase", async (route) => {
    await route.fulfill({ json: envelope({ current_phase: 2 }) });
  });
  await page.getByTestId("intake-paste").fill(
    "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งร้อยแปดสิบวัน สถานที่กรมบัญชีกลาง"
  );
  await page.getByTestId("intake-analyze-text").click();
  await expect(page.getByText("แกะข้อความแล้ว")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("intake-confirm-ready").click();
  await expect(page.getByText("Phase 2: ร่างเนื้อหา TOR")).toBeVisible({ timeout: 20_000 });
}
