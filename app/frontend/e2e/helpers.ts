import { expect, type Locator, type Page } from "@playwright/test";
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

/** Per-keystroke delay so headed runs look like a person typing. */
const TYPE_DELAY_MS = Number(process.env.E2E_TYPE_DELAY_MS || "70");
const PAUSE_MS = Number(process.env.E2E_PAUSE_MS || "600");

export const LIVE_INTAKE_TEXT = [
  "ความเป็นมา (s1): กรมบัญชีกลางมีความจำเป็นต้องจัดซื้อระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้าง",
  "เพื่อติดตามงวดจ่ายและการส่งมอบให้เป็นไปตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
  "วัตถุประสงค์ (s2): เพื่อให้เจ้าหน้าที่พัสดุบริหารสัญญา ตรวจรับงาน และรายงานสถานะได้ครบถ้วนตามกฎหมาย",
  "วงเงินงบประมาณ (s5): 2,500,000 บาท (สองล้านห้าแสนบาทถ้วน) จากงบดำเนินงานประจำปี",
  "ระยะเวลาดำเนินการ (s6): 180 วัน นับจากวันที่ลงนามในสัญญา",
  "สถานที่ดำเนินการ (s7): กรมบัญชีกลาง ถนนพระรามที่ 6 แขวงพญาไท เขตพญาไท กรุงเทพมหานคร",
  "ขอบเขตงานหลัก (s4.1): วิเคราะห์ความต้องการ พัฒนาโมดูลบริหารสัญญา ทดสอบระบบ อบรมผู้ใช้ และส่งมอบคู่มือใช้งาน",
].join("\n");

const FACT_SLOT_KEYS = ["s1", "s2", "s5", "s6", "s7", "s4.1"] as const;

const LIVE_GAP_ANSWERS = [
  "ความเป็นมาคือกรมบัญชีกลางต้องมีระบบบริหารสัญญาจัดซื้อจัดจ้างภาครัฐ",
  "วัตถุประสงค์เพื่อติดตามงวดจ่าย ตรวจรับงาน และรายงานสถานะตามกฎหมาย",
  "วงเงินงบประมาณสองล้านห้าแสนบาทถ้วน จากงบดำเนินงานประจำปี",
  "ระยะเวลาดำเนินการหนึ่งร้อยแปดสิบวันนับจากวันลงนามในสัญญา",
  "สถานที่ดำเนินการคือกรมบัญชีกลาง ถนนพระรามที่ 6 กรุงเทพมหานคร",
  "ขอบเขตงานหลักคือวิเคราะห์ความต้องการ พัฒนา ทดสอบ อบรม และส่งมอบคู่มือ",
  "รายละเอียดเพิ่มเติม ระบบต้องเชื่อมโยงข้อมูลสัญญา งวดจ่าย และการตรวจรับ",
  "ผู้ใช้งานหลักคือเจ้าหน้าที่พัสดุและผู้ตรวจสอบภายในของกรมบัญชีกลาง",
];

export async function pauseLikeUser(page: Page, ms = PAUSE_MS) {
  await page.waitForTimeout(ms);
}

export async function typeLikeUser(locator: Locator, text: string) {
  await locator.click();
  await locator.fill("");
  await locator.pressSequentially(text, { delay: TYPE_DELAY_MS });
}

export async function confirmPhase(page: Page) {
  await expect(page.getByTestId("confirm-phase-dialog")).toBeVisible();
  await pauseLikeUser(page, 400);
  await page.getByTestId("confirm-phase-ok").click();
}

export async function saveEvidence(page: Page, name: string) {
  await page.screenshot({
    path: path.join(evidenceDir, `${name}.png`),
    fullPage: true,
  });
}

export async function waitForLiveAssistant(page: Page, timeout = 180_000) {
  await expect(page.getByTestId("chat-msg-assistant").last()).toContainText(/\S.{15,}/, {
    timeout,
  });
}

export async function login(
  page: Page,
  email = DEMO_EMAIL,
  password = DEMO_PASSWORD
) {
  await page.goto("/login");
  await expect(page.getByTestId("login-form")).toBeVisible();
  await typeLikeUser(page.getByTestId("login-email"), email);
  await pauseLikeUser(page, 350);
  await typeLikeUser(page.getByTestId("login-password"), password);
  await pauseLikeUser(page, 400);
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/projects/, { timeout: 20_000 });
  await expect(page.getByTestId("projects-page")).toBeVisible();
  await expect(page.getByTestId("login-error")).toHaveCount(0);
  await expect(page.getByTestId("toast-region")).toHaveCount(1);
  await pauseLikeUser(page);
}

export async function createProjectAndOpenDraft(page: Page) {
  await page.getByTestId("new-project").click();
  await expect(page.getByTestId("new-project-dialog")).toBeVisible();
  await typeLikeUser(page.getByTestId("new-project-name"), "โครงการทดสอบ E2E");
  await pauseLikeUser(page, 300);
  await typeLikeUser(page.getByTestId("new-project-ministry"), "กรมบัญชีกลาง");
  await pauseLikeUser(page, 300);
  await typeLikeUser(page.getByTestId("new-project-budget"), "100000");
  await pauseLikeUser(page, 400);
  await page.getByTestId("create-project-submit").click();
  await expect(page.getByTestId("draft-page")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("phase-0")).toBeVisible();
  await pauseLikeUser(page);
}

