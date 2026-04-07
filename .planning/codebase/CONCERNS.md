# Codebase Concerns

**Analysis Date:** 2026-04-07

## Tech Debt

**Workspace template bootstrap now defaults to repo-local assets:**
- Status: 最小模板集已经收进 `skills/pm/templates/workspace`，`pm_workspace.py` 默认优先使用 repo 内模板。
- Files: `skills/pm/scripts/pm_workspace.py`, `skills/pm/templates/workspace/*`, `INSTALL.md`
- Residual risk: 如果 operator 显式把 `PM_WORKSPACE_TEMPLATE_ROOT` 指到错误目录，workspace scaffold 仍会失败，但这已经属于配置错误而不是仓库缺件。

**Feishu-first backend leaks into the "local-first" path:**
- Issue: PM 数据模型与上下文缓存默认就是 Feishu task/doc 语义，repo-local 验证路径仍暴露 tasklist/doc binding。
- Files: `pm.json`, `.pm/current-context.json`, `.pm/coder-context.json`, `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_docs.py`
- Impact: 用户容易把“本地优先验证”误解为“backend-neutral”，实际迁移到非 Feishu 环境时仍会受到默认值、命名和输出口径影响。
- Fix approach: 保留 Feishu 作为默认 backend，但把 `pm.json` 与上下文输出改成 backend-neutral 结构，再由适配层注入 Feishu 细节。

**Front agent and ACP worker semantics are easy to conflate:**
- Issue: 用户、文档甚至编排代码都容易把 OpenClaw front agent 与 ACP worker 当成同一个 `agent id`，尤其在 `codex` 只作为 worker 可用时更明显。
- Files: `skills/pm/SKILL.md`, `INSTALL.md`, `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_runtime.py`
- Impact: 会出现 `Unknown agent id "codex"` 这类误路由问题，也会让安装文档把前台对话对象和后台执行对象讲混。
- Fix approach: 在文档、命令默认值和运行时日志里持续区分 `front agent` 与 `ACP worker`，并优先从 project/front-agent 配置解析用户可见入口。

**Repository map and actual structure can drift:**
- Issue: 当前仓库真实结构包含 `.pm/`、`diagrams/`、根级 `scripts/`、`pm.json` 等资产，而旧 mapping 文档并未完整覆盖这些目录。
- Files: `README.md`, `.planning/codebase/STRUCTURE.md`, `.pm/doc-index.json`, `diagrams/pm-coder-bridge-architecture.drawio`, `scripts/export-drawio-png.mjs`
- Impact: 后续 planner/executor 可能从过期结构文档出发，错误判断配置位置、文档索引和图表资产所在位置。
- Fix approach: 把 `.planning/codebase/*` 视为需要定期刷新的产物，并在每次结构变化后同步更新 mapping 文档。

## Known Bugs

**Tracked PM metadata contradicts the documented "do not commit runtime data" rule:**
- Symptoms: 仓库已跟踪 `pm.json`、`.pm/current-context.json`、`.pm/coder-context.json`、`.pm/doc-index.json`，但 `.gitignore` 与 `README.md` 又把这些视为本地状态或敏感协作元数据。
- Files: `pm.json`, `.pm/current-context.json`, `.pm/coder-context.json`, `.pm/doc-index.json`, `.gitignore`, `README.md`
- Trigger: 在当前仓库直接提交 bootstrap 结果或同步真实 task/doc binding 时出现；忽略规则无法移除已被 Git 跟踪的文件。
- Workaround: 短期内只保留脱敏示例文件；长期需要把真实绑定移出仓库，或用模板化示例替代当前已跟踪文件。

**Workspace bootstrap no longer depends on external templates for the baseline path:**
- Status: repo 内模板已可完成默认 scaffold，`template_root_exists: false` 不再是新机器上的常见故障。
- Files: `skills/pm/scripts/pm_workspace.py`, `skills/pm/templates/workspace/*`, `INSTALL.md`
- Residual risk: 只有在显式覆盖模板根目录且指向错误位置时，才会退化回模板缺失问题。

## Security Considerations

**Collaboration metadata is stored in tracked repo-local files:**
- Risk: `pm.json` 与 `.pm/*.json` 保存了真实 tasklist/doc 绑定、文档链接和协作上下文；即使不是密钥，也属于不应默认公开的项目元数据。
- Files: `pm.json`, `.pm/current-context.json`, `.pm/coder-context.json`, `.pm/doc-index.json`
- Current mitigation: `.gitignore` 已忽略 `pm.json`、`.pm/`、`*.token.json`、`*.session.json`，且 `README.md` 已声明不要提交真实文档链接与 tasklist GUID。
- Recommendations: 将仓库中的现有真实绑定脱敏或移除，改为 `examples/pm.json.example` 这类模板文件；后续把 `.pm/` 完全视为生成态缓存。

