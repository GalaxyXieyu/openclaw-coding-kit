# Project Review Working Domain

## 一句话定位

`project-review` 是 `pm` 之后的统一 review 编排层，负责把项目复盘、代码质量巡检、文档治理、UI/UX 验证和结构观察收口成一个日常可执行的质量闭环。

它不是任务真相，不替代 `pm`。
它也不是一个通用卡片平台，不替代 delivery 层。

## 工作域边界

### 1. 项目复盘域

负责：

- 周报
- 月报
- 关键事件提醒
- 每个项目 50 字内大白话摘要

目标：

- 让用户不点很多页面，也能知道做了什么、还没做什么、下一步做什么

### 2. 代码健康域

负责：

- 最近 24 小时有 commit 时触发巡检
- 变更级 diff review
- 长文件 / 长函数 / 重复代码 / 测试缺口 / API 风险检查
- P0 / P1 / P2 风险分级

目标：

- 让代码质量问题变成“每天可见、可处理”的卡片，而不是积压成大修

### 3. 文档治理域

负责：

- docs 漂移
- 过期文档候选
- `AGENTS.md` 漂移
- 文档剪枝建议

目标：

- 保持仓库说明和真实做法一致

### 4. UI/UX 验证域

负责：

- 修复之后的 UI 定向 smoke
- 页面 / 组件 / 交互的最小验证
- 截图与证据回填

目标：

- 让“点击修复”不是只改代码，还带最基本的可见结果验证

### 5. 结构观察域

负责：

- 周 / 月级结构图谱刷新
- 热点模块观察
- 低复用区域、孤立区域观察

目标：

- 做长期结构保养，不做每日必跑项

## 不在工作域里的事

当前不归 `project-review` 管：

- 任务创建真相
- 任务状态真相
- 通用消息网关
- NotebookLM 学习系统
- 知识卡体系
- 每日高频群打卡

这些分别仍归 `pm`、delivery 层或后续阶段处理。

## 内部 lane 设计

建议固定 5 条 lane：

- `project-retro`
- `code-review`
- `docs-review`
- `ui-ux-review`
- `graph-observe`

每天质量复盘只认这一条路：

`commit_window -> code-review -> docs-review -> optional ui-ux-review -> code_health_risk_card`

周/月复盘只认这一条路：

`project-retro -> optional graph-observe -> review card`

## 工具收口建议

把日常运行工具都收在 `skills/project-review/` 下，不再散落引用外部 skill 作为主入口。

建议目录逐步收口成：

```text
skills/project-review/
├── SKILL.md
├── references/
│   ├── working-domain.md
│   ├── review-lanes.md
│   ├── product-spec.md
│   ├── code-health-spec.md
│   ├── card-packs.md
│   └── copy-rules.md
└── scripts/
    ├── commit_window.py
    ├── summary_guard.py
    ├── review_router.py
    ├── build_review_bundle.py
    ├── code_review_lane.py
    ├── docs_review_lane.py
    ├── uiux_review_lane.py
    ├── graph_observe_lane.py
    ├── risk_card_builder.py
    ├── callback_router.py
    ├── fix_executor.py
    └── review_state_store.py
```

## 推荐实施顺序

### Phase 1

- 固定工作域
- 固定 lane
- 固定卡片类型
- 固定文案规则

### Phase 2

- 做 `review_router.py`
- 做 `build_review_bundle.py`
- 跑通 `project-retro` 和 `code-review`

### Phase 3

- 接 `docs-review`
- 接 `code_health_risk_card_v1`
- 接 callback state

### Phase 4

- 接 `fix_executor.py`
- 接 `ui-ux-review`
- 把“点修复 -> 修复 -> 验证 -> 归档”跑通

### Phase 5

- 周 / 月级接 `graph-observe`
- 只做结构观察，不做每日强依赖

## 成功标准

如果这套 `project-review` 做对了，最后应该满足：

- 日常 review 只有一个入口
- 用户只看少量卡片就能知道项目和代码健康状态
- 代码、文档、UI 验证不再各自为战
- 点击修复后能进入真实的修复闭环
- 长期项目不会越做越乱
