# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3 - PM orchestration, context generation, task/doc sync, runtime discovery, workspace bootstrap, and coder observation live in `skills/pm/scripts/*.py` and `skills/coder/scripts/observe_acp_session.py`.
- TypeScript on Node.js - the OpenClaw bridge plugin lives in `plugins/acp-progress-bridge/index.ts`.

**Secondary:**
- Markdown - operator docs and planning assets live in `README.md`, `INSTALL.md`, `skills/pm/SKILL.md`, `skills/coder/SKILL.md`, and `.planning/*.md`.
- JSON - repo config and cached runtime snapshots live in `pm.json` and `.pm/*.json`.
- JSON5 snippets - OpenClaw integration examples live in `examples/openclaw.json5.snippets.md`.
- Draw.io / SVG / PNG artifacts - the architecture diagram source and exports live in `diagrams/pm-coder-bridge-architecture.drawio`, `diagrams/pm-coder-bridge-architecture.drawio.svg`, and `diagrams/pm-coder-bridge-architecture.drawio.png`.
- ES modules (`.mjs`) - a one-off export helper lives in `scripts/export-drawio-png.mjs`.

## Runtime

**Environment:**
- Python runtime is assumed by `skills/pm/scripts/pm.py` and the other `skills/pm/scripts/*.py` modules.
- Node.js runtime is assumed by `plugins/acp-progress-bridge/index.ts` and `scripts/export-drawio-png.mjs`.
- OpenClaw host runtime is required for plugin loading, session-state access, and CLI-mediated dispatch in `skills/pm/scripts/pm_runtime.py` and `plugins/acp-progress-bridge/index.ts`.
- Codex CLI is an execution backend resolved by `skills/pm/scripts/pm_runtime.py` and referenced from `pm.json`.

**Package Manager:**
- No repo-level package manager is pinned. There is no root `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `pyproject.toml`, or `requirements.txt`.
- `npm` is invoked ad hoc by `scripts/export-drawio-png.mjs` to create a temporary export environment under the OS temp directory.
- Lockfile: missing at repo root.

## Frameworks

**Core:**
- OpenClaw plugin API - `plugins/acp-progress-bridge/openclaw.plugin.json` defines the plugin contract loaded by the host runtime.
- PM CLI is a custom standard-library Python CLI centered on `skills/pm/scripts/pm.py` and `skills/pm/scripts/pm_cli.py`.

**Testing:**
- Not detected as a formal framework. Current verification is documentation-driven and CLI-based in `INSTALL.md` and `.planning/codebase/TESTING.md`.

**Build/Dev:**
- `npx tsx` is used transiently by `scripts/export-drawio-png.mjs` to run a generated worker script.
- `sharp`, `@markdown-viewer/drawio2svg`, `@markdown-viewer/text-measure`, `@xmldom/xmldom`, `gui`, and `coroutine` are temporary export-time dependencies installed by `scripts/export-drawio-png.mjs`.

## Key Dependencies

**Critical:**
- Python standard library modules such as `argparse`, `json`, `pathlib`, `subprocess`, `tempfile`, `urllib`, and `zoneinfo` power the PM CLI in `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_io.py`, and related modules.
- Node built-ins such as `node:child_process`, `node:fs/promises`, `node:path`, `node:crypto`, and `node:util` power `plugins/acp-progress-bridge/index.ts`.
- OpenClaw runtime conventions are assumed by `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_bridge.py`, and `plugins/acp-progress-bridge/index.ts`.

**Infrastructure:**
- Feishu/Lark task/doc integration is implemented by `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_docs.py`, `skills/pm/scripts/pm_tasks.py`, and `skills/pm/scripts/pm_attachments.py`.
- GSD planning metadata inspection is implemented by `skills/pm/scripts/pm_gsd.py` against `.planning/*`.
- Repo-local cache files live in `.pm/current-context.json`, `.pm/coder-context.json`, `.pm/bootstrap.json`, `.pm/doc-index.json`, `.pm/project-scan.json`, and `.pm/last-run.json`.

## Configuration

**Environment:**
- Repo config is rooted at `pm.json`.
- The main runtime override surface documented in `README.md`, `INSTALL.md`, and implemented by `skills/pm/scripts/pm_runtime.py` / `skills/pm/scripts/pm_auth.py` includes `OPENCLAW_BIN`, `CODEX_BIN`, `GSD_TOOLS_PATH`, `OPENCLAW_LARK_BRIDGE_SCRIPT`, `OPENCLAW_CONFIG`, `OPENCLAW_HOME`, `PM_STATE_DIR`, `PM_WORKSPACE_ROOT`, and `PM_WORKSPACE_TEMPLATE_ROOT`.
- Bridge child-session recursion protection is gated by `OPENCLAW_ACP_PROGRESS_BRIDGE_CHILD` in `plugins/acp-progress-bridge/index.ts`.

**Build:**
- Plugin schema and operator-facing defaults are declared in `plugins/acp-progress-bridge/openclaw.plugin.json`.
- Example bootstrap config lives in `examples/pm.json.example`.
- OpenClaw integration snippets live in `examples/openclaw.json5.snippets.md`.

## Platform Requirements

**Development:**
- Python 3 is required to run `skills/pm/scripts/pm.py` and `skills/coder/scripts/observe_acp_session.py`.
- Node.js and `npm` are required to run `scripts/export-drawio-png.mjs` and to host `plugins/acp-progress-bridge/index.ts`.
- OpenClaw CLI plus a valid config are required for the end-to-end PM → coder → bridge workflow described in `README.md` and `INSTALL.md`.
- Codex CLI is required when `pm.json` selects the `codex`/ACP execution path.

**Production:**
- This repo is consumed as an operator kit inside a larger OpenClaw environment rather than deployed as a standalone web service.
- Runtime state is split between repo-local planning/cache files and user-global OpenClaw/Codex state, as documented in `README.md`, `INSTALL.md`, and implemented in `skills/pm/scripts/pm_runtime.py`.

---

*Stack analysis: 2026-04-07*
