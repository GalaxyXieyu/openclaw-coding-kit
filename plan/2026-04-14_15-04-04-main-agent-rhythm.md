---
mode: plan
cwd: /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
task: 主Agent主动节律与知识闭环需求细化
complexity: complex
planning_method: builtin
created_at: 2026-04-14T15:04:04+08:00
---

# Plan: 主Agent主动节律与知识闭环需求细化

🎯 任务概述

当前 PM 能力已经覆盖 Feishu task/doc 写回、任务完成、评论和上下文刷新，但仍然以“用户主动发起”为主。目标是把它升级为一个主动驱动的主 Agent 系统：每天主动找用户收集计划、根据回复自动归类任务、在执行中跟踪风险、完成后沉淀知识，并按日/周/月生成复盘和规划建议。

这个需求的本质不是新增一个 wiki，而是建立一条可持续复用的工作闭环：
`主 Agent 主动触达 -> 对话归类为任务/想法/阻塞 -> 执行跟踪 -> 完成后知识提炼 -> 周/月复盘 -> 后续任务前召回`

📌 当前前提

- 当前仓库 `pm` 已运行在 `task.backend=feishu`、`doc.backend=feishu`
- 当前 GSD 路由仍处于 bootstrap，原因是仓库尚未初始化 `.planning/`
- 因此本文件先作为 GSD 风格的需求细化输入，后续可转入正式 `.planning/` phase 流程

✅ 已确认的 MVP 取舍

- 主目标优先级：`主动推送 > 任务对话归类 > 知识沉淀`
- project group 只承载周报 / 月报 / 关键事件推送，不做高频日报
- 知识卡先后置，不作为第一阶段范围
- 第一阶段重点是让主 Agent 主动汇总、主动提醒、主动推送
- 新增一条代码健康 review 线：若最近一天有代码提交，则自动产出代码健康风险卡

📋 需求拆分

1. 主 Agent 主动节律
   - 第一阶段弱化日级高频触达，优先完成周报 / 月报 / 关键事件推送
   - 后续如要增加日级触达，应优先放在私聊而不是 project group
   - 关键事件推送包括：长时间停滞、重要任务完成、需要确认计划调整

2. 自然语言任务归类
   - 用户在对话里说“今天想做什么”“我卡住了”“顺手研究一下 X”
   - 系统自动判断是：
     - 续做已有任务
     - 新建任务
     - 阻塞说明
     - 学习项 / 研究项
     - 暂不执行的想法 / backlog
   - 自动落到对应 tasklist / task / comment / note 载体

3. 执行跟踪与主动追问
   - 基于任务更新时间、评论频率、重复主题、长时间无完成信号等规则识别 stalled / drift
   - 主 Agent 触发最小必要追问：
     - 是否需要拆成子任务
     - 是否是知识盲区而非实现阻塞
     - 是否需要先做验证性 spike

4. 完成后的知识沉淀
   - `pm complete` 不再只写完成 comment
   - 第一阶段只要求生成任务复盘摘要或 wiki/doc 草稿
   - 可复用知识卡、checklist、错误模型沉淀放到第二阶段

5. 周/月复盘与规划建议
   - 自动汇总近一周 / 一月的任务、阻塞、知识主题
   - 输出：
     - 重复问题模式
     - 高频薄弱点
     - 最有价值的学习主题
     - 下周 / 下月建议优先事项
     - 建议暂停或延后的事项
   - 结果推送到绑定的 Feishu channel 主 bot
   - 这是第一阶段最优先交付能力

6. 任务前召回
   - 在 `pm plan` / `pm refine` / `pm coder-context` 之前召回相关历史经验
   - 优先召回与当前任务标题、路径、标签最相近的知识卡和复盘
   - 第一阶段可暂不实现，后续在知识沉淀稳定后再打开
   - 目标是减少重复踩坑，而不是仅在事后写文档

7. 代码健康巡检
   - 如果最近 24 小时内有代码提交，则触发一轮代码健康 review
   - review 不只看 diff，还要补一层 repo hygiene：
     - 过长文件 / 过长函数
     - 重复代码未复用
     - docs 漂移
     - 过期文件候选
     - `AGENTS.md` 与真实流程漂移
   - 输出一张风险卡，按 `P0 / P1 / P2` 分级
   - 点击“修复”后，触发自动修复流；若影响 UI，再补一轮定向 `ui-ux-test`

