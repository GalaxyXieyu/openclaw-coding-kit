# Roadmap: OpenClaw PM Coder Kit

## Overview

这条 roadmap 的目标不是重写现有仓库，而是在现有 brownfield 基础上，把已经验证过生产力的 `PM + Developer + ACPX + progress bridge + 飞书工作区` 协作模式，逐步产品化为一个更容易安装、更容易复制、更容易跨平台使用的复杂项目 AI 协作套件。

## Phases

- [x] **Phase 1: Brownfield Bootstrap** - 补齐 GSD/PM bootstrap 资产，让仓库拥有正式项目骨架和共享语言
- [x] **Phase 2: Cross-Platform Runtime** - 消除路径硬编码和平台耦合，优先补强 Windows/macOS/Linux 可移植性
- [x] **Phase 3: Install And Verification Loop** - 让安装、初始化、自检和示例配置形成真实闭环
- [x] **Phase 4: Bridge Reporting Hardening** - 稳定自动汇报链路，沉淀多会话/多群协作的可解释机制
- [ ] **Phase 5: PM-GSD Productization** - 收敛 PM/GSD 边界、补最小测试闭环，为后续 phase execution 提供长期可维护基础

## Phase Details

### Phase 1: Brownfield Bootstrap
**Goal**: 把当前仓库从“只有代码和零散文档”提升到“有正式项目定义、需求、路线图和状态文件”的可规划状态
**Depends on**: Nothing (first phase)
**Requirements**: [COLL-01, COLL-02, FLOW-01, BOOT-01, BOOT-02]
**Success Criteria** (what must be TRUE):
  1. `.planning/PROJECT.md`、`REQUIREMENTS.md`、`ROADMAP.md`、`STATE.md` 与 `.planning/codebase/*.md` 都存在并能表达当前项目真实目标
  2. `.pm/doc-index.json`、`.pm/current-context.json`、`.pm/bootstrap.json` 能证明 task/doc 绑定与 bootstrap 缓存已经就位
  3. 当前 brownfield 仓库的价值、痛点和架构动机已被清晰记录，后续 planner 不需要再猜
  4. phase 规划入口已经建立，下一步可以直接进入 `plan-phase`
**Plans**: 1 plan

Plans:
- [x] 01-01: 校验 bootstrap 资产、刷新 brownfield codebase map，并把仓库推进到正式 planning-ready 状态

Bootstrap evidence:
- `.planning/codebase/STACK.md`、`.planning/codebase/INTEGRATIONS.md`、`.planning/codebase/ARCHITECTURE.md`、`.planning/codebase/STRUCTURE.md`、`.planning/codebase/CONVENTIONS.md`、`.planning/codebase/TESTING.md`、`.planning/codebase/CONCERNS.md`
- `.pm/doc-index.json`、`.pm/current-context.json`、`.pm/bootstrap.json`

### Phase 2: Cross-Platform Runtime
**Goal**: 让关键运行链路不再依赖作者本机路径，优先为 Windows 用户打通使用路径
**Depends on**: Phase 1
**Requirements**: [PLAT-01, PLAT-02, PLAT-03]
**Success Criteria** (what must be TRUE):
  1. OpenClaw/Codex/bridge/state 相关路径发现支持显式配置和平台差异
  2. Windows 用户可以从文档和示例中明确知道该替换哪些路径、怎么验证
  3. 仓库中的关键平台假设被集中识别并有明确修复边界
**Plans**: 3 plans

Plans:
- [x] 02-01: 盘点并重构运行时路径发现策略
- [x] 02-02: 处理 Windows/macOS/Linux 的状态目录与命令发现差异
- [x] 02-03: 对齐示例配置和文档中的跨平台说明

### Phase 3: Install And Verification Loop
**Goal**: 让安装、初始化、文档、示例配置和最小自检构成一个可信闭环
**Depends on**: Phase 2
**Requirements**: [BOOT-03, BOOT-04, QUAL-01]
**Success Criteria** (what must be TRUE):
  1. README、INSTALL、examples 与实际命令和代码行为一致
  2. 用户可以完成最小安装并明确知道如何初始化 PM/GSD
  3. 仓库至少具备一组不依赖真实线上资源的 smoke checks
**Plans**: 3 plans

Plans:
- [x] 03-01: 修正文档与文件名/命令/配置不一致问题
- [x] 03-02: 补全安装后初始化与诊断步骤
- [x] 03-03: 增加最小 smoke check 和验证说明

### Phase 4: Bridge Reporting Hardening
**Goal**: 稳定 Codex 自动汇报主链路，并把它沉淀为可复用的协作能力说明
**Depends on**: Phase 3
**Requirements**: [BRDG-01, BRDG-02, BRDG-03, BRDG-04]
**Success Criteria** (what must be TRUE):
  1. progress / completion 自动回推链路对外可解释、对内可调试
  2. child session 到 parent session 的关联规则和配置边界清晰
  3. 自动汇报不会导致父会话上下文失控，同时能给用户足够的进度透明度
**Plans**: 3 plans

Plans:
- [x] 04-01: 固化 bridge 运行链路与配置契约
- [x] 04-02: 强化 progress / completion 回推的可观测性与调试方式
- [x] 04-03: 评估多 provider 扩展所需的抽象边界

### Phase 5: PM-GSD Productization
**Goal**: 让 PM、GSD、coder、bridge 的职责边界更清晰，并为长期维护建立最小质量基础
**Depends on**: Phase 4
**Requirements**: [FLOW-02, FLOW-03, QUAL-02, QUAL-03, COLL-03]
**Success Criteria** (what must be TRUE):
  1. PM 与 GSD 的衔接方式清晰，不再让任务事实和规划事实混乱
  2. `pm.py` 等关键总控模块的后续拆分路径明确
  3. 多群沟通、多角色执行、多文档沉淀可以被解释成一个稳定产品，而不是偶然可用的组合
**Plans**: 3 plans

Plans:
- [x] 05-01: 明确 PM/GSD/bridge/coder 各自边界和后续拆分策略
- [x] 05-02: 收敛关键架构债务与维护风险
- [x] 05-03: 形成面向后续版本的产品化基线

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Brownfield Bootstrap | 1/1 | Complete | 2026-04-07 |
| 2. Cross-Platform Runtime | 3/3 | Complete | 2026-04-07 |
| 3. Install And Verification Loop | 3/3 | Complete | 2026-04-07 |
| 4. Bridge Reporting Hardening | 3/3 | Complete | 2026-04-07 |
| 5. PM-GSD Productization | 3/3 | Complete | 2026-04-07 |
