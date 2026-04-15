# Interaction Board

`interaction-board` 是当前仓库里用于管理“交互原型 + 页面矩阵 + 路由关系 + 截图位”的轻量能力。

现在的推荐入口已经切到 `skills/product-canvas`：

- `product-canvas` 负责统一调用 board、scenario、runner 和报告
- `interaction-board` 保留为 board truth / render layer
- 兼容窗口结束前，这个目录仍然继续作为 board 资产位置

第一版目标不是替代 Figma，而是解决几个更现实的问题：

- 页面已经在开发，但没有统一的交互画布
- UI/UX review 只能看零散截图或代码，无法快速理解完整用户流
- 文档、路由常量、页面注册和实际入口容易漂移
- 后续想接自动截图和版本快照，却没有稳定的数据合同

## 当前产物结构

- `skills/interaction-board/`
  - skill 说明、数据合同、CLI 脚本
- `docs/interaction-board/eggturtle-miniapp/`
  - Eggturtle 小程序样板产物

## 当前最小链路

1. 从 miniapp repo 抽取页面矩阵与路由常量
2. 识别已注册页面、候选页面和文档漂移
3. 生成 `board.manifest.json`
4. 如已有截图，执行 `attach-screenshots` 回填 board 本地 `screenshots/`
5. 生成 `board.drawio`
6. 生成 `index.html`
7. 生成 `inventory.md`
8. 如已有场景 JSON，执行 `attach-scenarios` 把可复用的自动化路径绑到页面节点

## 新增能力：截图挂载

现在支持把已有截图资产直接挂到 manifest，而不是只保留占位路径。

典型命令：

```bash
python3 skills/interaction-board/scripts/interaction_board.py attach-screenshots \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --source compare=/abs/path/to/manual-ui-compare \
  --source smoke=/abs/path/to/miniapp-weapp-smoke
```

当前策略：

- 优先读取截图目录中的 `routes.json` 做显式匹配
- 其次使用文件名、路由尾部和页面别名做启发式匹配
- 匹配成功后复制到 board 自己的 `screenshots/<label>/` 目录
- HTML board 会直接渲染缩略图，便于 review

## 新增能力：overlay 板层

现在支持在抽取得到的 `board.manifest.json` 之上，再叠一层很轻的 `overlay`：

- 适合 AI 先创建草稿页卡片
- 适合把“未来页面”先接到已有页面流向上
- 不需要把整份代码上下文重新喂给模型
- 不会污染从代码抽出来的基础真值层

典型命令：

```bash
python3 skills/interaction-board/scripts/interaction_board.py apply-overlay \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --overlay docs/interaction-board/board.overlay.example.json \
  --output docs/interaction-board/sample/board.merged.json
```

`build-miniapp-sample` 也支持直接带 `--overlay`，一次输出合并后的样板。

## 新增能力：scenario -> Playwright spec

现在支持把场景 JSON 直接生成一个 Playwright `spec.ts`：

```bash
python3 skills/interaction-board/scripts/interaction_board.py render-scenario-spec \
  --scenario docs/interaction-board/scenario.example.json \
  --output docs/interaction-board/scenarios/products-to-detail.spec.ts
```

适合的用法是：

- 第一次人工或 AI 把某个页面链路走通
- 把过程沉淀成 `scenario.json`
- 把 `entry_node_id` / `target_node_id` 绑定回 manifest 节点
- 后续直接复用生成或更新 Playwright 脚本
- 用脚本自动到达目标页面并截图

如果只想把场景绑定进现有 board，而不重建整套样板，可直接执行：

```bash
python3 skills/interaction-board/scripts/interaction_board.py attach-scenarios \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --scenario-dir docs/interaction-board \
  --output docs/interaction-board/sample/board.with-scenarios.json
```

`scenario-dir` 会自动忽略 overlay、manifest 这类无关 JSON，只消费真正的 scenario contract。

## 后续扩展

- 接 miniapp automation / Playwright 自动截图
- 用任务/提交快照做版本管理
- 引入 SQLite 做跨版本索引
- 增加嵌入式画布编辑能力

更完整的拆层建议见：

- `docs/interaction-board/ARCHITECTURE.md`
- `docs/interaction-board/RUNNER-MIGRATION.md`
- `docs/interaction-board/scenario.example.json`
