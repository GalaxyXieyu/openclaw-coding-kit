import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-commerce-community", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/commerce/community", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("社区")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-commerce-community.png", fullPage: true });
});
