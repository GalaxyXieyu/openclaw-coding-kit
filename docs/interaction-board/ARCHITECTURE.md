# Interaction Board Architecture

## Current Split

当前实现已经拆成四层，避免继续把抽取、渲染、CLI、场景生成全塞进单文件：

兼容期内：

- `product-canvas` 是统一调用入口
- `interaction-board` 继续专注 board truth / render

- `skills/interaction-board/scripts/interaction_board_core.py`
  - 页面抽取
  - 路由关系推断
  - 截图挂载
  - overlay 合并
  - manifest/card 数据补全
- `skills/interaction-board/scripts/interaction_board_render.py`
  - HTML/draw.io/inventory 渲染拼装
- `skills/interaction-board/assets/board_template.html`
- `skills/interaction-board/assets/board.css`
- `skills/interaction-board/assets/board.js`
  - board 视图资产
  - draw.io
  - inventory markdown
- `skills/interaction-board/scripts/interaction_board_cli.py`
  - 命令入口
  - 文件写回
  - sample build orchestration
- `skills/interaction-board/scripts/interaction_board_scenarios.py`
  - scenario JSON -> Playwright spec 生成
- `skills/interaction-board/scripts/interaction_board.py`
  - 对外薄入口，只做 re-export 和 `main()` 转发

## Four-Layer Model

后续这套系统建议固定成四层，不要再混：

### 1. Extracted Truth Layer

来源于代码和文档的基础真值：

- route constants
- app.config 页面注册
- wrapper -> screen component 映射
- 代码里推断出的 navigation edges
- 文档漂移 / route 冲突

产物：

- `board.manifest.json`

原则：

- 这一层只记录“代码里已经存在或明确声明”的事实
- 不要把 AI 草图和手工想法直接写回这层

### 2. Overlay Board Layer

给 AI 和产品快速迭代的轻量层：

- 草稿页面卡片
- 临时连线
- 页面备注
- 手工补充标签

产物：

- `board.overlay.json`

原则：

- 允许不依赖真实代码页面先建卡片
- 允许把未来页面先接到已有页面流向上
- 后续真实页面落地后，再把 overlay 内容迁移或消化回真值层

### 3. Review Render Layer

面向 review 的展示层：

- HTML canvas
- draw.io
- inventory markdown

原则：

- 只消费 manifest + overlay 合并结果
- 不直接成为长期真值

### 4. Scenario Capture Layer

这是后续最值得补的层，用于省 token 和加速验证。

每个“第一次成功到达”的页面节点，都可以沉淀一个 Playwright 场景：

- 入口条件
- 前置 storage / login / tenant context
- 到达路径步骤
- 截图动作
- 命中节点

产物建议：

- `scenarios/<scenario_id>.json`
- `scenarios/<scenario_id>.spec.ts`

## Why Playwright Scenario Layer Matters

你刚才提到的想法是对的，这层价值很高：

- 第一次由 AI 或人工把路径走通
- 自动把到达过程保存成 Playwright 脚本
- 以后再次打开该节点时，直接复用脚本到达并截图
- 不需要重新把整段用户流和页面上下文讲一遍
- 非常适合 CI 周期性回归和 token 节省

## Recommended Scenario Contract

```json
{
  "scenario_id": "products-to-detail",
  "engine": "web-playwright-cli",
  "entry_node_id": "products",
  "target_node_id": "productdetail",
  "target": {
    "base_url": "http://127.0.0.1:3000"
  },
  "capture": {
    "mode": "screenshot",
    "output": "screenshots/scenario/productdetail.png"
  },
  "context": {
    "storage": [],
    "notes": "需要先进入 workspace"
  },
  "assertions": [
    {
      "type": "path",
      "value": "/subpackages/workspace/pages/product-detail/index"
    }
  ]
}
```

## Recommended Next MVP

下一版不要直接上复杂数据库，先做文件化 MVP：

1. `board.manifest.json`
2. `board.overlay.json`
3. `scenarios/*.json`
4. `scenarios/*.spec.ts`

当以下问题明显出现时，再考虑 SQLite：

- 跨版本索引
- 截图历史检索
- 多项目统一查询
- scenario 执行记录统计

## What AI Needs In JSON

为了让 AI 能直接消费图片，`node.card` 里至少要有：

- `primary_image.relative_path`
- `primary_image.absolute_path`
- `images[]`
- `scenario_refs[]`

其中 `scenario_refs[]` 不要只存字符串，应该是结构化对象，至少包含：

- `scenario_id`
- `script_path`
- `script_absolute_path`
- `scenario_path`
- `capture_output`
- `engine`
- `target`
- `assertions`
- `role`

这样模型只要读一份 manifest，就能知道：

- 这个页面主图在哪里
- 有没有真实截图
- 当前是 planned 占位还是实际截图
- 如果要自动到达这个页面，应该优先复用哪个 scenario

## Near-Term Refactor Direction

这次先把单文件拆成 core / render / cli。

下一次继续拆时，优先顺序应该是：

1. 把 HTML/CSS/JS 模板从 render 再拆到独立 assets
2. 把 screenshot matching 独立成 matcher 模块
3. 把 overlay merge 独立成 board-model 模块
4. 新增 scenario registry + playwright generator
