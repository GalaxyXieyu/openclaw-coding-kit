# Phase 4: Bridge Reporting Hardening - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

本 phase 的边界是把当前 `acp-progress-bridge` 从“已经能工作、但更多靠代码和口头解释理解”的状态，推进到“配置契约清楚、运行链路可解释、调试方式可落地、扩展边界明确”的状态。

重点是：

- 固化自动汇报链路的运行模型和配置语义
- 强化 progress / completion 回推的可观测性与调试方式
- 评估未来多 provider 扩展所需的抽象边界

本 phase 不负责：

- 现在就把所有非 Codex provider 一次性做到完全同等支持
- 构建完整 GUI 管理界面
- 引入大型测试框架或完整 TypeScript 工程化改造
- 改写 PM/GSD 总体架构边界，那是 Phase 5 的职责

</domain>

<decisions>
## Implementation Decisions

### Product contract
- **D-01:** 自动汇报的核心价值已经锁定，不再讨论“要不要做自动汇报”，而是要让它变成可解释、可调试、可复用的能力。
- **D-02:** 当前主链路仍以 Codex ACP 为第一优先级，Phase 4 先把 Codex 路径打稳，不把多 provider 扩展当成本 phase 的完成条件。
- **D-03:** 自动汇报必须继续保持“bridge 盯子会话 -> 回推内部 bridge update -> 父会话再生成自然语言回复”的两段式模型，不能偷换成 PM/coder 自己直接汇报。
- **D-04:** 本地无 Feishu 工作流仍然必须可行；bridge 是协作增强，不应反向成为本地 PM/GSD/Coder 链路的硬前置。

### Configuration contract
- **D-05:** `parentSessionPrefixes`、`childSessionPrefixes`、`deliverProgress`、`deliverCompletion`、去抖/settle/replay 等配置项，需要形成对外可讲清楚的契约，不再只存在于插件 schema 和源码里。
- **D-06:** 默认配置的适用范围必须明确表达为“Codex ACP 子会话 -> Feishu group 或 main 父会话”，避免用户误以为当前默认值已经覆盖所有 provider / 所有父会话类型。
- **D-07:** Phase 4 要把“哪些配置决定作用域、哪些配置决定节流、哪些配置决定完成回放”分层讲清楚，而不是平铺一串字段说明。

### Observability and debugging
- **D-08:** progress / completion 回推链路必须有清晰的 operator 调试路径，至少能回答：为什么没发现 run、为什么没发 progress、为什么没发 completion、为什么发到了错误父会话。
- **D-09:** 调试能力优先基于当前已有机制增强，例如 session store、stream/transcript 文件、状态 summary、日志信息；优先最小侵入，不引入重量级监控系统。
- **D-10:** 对外文档和仓库内盘点材料都必须能解释 `assistant_tail`、`spawnedBy`、prefix 匹配、settle delay、replay window 这些关键概念。

### Provider expansion boundary
- **D-11:** 本 phase 只评估多 provider 扩展需要什么抽象边界，不承诺在本 phase 完成 Claude / OpenCode / Gemini 全部自动汇报实现。
- **D-12:** 多 provider 支持的讨论必须围绕“session key 约定、prefix 作用域、运行态差异、消息策略”这些抽象边界展开，而不是直接扩表式堆前缀。

### Documentation behavior
- **D-13:** Phase 4 产物必须既能给维护者调试，也能给分享场景解释，不允许只修代码不补说明。
- **D-14:** 自动汇报链路的说明必须明确哪些是“当前已实现并验证的事实”，哪些只是“未来扩展方向”。

### the agent's Discretion
- 调试说明是落在 `README`、`INSTALL`、新文档，还是 `.planning/codebase/*`，由 agent 按最小改动原则决定
- 如果需要增加轻量辅助命令、状态输出或日志增强，由 agent 以最小侵入原则决定
- Phase 4 是否需要补一个专门的 bridge operator guide，由 agent 根据现有文档承载能力决定

</decisions>

<specifics>
## Specific Ideas

- 当前自动汇报链路的真实机制已经明确：
  1. PM / coder 把工作派发成一个 Codex ACP 子会话
  2. bridge 插件扫描 session store，利用 `spawnedBy` 和 prefix 匹配找到父子会话关系
  3. bridge 读取 ACP stream 里的 `progress` / `done`，并结合 transcript 里的 assistant tail
  4. bridge 构造 `[[acp_bridge_update]]` 内部消息回推父会话
  5. 父会话再把内部消息翻译成用户可见的自然语言进度或完成总结

