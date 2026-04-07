---
phase: 03-install-and-verification-loop
plan: 01
subsystem: docs
tags: [install, docs, examples, pm-skill, local-first]
requires:
  - phase: 02-cross-platform-runtime
    provides: cross-platform path conventions and repo-local vs user-global boundary language
provides:
  - aligned user-facing install contract across README, INSTALL, examples, and PM skill docs
  - separation between minimum local bootstrap and optional Feishu enhancement paths
  - clearer CLI help for non-ASCII project names and group-gated workspace bootstrap
affects: [bridge-reporting-hardening, pm-gsd-productization]
tech-stack:
  added: []
  patterns:
    - docs must reflect the real bootstrap order instead of historical workflow fragments
    - examples should separate minimum config from optional integration fragments
key-files:
  created:
    - .planning/phases/03-install-and-verification-loop/03-01-SUMMARY.md
  modified:
    - README.md
    - INSTALL.md
    - examples/openclaw.json5.snippets.md
    - examples/pm.json.example
    - skills/pm/SKILL.md
    - skills/pm/scripts/pm_cli.py
key-decisions:
  - "Treat local repo verification as the first-class installation path, with Feishu integration documented as optional enhancement."
  - "Split OpenClaw examples into minimum runtime, optional progress bridge, and optional Feishu binding fragments."
patterns-established:
  - "README, INSTALL, examples, and skill docs should all describe the same bootstrap commands."
  - "Non-ASCII project names and group-gated workspace bootstrap must be visible in docs and CLI help, not hidden in failure paths."
requirements-completed: [BOOT-03, BOOT-04]
duration: "session"
completed: 2026-04-07
---

# Phase 3: Install And Verification Loop Summary

**The repo now presents one consistent local-first install story across README, INSTALL, examples, and PM skill docs instead of mixing minimum bootstrap with Feishu-only enhancement paths.**

## Performance

- **Duration:** session
- **Completed:** 2026-04-07
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- README 现在先讲清楚这套 `PM + Developer + ACPX + progress bridge + 共享工作区` 架构是为了解决什么问题，再给出本地优先的 bootstrap 入口。
- INSTALL 现在明确拆成“本地无鉴权验证”和“真实集成验证”两条轨道，不再把 Feishu 绑定、progress bridge、workspace bootstrap 当成最小安装前置。
- `examples/openclaw.json5.snippets.md` 已拆成最小 OpenClaw 配置、可选 progress bridge、可选 Feishu binding 三个片段。
- `examples/pm.json.example` 已从 Feishu 密集示例收成最小本地示例。
- `skills/pm/SKILL.md` 现已补齐 `init --dry-run`、`context --refresh`、`route-gsd --repo-root .`、`plan-phase`、`materialize-gsd-tasks` 的当前口径。
- `pm_cli.py` 的 `--english-name` / `--group-id` 帮助文案更明确了。

## Files Created/Modified

- `README.md` - 重写仓库定位、架构动机和本地优先入口
- `INSTALL.md` - 重写安装顺序，分离本地验证与真实集成验证
- `examples/openclaw.json5.snippets.md` - 按最小 / 可选增强拆片段
- `examples/pm.json.example` - 改为本地优先的最小 PM 配置示例
- `skills/pm/SKILL.md` - 同步 PM 当前官方工作流口径
- `skills/pm/scripts/pm_cli.py` - 强化帮助信息

## Decisions Made

- 先把“用户看见的安装故事”讲对，再处理更深层的架构和运行时问题。
- 不再让任何示例文件默认暗示“必须先接 Feishu 才能开始”。

## Issues Encountered

- `context --refresh` 当前输出仍会暴露 Feishu-first 的默认 backend 和历史命名，这说明文档问题已收敛，但底层默认值中性化还没做完。

## User Setup Required

None for local verification.

## Next Phase Readiness

- 03-01 完成后，03-02 可以直接补安装后的官方 bootstrap / diagnostics 链路。

---
*Phase: 03-install-and-verification-loop*
*Completed: 2026-04-07*
