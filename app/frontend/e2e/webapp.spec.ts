import { test, expect } from "@playwright/test";
import { login, saveEvidence, skipReason, skipUnlessLive } from "./helpers";

test.describe("Help and standalone review", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  test.skip(skipUnlessLive, skipReason);

  test("help page tabs are usable", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-help").click();
    await expect(page).toHaveURL(/\/help/);
    await expect(page.getByTestId("help-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "ภาพรวมระบบ" })).toBeVisible();
    await page.getByTestId("help-tab-draft").click();
    await expect(page.getByRole("heading", { name: "กระบวนการร่าง 5 Phase" })).toBeVisible();
    await page.getByTestId("help-tab-faq").click();
    await expect(page.getByText(/google\/gemma-4-e4b/)).toBeVisible();
    await expect(page.getByText(/text-embedding-embeddinggemma-300m/)).toBeVisible();
    await expect(page.getByText(/127\.0\.0\.1:1234/)).toBeVisible();
    await saveEvidence(page, "10-help-faq");
  });

  test("knowledge base is in the main menu", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-knowledge-base").click();
    await expect(page).toHaveURL(/\/knowledge-base/);
    await expect(page.getByTestId("knowledge-base-page")).toBeVisible();
    await expect(page.getByText("อัปโหลดเอกสารเข้าคลังความรู้")).toBeVisible();
    await saveEvidence(page, "11-knowledge-base");
  });

  test("standalone review page loads", async ({ page }) => {
    await login(page);
    await page.getByTestId("nav-review").click();
    await expect(page).toHaveURL(/\/review/);
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByText("อัปโหลด TOR ที่ต้องการตรวจสอบ")).toBeVisible();
    await expect(page.getByRole("button", { name: "เริ่มตรวจสอบ TOR" })).toBeDisabled();
    await saveEvidence(page, "12-standalone-review");
  });
});
