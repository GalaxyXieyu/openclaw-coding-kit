# Testing Patterns

**Analysis Date:** 2026-04-07

## Test Framework

**Runner:**
- `python3 -m unittest discover -s tests -v`
- The repo now has a minimal stdlib `unittest` baseline under `tests/`.

**Assertion Library:**
- Python stdlib `unittest`

**Run Commands:**
```bash
python3 -m py_compile skills/pm/scripts/*.py skills/coder/scripts/*.py tests/*.py
python3 -m unittest discover -s tests -v
node --test plugins/acp-progress-bridge/core.test.mjs
python3 skills/pm/scripts/pm.py --help
python3 skills/pm/scripts/pm.py init --project-name demo --task-backend local --doc-backend repo --dry-run
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
python3 skills/coder/scripts/observe_acp_session.py --help
openclaw agents list --bindings
```

## Test File Organization

**Location:**
- Automated tests live in `tests/`.
- Manual verification knowledge still lives in docs and CLI flows, mainly `README.md`, `INSTALL.md`, `skills/pm/SKILL.md`, and `skills/coder/SKILL.md`.

**Naming:**
- Python tests use `tests/test_*.py`.
- Manual verification commands still follow the operator entrypoints, such as `init --dry-run`, `context --refresh`, and `route-gsd` from `skills/pm/scripts/pm.py`.

