import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-settings-tenant-branding", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/settings/tenant-branding", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("#tenant-branding-search").count()).toBeGreaterThanOrEqual(1);
  expect(await page.locator("#tenant-display-name").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-settings-tenant-branding.png", fullPage: true });
});
