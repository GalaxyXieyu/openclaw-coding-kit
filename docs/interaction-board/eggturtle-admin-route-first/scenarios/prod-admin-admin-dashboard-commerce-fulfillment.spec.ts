import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-commerce-fulfillment", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 默认复用持久化登录态直接打开目标页。
  await page.goto(new URL("/dashboard/commerce/fulfillment", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("发货履约")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-commerce-fulfillment.png", fullPage: true });
});
