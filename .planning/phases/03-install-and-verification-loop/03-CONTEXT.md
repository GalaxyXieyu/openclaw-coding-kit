# Phase 3: Install And Verification Loop - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

本 phase 的边界是把当前仓库从“已经补了跨平台路径与文档片段”推进到“用户拿到仓库后，能按文档完成最小安装、完成初始化、并跑通一组最小验证”的状态。重点是安装入口、初始化顺序、诊断步骤、最小 smoke checks 和文档一致性，不负责 provider 扩展、不负责完整 GUI、不负责把所有外部依赖都内置进仓库。

</domain>

<decisions>
## Implementation Decisions

### Installation entry flow
- **D-01:** Phase 3 以“本地可验证、再接外部依赖”的顺序组织安装闭环，先覆盖无鉴权/低依赖验证，再覆盖 Feishu/OpenClaw 完整接入。
- **D-02:** `python3 skills/pm/scripts/pm.py init --project-name "<name>" --dry-run` 是安装后的首要 bootstrap 入口，文档必须明确说明它先于真实 `pm init` 和真实 Feishu 绑定。
- **D-03:** `pm init`、`pm context --refresh`、`pm route-gsd --repo-root .` 应被视为当前官方 PM 初始化/诊断链路，而不是只在 skill 内部出现。

### Verification scope
- **D-04:** 最小 smoke check 以“无需真实线上资源也能跑”的命令为主，包括 Python 语法检查、CLI help、GSD route、`pm init --dry-run` 等。
- **D-05:** 手动验证清单必须显式区分“本地无鉴权验证”和“依赖真实 OpenClaw/Feishu 的集成验证”，不能把两者混在一起让用户误判失败原因。
- **D-06:** 本 phase 优先交付一组可直接复制执行的命令和检查表，不要求一次性补齐完整自动化测试框架。

### Installation constraints
- **D-07:** 中文项目名接入必须在文档里明确说明 `--english-name` 的使用条件，不能继续让用户在 workspace bootstrap 阶段碰撞式发现。
- **D-08:** workspace 模板资产缺失仍然是已知限制；Phase 3 需要把它写成显式安装前提或诊断结果，而不是假装仓库已自包含。
- **D-09:** repo-local 与 user-global 运行态边界必须在安装和诊断文档里延续 Phase 2 的口径，避免用户把 `.planning/.pm` 和 `~/.openclaw/%APPDATA%` 混为一谈。

### Documentation behavior
- **D-10:** README、INSTALL、examples、skills 说明和实际命令行为必须以仓库当前实现为准，发现矛盾时优先修正文档，不再继续保留历史说法。
- **D-11:** 安装文档要明确哪些步骤是“必须完成”、哪些只是“可选增强”（如 progress bridge、Feishu 回推），避免把主链路和增强链路混在一起。

### the agent's Discretion
- smoke check 是用独立脚本、Make-like 文档命令、还是纯 markdown checklist，由 agent 以最小侵入原则决定
- 手动验证清单的组织形式、命令分组和输出格式，由 agent 根据现有文档风格决定
- 如果某些验证更适合写进 `README`、`INSTALL`、`examples` 还是新建 `docs/`，由 agent 根据最小改动原则决定

</decisions>

<specifics>
## Specific Ideas

- 用户明确关注“安装步骤有没有问题”，所以 Phase 3 不能只修文字，要让文档和命令形成真正闭环
- 当前最适合做成 smoke checks 的命令已经存在：`py_compile`、`pm.py --help`、`pm.py context --help`、`pm.py route-gsd --repo-root .`、`pm.py init --project-name demo --dry-run`、`observe_acp_session.py --help`
- 需要把“先不依赖飞书也能开干”的路径在安装文档中讲清楚，因为当前用户就是这样推进的
- workspace 模板目录缺失现在已经能通过 dry-run 暴露出来，Phase 3 需要决定怎样把这个限制告知用户

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product intent and scope
- `.planning/PROJECT.md` — 项目核心价值、复杂项目协作目标和安装闭环约束
- `.planning/REQUIREMENTS.md` — Phase 3 对应 `BOOT-03, BOOT-04, QUAL-01`
- `.planning/ROADMAP.md` — Phase 3 目标、success criteria 和预期 plans
- `.planning/STATE.md` — 当前阶段位置与 blockers

### Prior phase decisions
- `.planning/phases/02-cross-platform-runtime/02-CONTEXT.md` — Phase 2 已锁定的路径/状态目录/Windows 兼容口径
- `.planning/phases/02-cross-platform-runtime/02-01-SUMMARY.md` — 运行时路径发现已完成的收敛结果
- `.planning/phases/02-cross-platform-runtime/02-02-SUMMARY.md` — config/state/workspace 路径收敛结果
- `.planning/phases/02-cross-platform-runtime/02-03-SUMMARY.md` — 文档与示例已完成的跨平台口径

### Existing docs and verification baseline
- `README.md` — 当前对外入口和跨平台总览
- `INSTALL.md` — 当前安装步骤、环境变量、验证命令和运行态目录说明
- `examples/openclaw.json5.snippets.md` — OpenClaw 配置占位符与路径示例
- `examples/pm.json.example` — PM 配置示例
- `.planning/codebase/TESTING.md` — 当前可行 smoke checks、未覆盖区域和最小测试建议
- `.planning/codebase/CONCERNS.md` — 当前安装断层、模板缺失和剩余风险

### Key implementation surfaces
- `skills/pm/SKILL.md` — PM 官方入口和 `pm init / context / route-gsd` 的现有说明
- `skills/pm/scripts/pm_cli.py` — 当前 CLI 暴露的命令面
- `skills/pm/scripts/pm_commands.py` — `init --dry-run` 和 workspace bootstrap 流程
- `skills/pm/scripts/pm_workspace.py` — workspace dry-run、模板路径和 bootstrap 限制
- `skills/coder/scripts/observe_acp_session.py` — 当前 observer 的本地验证入口

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/pm/scripts/pm.py` 已经能提供 `--help`、`context --help`、`route-gsd --repo-root .`、`init --dry-run` 等无鉴权 smoke checks
- `skills/coder/scripts/observe_acp_session.py` 提供了不依赖 Feishu 的 observer help/本地状态检查入口
- `pm_workspace.py` 已经能在 dry-run 中暴露 `template_root` 与 `template_root_exists`，适合作为安装诊断的一部分

### Established Patterns
- 仓库倾向用 markdown 文档 + examples 暴露用户契约，而不是复杂脚本封装
- Python 脚本的错误处理以短 `SystemExit` 文案为主，适合通过文档把诊断步骤补全
- Phase 2 已建立“环境变量 override -> PATH -> 平台 fallback”的统一口径，Phase 3 不能偏离

### Integration Points
- Phase 3 的安装闭环会直接承接 Phase 2 的路径/文档策略
- 后续 Phase 4 的 bridge hardening 依赖本 phase 把安装/启用链路说明清楚
- 后续 Phase 5 的质量与架构整理会依赖本 phase 定义的 smoke checks 和 operator checklist

</code_context>

<deferred>
## Deferred Ideas

- 把 workspace 模板资产正式收进仓库或提供单独分发机制
- 为 `plugins/acp-progress-bridge` 增加真正的 TypeScript build/typecheck 入口
- 在真实 Windows 主机上跑 E2E 验证并沉淀专项 runbook
- 把 smoke checks 进一步自动化成 CI 或独立脚本

</deferred>

---

*Phase: 03-install-and-verification-loop*
*Context gathered: 2026-04-07*
