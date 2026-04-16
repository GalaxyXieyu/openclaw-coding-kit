import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-settings-platform-branding", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/settings/platform-branding", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("平台品牌")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-settings-platform-branding.png", fullPage: true });
});