**Feishu bridge operations widen the blast radius of misconfiguration:**
- Risk: PM 通过 `feishu_task_tasklist`、`feishu_task_task` 等 bridge 调用直接操作真实任务和文档，一旦 backend 配置指向错误空间，会把评论、完成状态和附件写到错误对象。
- Files: `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_docs.py`, `skills/pm/scripts/pm_auth.py`, `pm.json`
- Current mitigation: repo 文档要求先走本地验证，再接真实 Feishu；`pm context --refresh` 会把当前绑定信息回写到 `.pm/*.json` 供人工核对。
- Recommendations: 增加显式的 dry-run/read-only 模式、目标 workspace 确认提示，以及对生产/测试工作区的隔离配置。

## Performance Bottlenecks

**Bridge polling cost grows with tracked child sessions:**
- Problem: `acp-progress-bridge` 通过轮询会话存储、遍历 `state.runs`、解析 child/parent session 关系来推送进度与完成消息。
- Files: `plugins/acp-progress-bridge/index.ts`
- Cause: 当前实现是基于前缀匹配和周期性扫描的 pull 模型；child session 数量越多，扫描、重放和父会话解析成本越高。
- Improvement path: 增加更强的过期清理、按 agent/provider 分片状态、把 discovery 与 delivery 的轮询粒度分开，并为高频运行路径补性能 smoke。

**Role narration can drift away from the actual source-of-truth split:**
- Problem: 口头介绍时很容易把 PM、GSD、coder、bridge 都讲成“都在管理项目”，但代码里它们分属 `.planning/*`、`.pm/*`、Feishu task/doc、`OpenClaw session/state` 这几类不同 truth plane。
- Files: `README.md`, `INSTALL.md`, `skills/pm/SKILL.md`, `skills/coder/SKILL.md`, `.planning/codebase/ARCHITECTURE.md`
- Cause: 当前仓库同时承载产品叙事、执行脚本、bridge 运行态和 planning 文档，若没有统一术语，很快又会回到 oral tradition。
- Improvement path: 维持一套固定说法并在所有 operator docs 里复用，避免把 bridge 讲成 owner、把 GSD 讲成 task backend、或把 `.pm/*.json` 讲成最终业务 truth。

**PM context refresh is backend-bound rather than repo-local only:**
- Problem: `pm context --refresh` 既要扫描仓库，又要读取 task/doc backend 状态，性能与可用性会受外部 Feishu bridge 影响。
- Files: `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_docs.py`, `.pm/current-context.json`
- Cause: 当前 PM 把 repo scan、bootstrap 检测、task/doc index 汇总放在同一条刷新路径里。
- Improvement path: 把 repo-local refresh 与 remote sync 拆开，允许本地只刷新代码与 planning 状态，再按需拉取远端协作信息。

## Fragile Areas

**`pm.py` is thinner than before but still remains an orchestration entrypoint:**
- Files: `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_cli.py`, `skills/pm/scripts/pm_commands.py`, `skills/pm/scripts/pm_runtime.py`
- Why fragile: CLI facade 仍串着配置发现、任务、文档、GSD、workspace 与 coder dispatch，但 GSD materialization 已下沉到 `pm_gsd_materializer.py`，local task backend 已下沉到 `pm_local_backend.py`。
- Safe modification: 新 backend / 新 workflow 继续先进独立模块，再由 `pm.py` 只做 facade 组装，不要把 backend-specific 细节塞回主文件。
- Test coverage: 已有最小 repo-local automated tests，但 CLI facade 仍主要靠 smoke 兜底，没有做到完整参数组合覆盖。

**Coder handoff is now primarily structured, with description parsing only as fallback:**
- Files: `skills/pm/scripts/pm_worker.py`, `skills/pm/scripts/pm.py`, `.pm/coder-context.json`
- Why fragile: `handoff_contract` 现在会优先读取结构化 `gsd_contract`，只有历史任务或外部 backend 没有同步 binding cache 时才回退解析 description。
- Safe modification: 后续 phase metadata 优先写进 `gsd_contract` / `.pm/gsd-task-bindings.json`，不要继续增加新的 description 约定字段。
- Test coverage: 已有针对 structured handoff contract 的单测，历史 description-only 路径仍主要靠兼容性 smoke。

**Host-runtime diagnostics are improved but still operator-driven:**
- Files: `skills/pm/scripts/pm_gsd.py`, `skills/pm/scripts/pm_runtime.py`, `INSTALL.md`, `.planning/codebase/TESTING.md`
- Why fragile: `route-gsd` 现在会暴露 `runtime.ready/issues`，`run_openclaw_agent()` 也会对 `Unknown agent id` 给出更明确提示，但整体仍依赖 operator 按 runbook 解读。
- Safe modification: 继续保持“更早暴露、更清楚报错”的思路，不要急着引入重型诊断系统。
- Test coverage: 当前只有 smoke + 人工验证，没有自动化断言这些诊断文本。

**Bridge contract is Codex-first and host-runtime-sensitive:**
- Files: `plugins/acp-progress-bridge/index.ts`, `INSTALL.md`, `.planning/PROJECT.md`
- Why fragile: 默认契约依赖 `agent:codex:acp:` child prefixes 与 `agent:*:feishu:group:` / `agent:*:main` parent prefixes，宿主 session key 规则或 provider 事件语义变化时容易失效。
- Safe modification: 修改 prefix、completion 或 replay 行为前，先核对 `INSTALL.md` 中的契约说明，并保留一条 Codex-first 的回归路径。
- Test coverage: 仓库内没有对 bridge discovery/delivery/replay 的自动化测试，只能靠日志与手工运行链路验证。

