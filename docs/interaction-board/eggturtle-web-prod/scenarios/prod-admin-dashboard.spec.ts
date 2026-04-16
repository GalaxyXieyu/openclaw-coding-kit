import { expect, test } from "@playwright/test";

test("prod-admin-dashboard", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 生产 Admin 登录态场景：复用持久化 session 打开 /dashboard，并校验平台概况。首次执行可通过 --login/--password 自动 bootstrap。
  await page.goto(new URL("/dashboard", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("text=平台概况").count()).toBeGreaterThanOrEqual(1);
  await expect(page.getByText("用户总数")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-dashboard-auth.png", fullPage: true });
});