- 当前默认配置已经包含：
  - `childSessionPrefixes = ["agent:codex:acp:"]`
  - `parentSessionPrefixes` 默认偏向 Feishu group
  - `deliverProgress = true`
  - `deliverCompletion = true`
  - `pollIntervalMs / firstProgressDelayMs / progressDebounceMs / settleAfterDoneMs / replayCompletedWithinMs`

- 当前最明显的风险点包括：
  - 插件通过 `process.argv[1]` 推断 CLI entrypoint
  - 默认作用域和真实可用范围很容易被用户误解
  - 没有系统化的 operator 调试说明
  - 多 provider 扩展边界还停留在前缀层面，抽象不够稳定

- 用户已经明确希望能把这套机制讲给别人听，所以 Phase 4 产物必须适合拿去做分享，而不只是补内部注释。

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product intent and requirements
- `.planning/PROJECT.md` — 产品定位、双角色协作逻辑、共享工作区闭环目标
- `.planning/PROJECT-BACKGROUND.md` — 自动汇报为什么存在，以及它对飞书工作区闭环的重要性
- `.planning/REQUIREMENTS.md` — Phase 4 对应 `BRDG-01, BRDG-02, BRDG-03, BRDG-04`
- `.planning/ROADMAP.md` — Phase 4 目标、success criteria 和预期 plans
- `.planning/STATE.md` — 当前阶段位置和剩余 blocker

### Prior phase outputs
- `.planning/phases/03-install-and-verification-loop/03-01-SUMMARY.md` — 文档/示例/skill 契约已统一
- `.planning/phases/03-install-and-verification-loop/03-02-SUMMARY.md` — 本地 bootstrap / diagnostics 链路已清楚
- `.planning/phases/03-install-and-verification-loop/03-03-SUMMARY.md` — 本地 smoke baseline 与风险盘点已建立

### Bridge implementation surfaces
- `plugins/acp-progress-bridge/index.ts` — 插件核心实现与当前回推逻辑
- `plugins/acp-progress-bridge/openclaw.plugin.json` — 对外配置 schema 与默认值
- `examples/openclaw.json5.snippets.md` — 当前对外暴露的 bridge 配置片段
- `INSTALL.md` — 当前安装与增强链路说明

### Architecture and integration docs
- `.planning/codebase/INTEGRATIONS.md` — 当前 delivery chain、prefix 作用域与集成风险
- `.planning/codebase/ARCHITECTURE.md` — progress bridge flow 与当前架构边界
- `.planning/codebase/CONCERNS.md` — 当前关于 bridge 宿主假设和自动化不足的风险
- `.planning/codebase/TESTING.md` — 当前哪些验证仍未覆盖到真实 bridge 集成

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `openclaw.plugin.json` 已经把核心配置面暴露出来，适合作为“配置契约”整理基础
- `index.ts` 已有状态扫描、消息构造、CLI 回推和状态 summary 等核心逻辑
- `INTEGRATIONS.md` / `ARCHITECTURE.md` 已经沉淀了当前 delivery chain 的一版解释

### Established Patterns
- 当前桥接逻辑以 prefix 匹配 + session store / stream / transcript 读取为核心
- progress 和 completion 采用不同的消息模板和不同的 deliver / settle 策略
- 插件通过内部 `[[acp_bridge_update]]` 消息与父会话隔离实现细节和用户可见回复

### Integration Points
- Phase 4 会直接承接 Phase 3 建立好的安装文档和 smoke baseline
- Phase 5 会依赖本 phase 对 PM / bridge / provider 边界的收口结果
- 用户分享里的“自动汇报原理”会直接依赖本 phase 的产物质量

</code_context>

<deferred>
## Deferred Ideas

- 为所有非 Codex provider 完成正式自动汇报支持
- 为 bridge 建立完整 TypeScript build/typecheck 和 CI
- 构建 GUI / dashboard 级别的 bridge 观测界面
- 重写插件与宿主之间的调用模型，彻底摆脱当前 CLI entrypoint 假设

</deferred>

---

*Phase: 04-bridge-reporting-hardening*
*Context gathered: 2026-04-07*