export async function walkFivePhases(page: Page) {
  await expect(page.getByTestId("draft-page")).toBeVisible();
  await expect(page.getByTestId("intake-chat-panel")).toBeVisible();
  await expect(page.getByText("Phase 0: เตรียมข้อมูล")).toBeVisible();
  await expect(page.getByTestId("intake-paste")).toBeVisible();
  await expect(page.getByTestId("intake-start-analyze")).toBeVisible();
  await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
  await page.getByTestId("phase-2").click({ force: true });
  await expect(page.getByText("Phase 0: เตรียมข้อมูล")).toBeVisible();
  await expect(page.getByText("Phase 3: ร่างเนื้อหา TOR")).toHaveCount(0);
  await saveEvidence(page, "03-phase-0-upload");
}

async function allFactSlotsFilled(page: Page): Promise<boolean> {
  for (const key of FACT_SLOT_KEYS) {
    const row = page.getByTestId(`coverage-row-${key}`);
    if ((await row.count()) === 0) {
      return false;
    }
    if ((await row.getAttribute("data-status")) !== "filled") {
      return false;
    }
  }
  return true;
}

async function answerFactGapsViaIntakeChat(page: Page) {
  for (const answer of LIVE_GAP_ANSWERS) {
    if (await allFactSlotsFilled(page)) {
      return;
    }
    await typeLikeUser(page.getByTestId("chat-input"), answer);
    await pauseLikeUser(page, 500);
    await page.getByTestId("chat-send").click();
    await waitForLiveAssistant(page, 180_000);
    await pauseLikeUser(page, 800);
  }
  expect(await allFactSlotsFilled(page)).toBe(true);
}

export async function walkLiveAnalyzeToPhase1(page: Page) {
  await expect(page.getByTestId("intake-paste")).toBeVisible();
  await typeLikeUser(page.getByTestId("intake-paste"), LIVE_INTAKE_TEXT);
  await pauseLikeUser(page, 800);
  await page.getByTestId("intake-start-analyze").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase1-coverage")).toBeVisible({ timeout: 240_000 });
  await saveEvidence(page, "04b-phase-1-coverage");
  await expect(page.getByTestId("phase1-filling-refs")).toHaveCount(0, {
    timeout: 240_000,
  });
  await expect(page.getByTestId("intake-enter-qa")).toBeVisible({ timeout: 30_000 });
}

/** Real backend + LM Studio: paste, analyze, fill-references, Phase 2 chat if needed, compose. */
export async function walkLiveDraftToCompose(page: Page) {
  await walkLiveAnalyzeToPhase1(page);
  await pauseLikeUser(page, 700);
  await page.getByTestId("intake-enter-qa").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase2-qa")).toBeVisible({ timeout: 30_000 });
  await answerFactGapsViaIntakeChat(page);
  await pauseLikeUser(page, 700);
  await page.getByTestId("intake-confirm-ready").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase3-draft")).toBeVisible({
    timeout: 90_000,
  });
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
  let projectPhase = 0;
  let readyToCompose = false;
  await page.route("**/intake/text", async (route) => {
    await route.fulfill({ json: envelope({ files: ["ข้อความผู้ใช้.txt"], count: 1 }) });
  });
  await page.route("**/intake/analyze", async (route) => {
    projectPhase = Math.max(projectPhase, 1);
    await route.fulfill({
      json: envelope({
        slot_map: slotMap,
        gap_questions: [],
        coverage,
        ready_to_compose: false,
        analyzed: true,
        phase: 1,
      }),
    });
  });
  await page.route("**/intake/coverage", async (route) => {
    await route.fulfill({
      json: envelope({
        coverage,
        gap_questions: [],
        ready_to_compose: readyToCompose,
        slot_map: slotMap,
        has_material: true,
        analyzed: true,
      }),
    });
  });
  await page.route("**/intake/fill-references", async (route) => {
    await route.fulfill({ json: envelope({ filled_keys: [], coverage }) });
  });
  await page.route("**/intake/confirm-ready", async (route) => {
    readyToCompose = true;
    projectPhase = 3;
    await route.fulfill({ json: envelope({ ready_to_compose: true, phase: 3 }) });
  });
  await page.route(/\/api\/v1\/projects\/[0-9a-f-]+$/i, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      json: envelope({
        name: "โครงการทดสอบ E2E",
        ministry: "กรมบัญชีกลาง",
        budget: 100000,
        project_type: "general",
        status: "draft",
        current_phase: projectPhase,
        current_step: 1,
        analysis_json: {
          analyzed: projectPhase >= 1,
          slot_map: projectPhase >= 1 ? slotMap : {},
          ready_to_compose: readyToCompose,
          has_material: true,
        },
        extracted_fields: { intake_texts: [{ text: "โครงการทดสอบ" }] },
      }),
    });
  });
  await page.route("**/projects/*/phase", async (route) => {
    const body = route.request().postDataJSON() as { phase?: number };
    projectPhase = Number(body?.phase ?? projectPhase);
    await route.fulfill({ json: envelope({ current_phase: projectPhase }) });
  });
  await typeLikeUser(
    page.getByTestId("intake-paste"),
    "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งร้อยแปดสิบวัน สถานที่กรมบัญชีกลาง"
  );
  await page.getByTestId("intake-start-analyze").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase1-coverage")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("intake-enter-qa")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("intake-enter-qa").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase2-qa")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("intake-confirm-ready").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase3-draft")).toBeVisible({ timeout: 20_000 });
}
