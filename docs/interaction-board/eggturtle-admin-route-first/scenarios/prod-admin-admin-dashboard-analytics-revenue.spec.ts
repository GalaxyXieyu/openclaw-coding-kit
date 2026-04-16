import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-analytics-revenue", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/analytics/revenue", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("付费看板")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-analytics-revenue.png", fullPage: true });
});
