---
created: 2026-04-14T08:50:29.614Z
title: Build task-reviewer umbrella runtime
area: planning
files:
  - skills/task-review/SKILL.md
  - skills/task-review/references/working-domain.md
  - skills/task-review/references/review-lanes.md
  - skills/task-review/references/product-spec.md
  - skills/task-review/references/code-health-spec.md
  - skills/task-review/references/card-packs.md
  - skills/task-review/scripts/commit_window.py
  - skills/task-review/scripts/summary_guard.py
  - plan/2026-04-14_15-04-04-main-agent-rhythm.md
---

## Problem

当前 `task-review` 的方向已经从“项目周报/月报”扩展成统一的 review 入口，但还停留在概念和局部脚本阶段，缺少一个明确的 GSD 执行抓手。

如果现在直接开始实现，很容易出现几种偏差：

- 又把 code review、docs review、ui/ux review 拆回多个平级入口
- 把 `task-review` 做成过宽的通用平台
- 先写零散脚本，没有统一 router、state、card、callback 契约
- 在没有固定工作域的情况下，越做越散

需要先把 `task-reviewer` 作为 umbrella runtime 的工作域、lane、工具收口和实施顺序固定下来，再开始做运行时实现。

## Solution

按下面顺序推进：

1. 以 `skills/task-review/references/working-domain.md` 作为总边界定义
2. 以 `review-lanes.md` 固定 5 条内部 lane：
   - project-retro
   - code-review
   - docs-review
   - ui-ux-review
   - graph-observe
3. 先实现统一编排层，而不是继续扩展零散脚本：
   - `review_router.py`
   - `build_review_bundle.py`
   - `risk_card_builder.py`
   - `callback_router.py`
   - `review_state_store.py`
4. 第一批只跑通：
   - weekly/monthly/event project retro
   - recent-commit code health risk card
5. 第二批再接：
   - fix executor
   - ui-ux verification
   - graph observe

实现过程中必须坚持：

- `pm` 仍是任务真相
- `task-reviewer` 只做 review 编排与卡片闭环
- 工具统一收在 `skills/task-review/`
- 日常质量复盘只保留一个入口
