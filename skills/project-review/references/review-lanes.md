# Project Review Internal Lanes

## 目标

`project-review` 不是一个单功能 skill，而是一个统一 review 入口。

你说的方向是对的：

- 不要把 `code-review`
- 不要把 docs review
- 不要把 `ui-ux-test`

做成几个平级、分散的日常入口。

更稳的方式是把它们收进 `project-review`，作为内部 lane 来编排。

## 内部 lane 列表

### 1. `project-retro`

负责：

- 周报
- 月报
- 项目事件提醒
- 每个项目 50 字内大白话摘要

### 2. `code-review`

负责：

- 最近提交的 diff review
- P0 / P1 / P2 分级
- 长函数 / 长文件 / 重复代码 / 测试缺口 / API 风险

### 3. `docs-review`

负责：

- 文档漂移
- 过期文档候选
- `AGENTS.md` 漂移
- 文档剪枝建议

### 4. `ui-ux-review`

负责：

- 修复之后的 UI 定向验证
- 页面/组件/交互 smoke
- 截图和证据回填

### 5. `graph-observe`

负责：

- 周/月级结构图谱刷新
- 热点模块观察
- 孤立模块 / 低复用区域观察

它不是每日巡检必跑项，只适合做结构观察补充。

## 每日质量复盘顺序

如果最近 24 小时有 commit，推荐按下面顺序跑：

1. `code-review`
2. `docs-review`
3. 判断是否需要 `ui-ux-review`
4. 合并为一张 `code_health_risk_card_v1`

如果没有 commit，就不跑这条 daily code quality retro。

## 周/月复盘顺序

周/月复盘推荐按下面顺序跑：

1. `project-retro`
2. 需要时补 `graph-observe`
3. 合并为 `weekly_review_card_v1` 或 `monthly_review_card_v1`

## 为什么不用平级 skills

因为你要的是一个长期稳定的质量维护入口。

如果 daily quality retro 要靠多个平级 skill 手工拼接，会出现这些问题：

- 入口分散
- 触发条件分散
- 归档状态分散
- 用户不知道该看哪一张卡
- 后续 callback 和自动修复难统一

所以：

- 可以参考外部 `code-review` 和 `ui-ux-test`
- 但不要让它们成为日常主入口
- 日常主入口只保留 `project-review`

## 推荐落地方式

在实现层，把 lane 理解成：

- 一组规则
- 一组脚本
- 一组输出结构

而不是额外再造几个 top-level skill。

这样后续你维护的时候，只需要盯住一个技能目录：

- `skills/project-review/`

这才符合你说的“日常就应该做好的代码质量复盘”。
