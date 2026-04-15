# UI/UX Automation Runner Migration

## 结论

这轮方向应该明确切成两条执行引擎，而不是继续把所有 UI 自动化都塞进一种 agent-browser 式交互里：

1. Web 场景：默认迁到 `Playwright CLI -> 场景脚本 -> 可选纯脚本/CI` 路线。
2. Miniapp 场景：继续用 `auto-miniprogram`，但补一层“可落盘、可复用、可回放”的 scenario runner，不再只靠 MCP 临场点点点。

不要试图让 Playwright CLI 直接替代微信开发者工具自动化。
对 Web 来说它是合适的执行层；对 Miniapp 来说它不是。

## 为什么要改

当前几套能力的边界已经很清楚：

- `interaction-board` 已经开始拥有 `scenario.json -> spec.ts` 和 `card.scenario_refs[]`
- `ui-ux-test` 仍然偏“覆盖矩阵 + CSV + 报告”
- `auto-miniprogram` 已经有持久化 broker/target，但没有场景资产层

这导致现在的问题不是“没有工具”，而是：

- 场景第一次走通之后，没有被沉淀成稳定资产
- 下一次 AI 还要重新理解页面、重新摸索路径、重新消耗 token
- 截图、页面节点、测试报告、自动化入口是分裂的
- Web 和 Miniapp 都缺少一个统一的 scenario contract

## 当前代码事实

### 1. `ui-ux-test` 现在偏测试管理，不是场景执行资产库

当前 skill 的主流程仍然是：

- 初始化 CSV/Excel 测试资产
- 做 coverage matrix
- 执行后回填 execution log
- 生成 Markdown 报告

它的 miniapp 部分也还是：

- 先 broker 绑定 target
- 再做 probe / screenshot / page data / query

它适合作为“测试编排层”，不适合作为“浏览器/小程序执行层”。

### 2. `auto-miniprogram` 已经有持久化 target registry

这个仓库已经具备两类关键基础设施：

- broker state 会落到 `~/.codex/state/miniapp-brokers`
- target 元数据会持久化 `projectRoot / worktreeRoot / appRoot / gitBranch / buildCommand / ports`

也就是说，小程序侧“目标工程绑定与复用”已经不是问题。
真正缺的是“场景脚本”和“回放约定”。

### 3. `auto-miniprogram` 已经有可脚本化命令，但还是 flag-heavy

当前已有：

- `broker:probe`
- `broker:validate-target`
- `devtools:smoke`
- `devtools:screenshot-doctor`
- `devtools:preview`

其中 `devtools:smoke` 已经可以做：

- 预设 storage
- relaunch / navigate / switchTab
- tap selector
- assert path / text / selector / storage
- 输出 screenshot + json result

它本质上已经是 runner，只是现在还不是“吃 scenario.json”的 runner。

## 推荐的新分层

### 1. Board Truth Layer

由 `interaction-board` 负责：

- 页面节点
- 页面关系
- 截图版本
- 场景引用

它是“页面真值 + review 入口”，不是执行器。

### 2. Scenario Registry Layer

新增 repo 内可持久保存的场景资产层。

推荐目录：

```text
docs/interaction-board/scenarios/
  web/
    login-to-dashboard.json
    products-to-detail.json
  miniapp/
    products-to-detail.json
    guiquan-to-supply-detail.json
```

每个场景都应该是 repo 资产，而不是一次性对话上下文。

### 3. Runner Adapter Layer

按运行环境拆成两类执行器：

#### Web Runner

- 探索态：`Playwright CLI`
- 固化态：`Playwright spec.ts` / shell script / CI job

#### Miniapp Runner

- 执行器：`auto-miniprogram`
- 形态：新增 `scenario-run.mjs` 或 `devtools:scenario`

不要混成一个执行器。
统一的是 `scenario.json`，不是底层驱动。

### 4. Evidence Layer

所有执行结果都要回写成稳定资产：

- screenshot
- result.json
- logs / exceptions
- scenario script path
- last_run metadata

