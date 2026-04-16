import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-guiquan-management", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。 当前节点是跳转页，打开后会落到 /dashboard/commerce/community。 默认批量回放会跳过该场景：redirect-only。
  await page.goto(new URL("/dashboard/guiquan-management", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("社区入口")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-guiquan-management.png", fullPage: true });
});
