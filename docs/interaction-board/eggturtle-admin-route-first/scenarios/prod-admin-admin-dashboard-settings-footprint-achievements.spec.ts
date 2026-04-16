import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-settings-footprint-achievements", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/settings/footprint-achievements", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("徽章分享素材")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-settings-footprint-achievements.png", fullPage: true });
});
