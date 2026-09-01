import { expect, type Locator, type Page } from "@playwright/test";
import { Buffer } from "node:buffer";
import path from "node:path";

export const DEMO_EMAIL = process.env.E2E_EMAIL || "officer@example.go.th";
export const DEMO_PASSWORD = process.env.E2E_PASSWORD || "Passw0rd!";
export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@example.go.th";
export const REVIEWER_EMAIL = process.env.E2E_REVIEWER_EMAIL || "reviewer@example.go.th";

export const skipUnlessLive = process.env.E2E !== "1";
export const headedRun = process.env.HEADED === "1";
export const skipReason =
  "Set E2E=1 and run a live stack (compose + seed) to execute this spec";
export const skipMockedInHeadedReason =
  "Headed runs walk the live 5-phase workflow instead of mocked APIs";

export const evidenceDir = path.resolve(
  __dirname,
  "../../../discussions/test-evidence"
);

/** Per-keystroke delay so headed runs look like a person typing. */
const TYPE_DELAY_MS = Number(process.env.E2E_TYPE_DELAY_MS || "70");
const PAUSE_MS = Number(
  process.env.E2E_PAUSE_MS || (process.env.HEADED === "1" ? "900" : "600")
);

export const LIVE_INTAKE_TEXT = [
  "ความเป็นมา (s1): กรมบัญชีกลางมีความจำเป็นต้องจัดซื้อระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้าง",
  "เพื่อติดตามงวดจ่ายและการส่งมอบให้เป็นไปตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
  "วัตถุประสงค์ (s2): เพื่อให้เจ้าหน้าที่พัสดุบริหารสัญญา ตรวจรับงาน และรายงานสถานะได้ครบถ้วนตามกฎหมาย",
  "ระยะเวลาดำเนินการ (s5): 180 วัน นับจากวันที่ลงนามในสัญญา",
  "วงเงินงบประมาณ (s6): 2,500,000 บาท (สองล้านห้าแสนบาทถ้วน) จากงบดำเนินงานประจำปี",
  "สถานที่ดำเนินการ (s7): กรมบัญชีกลาง ถนนพระรามที่ 6 แขวงพญาไท เขตพญาไท กรุงเทพมหานคร",
  "ขอบเขตงานหลัก (s4.1): วิเคราะห์ความต้องการ พัฒนาโมดูลบริหารสัญญา ทดสอบระบบ อบรมผู้ใช้ และส่งมอบคู่มือใช้งาน",
].join("\n");

const FACT_SLOT_KEYS = ["s1", "s2", "s5", "s6", "s7", "s4.1"] as const;

