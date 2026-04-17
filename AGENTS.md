# PM工具链 AGENTS

本仓库默认使用中文沟通，英文仅用于代码标识符、命令和必要的技术术语。

## 执行入口

- 受 PM 管理的工作先读取 `pm.json`、`.pm/current-context.json`、`.pm/bootstrap.json`、`.pm/coder-context.json`。
- 任何会改变项目行为、文档、流程或代码的用户需求，都必须先通过 `pm create`/`pm search` 归一到任务，再开始实现。
- 若需求改变 agent、PM、coder 或 review 的工作方式，必须同步更新对应 `skills/*/SKILL.md`，并保持真实仓库 `AGENTS.md` 与 OpenClaw 工作区 `AGENTS.md` 的共享 PM 规则一致。
- `current_task` 描述是本次执行索引卡；如果 handoff 没有 GSD 字段，回退到 PM task/doc 上下文。
- `brownfield` 仓库在做大范围改动前先做 codebase mapping 或最小必要的上下文收敛，再进入编辑。
- 编码完成后通过 PM 写回进度或完成结果，不要只停留在本地修改。

## 工作方式

- 两步及以上任务必须维护计划，并随着执行更新状态。
- 初始化或修正项目工作区时，必须同时检查/同步 OpenClaw 工作区与真实仓库内的 `AGENTS.md`；不能只更新其中一份。
- 先做最小充分的上下文收集，优先用 `rg` / 精确文件读取，不做大范围盲扫。
- 默认遵循 KISS / YAGNI，未经明确要求不要引入新架构或破坏现有 CLI / API / 数据格式。
- 编辑尽量收敛在当前任务相关文件；如果测试、文档或 AGENTS 同步需要联动，只扩展到直接相关文件。

## 代码与 Git 约束

- 手工编辑统一使用 `apply_patch`。
- 优先增量修改，不回滚用户已有改动，不使用 `git reset --hard`、`git checkout --` 这类破坏性命令。
- 能跑测试就跑；至少补针对性验证，不能假设结果正确。
- 涉及 UI 路径时，在交付说明中补充后续 `ui-ux-review` 提醒。

## 交付要求

- 总结里说明做了什么、验证了什么、还有什么风险。
- 引用关键文件时给出可定位的文件路径和行号。
- 若同步了文档，明确写出补了哪些项目描述、产品说明或协作规则。
