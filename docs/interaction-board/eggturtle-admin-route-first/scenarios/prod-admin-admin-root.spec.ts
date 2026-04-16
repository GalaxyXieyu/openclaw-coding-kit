import { expect, test } from "@playwright/test";

test("prod-admin-admin-root", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 当前节点是跳转页，打开后会落到 /dashboard。 默认批量回放会跳过该场景：redirect-only。
  await page.goto(new URL("/", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("后台根入口")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-root.png", fullPage: true });
});
