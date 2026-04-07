---
phase: 02-cross-platform-runtime
plan: 01
subsystem: infra
tags: [runtime, path-discovery, cross-platform, codex, openclaw]
requires:
  - phase: 01-brownfield-bootstrap
    provides: bootstrap docs and executable phase planning assets
provides:
  - cross-platform runtime path discovery for OpenClaw, Codex, and GSD tools
  - bridge script override path without mandatory startup dependency
  - clearer runtime error messages for missing local CLIs
affects: [install-and-verification-loop, pm-gsd-productization]
tech-stack:
  added: []
  patterns:
    - runtime entry resolution follows env override -> PATH discovery -> platform fallback
    - bridge-dependent commands no longer block local GSD routing at process startup
key-files:
  created:
    - .planning/phases/02-cross-platform-runtime/02-01-SUMMARY.md
  modified:
    - skills/pm/scripts/pm_runtime.py
    - skills/pm/scripts/pm_gsd.py
    - skills/pm/scripts/pm.py
key-decisions:
  - "Promote environment-variable overrides to first-class runtime entrypoints instead of hard-coded machine paths."
  - "Remove unconditional bridge startup validation so local planning/execution commands can run without Feishu dependencies."
patterns-established:
  - "Runtime binaries must be discoverable without encoding a specific developer machine or Node version directory."
  - "Support scripts may use explicit overrides and repo-local fallbacks, but should not gate unrelated commands."
requirements-completed: [PLAT-01, PLAT-02]
duration: "session"
completed: 2026-04-07
---

# Phase 2: Cross-Platform Runtime Summary

**Runtime entry discovery now resolves OpenClaw, Codex, GSD tools, and bridge script paths through env override, PATH lookup, and portable fallbacks instead of single-machine hardcoding.**

## Performance

- **Duration:** session
- **Started:** 2026-04-07T07:21:37Z
- **Completed:** 2026-04-07T07:33:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- 把 `openclaw` 和 `codex` 的查找顺序统一为环境变量优先、PATH 其次、平台标准目录兜底。
- 让 `gsd-tools` 支持 `GSD_TOOLS_PATH`、`CODEX_HOME` 和 PATH 中的 wrapper/script，而不再只认 `~/.codex/get-shit-done/bin/gsd-tools.cjs`。
- 去掉了 `pm.py` 对 bridge script 的无条件启动前校验，使 `route-gsd`、`--help` 这类本地命令可以脱离飞书桥接独立运行。

## Task Commits

This plan was completed in the working tree without standalone task commits.

1. **Task 1: Centralize CLI/script path discovery priorities** - no standalone commit
2. **Task 2: Verify runtime discovery remains readable and debuggable** - no standalone commit

**Plan metadata:** no standalone commit

## Files Created/Modified

- `skills/pm/scripts/pm_runtime.py` - 新增统一的运行时路径解析 helper，并替换 OpenClaw/Codex 硬编码路径
- `skills/pm/scripts/pm_gsd.py` - 让 GSD tools 支持环境变量、PATH wrapper 和 `CODEX_HOME`
- `skills/pm/scripts/pm.py` - 让 bridge script 支持显式覆盖，并移除与本地命令无关的强制前置检查

## Decisions Made

- 没有继续保留 `.nvm` 具体 Node 版本目录作为默认主路径，因为这会把运行时绑死到作者本机。
- 对 bridge script 只做显式覆盖和仓库/用户技能目录兜底，不把它扩展成真正的 PATH 命令发现对象。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- 当前验证仍是在 macOS 环境完成，Windows 路径策略属于静态兼容设计，尚未做真机执行验证。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `02-01` 已收口，下一步可以进入 `02-02`，处理 `.pm`、`.planning`、`~/.openclaw` 等状态目录和运行态边界。
- 后续 `02-03` 需要把新增环境变量和跨平台路径写法同步到 `README`、`INSTALL` 和示例配置里。

---
*Phase: 02-cross-platform-runtime*
*Completed: 2026-04-07*
