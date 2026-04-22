# Product Canvas Workflow

`product-canvas` 负责统一“产品流转画布 + 场景资产 + 截图证据 + 报告”。

当前分层如下：

1. board assets
   - 页面真值
   - manifest / draw.io / HTML board
   - 页面节点与关系
2. `product-canvas`
   - 统一调用入口
   - scenario registry
   - miniapp/web runner 调度
   - UI review 报告与 evidence 组织
3. `pm`
   - 任务真值、进度写回、交付记录

## 默认目录

- Board truth:
  - `docs/interaction-board/`
- Scenario assets:
  - `docs/interaction-board/scenarios/`
- Review runs:
  - `out/product-canvas/runs/<run_id>/`

## 推荐顺序

1. 先产出或刷新 `board.manifest.json`
2. 再为关键链路沉淀 `scenario.json`
3. runner 执行后保存 screenshot/result.json
4. 报告消费执行结果，不直接承担页面驱动

## Miniapp 目标约定

- 优先把 miniapp 根信息写进 `scenario.target.project_root`
- 如果是实时 DevTools target，调用 wrapper 时补：
  - `--target-name`
  - `--ide-port`
  - `--automator-port`
- `tap` step 一旦声明 `path`，就表示这是强约束；跳到别的页面应视为失败，而不是“任意导航都算成功”

## 不要做的事

- 不要把截图二进制塞进 JSON
- 不要把一次性对话路径当成长期自动化资产
- 不要让报告层直接替代 board 或 scenario 真值
- 不要在 phase 1 就引入数据库