推荐目录：

```text
out/ui-ux-runs/<run_id>/
  screenshots/
  results/
  logs/
```

同时把关键截图同步进 `interaction-board` 的版本图层。

### 5. Reporting Layer

`ui-ux-test` 保留在这一层：

- coverage planning
- run matrix
- bug list
- report generation
- task writeback

它应该消费 scenario 执行结果，而不是自己承担底层页面驱动。

## 统一 Scenario Contract

现有 `interaction-board` 的 scenario contract 方向是对的，但字段还不够。
建议扩成下面这个结构：

```json
{
  "scenario_id": "products-to-detail",
  "engine": "miniapp-devtools",
  "entry_node_id": "products",
  "target_node_id": "productdetail",
  "target": {
    "project_key": "eggturtle-breeding-library",
    "target_name": "guiquan-supply-catalog"
  },
  "context": {
    "auth_profile": "workspace-owner",
    "storage": [
      {
        "key": "workspace",
        "value": "{\"id\":\"w1\"}"
      }
    ],
    "notes": "首次进入前需要具备 workspace 上下文。"
  },
  "steps": [
    { "action": "relaunch", "target": "/pages/products/index" },
    { "action": "tap", "selector": "[data-testid='product-card']" }
  ],
  "assertions": [
    { "type": "path", "value": "subpackages/workspace/pages/product-detail/index" },
    { "type": "text", "value": "宠物详情" }
  ],
  "capture": {
    "mode": "screenshot",
    "output": "screenshots/scenario/productdetail.png"
  }
}
```

### 必须补的字段

- `engine`
  - `web-playwright-cli`
  - `web-playwright-spec`
  - `miniapp-devtools`
- `target`
  - Web 用 `base_url` / `storage_state`
  - Miniapp 用 `project_key` / `target_name`
- `assertions`
  - 不要把断言塞回自由文本
- `capture`
  - 明确输出路径和产物类型

## Web 侧怎么做

### 推荐策略

Web 不再默认走 agent-browser/MCP 风格的全页面灌上下文。

应该改成两阶段：

1. **探索阶段**
   - AI 用 `Playwright CLI` 看页面摘要、截图、局部结构
   - 目的不是长期执行，而是把路径摸清

2. **固化阶段**
   - 产出 `scenario.json`
   - 由 AI 生成 `spec.ts` 或本地脚本
   - 后续执行尽量脱离 AI，走纯脚本或 CI

### 为什么这样最稳

- 探索阶段需要 AI 判断页面反馈
- 固化阶段需要低成本、低 token、可回归
- 两者混在一起时，永远会反复烧 token

### 不建议把 undocumented flag 当架构核心

视频里提到的 `--persistent` 思路可以保留为工程技巧，但当前正式架构不要依赖“某个未稳定公开参数”。

Web 登录态持久化建议优先用：

- Playwright 自己的 `storageState`
- 本地 session/profile 文件
- 生成后的固定 spec/script

而不是把“AI 交互式会话是否保持”当成唯一依赖。

## Miniapp 侧怎么做

### 结论

`auto-miniprogram` 能做脚本化持久保存，但现在只做到一半：

- **能持久保存 target/broker**
- **能命令行执行 smoke**
- **不能持久保存 scenario 作为一等资产**

所以不是推倒重来，而是补一层。

### 最小可行做法

在 `/Volumes/DATABASE/code/auto-miniprogram` 新增：

- `scripts/devtools-scenario.mjs`
- `src/commands/devtools-scenario.mjs`

功能：

1. 读取 `scenario.json`
2. 根据 `target.project_key / target.target_name` 选 active runtime
3. 自动补 `connect / reconnect / ensure_build`
4. 执行 `storage / relaunch / navigate / switchTab / tap / input / wait / assert`
5. 产出：
   - `result.json`
   - `screenshot`
   - `consoleLogs`
   - `exceptionLogs`
6. 失败时返回结构化错误而不是只报 stderr

### 为什么不要继续只堆 MCP tool calls

如果每次都让 AI 现调：

