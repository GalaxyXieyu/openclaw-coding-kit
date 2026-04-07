# Coding Conventions

**Analysis Date:** 2026-04-07

## Naming Patterns

**Files:**
- PM Python modules use `pm_<domain>.py` under `skills/pm/scripts/`, for example `skills/pm/scripts/pm_context.py` and `skills/pm/scripts/pm_runtime.py`.
- CLI-adjacent helpers stay close to the entrypoint instead of introducing package indirection, for example `skills/pm/scripts/pm_cli.py` and `skills/coder/scripts/observe_acp_session.py`.
- Operator-facing planning/docs use uppercase file names under `.planning/`, for example `.planning/PROJECT.md` and `.planning/codebase/TESTING.md`.
- Example/config files use descriptive host-oriented names, for example `examples/pm.json.example` and `examples/openclaw.json5.snippets.md`.

**Functions:**
- Use `snake_case` for all Python functions, including public orchestration helpers such as `build_coder_context()` in `skills/pm/scripts/pm_context.py` and utility helpers such as `default_state_dir()` in `skills/pm/scripts/pm_io.py`.
- Prefix internal-only helpers with `_`, for example `_first_env_path()` in `skills/pm/scripts/pm_io.py` and `_openclaw_config_candidates()` in `skills/pm/scripts/pm_config.py`.
- Keep CLI verbs aligned with subcommand intent, so handler wiring and operator vocabulary stay consistent across `skills/pm/scripts/pm_cli.py`, `skills/pm/scripts/pm_commands.py`, and `README.md`.

**Variables:**
- Use `UPPER_SNAKE_CASE` for module-level constants and env-var tuples, for example `STATE_DIR_ENV_VARS` in `skills/pm/scripts/pm_io.py` and `OPENCLAW_CONFIG_PATHS` in `skills/pm/scripts/pm_config.py`.
- Use `lower_snake_case` for local variables and parsed payload fields, especially in path/config discovery code such as `skills/pm/scripts/pm_config.py` and `skills/coder/scripts/observe_acp_session.py`.

**Types:**
- Prefer built-in generic annotations such as `dict[str, Any]`, `list[Path]`, and `Path | None`, as seen throughout `skills/pm/scripts/pm_io.py`, `skills/pm/scripts/pm_context.py`, and `skills/coder/scripts/observe_acp_session.py`.
- Use `@dataclass` only for small record-like carriers, for example `Candidate` in `skills/coder/scripts/observe_acp_session.py`.

## Code Style

**Formatting:**
- No repo-local formatter config is detected: there is no `.prettierrc`, `eslint.config.*`, `pyproject.toml`, or `ruff`/`black` config at repo root.
- Preserve the existing style instead of introducing a new toolchain: 4-space indentation, explicit blank-line separation, and readable `Path`-centric file operations, as shown in `skills/pm/scripts/pm_io.py` and `skills/pm/scripts/pm_config.py`.
- Keep `from __future__ import annotations` at the top of Python modules where already used, matching `skills/pm/scripts/pm_io.py`, `skills/pm/scripts/pm_config.py`, and other PM scripts.

**Linting:**
- No formal lint runner is detected in the repo.
- Consistency is maintained manually through repetitive patterns across `skills/pm/scripts/*.py`, `README.md`, and `INSTALL.md`.

## Import Organization

**Order:**
1. `from __future__ import annotations`
2. Python standard-library imports such as `json`, `os`, `argparse`, `pathlib`, and `datetime`
3. Local sibling-module imports inside `skills/pm/scripts/`, for example imports from `pm_config`, `pm_context`, or `pm_runtime`

**Path Aliases:**
- Not detected.
- Use direct relative module resolution from the script directory, as in `skills/pm/scripts/pm.py` and `skills/pm/scripts/pm_cli.py`.

## Error Handling

**Patterns:**
- Validate input and environment early, then fail fast with short operator-readable errors when a command cannot proceed; this is the dominant CLI pattern in `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_auth.py`, and `skills/pm/scripts/pm_workspace.py`.
- Use tolerant readers for cached/generated state: helpers such as `load_json_file()` in `skills/pm/scripts/pm_io.py` return `None` on unreadable or malformed files instead of crashing downstream routing.
- Keep “discovery” helpers pure and side-effect light, then let orchestration layers decide whether to stop, continue, or surface diagnostics, which is visible in `skills/pm/scripts/pm_config.py`, `skills/pm/scripts/pm_runtime.py`, and `skills/coder/scripts/observe_acp_session.py`.

