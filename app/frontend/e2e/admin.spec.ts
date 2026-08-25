import { test, expect } from "@playwright/test";
import {
  ADMIN_EMAIL,
  DEMO_PASSWORD,
  login,
  saveEvidence,
  skipReason,
  skipUnlessLive,
} from "./helpers";

test.describe("Admin pages", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("templates, knowledge base, users, and AI settings load", async ({ page }) => {
    await login(page, ADMIN_EMAIL, DEMO_PASSWORD);
    await expect(page.getByTestId("nav-admin-templates")).toBeVisible();

    await page.getByTestId("nav-admin-templates").click();
    await expect(page).toHaveURL(/\/admin\/templates/);
    await expect(page.getByTestId("admin-templates-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "จัดการแม่แบบ" })).toBeVisible();
    await saveEvidence(page, "16-admin-templates");

    await page.getByTestId("nav-admin-knowledge-base").click();
    await expect(page).toHaveURL(/\/admin\/knowledge-base/);
    await expect(page.getByTestId("admin-kb-page")).toBeVisible();
    await expect(
      page.getByTestId("admin-kb-page").getByRole("heading", { name: "ฐานความรู้" })
    ).toBeVisible();
    await saveEvidence(page, "17-admin-kb");

    await page.getByTestId("nav-admin-users").click();
    await expect(page).toHaveURL(/\/admin\/users/);
    await expect(page.getByTestId("admin-users-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "ผู้ใช้ระบบ" })).toBeVisible();
    await saveEvidence(page, "18-admin-users");

    await page.getByTestId("nav-admin-ai-settings").click();
    await expect(page).toHaveURL(/\/admin\/ai-settings/);
    await expect(page.getByTestId("admin-ai-settings-page")).toBeVisible();
    await expect(
      page.getByTestId("admin-ai-settings-page").getByRole("heading", { name: "การตั้งค่า AI" })
    ).toBeVisible();
    await expect(page.locator("#ai-mode")).toHaveValue("on_prem");
    await expect(page.locator("#chat-model")).toHaveValue("google/gemma-4-e4b");
    await expect(page.locator("#embed-model")).toHaveValue(
      "text-embedding-embeddinggemma-300m"
    );
    await expect(page.locator("#vector-store")).toHaveValue("pgvector");
    await saveEvidence(page, "09a-admin-ai-local");

    await page.locator("#ai-mode").selectOption("cloud");
    await expect(page.locator("#ai-llm")).toHaveValue("lm_studio");
    await expect(page.locator("#ai-embed")).toHaveValue("local");
    await expect(page.locator("#ai-llm option[value='claude']")).toHaveCount(1);
    await expect(page.locator("#ai-llm option[value='openai']")).toHaveCount(1);
    await expect(page.locator("#ai-llm option[value='gemini']")).toHaveCount(1);
    await expect(page.locator("#ai-llm option[value='lm_studio']")).toHaveCount(1);

    await page.locator("#ai-llm").selectOption("claude");
    await expect(page.locator("#anthropic-key")).toBeVisible();
    await expect(page.locator("#embed-model")).toBeVisible();
    await saveEvidence(page, "09b-admin-ai-cloud");

    await page.locator("#ai-llm").selectOption("lm_studio");
    await page.locator("#ai-mode").selectOption("on_prem");
    await expect(page.locator("#ai-llm")).toHaveValue("lm_studio");
    await expect(page.locator("#chat-model")).toBeVisible();

    await page.getByTestId("ai-settings-test").click();
    await expect(page.getByTestId("ai-settings-status")).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByTestId("ai-settings-status")).toContainText(/เชื่อมต่อ/);
    await saveEvidence(page, "09-admin-ai-lm-studio");
  });
});
