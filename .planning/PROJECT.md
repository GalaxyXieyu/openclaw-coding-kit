# OpenClaw PM Coder Kit

## What This Is

这是一个面向复杂项目交付的 AI 协作开发套件。它把 `PM + Developer` 双角色协作、飞书共享文档/任务事实源、ACPX 执行链路、以及 Codex 本地编码能力组合成一套可复用的工作模式，让业务沟通和代码实现可以并行推进而不让上下文失控。

当前这个仓库既是这套模式的实现载体，也是后续要产品化、安装化、跨平台化的交付物。它不是单纯的脚本集合，而是对“复杂项目如何用 AI 稳定协作”这件事的工程化落地。

## Core Value

让 PM 侧沟通上下文和 Developer 侧编码执行始终共享同一套项目事实，并能把进度与结果稳定回流到飞书工作区，而不让主会话上下文爆炸。

## Requirements

### Validated

- ✓ PM 可以作为项目协作入口，承载任务、上下文、文档同步与执行分发 — existing
- ✓ Developer/Coder 角色可以通过 ACP/Codex 承接实际编码执行 — existing
- ✓ `acp-progress-bridge` 可以把 Codex ACP 子会话的进度和完成结果回推到父会话 — existing
- ✓ 仓库已提供基本安装说明、示例配置和插件/skills 目录结构 — existing
- ✓ brownfield codebase map 与 doc index 已落盘，可直接从 `.planning/codebase/*.md` 与 `.pm/doc-index.json` 进入上下文 — existing
- ✓ 这套模式已经在包含展示、后台、支付、引导、CI/CD 的复杂项目中验证过生产力 — prior real-world usage

### Active

- [ ] 让这套 kit 在 macOS / Linux / Windows 上都能稳定安装和运行
- [ ] 让 `pm -> gsd -> coder/acp -> bridge -> 飞书工作区` 的链路形成清晰、可复用的 bootstrap 流程
- [ ] 消除明显的路径硬编码和本机环境耦合，降低迁移成本
- [ ] 让安装文档、示例配置、代码行为和真实工作流保持一致
- [ ] 让多群并行沟通、多角色协作、多子会话执行后的信息都能规范回落到共享文档与任务清单
- [ ] 为后续 phase planning / execute-phase 提供可维护的架构边界和最小验证闭环

### Out of Scope

- 用这个仓库替代 OpenClaw 本体 — 这个仓库是协作模式增强层，不是平台替代品
- 在当前阶段同时把所有非 Codex provider 的自动汇报做到完全同等支持 — 先把 Codex 主链路打稳，再扩其他 provider
- 现在就构建独立 Web 管理台或 GUI — 当前优先级是工作流稳定性、安装闭环和跨平台能力
- 为简单 demo 场景做过度简化版本 — 当前目标是复杂项目可持续协作，不是玩具模板

## Context

这套架构的直接背景是复杂需求开发里常见的上下文污染、会话管理混乱和沟通损耗问题。单个 AI 会话在需求、代码、测试、进度混杂时容易失真，而不同 AI 工具又各有擅长方向: PM/龙虾更适合业务理解和沟通，Codex 更适合本地高质量编码执行，但原生工具之间并不自然协作。

这个仓库试图把传统“业务 -> PM -> 开发”的信息损耗链路压缩成一个共享事实源驱动的双角色模型。共享飞书工作区承载文档和任务，PM 负责理解需求和维护上下文，Developer 负责对着稳定任务直接编码，ACPX 负责串联执行链路，`acp-progress-bridge` 负责把子会话的进度和结果压缩回父会话，使进度、变更、业务沟通和代码交付始终落在同一套事实体系中。

当前代码库已经实现了基础形态，但也暴露出产品化问题: 路径硬编码、平台耦合、安装步骤不完整、PM 总入口过重、测试与验证不足。这也是当前 roadmap 的主要来源。

## Constraints

- **Compatibility**: 需要考虑 Windows 用户接入 — 这会直接约束路径发现、命令调用、安装文档和示例配置写法
- **Platform Dependency**: 当前依赖 OpenClaw、ACPX、Codex CLI、飞书渠道配置 — 这些外部前提决定了 bootstrap 不能假设“纯 repo 内可运行”
- **Shared Source of Truth**: 文档与任务必须能回落到飞书工作区 — 这是这套架构存在的核心价值，不能退化为纯本地文件流
- **Context Discipline**: 主会话不能承接所有执行细节 — 否则这套架构会失去控制上下文污染的意义
- **Brownfield Reality**: 当前仓库已有真实实现和历史包袱 — roadmap 必须基于现状修整，而不是按理想化 greenfield 重写
- **Small-Team Pragmatism**: 目标用户包含一人公司和小团队 — 方案必须可落地、低摩擦、可复制，不能依赖重型流程

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 采用 `PM + Developer` 双角色 | 分离业务沟通和代码执行，减少需求传递损耗 | ✓ Good |
| 以飞书文档 + tasklist 作为共享事实源 | 需要让客户、PM、Developer 对项目状态保持一致 | ✓ Good |
| 通过 ACPX 串联执行链路 | 需要把 PM 侧任务稳定交给本地 coder 执行 | ✓ Good |
| 用 `acp-progress-bridge` 压缩回传子会话状态 | 需要让外部会话知道进度，但不暴露全部执行细节 | ✓ Good |
| 先按 brownfield 方式做 codebase map 再 bootstrap | 当前仓库已有实现，不适合空想式初始化 | ✓ Good |
| bootstrap 证据固定为 `.planning` + `.pm` 双轨快照 | 需要让 repo 内既能看到长文档，也能看到 task/doc 绑定与 handoff 缓存 | ✓ Good |
| 当前阶段优先打稳 Codex 主链路 | Codex 是当前本地执行主力，先把主链路产品化 | — Pending |
| 将 Windows 兼容视为近期核心目标 | 路径/安装设计如果不提早处理，后续成本更高 | — Pending |

## Brownfield Snapshot (2026-04-07)

本轮 bootstrap 映射以当前仓库真实结构为准，已经把 task/doc 绑定、repo-local 上下文缓存和代码入口统一到可检索的本地证据里。后续 planner / coder 不需要再从零猜测项目形状。

- 任务与文档绑定配置入口在 `pm.json`，对应 doc 索引缓存落在 `.pm/doc-index.json`。
- 当前 PM / coder 主入口分别是 `skills/pm/scripts/pm.py` 与 `skills/coder/scripts/observe_acp_session.py`。
- 自动汇报插件主入口是 `plugins/acp-progress-bridge/index.ts`，结构图源文件与导出图落在 `diagrams/pm-coder-bridge-architecture.drawio*`。
- 当前 brownfield codebase map 已覆盖 `STACK.md`、`INTEGRATIONS.md`、`ARCHITECTURE.md`、`STRUCTURE.md`、`CONVENTIONS.md`、`TESTING.md`、`CONCERNS.md`。
- 根级 `scripts/export-drawio-png.mjs` 是独立工具脚本，不属于 PM 包内部模块。

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after brownfield bootstrap initialization*