const LIVE_GAP_ANSWERS = [
  "ความเป็นมาคือกรมบัญชีกลางต้องมีระบบบริหารสัญญาจัดซื้อจัดจ้างภาครัฐ",
  "วัตถุประสงค์เพื่อติดตามงวดจ่าย ตรวจรับงาน และรายงานสถานะตามกฎหมาย",
  "ระยะเวลาดำเนินการหนึ่งร้อยแปดสิบวันนับจากวันลงนามในสัญญา",
  "วงเงินงบประมาณสองล้านห้าแสนบาทถ้วน จากงบดำเนินงานประจำปี",
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
  if (text.length > 80) {
    await locator.fill(text);
    return;
  }
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

export function liveProjectName(): string {
  return `โครงการทดสอบ E2E ${Date.now()}`;
}

export async function createProjectAndOpenDraft(
  page: Page,
  name = liveProjectName()
): Promise<string> {
  await page.getByTestId("new-project").click();
  await expect(page.getByTestId("new-project-dialog")).toBeVisible();
  await typeLikeUser(page.getByTestId("new-project-name"), name);
  await pauseLikeUser(page, 300);
  await typeLikeUser(page.getByTestId("new-project-ministry"), "กรมบัญชีกลาง");
  await pauseLikeUser(page, 300);
  await typeLikeUser(page.getByTestId("new-project-budget"), "100000");
  await pauseLikeUser(page, 400);
  await page.getByTestId("create-project-submit").click();
  await expect(page.getByTestId("draft-page")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("phase-0")).toBeVisible();
  await pauseLikeUser(page);
  return name;
}

export async function walkFivePhases(page: Page) {
  await expect(page.getByTestId("draft-page")).toBeVisible();
  await expect(page.getByTestId("intake-chat-panel")).toBeVisible();
  await expect(page.getByText("ขั้นที่ ๐: เตรียมข้อมูล")).toBeVisible();
  await expect(page.getByTestId("intake-paste")).toBeVisible();
  await expect(page.getByTestId("intake-start-analyze")).toBeVisible();
  await expect(page.getByText("โหลดห้องแชทไม่สำเร็จ")).toHaveCount(0);
  await page.getByTestId("phase-2").click({ force: true });
  await expect(page.getByText("ขั้นที่ ๐: เตรียมข้อมูล")).toBeVisible();
  await expect(page.getByText("Phase 3: ร่างเนื้อหา TOR")).toHaveCount(0);
  await walkLiveFivePhases(page);
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

async function uploadPhase0Sample(page: Page) {
  await page.getByTestId("intake-upload").setInputFiles({
    name: "pB0.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      `${LIVE_INTAKE_TEXT}\nไฟล์แนบประกอบการวิเคราะห์โครงการทดสอบ E2E`,
      "utf-8"
    ),
  });
  await expect(page.getByTestId("phase0-file-list")).toContainText("pB0.txt", {
    timeout: 30_000,
  });
}

export async function walkLiveAnalyzeToPhase1(page: Page) {
  await expect(page.getByTestId("intake-paste")).toBeVisible();
  await typeLikeUser(page.getByTestId("intake-paste"), LIVE_INTAKE_TEXT);
  await pauseLikeUser(page, 600);
  await uploadPhase0Sample(page);
  await saveEvidence(page, "03-phase-0-upload");
  await pauseLikeUser(page, 800);
  await page.getByTestId("intake-start-analyze").click();
  await confirmPhase(page);
  const analyzing = page.getByTestId("phase0-analyzing");
  await expect(analyzing.or(page.getByTestId("phase1-coverage"))).toBeVisible({
    timeout: 30_000,
  });
  if (await analyzing.count()) {
    await expect(analyzing).toContainText("อย่าปิดหน้านี้");
    await saveEvidence(page, "03b-phase-0-analyzing");
  }
  await expect(page.getByTestId("phase1-coverage")).toBeVisible({ timeout: 240_000 });
  await expect(page.getByText("รายละเอียดที่จัดเข้าช่อง")).toBeVisible();
  await expect(page.getByTestId("coverage-row-s1")).toBeVisible();
  await saveEvidence(page, "04b-phase-1-coverage");
  const skip = page.getByTestId("phase1-skip");
  await expect(skip).toBeVisible();
  await skip.click();
}

/** Real backend + LM Studio: paste, upload, analyze, Phase 2 chat if needed, compose. */
export async function walkLiveDraftToCompose(page: Page) {
  await walkLiveAnalyzeToPhase1(page);
  await expect(page.getByTestId("phase2-qa")).toBeVisible({ timeout: 25_000 });
  await expect(page.getByTestId("confirm-phase-ok")).toHaveCount(0);
  await expect(page.getByText("รายละเอียดที่จัดเข้าช่อง")).toBeVisible();
  await expect(page.getByTestId("chat-input")).toBeVisible();
  await expect(page.getByTestId("intake-enter-qa")).toHaveCount(0);
  await expect(page.getByTestId("intake-attach-legal")).toBeVisible();
  await expect(page.getByTestId("intake-attach-legal")).not.toBeChecked();
  await expect(page.getByTestId("intake-ref-chips")).toHaveCount(0);
  await saveEvidence(page, "05-phase-2-chat");
  await waitForLiveAssistant(page, 180_000);
  await answerFactGapsViaIntakeChat(page);
  await expect(page.getByTestId("intake-confirm-ready")).toBeEnabled({ timeout: 30_000 });
  await saveEvidence(page, "e2e-phase-2-qa");
  await pauseLikeUser(page, 700);
  await page.getByTestId("intake-confirm-ready").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase3-draft")).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByTestId("draft-chat")).toBeVisible();
}

const SCOPE_SUB_KEYS = Array.from({ length: 14 }, (_, i) => `s4.${i + 1}`);

const SAMPLE_SCOPE_TABLE = [
  "| รายการ | รายละเอียด |",
  "| --- | --- |",
  "| งวดที่ ๑ | ส่งมอบรายงานวิเคราะห์ |",
].join("\n");

async function assertPhase3SubsectionsThaiAndTable(page: Page) {
  const phase3 = page.getByTestId("phase3-draft");
  await expect(phase3).toContainText("ขั้นที่ ๓");
  await expect(phase3).toContainText("๔.๑–๔.๑๔");
  await expect(page.getByTestId("phase3-heading")).toBeVisible();
  await expect(page.getByTestId("phase3-heading")).toHaveText(/ขั้นที่ ๓/);
  await expect(page.getByTestId("phase3-heading")).not.toContainText("Phase 3");
  await expect(page.getByTestId("phase3-heading")).not.toContainText("As-Is");
  await expect(phase3.locator("h3", { hasText: "As-Is" })).toHaveCount(0);
  await expect(phase3.locator("label", { hasText: "As-Is" })).toHaveCount(0);
  await expect(
    page.getByTestId("scope-subsection-editor").getByRole("button", { name: /As-Is/ })
  ).toHaveCount(0);
  await expect(page.getByText("เนื้อหาร่าง (จากเอกสารหรือระบบ)")).toHaveCount(0);
  await expect(page.getByText("เนื้อหาร่าง (จากเอกสาร/AI)")).toHaveCount(0);
  const s1Header = page.getByRole("button", { name: /หมวด 1:/ });
  await expect(s1Header).toBeVisible();
  const historyField = page.getByText("ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม");
  if ((await historyField.count()) === 0) {
    await s1Header.click();
  }
  await expect(historyField).toBeVisible();
  await s1Header.click();
  const scopeHeader = page.getByRole("button", { name: /หมวด 4:/ });
  await expect(scopeHeader).toBeVisible();
  if ((await page.getByTestId("scope-subsection-editor").count()) === 0) {
    await scopeHeader.click();
  }
  await expect(page.getByTestId("scope-subsection-editor")).toBeVisible();
  await expect(page.getByTestId("scope-subsection-editor")).toContainText("๔.๑");
  for (const key of SCOPE_SUB_KEYS) {
    const panel = page.getByTestId(`scope-sub-${key}`);
    await expect(panel).toBeVisible();
    await expect(panel.locator("textarea")).toHaveValue(/\S.{15,}/);
  }
  const deliverable = page.getByTestId("scope-sub-s4.8");
  const textarea = deliverable.locator("textarea");
  const current = await textarea.inputValue();
  await textarea.fill(`${current.trim()}\n\n${SAMPLE_SCOPE_TABLE}`);
  await textarea.blur();
  await expect(deliverable.locator("table").first()).toBeVisible({ timeout: 20_000 });
  await saveEvidence(page, "08b-phase-3-subsections");
  await saveEvidence(page, "08c-phase-3-table");
}

async function assertPhase4Assemble(page: Page) {
  await expect(page.getByTestId("phase4-merged-preview")).toBeVisible();
  await expect(page.getByTestId("phase4-merged-preview")).toContainText("4.1");
  await expect(page.getByTestId("phase4-merged-preview")).toContainText("4.8");
  await expect(page.getByTestId("phase4-merged-preview").locator("table").first()).toBeVisible();
  await expect(page.getByText("s4.s4.1")).toHaveCount(0);
  await saveEvidence(page, "07b-phase-4-assemble");
}

/** From a completed Phase 3 (13/13): HITL-free confirm, Rule Engine, export, submit. */
export async function finishLivePhase3ToSubmit(page: Page) {
  const draftUrl = page.url();
  await page.goto("/projects");
  await expect(page.getByTestId("projects-page")).toBeVisible();
  await page.goto(draftUrl);
  await expect(page.getByTestId("phase3-draft")).toBeVisible({ timeout: 30_000 });
  await assertPhase3SubsectionsThaiAndTable(page);
  await saveEvidence(page, "08-phase-2-ai-draft");
  await saveEvidence(page, "e2e-phase-3-draft");
  await expect(page.getByTestId("hitl-confirm-s3")).toHaveCount(0);
  await expect(page.getByText("ต้องให้เจ้าหน้าที่ยืนยัน")).toHaveCount(0);
  await expect(page.getByTestId("phase3-confirm")).toBeEnabled();
  await page.getByTestId("phase3-confirm").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase4-review")).toBeVisible({ timeout: 30_000 });
  await assertPhase4Assemble(page);
  await expect(page.getByTestId("review-chat")).toBeVisible();
  await expect(page.getByTestId("review-chat-input")).toBeVisible();
  await expect(page.getByTestId("run-review")).toBeVisible();
  await expect(page.getByTestId("phase4-export")).toBeVisible();
  await saveEvidence(page, "07a-phase-4-reviewing");
  await expect(page.getByTestId("phase4-rule-score")).toBeVisible({ timeout: 360_000 });
  // Keep ASCII digits [0-9] (not \\d) — same convention as backend date/money regexes.
  await expect(page.getByTestId("phase4-rule-score")).toContainText(/[0-9]{1,3}\/100/); // NOSONAR typescript:S6353 — [0-9] required; S8786 bounded quantifier
  await typeLikeUser(
    page.getByTestId("review-chat-input"),
    "สรุปผลการตรวจจากกฎระเบียบ"
  );
  await pauseLikeUser(page, 400);
  await page.getByTestId("review-chat-send").click();
  await expect(page.getByTestId("review-chat-messages")).toContainText(
    "สรุปผลการตรวจจากกฎระเบียบ"
  );
  await expect(page.getByTestId("review-chat-messages")).toContainText(
    /ตรวจอีกครั้ง|คะแนนคุณภาพ/,
    { timeout: 15_000 }
  );
  await saveEvidence(page, "e2e-phase-4-review-chat");
  const [docx] = await Promise.all([
    page.waitForEvent("download", { timeout: 90_000 }).catch(() => null),
    page.getByTestId("export-docx").click(),
  ]);
  if (docx) {
    expect(await docx.failure()).toBeNull();
  }
  await expect(page.getByTestId("phase4-export").getByText("ดาวน์โหลดเอกสารแล้ว")).toBeVisible({
    timeout: 90_000,
  });
  const [pdf] = await Promise.all([
    page.waitForEvent("download", { timeout: 90_000 }).catch(() => null),
    page.getByTestId("export-pdf").click(),
  ]);
  if (pdf) {
    expect(await pdf.failure()).toBeNull();
  }
  await expect(page.getByTestId("phase4-submit")).toBeEnabled();
  const submitResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      /\/projects\/[^/]+\/submit(?:\?|$)/.test(response.url()),
    { timeout: 20_000 }
  );
  await page.getByTestId("phase4-submit").click();
  const submitted = await submitResponse;
  expect(submitted.ok(), await submitted.text()).toBeTruthy();
  await expect(page).toHaveURL(/\/projects\/?(?:\?.*)?$/, { timeout: 20_000 });
  await expect(page.getByTestId("projects-page")).toBeVisible();
  await saveEvidence(page, "07-phase-4-publish");
}

