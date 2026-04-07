# Requirements: OpenClaw PM Coder Kit

**Defined:** 2026-04-07
**Core Value:** 让 PM 侧沟通上下文和 Developer 侧编码执行始终共享同一套项目事实，并能把进度与结果稳定回流到飞书工作区，而不让主会话上下文爆炸

## v1 Requirements

### Collaboration Foundation

- [ ] **COLL-01**: PM 角色可以基于共享飞书文档与任务清单，稳定表达当前项目上下文、需求和进度
- [ ] **COLL-02**: Developer 角色可以读取与执行同一套项目事实，而不是依赖散落在本地会话里的上下文
- [ ] **COLL-03**: 多个群/会话中的沟通内容最终可以回落到统一的业务文档和 tasklist 流程

### Platform Compatibility

- [ ] **PLAT-01**: 仓库在 macOS、Linux、Windows 上都具备明确且可执行的安装路径
- [ ] **PLAT-02**: OpenClaw CLI、Codex CLI、bridge、state 路径发现逻辑不依赖作者本机固定路径
- [ ] **PLAT-03**: 示例配置中的路径写法和说明对 Windows 用户是可理解、可替换、可验证的

### Bootstrap And Installation

- [ ] **BOOT-01**: 用户拿到仓库后可以按文档完成最小安装，并知道后续如何初始化 PM/GSD
- [ ] **BOOT-02**: 安装文档覆盖 `pm init`、中文项目名、前置依赖检查、OpenClaw 配置与插件启用
- [ ] **BOOT-03**: 文档、示例配置、代码行为之间不存在明显矛盾或失效引用
- [ ] **BOOT-04**: 仓库可以明确说明哪些运行态文件属于 repo-local，哪些属于 user-global

### Execution Bridge

- [ ] **BRDG-01**: Codex ACP 子会话的进度可以自动回推到父会话
- [ ] **BRDG-02**: Codex ACP 子会话完成后可以自动回推一条基于结果摘要的完成汇报
- [ ] **BRDG-03**: 自动汇报链路可以稳定关联 child session 与 parent session
- [ ] **BRDG-04**: 自动汇报配置项能清晰表达 parent/child session scope、节流与完成策略

### PM And GSD Workflow

- [ ] **FLOW-01**: 仓库具备完整 `.planning` 骨架，可支持 `new-project -> plan-phase -> execute-phase`
- [ ] **FLOW-02**: PM 与 GSD 的职责边界清晰，避免任务事实与规划事实混乱
- [ ] **FLOW-03**: 当前 brownfield 实现可以通过 roadmap 分阶段产品化，而不是一次性重写

### Quality And Maintainability

- [ ] **QUAL-01**: 关键脚本具备最小 smoke check，至少能验证 CLI 可启动、bootstrap 可 dry-run、核心配置可被读取
- [ ] **QUAL-02**: 关键模块的架构边界可解释，便于后续 phase planning 与重构
- [ ] **QUAL-03**: 仓库能清晰识别当前主链路风险，例如路径硬编码、安装断层、测试不足、状态路径不一致

## v2 Requirements

### Provider Expansion

- **PROV-01**: 自动汇报机制支持除 Codex 外的更多 ACP provider，并具备一致的配置方式
- **PROV-02**: 多 provider 的 session prefix、行为差异和回推策略有统一抽象

### Product Surface

- **PROD-01**: 提供更完整的 operator guide / architecture guide / troubleshooting guide
- **PROD-02**: 提供更强的自检命令或诊断模式，帮助用户快速定位安装和运行问题

### Workflow Automation

- **AUTO-01**: PM 与 GSD 的串联进一步自动化，减少手工桥接步骤
- **AUTO-02**: 对 phase、progress、completion 的写回具备更强的一致性和自修复能力

## Out of Scope

| Feature | Reason |
|---------|--------|
| 替代 OpenClaw 主平台 | 本仓库目标是协作增强层，不是平台重写 |
| 当前版本支持所有 provider 的完整自动汇报闭环 | 先稳定 Codex 主链路，避免过早扩面 |
| 提供 GUI/控制台产品界面 | 当前阶段更需要稳定工作流和安装闭环 |
| 为简单玩具项目做极简变体 | 当前定位是复杂项目协作模式，不优先优化 demo 场景 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COLL-01 | Phase 1 | Pending |
| COLL-02 | Phase 1 | Pending |
| FLOW-01 | Phase 1 | Pending |
| BOOT-01 | Phase 1 | Pending |
| BOOT-02 | Phase 1 | Pending |
| PLAT-01 | Phase 2 | Complete |
| PLAT-02 | Phase 2 | Complete |
| PLAT-03 | Phase 2 | Complete |
| BOOT-03 | Phase 3 | Complete |
| BOOT-04 | Phase 3 | Complete |
| QUAL-01 | Phase 3 | Complete |
| BRDG-01 | Phase 4 | Complete |
| BRDG-02 | Phase 4 | Complete |
| BRDG-03 | Phase 4 | Complete |
| BRDG-04 | Phase 4 | Complete |
| FLOW-02 | Phase 5 | Pending |
| FLOW-03 | Phase 5 | Pending |
| QUAL-02 | Phase 5 | Pending |
| QUAL-03 | Phase 5 | Pending |
| COLL-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after Phase 4 bridge hardening closeout*
