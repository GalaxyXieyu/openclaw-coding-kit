import { expect, test } from "@playwright/test";

test("products-to-detail", async ({ page }) => {
  const baseUrl = process.env.BOARD_BASE_URL || "http://127.0.0.1:3000";
  const storageEntries = [];
  // 首次进入前需要具备 workspace 上下文。
  await page.goto(new URL("/pages/products/index", baseUrl).toString());
  await page.locator("[data-testid='product-card']").click();
  await expect(page).toHaveURL(new RegExp("/subpackages/workspace/pages/product-detail/index"));
  await page.screenshot({ path: "screenshots/scenario/productdetail.png", fullPage: true });
});
