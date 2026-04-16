import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-tenants", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。 当前节点是跳转页，打开后会落到 /dashboard/tenant-management。 默认批量回放会跳过该场景：redirect-only。
  await page.goto(new URL("/dashboard/tenants", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("Tenants")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-tenants.png", fullPage: true });
});
