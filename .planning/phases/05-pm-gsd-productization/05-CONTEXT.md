# Phase 5: PM-GSD Productization - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

本 phase 的边界是把当前仓库里已经存在的 `PM / GSD / coder / bridge` 协作链路，从“能工作但职责边界更多靠人理解”的状态，推进到“职责、路由、写回责任、最小质量基线都清楚”的状态。

重点是：

- 明确 PM、GSD、coder、bridge 各自的责任边界和 source-of-truth 边界
- 收口 `pm.py` 当前承载过多职责的问题，明确最小可执行的拆分 seam
- 让 PM -> GSD -> coder/acp -> bridge 的链路可以被解释成稳定产品，而不是一串偶然拼接的脚本
- 为后续维护建立最小质量基线，优先覆盖路由、上下文、路径/配置和 planning handoff

本 phase 不负责：

- 现在就把 Feishu 完全抽象成 backend-neutral
- 现在就重写整套 PM 实现或彻底拆包
- 为所有 provider 完成完整 bridge 等级自动汇报支持
- 引入完整 CI、完整 TypeScript 工程化或大型测试框架

</domain>

<decisions>
## Implementation Decisions

### Product and role contract
- **D-01:** PM 继续是 tracked work 的前门，负责任务/文档同步、上下文缓存、路由判断和结果写回；不要让 GSD 绕过 PM 成为另一个事实源。
- **D-02:** GSD 的职责锁定为 roadmap/phase 级 context、planning、execution orchestration；它服务 phase 流程，不直接替代 PM 的任务系统。
- **D-03:** coder 的职责锁定为 canonical execution worker，必须先读 PM context，再读 GSD plan/required reads；coder 不是需求澄清器，也不是 phase planner。
- **D-04:** bridge 的职责锁定为异步 progress/completion relay；它不拥有 task state、文档 state 或 phase state，也不直接替 PM 做 write-back。
- **D-05:** 用户可见的产品叙事应统一为 “PM front door, GSD planning backend, coder execution worker, bridge progress relay”。

### Source-of-truth boundary
- **D-06:** `.planning/*` 是 phase/roadmap truth，`.pm/*` 是 repo-local execution cache，Feishu task/doc 是协作业务事实，OpenClaw session/state 是运行态事实；这四层边界必须在文档和代码里统一表达。
- **D-07:** `route-gsd`、`plan-phase`、`materialize-gsd-tasks` 是当前 PM 与 GSD 的关键桥点，必须被视为正式产品界面而不是临时 helper。
- **D-08:** bridge 只消费 OpenClaw session/state 并回推父会话，它不应被混写成 PM/GSD 路由器。

### Refactor posture
- **D-09:** Phase 5 优先做 seam carving 和 contract hardening，不做大爆炸重写。
- **D-10:** `pm.py` 可以继续保留为 CLI 入口，但应把 GSD routing/planning、task materialization、execution handoff 这些能力收得更薄、更容易单测。
- **D-11:** 任何重构都不能破坏 Phase 3 已建立的 local-first bootstrap 和 Windows 兼容语义。

### Quality baseline
- **D-12:** 最小质量基线优先覆盖 path/config discovery、GSD routing、phase plan indexing、PM->coder handoff，而不是一开始就追求全链路 E2E。
- **D-13:** 当前仓库允许继续使用 smoke check + fixture-style verification 的组合，不强行上完整测试体系。
- **D-14:** 对外分享要能诚实说明“哪些能力已经产品化、哪些仍需要真实 OpenClaw/Feishu runtime 回归”。

### the agent's Discretion
- 是否新增独立的 adapter/service 文件，还是先在现有模块内收 seam，由后续 planner 按最小改动原则决定
- 测试基线是新增轻量单测、fixture、还是更强的 smoke harness，由后续 planner 结合当前仓库结构决定
- Phase 5 的 operator/product docs 落在 `README`、`INSTALL` 还是 `.planning/codebase/*`，由 agent 按信息密度决定

</decisions>

<specifics>
## Specific Ideas

