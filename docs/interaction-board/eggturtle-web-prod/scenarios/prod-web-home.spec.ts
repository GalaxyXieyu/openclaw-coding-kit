import { expect, test } from "@playwright/test";

test("prod-web-home", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "https://xuanyuku.cn";
  const storageEntries = [];
  // 生产 Web 首页 smoke：验证公开首页可打开，核心 CTA 可见，并保存全页截图。
  await page.goto(new URL("/", baseUrl).toString());
  await page.waitForTimeout(1000);
  expect(await page.locator("text=立即开始记录").count()).toBeGreaterThanOrEqual(1);
  expect(await page.locator("text=查看功能演示").count()).toBeGreaterThanOrEqual(1);
  await page.screenshot({ path: "docs/interaction-board/eggturtle-web-prod/screenshots/prod-web-home.png", fullPage: true });
});
