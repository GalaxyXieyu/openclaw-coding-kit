---
phase: 02-cross-platform-runtime
plan: 02
subsystem: infra
tags: [state, config, workspace, cross-platform, openclaw]
requires:
  - phase: 02-cross-platform-runtime
    provides: runtime command path discovery hardening for core CLIs
provides:
  - portable config and state directory fallbacks for PM and OpenClaw observers
  - clearer repo-local vs user-global config error messaging
  - explicit workspace root/template override paths and dry-run diagnostics
affects: [install-and-verification-loop, pm-gsd-productization]
tech-stack:
  added: []
  patterns:
    - repo-local and user-global path candidates are resolved through env override and platform-aware fallbacks
    - missing workspace templates fail with actionable diagnostics instead of implicit repository assumptions
key-files:
  created:
    - .planning/phases/02-cross-platform-runtime/02-02-SUMMARY.md
  modified:
    - skills/pm/scripts/pm_auth.py
    - skills/pm/scripts/pm_config.py
    - skills/pm/scripts/pm_io.py
    - skills/coder/scripts/observe_acp_session.py
    - skills/pm/scripts/pm_workspace.py
key-decisions:
  - "Move PM global state to explicit env override or platform state directories instead of ~/.codex-only storage."
  - "Treat missing workspace templates as an explicit installation gap with visible diagnostics, not a silent repository assumption."
patterns-established:
  - "OpenClaw config discovery should consider OPENCLAW_CONFIG, OPENCLAW_HOME, repo-local config files, and platform config directories."
  - "Workspace bootstrap defaults should expose their template root and root overrides for easier cross-platform diagnosis."
requirements-completed: [PLAT-01, PLAT-02]
duration: "session"
completed: 2026-04-07
---

# Phase 2: Cross-Platform Runtime Summary

**Config, state, observer, and workspace path discovery now separate repo-local and user-global locations more explicitly, while surfacing missing template assets through dry-run diagnostics instead of hidden assumptions.**

## Performance

- **Duration:** session
- **Started:** 2026-04-07T07:33:29Z
- **Completed:** 2026-04-07T07:33:29Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `pm_io` 不再把 PM 全局状态固定写到 `~/.codex/skills/pm/state`，而是支持环境变量与平台状态目录 fallback。
- `pm_config` / `pm_auth` / `observe_acp_session` 现在会理解 `OPENCLAW_CONFIG`、`OPENCLAW_HOME`、repo-local config、XDG 和 Windows AppData 候选。
- `pm_workspace` 新增 workspace 根路径和模板根路径的环境变量覆盖，dry-run 会明确回显模板路径与是否存在。

## Task Commits

This plan was completed in the working tree without standalone task commits.

1. **Task 1: Normalize config and state directory discovery** - no standalone commit
2. **Task 2: Rework workspace default path assumptions** - no standalone commit

**Plan metadata:** no standalone commit

## Files Created/Modified

- `skills/pm/scripts/pm_io.py` - 增加 PM state 目录的跨平台 fallback
- `skills/pm/scripts/pm_config.py` - 增强 OpenClaw config 候选路径发现
- `skills/pm/scripts/pm_auth.py` - 调整 OpenClaw config 读取优先级与错误提示
- `skills/coder/scripts/observe_acp_session.py` - 让 observer 支持环境变量和平台化 OpenClaw state 目录
- `skills/pm/scripts/pm_workspace.py` - 加入 workspace/template 根路径 override，并输出更可解释的 dry-run 信息

## Decisions Made

- 继续保留 repo-local `.openclaw/openclaw.json` 作为有效入口，但不再把它视作唯一合理布局。
- 没有在本阶段内置模板资产本身，而是优先把“模板从哪里来、缺了怎么报错”解释清楚。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- 当前仓库中的 `incubator/devteam/templates` 仍不存在；现在 dry-run 会明确暴露 `template_root_exists: false`，但模板资产本身要留到后续阶段处理。
- Windows 兼容仍然是静态路径策略验证，尚未在 Windows 主机上做真实运行验证。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `02-03` 可以直接开始，把新增环境变量、repo-local/user-global 边界和 Windows 路径写法同步进文档和示例。
- Phase 3 之后需要继续处理模板资产缺失和安装闭环问题。

---
*Phase: 02-cross-platform-runtime*
*Completed: 2026-04-07*
