import { test, expect } from "@playwright/test";
import { saveEvidence, skipReason, skipUnlessLive } from "./helpers";

test.describe("Landing page", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  // NOSONAR: Playwright live-stack spec. Skipped unless E2E=1 (see skipReason in helpers).
  test.skip(skipUnlessLive, skipReason);

  test("sends guests to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
    await expect(page.getByTestId("login-form")).toBeVisible();
    await saveEvidence(page, "00-login");
  });

  test("register form is reachable", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByTestId("register-form")).toBeVisible();
    await expect(page.getByRole("heading", { name: "สมัครสมาชิก" })).toBeVisible();
    await expect(page.getByLabel("ชื่อ-นามสกุล")).toBeVisible();
    await saveEvidence(page, "00b-register");
  });
});