/** Completes live Phase 0–4: 13 AI drafts, Rule Engine, review chat, export. */
export async function walkLiveFivePhases(page: Page) {
  await walkLiveDraftToCompose(page);
  await expect(page.getByTestId("draft-chat")).toContainText("กำลังเริ่มร่างทั้ง ๑๓ หมวด", {
    timeout: 90_000,
  });
  await pauseLikeUser(page, 2500);
  await expect(page.getByText("ร่างด้วยระบบอัจฉริยะไม่สำเร็จ")).toHaveCount(0);
  await expect(page.getByText("ร่างด้วย AI ไม่สำเร็จ")).toHaveCount(0);
  await expect(page.getByTestId("draft-section-badge-s1")).toBeVisible({ timeout: 300_000 });
  await saveEvidence(page, "08a-phase-3-drafting");
  await expect(page.getByTestId("phase3-all-drafted")).toBeVisible({ timeout: 3_600_000 });
  await expect(page.getByTestId("draft-chat-count")).toHaveText("13/13 หมวด");
  await expect(page.getByTestId("section-preview-s1")).toContainText(/\S.{20,}/);
  await finishLivePhase3ToSubmit(page);
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
    s10: { content: "", status: "gap", sources: [] as string[] },
  };
  const coverage = Object.entries(slotMap).map(([key, slot]) => ({
    key,
    label: key,
    status: slot.status,
    filled: slot.status === "filled",
    fact_required: key !== "s10",
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
  await page.route("**/intake/open-qa", async (route) => {
    await route.fulfill({
      json: envelope({
        room_id: "room-e2e",
        brief: "สวัสดีครับ ผมอ่านเอกสารจากขั้นที่ ๑ แล้ว ขอข้อมูลวงเงินงบประมาณ",
        coverage,
        current_slot: null,
        next_question: "ขอข้อมูลวงเงินงบประมาณ",
      }),
    });
  });
  await page.route("**/chat/rooms/*/messages", async (route) => {
    await route.fulfill({
      json: envelope({
        messages: [
          {
            id: "m1",
            role: "assistant",
            content: "สวัสดีครับ ผมอ่านเอกสารจากขั้นที่ ๑ แล้ว ข้อเท็จจริงหลักครบแล้วครับ",
            citations: [],
          },
        ],
      }),
    });
  });
  const torKeys = [
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "s8",
    "s9",
    "s10",
    "s11",
    "s12",
    "s13",
  ];
  const hitl = new Set(["s3", "s6", "s8", "s10", "s13"]);
  const sections = torKeys.map((key) => ({
    key,
    title: key,
    filled: true,
    content: `ร่างหมวด ${key} สำหรับโครงการทดสอบ`,
    human_confirmed: hitl.has(key),
    hitl: hitl.has(key),
    matchStatus: "matched",
  }));
  await page.route(/\/projects\/[^/]+\/sections$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({ json: envelope({ sections }) });
  });
  await page.route("**/draft-chat/status", async (route) => {
    await route.fulfill({
      json: envelope({
        sections: torKeys.map((key) => ({
          section_key: key,
          title: key,
          has_content: true,
          content_preview: `ร่าง ${key}`,
          human_confirmed: hitl.has(key),
        })),
        drafted_count: 13,
        total: 13,
        all_drafted: true,
      }),
    });
  });
  await page.route("**/intake/confirm-phase4", async (route) => {
    projectPhase = 4;
    await route.fulfill({ json: envelope({ phase4_confirmed: true, phase: 4 }) });
  });
  await page.route(/\/projects\/[^/]+\/review$/, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fulfill({
      json: envelope({
        quality_score: 82,
        findings: [
          {
            severity: "warning",
            rule: "budget",
            section: "s6",
            message: "ตรวจวงเงินให้ตรงกับเอกสาร",
            recommendation: "ทบทวนตัวเลข",
          },
        ],
      }),
    });
  });
  await page.route("**/projects/*/suggestions", async (route) => {
    await route.fulfill({ json: envelope({ items: [] }) });
  });
  await page.route("**/review/requirements", async (route) => {
    await route.fulfill({ json: envelope({ has_requirements: false }) });
  });
  await expect(page.getByTestId("phase0-upload")).toBeVisible();
  await typeLikeUser(
    page.getByTestId("intake-paste"),
    "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งร้อยแปดสิบวัน สถานที่กรมบัญชีกลาง"
  );
  await page.getByTestId("intake-start-analyze").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase1-coverage")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("รายละเอียดที่จัดเข้าช่อง")).toBeVisible();
  await expect(page.getByTestId("intake-enter-qa")).toHaveCount(0);
  await saveEvidence(page, "e2e-phase-1-coverage");
  const skip = page.getByTestId("phase1-skip");
  if (await skip.count()) {
    await skip.click();
  }
  await expect(page.getByTestId("confirm-phase-ok")).toBeHidden();
  await expect(page.getByTestId("phase2-qa")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("รายละเอียดที่จัดเข้าช่อง")).toBeVisible();
  await expect(page.getByTestId("phase2-fact-chips")).toBeVisible();
  await expect(page.getByTestId("phase2-chip-s1")).toBeVisible();
  await expect(page.getByTestId("chat-input")).toBeVisible();
  await expect(page.getByTestId("draft-conversation")).toBeVisible();
  await expect(page.getByTestId("coverage-row-s1")).toBeVisible();
  await expect(page.getByTestId("intake-attach-legal")).toBeVisible();
  await expect(page.getByTestId("intake-ref-chips")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "ดึงอ้างอิงกฎหมาย" })).toHaveCount(0);
  await expect(page.getByTestId("chat-msg-assistant")).toBeVisible();
  await expect(page.getByTestId("intake-confirm-ready")).toBeEnabled();
  await saveEvidence(page, "e2e-phase-2-qa");
  await page.getByTestId("intake-confirm-ready").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase3-draft")).toBeVisible({ timeout: 20_000 });
}

