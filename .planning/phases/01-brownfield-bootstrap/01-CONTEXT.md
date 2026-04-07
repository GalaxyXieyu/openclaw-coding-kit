# Phase 1: Brownfield Bootstrap - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

本 phase 的边界是把当前 brownfield 仓库补齐为一个正式的 GSD/PM 项目骨架，并确认后续 planner/executor 不再需要猜测“这个仓库是什么、为什么这样设计、下一步该往哪里走”。它不负责修复跨平台代码、不负责大规模重构、也不负责扩展新 provider，只负责把项目定义、需求、路线图、状态和 phase 入口稳定下来。

</domain>

<decisions>
## Implementation Decisions

### Brownfield framing
- **D-01:** 这个仓库必须按 brownfield 项目处理，先基于现有代码和真实历史背景建模，不能按 greenfield 假设重写
- **D-02:** `.planning/codebase/*` 和 `.planning/PROJECT-BACKGROUND.md` 是本 phase 的核心输入，不再重新发明项目背景

### Product framing
- **D-03:** 这个仓库不是玩具 demo 工具集，而是面向复杂项目的 AI 协作开发架构产品化载体
- **D-04:** 核心模型固定为 `PM + Developer + 共享飞书工作区 + ACPX + progress bridge`

### Scope boundary
- **D-05:** 本 phase 只解决“项目定义和 planning readiness”，不提前进入路径兼容、安装修复、架构瘦身的执行细节
- **D-06:** Windows 兼容是高优先级目标，但属于后续 phase 的执行主题，不在本 phase 直接落代码

### Reporting and source of truth
- **D-07:** 自动汇报机制必须被视为核心闭环，而不是附属功能，因为它决定多会话/多群沟通是否能回落到统一事实源
- **D-08:** 飞书文档和 tasklist 是共享事实源，PM/GSD/coder/bridge 的规划都要围绕这一点展开

### the agent's Discretion
- Phase 1 计划文件拆成 1 个还是多个，只要能保持 phase 边界清晰即可
- bootstrap 校验步骤的命令组织方式、文档顺序、验证语句可由 agent 自主决定

</decisions>

<specifics>
## Specific Ideas

- 用户明确强调这套模式已经用于包含宠物展示、后台管理、支付、新手指引、CI/CD 的复杂项目
- 用户明确强调当前要优先考虑 Windows 用户接入，不希望后续路径问题返工
- 用户明确强调“自动汇报”不是 PM 自报，而是 bridge 观察子会话后回推给父会话
- 用户希望多个群可以沟通不同内容，但最终业务内容和排期都能规范沉淀到飞书

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project definition
- `.planning/PROJECT.md` — 当前项目定义、核心价值、约束和关键决策
- `.planning/REQUIREMENTS.md` — v1/v2 requirements 和 phase traceability
- `.planning/ROADMAP.md` — Phase 1-5 的正式路线图和成功标准
- `.planning/STATE.md` — 当前项目位置和 blockers 摘要

### Architecture and motivation
- `.planning/PROJECT-BACKGROUND.md` — 这套 PM-coder-ACP-bridge 架构的真实痛点、动机和产品定位
- `.planning/codebase/ARCHITECTURE.md` — 当前代码的模块分层和数据流
- `.planning/codebase/INTEGRATIONS.md` — OpenClaw / Codex / Feishu / GSD / bridge 集成链路
- `.planning/codebase/CONCERNS.md` — 路径硬编码、安装缺口、架构债务等核心问题

### User-facing repo surface
- `README.md` — 当前对外项目定位和入口文档
- `INSTALL.md` — 当前安装说明
- `examples/openclaw.json5.snippets.md` — OpenClaw + bridge 配置示例
- `examples/pm.json.example` — PM 配置示例

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/pm/scripts/pm_scan.py`：已经能识别 brownfield/bootstrap 状态和 GSD 资产
- `skills/pm/scripts/pm_gsd.py`：已经能探测 `.planning` 文档与 phase 信息
- `plugins/acp-progress-bridge/index.ts`：已经实现自动汇报主链路，可作为后续 phase 的真实能力基础

### Established Patterns
- `.planning/codebase/*` 已经形成 GSD 风格的 codebase map，可直接作为 planning 参考资料
- 仓库采用 markdown + JSON + Python CLI 的工作流驱动模式，而不是 Web app 模式
- PM 侧强依赖 Feishu/OpenClaw，不能忽略外部系统边界

### Integration Points
- 后续 phase planning 会继续依赖 `pm route-gsd`、`gsd-tools init plan-phase` 等探测逻辑
- Phase 2 需要落到 `pm_runtime.py`、`pm_auth.py`、`pm_io.py`、`observe_acp_session.py` 等路径相关文件
- Phase 3/4 会涉及 `README.md`、`INSTALL.md`、`examples/*` 和 `plugins/acp-progress-bridge/index.ts`

</code_context>

<deferred>
## Deferred Ideas

- 非 Codex provider 的自动汇报扩展
- GUI/管理台类产品表层
- PM 与 GSD 的更深度自动串联
- 更大规模的架构拆分与测试体系建设

</deferred>

---

*Phase: 01-brownfield-bootstrap*
*Context gathered: 2026-04-07*