**Windows/install portability still depends on disciplined path abstraction:**
- Files: `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_bridge.py`, `skills/pm/scripts/pm_workspace.py`, `INSTALL.md`
- Why fragile: 虽然运行时发现已经转向 env override -> PATH -> 平台候选目录，但 workspace 模板、OpenClaw home、外部 bridge script 仍可能被用户环境差异放大。
- Safe modification: 新增任何路径相关逻辑时都必须先检查是否已有 env override，并在 `INSTALL.md` 同步写明 Windows 写法与 fallback 顺序。
- Test coverage: 当前只有 smoke 验证，没有 Windows regression 环境。

## Scaling Limits

**Human-in-the-loop collaboration scale is the current ceiling:**
- Current capacity: 适合单项目、小团队、少量并行 child sessions 的协作；仓库内没有显示更高并发下的 benchmark 或限流策略。
- Limit: 当 task/doc 数量、child session 数量、工作区数量同时增长时，`.pm/*.json` 缓存、轮询式 bridge 与人工核对流程都会变得脆弱。
- Scaling path: 引入 repo-local state schema、remote sync 分层、bridge telemetry 指标，以及最小 CI/automation 来替代人工 smoke。

## Dependencies at Risk

**Repo-local workspace templates are now available by default:**
- Status: `skills/pm/templates/workspace` 已覆盖最小模板集，外部模板目录只剩兼容 fallback。
- Impact: 新用户只要 clone 当前仓库，就可以完成 workspace scaffold 所需模板解析。
- Residual risk: 更复杂的组织级模板定制仍要通过 env override 注入。

**Feishu tool bridge is assumed but not abstracted away:**
- Risk: `feishu_task_tasklist`、`feishu_task_task` 等调用名直接散落在 PM 代码里，迁移到别的 task/doc backend 时会牵动多个模块。
- Impact: PM 对外宣称是 task/doc 语义，但实现层仍深度绑定 Feishu bridge。
- Migration plan: 收敛 backend interface，先把 `skills/pm/scripts/pm_tasks.py`、`skills/pm/scripts/pm_docs.py` 包成统一 adapter，再让 `pm.py` 面向抽象层调用。

**GSD task materialization now supports a repo-local backend seam:**
- Status: `materialize-gsd-tasks` 已拆到 `pm_gsd_materializer.py`，并支持 `task.backend = "local"` 写入 `.pm/local-tasks.json`，同时生成 `.pm/gsd-task-bindings.json`。
- Impact: phase plan 现在可以先在 repo-local task backend 落地，再决定是否切换到 Feishu。
- Residual risk: doc sync 与 attachments 仍然是 Feishu-first，task/doc 的全量 backend-neutral 还没完全结束。

## Missing Critical Features

**Automated verification now has a minimal repo-local baseline, but not full CI:**
- Status: 已新增 `tests/` 下的 unittest，覆盖 GSD materializer、structured handoff、runtime diagnostics、workspace template 自包含性。
- Remaining gap: 仍没有 bridge lifecycle 自动化回归，也没有真实 OpenClaw/Feishu 集成 CI。

**Backend-neutral bootstrap is materially improved but not universal yet:**
- Status: `task.backend = "local"` + `doc.backend = "repo"` 已可支撑 repo-local bootstrap、context、coder-context、materialize 路径。
- Remaining gap: doc sync、attachment upload、真实协作文档写回仍然是 Feishu-first。

## Test Coverage Gaps

**PM orchestration flows now have a repo-local baseline but still lack full integration coverage:**
- What's not tested: 真实 Feishu doc/task 写回、attachment 上传、bridge delivery lifecycle、OpenClaw host runtime 全链路。
- Files: `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_context.py`, `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_docs.py`
- Risk: 参数、默认值或远端响应格式变化时，问题仍会在真实集成阶段才暴露。
- Priority: High

**Bridge delivery lifecycle lacks repo-local regression tests:**
- What's not tested: child session discovery、parent session 解析、progress 节流、completion delivery、replay/cleanup 的实际行为。
- Files: `plugins/acp-progress-bridge/index.ts`, `plugins/acp-progress-bridge/openclaw.plugin.json`
- Risk: 多 provider、时序差异或宿主运行时变化会导致静默失败，只能依赖 operator 查看日志定位。
- Priority: High

**Documentation-to-repo consistency is not enforced automatically:**
- What's not tested: `README.md`、`INSTALL.md`、`.planning/codebase/*`、示例配置与真实仓库结构是否持续一致。
- Files: `README.md`, `INSTALL.md`, `.planning/codebase/STRUCTURE.md`, `examples/pm.json.example`, `scripts/export-drawio-png.mjs`
- Risk: 文档先行修复后，如果结构再变化但 mapping 不刷新，后续 agent 会基于过期信息继续规划。
- Priority: Medium

---

*Concerns audit: 2026-04-07*
