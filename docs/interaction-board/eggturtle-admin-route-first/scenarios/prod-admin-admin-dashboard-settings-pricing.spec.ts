import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-settings-pricing", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/settings/pricing", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("#subscription-pricing-enabled").count()).toBeGreaterThanOrEqual(1);
  expect(await page.locator("#subscription-pricing-pay-rate").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-settings-pricing.png", fullPage: true });
});
