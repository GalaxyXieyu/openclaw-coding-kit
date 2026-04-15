# Eggturtle Miniapp Automation Status

最后更新：2026-04-15

## 当前已落地

- `product-canvas` 已成为统一入口
- Eggturtle board 已刷新为最新页面矩阵，当前 `registered_count = 26`、`conflict_count = 0`
- miniapp wrapper 已支持从 scenario `target` 读取默认目标，并显式透传：
  - `--target-name`
  - `--ide-port`
  - `--automator-port`
  - `--label`
- `miniapp_scenario.js` / `miniapp_smoke.js` 现在不会再把 live target 静默切回默认 `main`
- `tap` step 的 `path` 现在是强约束；如果跳到错误页面，会返回 `unexpected-path:*`
- 已挂载 4 条项目级 miniapp scenario：
  - `products-to-detail`
  - `products-to-me-tab`
  - `products-to-footprint-tab`
  - `guiquan-to-community-detail`
- `products-to-detail` 已按真实交互改为双击卡片

## 最近一次真实回放

### 1. live target smoke

- 命令：
  - `node skills/product-canvas/scripts/miniapp_smoke.js --scenario /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit/docs/interaction-board/eggturtle-miniapp/scenarios/products-to-detail.json --target-name main-live-37768 --ide-port 37768 --automator-port 37381 --json-output /Volumes/DATABASE/code/Eggturtle-breeding-library/out/product-canvas/miniapp-smoke-live.json --no-screenshot`
- 结果：成功
- 说明：
  - 当前 live target 已锁定为 `main-live-37768`
  - WeChat DevTools IDE 端口 `37768`
  - automator 端口 `37381`
  - wrapper 没有回退到默认 target `main`

### 2. `guiquan-to-community-detail`

- 命令：
  - `node skills/product-canvas/scripts/miniapp_scenario.js --scenario /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit/docs/interaction-board/eggturtle-miniapp/scenarios/guiquan-to-community-detail.json --target-name main-live-37768 --ide-port 37768 --automator-port 37381 --json-output /Volumes/DATABASE/code/Eggturtle-breeding-library/out/product-canvas/guiquan-to-community-detail.json`
- 结果：成功
- 关键事实：
  - step 级 `path` 校验生效
  - 实际命中 `.guiquan-feed-card`
  - 最终到达 `subpackages/workspace/pages/guiquan-community-detail/index`
  - 场景截图已更新到 `docs/interaction-board/eggturtle-miniapp/screenshots/scenario/guiquan-to-community-detail.png`

### 3. `products-to-detail`

- 命令：
  - `node skills/product-canvas/scripts/miniapp_scenario.js --scenario /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit/docs/interaction-board/eggturtle-miniapp/scenarios/products-to-detail.json --target-name main-live-37768 --ide-port 37768 --automator-port 37381 --json-output /Volumes/DATABASE/code/Eggturtle-breeding-library/out/product-canvas/products-to-detail.json --skip-probe`
- 结果：失败，但已进入真实 step 执行阶段
- 失败点：
  - 双击 `.workspace-product-card--interactive` 后
  - 实际到达 `subpackages/workspace/pages/breeders/detail/index`
  - 预期是 `subpackages/workspace/pages/product-detail/index`
  - runner 现在会明确报错：
    - `unexpected-path:subpackages/workspace/pages/breeders/detail/index`

## 当前判断

- 运行态主阻塞已解除；当前不是 target 绑定问题
- 当前真实问题是“board / scenario 预期”和“业务实际流向”不一致
- 代码证据表明 `products` 页面双击详情是条件路由：
  - `packages/front-core/src/controllers/product-detail.ts`
  - `resolveEntityDetailIntent(product)` 会根据 `product.type` 在 `product-detail` / `breeder-detail` 之间切换
- 当前首个可点击卡片是 `breeder` 类型，因此场景进入了 `breeder-detail`
- 现有 board 仍只表达了 `products -> productdetail`，尚未表达这条条件分支

## 统一自动化能力补充

- `product-canvas` 现在不只覆盖 miniapp
- 生产 Web / Admin 的 Playwright CLI 验证也已落地到独立目录：
  - `docs/interaction-board/eggturtle-web-prod/PLAYWRIGHT-STATUS.md`
- 当前建议保持双轨：
  - miniapp 继续走 `auto-miniprogram` / DevTools scenario
  - Web / Admin 继续走 Playwright CLI + scenario/spec 契约
- 二者都归到同一个 `product-canvas` 语义层，而不是拆成两个独立流程

## 下次继续时的最短动作

1. 确认产品语义：
   - 如果这是预期行为，补一条 `products -> breederdetail` 的 board 关系与 scenario
   - 如果这不是预期行为，修业务逻辑或列表筛选，让 `products-to-detail` 落到真正的 `product-detail`
2. 升级 board / scenario 表达能力：
   - 支持条件路由备注，避免把数据驱动分支压扁成单一路径
3. 再刷新一次 board 真值与 scenario 绑定：
   - `board.manifest.json`
   - `board.drawio`
   - `index.html`
   - `inventory.md`
4. 复跑：
   - `miniapp_smoke.js`
   - `guiquan-to-community-detail`
   - `products-to-detail`

## 已验证命令

- `node --test /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit/tests/test_product_canvas_miniapp_support.mjs`
- `node --test /Volumes/DATABASE/code/auto-miniprogram/test/devtools-runner-utils.test.mjs`
- `node --test /Volumes/DATABASE/code/auto-miniprogram/test/devtools-scenario-contract.test.mjs`
