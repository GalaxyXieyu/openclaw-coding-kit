import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-commerce-community-new", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/commerce/community/new", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("form.commerce-editor-form").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-commerce-community-new.png", fullPage: true });
});
