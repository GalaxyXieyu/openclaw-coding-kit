# Phase 2: Cross-Platform Runtime - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

本 phase 的边界是把当前运行时路径发现、状态目录发现和平台相关假设从“作者本机可用”推进到“macOS / Linux / Windows 有清晰接入路径”的状态。重点是路径与平台兼容，不负责完整安装闭环、不负责 bridge 功能扩展、不负责大规模架构拆分。

</domain>

<decisions>
## Implementation Decisions

### Path discovery strategy
- **D-01:** 关键运行时路径统一采用“显式配置/环境变量优先 -> PATH/系统发现 -> 少量平台候选兜底”的顺序
- **D-02:** 不再把具体 Node 版本目录、作者本机目录结构或单平台目录作为默认主路径
- **D-03:** Windows 兼容必须作为本 phase 的一等约束，而不是文档附注

### Scope boundary
- **D-04:** 本 phase 只处理跨平台运行时与路径发现，不承担 README/INSTALL 全量修复；文档对齐只做与路径/平台直接相关的部分
- **D-05:** workspace 模板目录等更大的产品化问题可以暴露和收敛，但不在本 phase 内彻底解决所有模板资产问题

### State model
- **D-06:** repo-local 状态和 user-global 状态必须被明确区分，不能继续让用户猜测 `.pm`、`.planning`、`~/.openclaw`、`~/.codex` 分别承担什么职责
- **D-07:** 路径发现逻辑应尽量收敛为可复用 helper，而不是继续分散在多个脚本里各自猜路径

### Compatibility expectations
- **D-08:** 文档和示例里涉及路径时，要允许用户理解 Windows 形式路径、环境变量和常见 shell 差异
- **D-09:** 当前主链路仍以 Codex + OpenClaw + Feishu 为核心，不因为平台兼容而改变产品核心模型

### the agent's Discretion
- 是否引入新的集中式 path/platform helper 模块，由 agent 根据最小侵入原则决定
- Windows 具体候选目录、环境变量命名和 fallback 顺序，可由 agent 基于现有代码风格做最合理设计

</decisions>

<specifics>
## Specific Ideas

- 用户明确要求后续 Windows 用户也需要使用这套系统，所以要提早考虑路径和安装设计
- 当前已识别的关键痛点包括：二进制路径硬编码、主目录依赖、状态目录不一致、模板路径依赖仓库外资源
- 当前产品目标不是只让本地作者环境可用，而是让这套复杂项目协作模式更容易复制

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product intent and constraints
- `.planning/PROJECT.md` — 项目核心价值、约束和 Windows 兼容优先级
- `.planning/REQUIREMENTS.md` — Phase 2 对应 `PLAT-01, PLAT-02, PLAT-03`
- `.planning/ROADMAP.md` — Phase 2 目标、success criteria 和预期 plans
- `.planning/STATE.md` — 当前 blockers 与项目位置
- `.planning/PROJECT-BACKGROUND.md` — 这套协作模式为什么需要被产品化

### Existing codebase analysis
- `.planning/codebase/CONCERNS.md` — 当前路径硬编码与可移植性问题总表
- `.planning/codebase/ARCHITECTURE.md` — 现有模块分层与重构 seams
- `.planning/codebase/INTEGRATIONS.md` — OpenClaw / Codex / Feishu / GSD / bridge 的运行链路
- `.planning/codebase/STACK.md` — 技术栈与运行环境概览

### Key implementation surfaces
- `skills/pm/scripts/pm_runtime.py` — OpenClaw/Codex CLI 路径发现
- `skills/pm/scripts/pm_auth.py` — OpenClaw 配置定位
- `skills/pm/scripts/pm_config.py` — PM 配置与 OpenClaw config 发现
- `skills/pm/scripts/pm_io.py` — PM state 目录
- `skills/pm/scripts/pm.py` — bridge 脚本候选路径与 workspace root 解析
- `skills/pm/scripts/pm_gsd.py` — GSD tools 路径发现
- `skills/coder/scripts/observe_acp_session.py` — OpenClaw state 读取路径
- `skills/pm/scripts/pm_workspace.py` — workspace/template 根路径与默认 workspace 推导
- `examples/openclaw.json5.snippets.md` — 当前路径示例和插件配置
- `INSTALL.md` — 当前面向用户的安装说明

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pm_config.py` 已经有配置候选、环境变量与 repo-root 解析的基础逻辑，可以作为跨平台发现策略的起点
- `pm_runtime.py` 已经集中处理 OpenClaw/Codex CLI 调用，是运行时路径治理的首要入口
- `observe_acp_session.py` 和 `acp-progress-bridge` 清楚展示了当前对 OpenClaw state layout 的假设

### Established Patterns
- Python 侧偏向标准库与 `Path` 风格处理路径
- 错误处理偏 `SystemExit` + 短错误消息
- 仓库喜欢通过 examples 和 markdown 文档暴露配置契约

### Integration Points
- Phase 3 的安装闭环会依赖本 phase 的路径与平台设计结果
- bridge 自动汇报链路依赖 OpenClaw state 布局，不能随意改动其契约
- PM/GSD route 探测依赖 `.planning` 已存在，因此本 phase 不需要再处理 bootstrap

</code_context>

<deferred>
## Deferred Ideas

- 把 workspace 模板资产彻底收进仓库
- provider 无关的统一路径抽象层
- 完整 Windows 专项安装指南与诊断脚本
- PM 总控模块的更大规模拆分

</deferred>

---

*Phase: 02-cross-platform-runtime*
*Context gathered: 2026-04-07*
