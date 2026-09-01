import { test, expect } from "@playwright/test";
import {
  ADMIN_EMAIL,
  DEMO_EMAIL,
  DEMO_PASSWORD,
  REVIEWER_EMAIL,
  login,
  saveEvidence,
} from "./helpers";

/** Extra screenshots for the user guideline. Run with CAPTURE_GUIDE=1. */
test.describe("Guide screenshots", () => {
  test("register, create dialog, help tabs, admin pages", async ({ page }) => {
    test.setTimeout(300_000);

    await page.goto("/register");
    await expect(page.getByTestId("register-form")).toBeVisible();
    await saveEvidence(page, "00b-register");

    await login(page);
    await page.getByTestId("new-project").click();
    await expect(page.getByTestId("new-project-dialog")).toBeVisible();
    await saveEvidence(page, "02b-create-dialog");
    await page.keyboard.press("Escape");

    await page.getByTestId("nav-help").click();
    await expect(page.getByTestId("help-page")).toBeVisible();
    await saveEvidence(page, "10a-help-overview");
    await page.getByTestId("help-tab-login").click();
    await saveEvidence(page, "10g-help-login");
    await page.getByTestId("help-tab-dashboard").click();
    await saveEvidence(page, "10b-help-dashboard");
    await page.getByTestId("help-tab-draft").click();
    const draftHeading = page.getByTestId("help-draft-heading");
    await draftHeading.scrollIntoViewIfNeeded();
    await expect(draftHeading).toBeVisible();
    await expect(page.getByRole("heading", { name: "กระบวนการร่างห้าขั้น" })).toBeVisible();
    await saveEvidence(page, "10c-help-draft");
    await page.getByTestId("help-tab-chat").click();
    await saveEvidence(page, "10f-help-chat");
    await page.getByTestId("help-tab-review").click();
    await saveEvidence(page, "10d-help-review");
    await page.getByTestId("help-tab-kb").click();
    await saveEvidence(page, "10e-help-kb");
    await page.getByTestId("help-tab-admin").click();
    await saveEvidence(page, "10h-help-admin");
    await page.getByTestId("help-tab-faq").click();
    await saveEvidence(page, "10-help-faq");
  });

  test("admin templates, KB, users, AI local and cloud", async ({ page }) => {
    test.setTimeout(120_000);
    await login(page, ADMIN_EMAIL, DEMO_PASSWORD);

    await page.getByTestId("nav-admin-templates").click();
    await expect(page.getByTestId("admin-templates-page")).toBeVisible();
    await saveEvidence(page, "16-admin-templates");

    await page.getByTestId("nav-admin-knowledge-base").click();
    await expect(page.getByTestId("admin-kb-page")).toBeVisible();
    await saveEvidence(page, "17-admin-kb");

    await page.getByTestId("nav-admin-users").click();
    await expect(page.getByTestId("admin-users-page")).toBeVisible();
    await saveEvidence(page, "18-admin-users");

    await page.getByTestId("nav-admin-ai-settings").click();
    await expect(page.getByTestId("admin-ai-settings-page")).toBeVisible();
    await saveEvidence(page, "09a-admin-ai-local");

    // Mode is a label only — cloud key fields appear when chat/embed is a cloud vendor.
    await page.locator("#ai-mode").selectOption("hybrid");
    await page.locator("#ai-llm").selectOption("claude");
    await expect(page.locator("#anthropic-key")).toBeVisible();
    await saveEvidence(page, "09b-admin-ai-cloud");
  });

  test("login error and reviewer dashboard", async ({ page }) => {
    test.setTimeout(180_000);

    await page.goto("/login");
    await page.getByTestId("login-email").fill(DEMO_EMAIL);
    await page.getByTestId("login-password").fill("WrongPass1!");
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-error")).toBeVisible({ timeout: 15_000 });
    await saveEvidence(page, "00c-login-error");

    await login(page, REVIEWER_EMAIL, DEMO_PASSWORD);
    await expect(page.getByTestId("projects-page")).toBeVisible();
  });
});
