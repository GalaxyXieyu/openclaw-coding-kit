# Eggturtle Web Prod Playwright Status

最后更新：2026-04-15

## 当前结论

- 生产 Web 与生产 Admin 已能通过 Playwright CLI 直接验证
- 当前可行路径是 `--channel chrome`
- 当前 repo **没有本地安装** `@playwright/test`
- 因此：
  - `npx playwright screenshot --channel chrome ...` 可直接执行
  - 生成的 `.spec.ts` 可以作为契约保留
  - 但 `npx playwright test ...` 目前会因为 `@playwright/test` 缺失而失败

## 为什么之前总提示没装 Chromium

- 本机系统里有 `Google Chrome.app`
- 但 Playwright 默认找的是**当前 CLI 版本对应的浏览器缓存**
- 这次 `npx playwright --version` 命中的是 `1.59.1`
- 它尝试找的是：
  - `~/Library/Caches/ms-playwright/chromium_headless_shell-1217/...`
- 机器里已经有多个别的缓存版本：
  - `chromium-1208`
  - `chromium-1219`
  - `chromium_headless_shell-1200`
  - `chromium_headless_shell-1208`
  - `chromium_headless_shell-1219`
- 所以它不是“没有浏览器”，而是“当前 Playwright 版本要的缓存号和机器里现有的不一致”

## 已落地文件

- 场景 JSON：
  - `docs/interaction-board/eggturtle-web-prod/scenarios/prod-web-home.json`
  - `docs/interaction-board/eggturtle-web-prod/scenarios/prod-admin-login.json`
- 渲染出来的 spec：
  - `docs/interaction-board/eggturtle-web-prod/scenarios/prod-web-home.spec.ts`
  - `docs/interaction-board/eggturtle-web-prod/scenarios/prod-admin-login.spec.ts`
- Playwright 配置：
  - `docs/interaction-board/eggturtle-web-prod/playwright.config.cjs`
- 真实截图：
  - `docs/interaction-board/eggturtle-web-prod/screenshots/prod-web-home.png`
  - `docs/interaction-board/eggturtle-web-prod/screenshots/prod-admin-login.png`

## 本次真实验证

### 1. 生产 Web 首页

- 目标：
  - `https://xuanyuku.cn`
- 命令：
  - `npx playwright screenshot --channel chrome --full-page --viewport-size "1440,1000" --wait-for-selector "text=立即开始记录" https://xuanyuku.cn docs/interaction-board/eggturtle-web-prod/screenshots/prod-web-home.png`
- 结果：成功
- 说明：
  - Playwright 已等待到首页 CTA `立即开始记录`
  - 全页截图已产出

### 2. 生产 Admin 登录页

- 目标：
  - `https://eggturtles-admin.sealoshzh.site/login?redirect=%2Fdashboard`
- 命令：
  - `npx playwright screenshot --channel chrome --full-page --viewport-size "1440,1000" --wait-for-selector "text=管理后台登录" "https://eggturtles-admin.sealoshzh.site/login?redirect=%2Fdashboard" docs/interaction-board/eggturtle-web-prod/screenshots/prod-admin-login.png`
- 结果：成功
- 说明：
  - Playwright 已等待到登录页标题 `管理后台登录`
  - 全页截图已产出

## 当前限制

- 当前 repo 没有 `@playwright/test`
- 所以这条命令现在不能直接跑通：
  - `npx playwright test --config docs/interaction-board/eggturtle-web-prod/playwright.config.cjs ...`
- 失败原因不是脚本内容错误，而是模块解析边界：
  - `Cannot find module '@playwright/test'`

## 建议的后续路径

1. 默认使用 CLI-first 模式
   - 用 `playwright screenshot --channel chrome --wait-for-selector`
   - 适合生产 smoke、截图存档、低依赖验证
2. 需要真正断言测试时，再补 `@playwright/test`
   - 让当前生成的 `.spec.ts` 直接变成可执行测试
3. 把这套 Web/Admin 场景接回 `product-canvas`
   - 让 board 卡片能直接挂 `scenario_refs`
   - 实现“页面卡片 -> Playwright 场景 -> 真实截图”的闭环