## Logging

**Framework:** None repo-local; CLI stdout plus plugin/runtime logs.

**Patterns:**
- PM/coder scripts are designed for structured CLI use, so machine-readable JSON payloads and concise stdout/stderr messaging are preferred over chatty logging; see command-oriented files such as `skills/pm/scripts/pm.py` and `skills/coder/scripts/observe_acp_session.py`.
- Operational diagnostics live in workflow docs and plugin status flows rather than bespoke Python log wrappers, for example `README.md`, `INSTALL.md`, and `plugins/acp-progress-bridge/index.ts`.
- When adding new diagnostics, prefer status-style summaries that help operators answer “which path/config/session was chosen” without exposing secrets, consistent with `INSTALL.md` and `skills/pm/scripts/pm_worker.py`.

## Comments

**When to Comment:**
- Keep inline comments sparse; most explanation is pushed into operator docs such as `README.md`, `INSTALL.md`, `skills/pm/SKILL.md`, and `skills/coder/SKILL.md`.
- Add code comments only when a platform edge case or path fallback is hard to infer from the function name alone.

**JSDoc/TSDoc:**
- Not detected.
- Documentation responsibility currently sits in Markdown rather than docstrings or API-style annotations.

## Function Design

**Size:**
- Small pure helpers handle path resolution, JSON IO, and timestamp formatting, as in `skills/pm/scripts/pm_io.py` and `skills/pm/scripts/pm_config.py`.
- Larger orchestration remains centralized in entry/controller files such as `skills/pm/scripts/pm.py` and `skills/pm/scripts/pm_commands.py`; new behavior should extend helper modules first and keep the entrypoint thin when possible.

**Parameters:**
- Prefer explicit primitive/path parameters over hidden globals, especially in helper modules such as `skills/pm/scripts/pm_docs.py` and `skills/pm/scripts/pm_tasks.py`.
- Use env-var fallbacks only for runtime discovery boundaries, for example `PM_STATE_DIR`, `OPENCLAW_HOME`, `OPENCLAW_CONFIG`, `PM_WORKSPACE_ROOT`, and `PM_WORKSPACE_TEMPLATE_ROOT` in `skills/pm/scripts/pm_io.py`, `skills/pm/scripts/pm_config.py`, and `skills/pm/scripts/pm_workspace.py`.

**Return Values:**
- Return plain dict/list payloads for command/data exchange, matching `skills/pm/scripts/pm_context.py`, `skills/pm/scripts/pm_tasks.py`, and `.pm/*.json` cache files.
- Return `Path` objects for filesystem discovery helpers so callers can keep path joins explicit, as in `skills/pm/scripts/pm_io.py` and `skills/coder/scripts/observe_acp_session.py`.

## Module Design

**Exports:**
- One script generally owns one responsibility slice: config in `skills/pm/scripts/pm_config.py`, state IO in `skills/pm/scripts/pm_io.py`, task/doc adapters in `skills/pm/scripts/pm_tasks.py` and `skills/pm/scripts/pm_docs.py`, runtime dispatch in `skills/pm/scripts/pm_runtime.py`.
- Keep new shared logic in the narrowest matching module instead of expanding `skills/pm/scripts/pm.py` further.

**Barrel Files:**
- Not used.
- Entry wiring happens directly in `skills/pm/scripts/pm.py` and `skills/pm/scripts/pm_cli.py`.

## Runtime Boundary Conventions

**Repo-local state:**
- Treat `pm.json`, `.pm/*.json`, and `.planning/*.md` as repo-scoped collaboration artifacts, matching `README.md`, `INSTALL.md`, and `skills/pm/scripts/pm_context.py`.
- Generated repo-local snapshots should stay JSON/Markdown and be safe to inspect, diff, and review.

**User-global state:**
- Treat OpenClaw session/config discovery as user-environment state, not repo truth, following `skills/pm/scripts/pm_config.py`, `skills/pm/scripts/pm_auth.py`, `skills/coder/scripts/observe_acp_session.py`, and the boundary table in `INSTALL.md`.
- When changing runtime discovery, preserve the documented precedence: env override → PATH/config discovery → platform fallback.

---

*Convention analysis: 2026-04-07*
