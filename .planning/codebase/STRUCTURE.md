# Codebase Structure

**Analysis Date:** 2026-04-07

## Directory Layout

```text
openclaw-pm-coder-kit/
├── .planning/                         # GSD project docs, roadmap, phase plans, and codebase map
├── .pm/                               # PM repo-local context, bootstrap, scan, and doc-index cache
├── diagrams/                          # Draw.io source plus rendered SVG/PNG architecture assets
├── examples/                          # Minimal repo config and OpenClaw snippet examples
├── plugins/acp-progress-bridge/       # OpenClaw progress-bridge plugin source and manifest
├── scripts/                           # Root-level utility scripts that are not part of the PM package
├── skills/coder/                      # Coder skill doc plus ACP session observer helper
├── skills/pm/                         # PM skill doc plus Python implementation modules
├── INSTALL.md                         # Installation, bootstrap, and troubleshooting guide
├── README.md                          # High-level positioning and quick-start entry
└── pm.json                            # Repo-local PM project config
```

## Directory Purposes

**`.planning/`:**
- Purpose: project definition, requirements, roadmap, current state, phase artifacts, and codebase map.
- Contains: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `.planning/codebase/*.md`, and `.planning/phases/*`.
- Key files: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/codebase/STACK.md`.

**`.pm/`:**
- Purpose: repo-local PM cache and handoff bundle storage.
- Contains: JSON snapshots produced by PM commands.
- Key files: `.pm/current-context.json`, `.pm/coder-context.json`, `.pm/bootstrap.json`, `.pm/doc-index.json`, `.pm/project-scan.json`, `.pm/last-run.json`.

**`diagrams/`:**
- Purpose: architecture diagram source and committed exports.
- Contains: `.drawio`, `.svg`, and `.png` files.
- Key files: `diagrams/pm-coder-bridge-architecture.drawio`, `diagrams/pm-coder-bridge-architecture.drawio.svg`, `diagrams/pm-coder-bridge-architecture.drawio.png`.

**`examples/`:**
- Purpose: operator-facing config samples.
- Contains: example PM config and OpenClaw JSON5 snippets.
- Key files: `examples/pm.json.example`, `examples/openclaw.json5.snippets.md`.

**`plugins/acp-progress-bridge/`:**
- Purpose: bridge plugin source code and manifest.
- Contains: TypeScript implementation plus `openclaw.plugin.json` schema/defaults.
- Key files: `plugins/acp-progress-bridge/index.ts`, `plugins/acp-progress-bridge/openclaw.plugin.json`.

**`scripts/`:**
- Purpose: root-level utilities that do not belong inside the PM or coder skill packages.
- Contains: diagram export helper scripts.
- Key files: `scripts/export-drawio-png.mjs`.

**`skills/pm/`:**
- Purpose: PM task orchestration skill and its Python implementation.
- Contains: `SKILL.md` plus `skills/pm/scripts/pm_*.py` modules.
- Key files: `skills/pm/SKILL.md`, `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_commands.py`, `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_gsd.py`, `skills/pm/scripts/pm_workspace.py`.

**`skills/coder/`:**
- Purpose: coder execution-role skill and ACP observation helper.
- Contains: `SKILL.md` and `skills/coder/scripts/observe_acp_session.py`.
- Key files: `skills/coder/SKILL.md`, `skills/coder/scripts/observe_acp_session.py`.

## Key File Locations

**Entry Points:**
- `skills/pm/scripts/pm.py`: main PM CLI entrypoint.
- `skills/coder/scripts/observe_acp_session.py`: local ACP session inspection helper.
- `plugins/acp-progress-bridge/index.ts`: plugin runtime entrypoint.
- `scripts/export-drawio-png.mjs`: diagram export utility entrypoint.

**Configuration:**
- `pm.json`: tracked repo-level PM config.
- `examples/pm.json.example`: minimal sample PM config.
- `examples/openclaw.json5.snippets.md`: OpenClaw integration snippets.
- `plugins/acp-progress-bridge/openclaw.plugin.json`: bridge plugin schema and defaults.

**Core Logic:**
- `skills/pm/scripts/pm_commands.py`: PM command routing.
- `skills/pm/scripts/pm_context.py`: PM context generation and refresh.
- `skills/pm/scripts/pm_runtime.py`: runtime path discovery and subprocess execution.
- `skills/pm/scripts/pm_auth.py`: OpenClaw / Feishu auth-related helpers.
- `skills/pm/scripts/pm_docs.py` and `skills/pm/scripts/pm_tasks.py`: doc/task synchronization.
- `skills/pm/scripts/pm_gsd.py`: GSD planning metadata integration.
- `plugins/acp-progress-bridge/index.ts`: child-run discovery and parent-session relay.

**Testing:**
- No dedicated `tests/` directory or formal test files are present in the repo.
- Current validation guidance lives in `INSTALL.md` and `.planning/codebase/TESTING.md`.

## Naming Conventions

**Files:**
- PM modules use `pm_<domain>.py`, for example `skills/pm/scripts/pm_runtime.py` and `skills/pm/scripts/pm_workspace.py`.
- Planning docs use uppercase markdown names such as `.planning/PROJECT.md` and `.planning/codebase/STACK.md`.
- Example/config docs use descriptive suffixes such as `examples/pm.json.example` and `examples/openclaw.json5.snippets.md`.
- Diagram assets share the same basename across source and render outputs in `diagrams/pm-coder-bridge-architecture.drawio*`.

**Directories:**
- Skill implementation stays under `skills/<role>/`.
- Plugin code stays under `plugins/<plugin-id>/`.
- Repo-local stateful caches stay under dot-directories such as `.pm/` and `.planning/`.

## Where to Add New Code

**New PM feature:**
- Primary code: `skills/pm/scripts/pm_<domain>.py` or the nearest existing PM module.
- Command wiring: `skills/pm/scripts/pm_cli.py` and `skills/pm/scripts/pm_commands.py`.
- Repo-local context updates: `.pm/*.json` are generated artifacts, so change the Python producer rather than editing cache files by hand.

**New coder helper:**
- Implementation: `skills/coder/scripts/`.
- Skill-facing instructions: `skills/coder/SKILL.md`.

**New bridge capability:**
- Implementation: `plugins/acp-progress-bridge/index.ts`.
- Config surface: `plugins/acp-progress-bridge/openclaw.plugin.json`.

**New docs / planning assets:**
- Project-level narrative: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`.
- Operator docs: `README.md` and `INSTALL.md`.
- Integration samples: `examples/`.
- Architecture visuals: `diagrams/` plus `scripts/export-drawio-png.mjs` if exports must be regenerated.

**Utilities:**
- Shared repo utilities that are not PM modules belong in `scripts/`.

## Special Directories

**`.planning/`:**
- Purpose: committed project/planning knowledge.
- Generated: partially; content is curated and then committed.
- Committed: yes.

**`.pm/`:**
- Purpose: repo-local PM cache and handoff bundles.
- Generated: yes, by PM commands.
- Committed: yes in the current repo snapshot because bootstrap evidence is intentionally preserved.

**`diagrams/`:**
- Purpose: source-of-truth architecture visualization and exports.
- Generated: source file is hand-authored; SVG/PNG outputs are generated.
- Committed: yes.

---

*Structure analysis: 2026-04-07*
