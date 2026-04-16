import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-commerce-catalog-productid", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 执行前需要把 productId 占位符替换成真实值。 默认复用持久化登录态直接打开目标页。 默认批量回放会跳过该场景：dynamic-route。 当前生成的是 stub，默认不会自动填参。 已解析动态参数: productId=cmnybc6gh0001rofi0koa7q15
  await page.goto(new URL("/dashboard/commerce/catalog/cmnybc6gh0001rofi0koa7q15", baseUrl).toString());
  await page.waitForTimeout(1200);
  await expect(page.getByText("商品详情")).toBeVisible();
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-commerce-catalog-productid.png", fullPage: true });
});
