import { expect, test } from "@playwright/test";

test("prod-admin-admin-login", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认批量回放会跳过该场景：entry-auth-page。
  await page.goto(new URL("/login", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("#login-identifier").count()).toBeGreaterThanOrEqual(1);
  expect(await page.locator("#code-phone").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "../screenshots/prod-admin-admin-login.png", fullPage: true });
});
