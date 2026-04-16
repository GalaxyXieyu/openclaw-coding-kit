import { expect, test } from "@playwright/test";

test("prod-admin-admin-dashboard-commerce-community-postid", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://eggturtles-admin.sealoshzh.site";
  const storageEntries = [];
  // 执行前需要把 postId 占位符替换成真实值。 默认复用持久化登录态直接打开目标页。 默认批量回放会跳过该场景：dynamic-route。 当前生成的是 stub，默认不会自动填参。 已解析动态参数: postId=preview-post-20260413-24a
  await page.goto(new URL("/dashboard/commerce/community/preview-post-20260413-24a", baseUrl).toString());
  await page.waitForTimeout(1200);
  expect(await page.locator("form.commerce-editor-form").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "../screenshots/prod-admin-admin-dashboard-commerce-community-postid.png", fullPage: true });
});