🧱 系统边界

主系统优先使用现有 Feishu + PM 能力：

- Feishu Task：任务真相
- Feishu Doc / Wiki：长文档与沉淀页面
- 结构化知识载体：建议使用多维表格或 repo/local JSON 索引后续可切换
- 主 Agent：主动触达、追问、建议和汇总
- PM：分类、落库、上下文生成和回写
- 本地 repo：证据源、变更源、知识提炼原始素材

NotebookLM 不应作为第一阶段主系统，只适合作为第二阶段的学习增强层。

🧠 推荐数据模型

1. `cadence_events`
   - agent 何时触达
   - 触达类型：standup/checkin/wrapup/weekly/monthly
   - 是否收到用户回复
   - 本次触达生成了哪些 side effects

2. `inbox_items`
   - 原始用户文本
   - 分类结果：task / continuation / blocker / learning / backlog
   - 关联 task_guid / task_id
   - 置信度

3. `knowledge_cards`
   - task_guid
   - topic
   - wrong_model
   - correct_model
   - signals
   - checklist
   - related_paths
   - review_at

4. `retro_reports`
   - period: daily / weekly / monthly
   - source task ids
   - repeated patterns
   - suggestions
   - published_to channel / dm

🎯 第一阶段 MVP 范围

- `pm digest --period week|month`
- `pm suggest` 或等效建议生成入口
- 主 Agent 对 project group 的主动推送
- 基于任务状态、评论和最近完成情况做聚合
- 关键事件提醒，但不做高频日报轰炸
- 最近 24 小时 commit 检测 + 代码健康风险卡

🚫 第一阶段暂不包含

- 知识卡系统
- 高频日级群日报
- 复杂任务前召回
- NotebookLM 集成

🔧 推荐技术切分

Phase A: 交互与节律框架
- 定义 weekly / monthly / event-driven 三类消息协议
- 完成 project group 的推送边界
- 建立定时调度入口

Phase B: 对话归类与任务落库
- 新增 `pm inbox` 或等效入口
- 将自然语言归类后写入 task/comment/backlog
- 对重复任务先检索再创建

Phase C: 完成后知识沉淀
- 扩展 `pm complete`
- 第一阶段只保留复盘 / doc 草稿
- `pm learn` 和知识卡后置

Phase D: 周/月复盘与主动建议
- 新增 `pm review` / `pm digest`
- 从任务和知识卡聚合趋势
- 通过 Feishu 主 bot 推送到 channel

Phase E: 代码健康巡检与风险卡
- 最近 24 小时 commit 检测
- diff review + repo hygiene review
- 风险卡输出与“开始修复”动作
- UI 受影响时串联 `ui-ux-test`

Phase F: 任务前召回
- 在 `pm coder-context` / `pm refine` 里注入相关历史经验
- 完成真正的“事后沉淀 -> 事前提醒”闭环

⚠️ 风险与注意事项

- 不能让主 Agent 过度打扰用户，必须有触发阈值和静默窗口
- 群消息和私聊必须分层：第一阶段群里适合汇总和事件推送，不适合高频日报
- 长文档可以先有，但结构化知识卡先后置，不作为当前阻塞
- 如果用户直接在 Feishu UI 手动完成任务，需要补一个对账或补偿流程，避免漏掉知识沉淀
- 当前 doc token 还未初始化完成，正式写 wiki 前要先保证 doc 绑定就绪

❓ 待明确的决策问题

1. 周报和月报的固定发送时间分别是什么？
2. 关键事件提醒的阈值是什么，例如“几天未更新”才推送？
3. “今天想做什么”的输入是否仍要保留，只是改成低频触发而不是每日触发？
4. 周报/月报是只推汇总，还是附带下一周期的自动排程建议？

📎 参考

- `skills/pm/scripts/pm_commands.py:659`
- `skills/pm/scripts/pm.py:612`
- `skills/pm/scripts/pm_docs.py:111`
- `pm.json:1`