/** Continues the mocked wizard through Phase 4 review chat. */
export async function walkMockedIntakeToPhase4(page: Page) {
  await unlockPhase2ViaMockedIntake(page);
  await expect(page.getByTestId("draft-chat")).toBeVisible();
  await expect(page.getByTestId("draft-chat-input")).toBeVisible();
  await expect(page.getByTestId("hitl-confirm-s3")).toHaveCount(0);
  await expect(page.getByText("ต้องให้เจ้าหน้าที่ยืนยัน")).toHaveCount(0);
  await expect(page.getByTestId("phase3-confirm")).toBeEnabled();
  await expect(page.getByTestId("phase3-confirm")).toHaveText("ไปทบทวน (ขั้นที่ ๔)");
  await saveEvidence(page, "e2e-phase-3-draft");
  await page.getByTestId("phase3-confirm").click();
  await confirmPhase(page);
  await expect(page.getByTestId("phase4-review")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("review-chat")).toBeVisible();
  await expect(page.getByTestId("review-chat-input")).toBeVisible();
  await expect(page.getByTestId("phase4-export")).toBeVisible();
  await expect(
    page.getByTestId("phase4-review").getByText("คะแนนคุณภาพจากการตรวจกฎ 82/100")
  ).toBeVisible({ timeout: 20_000 });
}
