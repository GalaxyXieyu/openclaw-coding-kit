import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-audit-logs", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。 当前节点是跳转页，打开后会落到 /dashboard/settings/audit-logs。 默认批量回放会跳过该场景：redirect-only。
  await page.goto(new URL("/dashboard/audit-logs", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("治理记录")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-audit-logs.png", fullPage: true });
});