**Structure:**
```text
tests/
  test_pm_bridge.py
  test_pm_context.py
  test_pm_gsd_materializer.py
  test_pm_local_cli.py
  test_pm_runtime.py
  test_pm_worker.py
  test_pm_workspace.py
Manual verification is still documented in `README.md` and `INSTALL.md`.
Repo-local evidence is written to `.pm/*.json` and `.planning/*.md`.
```

## Test Structure

**Suite Organization:**
```text
1. Run repo-local unit tests first.
2. Run a local no-auth smoke check against `skills/pm/scripts/pm.py` and `skills/coder/scripts/observe_acp_session.py`.
3. Inspect repo-local outputs such as `.pm/current-context.json`, `.pm/doc-index.json`, `.pm/local-tasks.json`, and `.pm/gsd-task-bindings.json`.
4. Escalate to real runtime checks only after local tests and smoke pass.
```

**Patterns:**
- Use syntax/CLI boot checks first, as documented in `INSTALL.md` and reflected by script entrypoints under `skills/pm/scripts/` and `skills/coder/scripts/`.
- Keep pure logic in unit tests when possible, especially for backend-neutral seams such as GSD materialization and handoff contract assembly.
- Separate local no-auth validation from real integration validation; this boundary is explicit in `README.md` and `INSTALL.md`.
- Treat generated repo-local artifacts such as `.pm/current-context.json`, `.pm/bootstrap.json`, `.pm/doc-index.json`, `.pm/local-tasks.json`, and `.pm/gsd-task-bindings.json` as the first evidence layer before inspecting user-global OpenClaw state.

## PM/GSD Productization Baseline

**Layer 1: 本地无鉴权**

These checks do not require a real Feishu backend:

```bash
python3 -m py_compile skills/pm/scripts/pm.py skills/pm/scripts/pm_commands.py skills/pm/scripts/pm_gsd.py skills/pm/scripts/pm_worker.py skills/pm/scripts/pm_runtime.py skills/pm/scripts/pm_local_backend.py skills/pm/scripts/pm_gsd_materializer.py skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py
python3 -m unittest discover -s tests -v
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py --help
python3 skills/pm/scripts/pm.py init --project-name demo --task-backend local --doc-backend repo --dry-run
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
```

What this proves:
- `.planning/*` and `.pm/*` can be read and refreshed locally
- `route-gsd` can explain the current phase route
- `route.runtime` can expose missing `gsd-tools` or `node` without waiting for a later failure
- local task backend and structured handoff seams stay covered by unit tests
- local task attachment and complete flow stay covered by CLI-level repo-local tests
- bridge discovery / progress / completion message shaping stays covered by `node:test`

What this does **not** prove:
- `plan-phase` can talk to a real OpenClaw front agent
- real Feishu doc/task writes are healthy
- any OpenClaw/Feishu host integration is healthy

**Layer 2: 宿主 runtime 验证**

These checks require a real OpenClaw runtime, but not necessarily a full Feishu delivery path:

```bash
openclaw agents list --bindings
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
python3 skills/pm/scripts/pm.py plan-phase --repo-root . --phase 5 --no-doc-sync --no-progress-sync --no-state-append
```

Operator interpretation:
- if `openclaw agents list --bindings` does not show the intended front agent, `plan-phase` is not ready
- if `plan-phase` reports `Unknown agent id`, the front agent selection is wrong even if `codex` exists as an ACP worker
- if `route-gsd` shows `runtime.ready=false`, fix `GSD_TOOLS_PATH` or `node` first

**Layer 3: backend 集成**

These checks require backend readiness, but the backend can now be repo-local:

```bash
python3 skills/pm/scripts/pm.py materialize-gsd-tasks --repo-root . --phase 5
python3 skills/pm/scripts/pm.py sync-gsd-progress --repo-root . --phase 5
```

What this proves:
- GSD plans can be projected into tracked tasks
- progress snapshots can write back to STATE/task comments

What this still depends on:
- a valid task/doc backend
- correct PM bindings in `pm.json`
- real OpenClaw runtime when you move past the repo-local path

## Mocking

**Framework:** Python stdlib `unittest`

**Patterns:**
```text
No third-party mocking framework is in use.
Current unit tests rely on hand-written fakes plus dry-run commands and generated JSON snapshots.
```

**What to Mock:**
- Feishu/task/doc bridge calls from `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_docs.py`, and `skills/pm/scripts/pm_attachments.py`
- env vars and filesystem layout around `skills/pm/scripts/pm_config.py`, `skills/pm/scripts/pm_io.py`, and `skills/pm/scripts/pm_workspace.py`

**What NOT to Mock:**
- Do not hide repo-local file layout behavior when testing `.pm/` and `.planning/` generation; those files are part of the contract described in `README.md` and `INSTALL.md`.
- Do not treat real OpenClaw session discovery as a unit-test-only concern; keep one manual validation path for actual `OPENCLAW_HOME` / session-store behavior used by `skills/coder/scripts/observe_acp_session.py`.

## Fixtures and Factories

**Test Data:**
```text
Use `examples/pm.json.example` as the minimal config seed.
Use `examples/openclaw.json5.snippets.md` as the integration-shape reference.
Use generated `.pm/*.json` files as inspectable smoke-test evidence.
Use `.pm/local-tasks.json` and `.pm/gsd-task-bindings.json` when validating the repo-local backend path.
```

**Location:**
- Static sample inputs live in `examples/pm.json.example` and `examples/openclaw.json5.snippets.md`.
- Generated verification outputs live under `.pm/` and `.planning/`.

## Coverage

**Requirements:** None enforced yet.

**View Coverage:**
```bash
No coverage command is configured in this repository.
```

## Test Types

**Unit Tests:**
- Present under `tests/`.
- Current coverage targets:
  - `skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py`
  - `skills/pm/scripts/pm_context.py`
  - `skills/pm/scripts/pm_gsd_materializer.py`
  - repo-local CLI lifecycle (`create` / `upload-attachments` / `complete`)
  - `skills/pm/scripts/pm_worker.py`
  - `skills/pm/scripts/pm_runtime.py`
  - `skills/pm/scripts/pm_workspace.py`
- Highest-value next candidates are path/config helpers in `skills/pm/scripts/pm_config.py`, `skills/pm/scripts/pm_io.py`, and repo-local backend behavior in `skills/pm/scripts/pm_local_backend.py`.

**Integration Tests:**
- Not automated inside this repo.
- Current integration validation is an operator checklist spanning `skills/pm/scripts/pm.py`, `plugins/acp-progress-bridge/index.ts`, OpenClaw runtime wiring, and optional Feishu bindings described in `INSTALL.md`.

**E2E Tests:**
- Not used.
- The closest current equivalent is a manual runtime drill: load PM/coder in OpenClaw, enable `acp-progress-bridge`, run a child session, then inspect `bridge-status`, plugin logs, and session files.

## Common Patterns

**Async Testing:**
```text
No async test harness is present.
Async/runtime behavior is checked manually through OpenClaw session files and plugin logs.
```

**Error Testing:**
```text
Prefer failure cases that prove diagnostics are readable:
- missing OpenClaw config in `skills/pm/scripts/pm_auth.py`
- missing workspace template root in `skills/pm/scripts/pm_workspace.py`
- missing/ambiguous task-doc bindings in `skills/pm/scripts/pm.py`
- missing `gsd-tools` / `node` surfaced through `route-gsd`
- missing OpenClaw front agent surfaced through `plan-phase`
```

## Verification Boundary Guidance

**Repo-local first:**
- Validate `.planning/` and `.pm/` generation before touching external services.
- Keep local smoke checks aligned with the repo-local collaboration contract described in `README.md` and `INSTALL.md`.

**User-global second:**
- Only after local smoke passes should you inspect user-global state such as `~/.openclaw/`, `~/.config/openclaw/`, `%APPDATA%\\OpenClaw\\`, or `%LOCALAPPDATA%\\OpenClawPMCoder\\`, matching the boundary table in `INSTALL.md` and discovery logic in `skills/pm/scripts/pm_config.py` plus `skills/coder/scripts/observe_acp_session.py`.

## Test Coverage Gaps Worth Preserving In Future Plans

**Path and config discovery:**
- `skills/pm/scripts/pm_config.py`
- `skills/pm/scripts/pm_runtime.py`
- `skills/pm/scripts/pm_workspace.py`

**Task/doc adapter behavior:**
- `skills/pm/scripts/pm_tasks.py`
- `skills/pm/scripts/pm_docs.py`
- `skills/pm/scripts/pm_attachments.py`

**Observer and bridge diagnostics:**
- `skills/coder/scripts/observe_acp_session.py`
- `plugins/acp-progress-bridge/index.ts`

---

*Testing analysis: 2026-04-07*