- 当前已经观察到的关键代码事实：
  1. `route_gsd_work()` 已经把 PM 和 GSD 的阶段路由固化成 `discuss-phase -> plan-phase -> materialize-tasks -> verify-phase`，这是 Phase 5 的天然产品 seam。
  2. `execute_gsd_plan_phase()` 仍通过 `run_openclaw_agent()` 调宿主 agent，且默认 `coder.agent_id` 是 `codex`；如果宿主没有这个 agent，就会像本次一样直接失败。
  3. `cmd_plan_phase()` 现在同时承担 phase planning、doc sync、task materialization、progress sync，多职责聚在一起。
  4. coder skill 已经要求先读 `pm.json`、`.pm/coder-context.json` 和 GSD plan path，这说明 handoff contract 已经有雏形，但还不够系统化。
  5. bridge 在 Phase 4 已经收口为内部 relay，不应在 Phase 5 再被混写成 PM/GSD 的 state owner。

- 当前最明显的架构问题：
  - `pm.py` 仍是过重总控入口
  - PM 与 GSD 仍主要靠命令和描述字段手工桥接
  - `pm plan-phase` 依赖宿主 OpenClaw agent 配置，导致本地 planning 不是完全自包含
  - 质量基线仍偏 smoke/doc-driven，缺少对 GSD routing 与 plan materialization 的自动化验证

- 本 phase 应更关注“契约和 seam”，而不是继续扩 provider 或补 Feishu 细节。

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product intent and requirements
- `.planning/PROJECT.md` — 当前产品定位、双角色协作模型、核心约束
- `.planning/REQUIREMENTS.md` — Phase 5 对应 `FLOW-02, FLOW-03, QUAL-02, QUAL-03, COLL-03`
- `.planning/ROADMAP.md` — Phase 5 目标、success criteria 和既定 3 plans
- `.planning/STATE.md` — 当前 phase 状态与已知 blockers

### Prior phase outputs
- `.planning/phases/04-bridge-reporting-hardening/04-01-SUMMARY.md` — bridge contract 已清楚
- `.planning/phases/04-bridge-reporting-hardening/04-02-SUMMARY.md` — bridge observability 已补齐
- `.planning/phases/04-bridge-reporting-hardening/04-03-SUMMARY.md` — Codex-first 与 provider boundary 已收口

### PM/GSD/coder surfaces
- `skills/pm/SKILL.md` — PM front door 语义
- `skills/coder/SKILL.md` — coder canonical execution intake
- `skills/pm/scripts/pm.py` — PM 总控入口、route-gsd、plan-phase、materialize-gsd-tasks
- `skills/pm/scripts/pm_commands.py` — PM CLI command wiring
- `skills/pm/scripts/pm_gsd.py` — GSD asset detection、phase lookup、plan indexing
- `skills/pm/scripts/pm_worker.py` — PM -> coder handoff message contract
- `skills/pm/scripts/pm_runtime.py` — OpenClaw/Codex runtime invocation

### Architecture and risk docs
- `.planning/codebase/ARCHITECTURE.md` — 当前子系统边界与 refactor seam
- `.planning/codebase/INTEGRATIONS.md` — PM、GSD、bridge、OpenClaw、Feishu 集成关系
- `.planning/codebase/CONCERNS.md` — 当前产品化与架构风险
- `.planning/codebase/TESTING.md` — 当前 smoke baseline 与缺口
- `.planning/codebase/STRUCTURE.md` — 当前目录结构与职责分布

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `route_gsd_work()` 已经把阶段路由逻辑集中在一个 seam 里
- `pm_gsd.py` 已经沉淀了 phase lookup / plan index / progress snapshot 的 helper
- `pm_worker.py` 已经提供了 coder handoff message contract 的基础模板
- `.planning/codebase/*` 已经有一轮架构、风险、测试盘点，可以直接承接

### Established Patterns
- PM front door + downstream GSD backend 是当前 repo 的既定方向
- local-first bootstrap 与 optional Feishu integration 仍然是全仓库非协商约束
- bridge 保持内部消息 relay，两段式模型不回退

### Integration Points
- Phase 5 planning 需要直接承接当前 `pm route-gsd` / `pm plan-phase` / `pm materialize-gsd-tasks` 的行为
- Phase 5 execute 结果会决定后续这套 kit 是否能被讲成真正的产品，而不是工作流拼接
- 本 phase 也会影响以后真实 Windows 回归和模板资产分发的可维护性

</code_context>

<deferred>
## Deferred Ideas

- 完全 backend-neutral 的 PM/task/doc 适配层
- 完整 TypeScript build/typecheck / CI 体系
- 独立的 operator dashboard / GUI
- 所有 provider 的统一 bridge capability layer 实现
- 完整 E2E harness 覆盖 OpenClaw + Feishu 真环境

</deferred>

---

*Phase: 05-pm-gsd-productization*
*Context gathered: 2026-04-07*