- `miniapp_register_target`
- `miniapp_use_target`
- `miniapp_set_storage_value`
- `miniapp_relaunch`
- `miniapp_tap_element`
- `miniapp_wait_for_page`
- `miniapp_screenshot`

那本质上还是“把执行脚本写在对话里”。
这和使用 agent-browser 没有本质区别，只是换了工具名。

## `ui-ux-test` 应该怎么改

### 新职责

`ui-ux-test` 不再负责“直接驱动页面”。
它应该改成：

1. 规划 coverage
2. 选择或生成 scenario
3. 调用 runner 执行
4. 回填 execution log
5. 生成报告
6. 写回任务

### skill 层最应该新增的能力

- Web runner 选择策略
  - 探索态用 Playwright CLI
  - 回归态用 spec/script
- Miniapp runner 选择策略
  - 优先 `devtools:scenario`
  - 退化到 `devtools:smoke`
- 统一 evidence 目录约定
- 统一 `scenario -> board screenshot -> report` 回写路径

## `interaction-board` 应该怎么改

当前已经有：

- `scenario.json -> Playwright spec.ts`
- `card.scenario_refs[]`

下一步不要继续往“更漂亮的 HTML”上堆，而要补“执行回写”：

### 建议新增

- `scenario_runs/<run_id>.json`
- `node.card.last_capture`
- `node.card.last_result`
- `node.card.runner_refs[]`

### 这样做的结果

用户点开一个节点时，看到的不只是：

- 这是哪个页面
- 有哪些截图版本

还会看到：

- 最近一次是哪个 runner 跑出来的
- 用的是哪个场景
- 成功还是失败
- 失败日志是什么

这才是真正的“交互画布 + 自动化验证”闭环。

## 关于当前图片加载失败

我检查了当前 Eggturtle 样板：

- `exists=true` 的截图引用没有发现文件丢失
- 当前“加载失败”的主要来源不是路径写错，而是 14 个节点仍然只有 planned 占位，没有真实截图文件

当前缺图节点是：

- `workspaceEntry`
- `guiquanMarketplaceDetail`
- `guiquanMarketplace`
- `guiquanSupplyAddresses`
- `guiquanSupplyCart`
- `guiquanSupplyDetail`
- `guiquanSupplyOrders`
- `productDetail`
- `productEditor`
- `quickRecord`
- `footprintBadges`
- `seriesManage`
- `accountCertificates`
- `accountReferral`

所以这部分要靠 runner 去补采集，不是单纯修前端渲染。

## 推荐迭代顺序

### Phase 1: 先定 contract

先统一 `scenario.json`，不要先写很多 runner。

产物：

- Web / Miniapp 共用字段模型
- `interaction-board` 节点绑定规则

### Phase 2: 先补 Miniapp scenario runner

因为 Web 已经有成熟 Playwright 生态，小程序这边反而更缺。

最小交付：

- `devtools:scenario --scenario <file> --json-output <file>`

### Phase 3: 更新 `ui-ux-test`

把 skill 从“报告中心”升级为“场景编排 + 报告中心”。

### Phase 4: 回写 `interaction-board`

让 runner 执行结果自动沉淀成：

- 节点截图版本
- scenario refs
- 最近一次执行状态

### Phase 5: Web 再迁纯 runner

Web 的真正目标不是一直让 AI 盯着页面，而是：

- AI 帮你摸清流程
- 然后产出固定 spec/script
- 再由 CI 或本地命令 0-token 跑

## 最小落地任务

如果下一轮直接开工，我建议按这个顺序拆：

1. 在 `auto-miniprogram` 新增 `devtools:scenario`
2. 在 `interaction-board` 扩 scenario contract
3. 在 `ui-ux-test` 新增 “scenario-first workflow” 文档与入口脚本
4. 在 Eggturtle 先补 2 到 3 条真实场景：
   - `products -> productdetail`
   - `products -> shareconfig`
   - `me -> accountcertificates`

这三步跑通后，整套方向就基本坐实了。
