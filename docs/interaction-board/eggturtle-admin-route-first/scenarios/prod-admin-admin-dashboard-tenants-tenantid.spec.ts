import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-tenants-tenantid", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 执行前需要把 tenantId 占位符替换成真实值。 默认复用持久化登录态直接打开目标页。 默认批量回放会跳过该场景：dynamic-route。 当前生成的是 stub，默认不会自动填参。 已解析动态参数: tenantId=cmnyn7fjv005dro08d1gbudi8
  await page.goto(new URL("/dashboard/tenants/cmnyn7fjv005dro08d1gbudi8", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("#tenant-delete-dialog-title").count()).toBeGreaterThanOrEqual(1);
  expect(await page.locator("#tenant-delete-dialog-desc").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-tenants-tenantid.png", fullPage: true });
});
