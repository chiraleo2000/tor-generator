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
  await saveEvidence(page, "03-phase-0-upload");
  await page.getByTestId("phase-1").click();
  await expect(page.getByText("Phase 1: วิเคราะห์ความต้องการ")).toBeVisible();
  await saveEvidence(page, "04-phase-1-analysis");
  await page.getByTestId("phase-2").click();
  await expect(page.getByText("Phase 2: ร่างเนื้อหา TOR")).toBeVisible();
  await saveEvidence(page, "05-phase-2-draft");
  await page.getByTestId("phase-3").click();
  await expect(page.getByText("Phase 3: ทบทวนและอนุมัติ")).toBeVisible();
  await saveEvidence(page, "06-phase-3-review");
  await page.getByTestId("phase-4").click();
  await expect(page.getByText("Phase 4: เผยแพร่")).toBeVisible();
  await expect(page.getByRole("button", { name: "ส่งออก Word" })).toBeVisible();
  await saveEvidence(page, "07-phase-4-publish");
}
