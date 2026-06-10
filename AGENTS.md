# PM工具链 AGENTS

本仓库默认使用中文沟通，英文仅用于代码标识符、命令和必要的技术术语。

## 执行入口

- 未来业务项目以真实代码仓库目录为绑定点，例如 `/Volumes/DATABASE/code/business/Eggturtle-breeding-library`。
- 受 PM 管理的工作先读取业务仓库内的 `pm.json`、`.pm/current-context.json`、`.pm/bootstrap.json`、`.pm/coder-context.json`。
- 任何会改变项目行为、文档、流程或代码的用户需求，都必须先通过 `pm create` / `pm search` 归一到任务，再开始实现。
- 若需求改变 agent、PM、coder 或 review 的工作方式，必须同步更新对应 `skills/*/SKILL.md` 和 repo-local `AGENTS.md` / `CLAUDE.md` 初始化说明。
- `current_task` 描述是本次执行索引卡；没有额外 handoff 字段时，回退到 PM task/doc 上下文。
- `brownfield` 仓库在做大范围改动前先做 codebase mapping 或最小必要的上下文收敛，再进入编辑。
- 编码完成后通过 PM 写回进度或完成结果，不要只停留在本地修改。
- PM 的 Feishu 投递默认使用官方 `lark-cli`，不得默认路由到 OpenClaw/Gateway；本地 backend 必须保持不依赖 `lark-cli`。
- 每日/夜间复盘若要发到 Feishu，默认走 `project-review` 卡片链路；不要用 cron `announce` 直接发 agent 文本。
- 多项目夜间复盘若集中在同一时段，优先通过 `project_review.nightly.stagger_minutes` 串行错峰；reviewer 失败时也必须保留可发送的降级结果，不能直接静默消失。

## Repo-Local 绑定模式

- Claude Code 和 Codex 都应直接在业务仓库根目录启动或 `cd` 进去工作。
- 每个业务仓库维护自己的 `pm.json`、`.pm/` 缓存、`AGENTS.md` 和可选 `CLAUDE.md`。
- `AGENTS.md` 作为跨 agent 通用规则；`CLAUDE.md` 可作为 Claude Code 专用入口，但不要和 `AGENTS.md` 写出冲突规则。
- Feishu 任务、评论和文档同步通过官方 `lark-cli` 完成；密钥、access token、refresh token、tenant secret、user token 不写入 `pm.json`。
- 旧的 OpenClaw workspace / Gateway / Hermes 绑定不是默认路径；只有明确要跑 OpenClaw/ACP 多 agent 派发时，才单独启用相关运行时。

## 工作方式

- 两步及以上任务必须维护计划，并随着执行更新状态。
- 初始化或修正业务项目时，优先更新真实仓库内的 `AGENTS.md` / `CLAUDE.md`；不再默认生成或同步 OpenClaw workspace 合同。
- 先做最小充分的上下文收集，优先用 `rg` / 精确文件读取，不做大范围盲扫。
- 默认遵循 KISS / YAGNI，未经明确要求不要引入新架构或破坏现有 CLI / API / 数据格式。
- 编辑尽量收敛在当前任务相关文件；如果测试、文档或 agent 规则同步需要联动，只扩展到直接相关文件。

## 代码与 Git 约束

- 手工编辑统一使用 `apply_patch`。
- 优先增量修改，不回滚用户已有改动，不使用 `git reset --hard`、`git checkout --` 这类破坏性命令。
- 能跑测试就跑；至少补针对性验证，不能假设结果正确。
- 涉及 UI 路径时，在交付说明中补充后续 `ui-ux-review` 提醒。

## 交付要求

- 总结里说明做了什么、验证了什么、还有什么风险。
- 引用关键文件时给出可定位的文件路径和行号。
- 若同步了文档，明确写出补了哪些项目描述、产品说明或协作规则。

<!-- PM_SHARED_CONTRACT:START -->
## Repo / Coder Execution Contract

- project: `PM工具链`
- PM config: `/Volumes/DATABASE/code/learn/openclaw-pm-coder-kit/pm.json`
- repo root: `/Volumes/DATABASE/code/learn/openclaw-pm-coder-kit`
- tasklist: `CodingTeam`
- doc folder: `项目文档`
- default engineering worker: `codex`
- preferred UI worker: `gemini`

- `product-canvas` clarifies ambiguous product, UX, and acceptance questions before implementation.
- `pm` remains task truth, context truth, progress write-back, and completion truth.
- `coder` executes implementation after PM intake and routes engineering work to `codex` while preferring `gemini` for UI or visual exploration.
- `project-review` is the project-level review and quality layer after implementation, not the front-door intake role.
- Any tracked behavior, docs, workflow, or code change should still start from a normalized PM task before execution.
<!-- PM_SHARED_CONTRACT:END -->
