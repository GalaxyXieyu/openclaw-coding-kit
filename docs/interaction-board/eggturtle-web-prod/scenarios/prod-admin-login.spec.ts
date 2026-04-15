import { expect, test } from "@playwright/test";

test("prod-admin-login", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 生产 Admin 登录页 smoke：验证 /login?redirect=%2Fdashboard 可打开，登录文案可见，并保存全页截图。
  await page.goto(new URL("/login?redirect=%2Fdashboard", baseUrl).toString());
  await page.waitForTimeout(1000);
  expect(await page.locator("text=管理后台登录").count()).toBeGreaterThanOrEqual(1);
  expect(await page.locator("text=仅超级管理员账号可访问").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "docs/interaction-board/eggturtle-web-prod/screenshots/prod-admin-login.png", fullPage: true });
});
