import { test, expect } from "@playwright/test";
import {
  DEMO_EMAIL,
  DEMO_PASSWORD,
  pauseLikeUser,
  saveEvidence,
  skipReason,
  skipUnlessLive,
  typeLikeUser,
} from "./helpers";

test.describe("Login", () => {
  // Live Docker stack only. Unit-only CI sets E2E!=1 so this suite is skipped.
  test.skip(skipUnlessLive, skipReason);

  test("shows validation when password is missing", async ({ page }) => {
    await page.goto("/login");
    await typeLikeUser(page.getByTestId("login-email"), DEMO_EMAIL);
    await pauseLikeUser(page, 300);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-error")).toBeVisible();
    await expect(page.getByTestId("login-error")).toContainText("รหัสผ่าน");
  });

  test("shows an error for wrong credentials", async ({ page }) => {
    await page.goto("/login");
    await typeLikeUser(page.getByTestId("login-email"), DEMO_EMAIL);
    await pauseLikeUser(page, 300);
    await typeLikeUser(page.getByTestId("login-password"), "WrongPass1!");
    await pauseLikeUser(page, 300);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-error")).toBeVisible({ timeout: 15_000 });
  });

  test("logs in with demo officer account", async ({ page }) => {
    await page.goto("/login");
    await typeLikeUser(page.getByTestId("login-email"), DEMO_EMAIL);
    await pauseLikeUser(page, 300);
    await typeLikeUser(page.getByTestId("login-password"), DEMO_PASSWORD);
    await pauseLikeUser(page, 400);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/\/projects/, { timeout: 20_000 });
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await expect(page.getByText("รายการโครงการ TOR")).toBeVisible();
    await saveEvidence(page, "01-login-dashboard");
  });

  test("logs out back to the login form", async ({ page }) => {
    await page.goto("/login");
    await typeLikeUser(page.getByTestId("login-email"), DEMO_EMAIL);
    await pauseLikeUser(page, 300);
    await typeLikeUser(page.getByTestId("login-password"), DEMO_PASSWORD);
    await pauseLikeUser(page, 400);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await page.getByTestId("logout").click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
    await expect(page.getByTestId("login-form")).toBeVisible();
  });
});
