# External Integrations

**Analysis Date:** 2026-04-07

## APIs & External Services

Role boundary across integrations:

- PM is the integration front door for task/doc/context operations.
- GSD is a planning backend over `.planning/*`, not the collaboration truth owner.
- coder uses Codex/OpenClaw runtime as the execution backend.
- bridge reads runtime state and relays updates, but does not mutate task/doc truth by itself.

**Task / Document Collaboration:**
- Feishu / Lark - PM tasklists, docs, doc folders, attachments, and OAuth flows are handled by `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_docs.py`, `skills/pm/scripts/pm_tasks.py`, and `skills/pm/scripts/pm_attachments.py`.
  - SDK/Client: custom HTTP requests via the Python standard library in `skills/pm/scripts/pm_auth.py`.
  - Auth: Feishu channel/app credentials are resolved through OpenClaw config handling in `skills/pm/scripts/pm_auth.py`.

**Local AI Runtime:**
- OpenClaw CLI/runtime - agent invocation, config loading, plugin hosting, and session-store discovery are handled by `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_bridge.py`, and `plugins/acp-progress-bridge/index.ts`.
  - SDK/Client: direct CLI subprocess invocation from `skills/pm/scripts/pm_runtime.py` and `plugins/acp-progress-bridge/index.ts`.
  - Auth: host OpenClaw config resolved from `OPENCLAW_CONFIG`, `OPENCLAW_HOME`, or platform defaults in `skills/pm/scripts/pm_auth.py` and `skills/pm/scripts/pm_runtime.py`.
  - Boundary: front agent identity and ACP worker identity are related but not identical. A host may expose `main` or a Feishu group as the parent front agent while still using Codex as the ACP worker.

**Coder Backend:**
- Codex CLI - PM can dispatch coder work through the runtime discovery in `skills/pm/scripts/pm_runtime.py`, while session observation is implemented by `skills/coder/scripts/observe_acp_session.py`.
  - SDK/Client: CLI execution via subprocess in `skills/pm/scripts/pm_runtime.py`.
  - Auth: external to this repo; the repo assumes a working Codex installation rather than storing credentials locally.

**Planning Backend:**
- GSD tools - roadmap / phase status inspection is implemented by `skills/pm/scripts/pm_gsd.py` against `.planning/*` and an external `gsd-tools.cjs` runtime.
  - SDK/Client: subprocess invocation from `skills/pm/scripts/pm_gsd.py`.
  - Auth: not applicable inside this repo.
  - Boundary: `route-gsd` and `plan-phase` operate on `.planning/*`; `materialize-gsd-tasks` is the optional point where those plans are projected into the task backend.

**Diagram Export Tooling:**
- Draw.io SVG/PNG export toolchain - `scripts/export-drawio-png.mjs` installs `@markdown-viewer/drawio2svg`, `@markdown-viewer/text-measure`, `@xmldom/xmldom`, `sharp`, `tsx`, `gui`, and `coroutine` into a temporary directory to export `diagrams/pm-coder-bridge-architecture.drawio`.
  - SDK/Client: direct `npm` / `npx` invocations from `scripts/export-drawio-png.mjs`.
  - Auth: none.

## Data Storage

**Databases:**
- Not detected. The repo does not include a database, ORM, or schema migration system.

**File Storage:**
- Repo-local JSON and markdown files act as the primary persistence layer in `pm.json`, `.pm/*.json`, `.planning/*.md`, and `.planning/codebase/*.md`.
- Diagram source and rendered assets live under `diagrams/`.
- Example configuration snippets live under `examples/`.

**Caching:**
- PM caches project scan, bootstrap, context, doc index, and last-run snapshots in `.pm/project-scan.json`, `.pm/bootstrap.json`, `.pm/current-context.json`, `.pm/coder-context.json`, `.pm/doc-index.json`, and `.pm/last-run.json`.
- The bridge plugin stores relay state in `plugins/acp-progress-bridge` host state under `ctx.stateDir/plugins/acp-progress-bridge/state.json`, as implemented in `plugins/acp-progress-bridge/index.ts`.
- OpenClaw session metadata is read from the host state directory path `agents/<agent>/sessions/sessions.json` and related ACP stream files in `plugins/acp-progress-bridge/index.ts`.

Source-of-truth interpretation:

- `.planning/*` is planning truth
- `.pm/*.json` is repo-local execution cache
- Feishu objects are collaboration truth when enabled
- OpenClaw session/state is runtime truth for bridge observation and delivery

## Authentication & Identity

**Auth Provider:**
- Feishu / Lark OAuth and attachment token flows are brokered through OpenClaw channel config in `skills/pm/scripts/pm_auth.py`.
  - Implementation: repo code reads host config, requests auth links / tokens, then calls Feishu APIs; secrets are not stored in tracked files.

## Monitoring & Observability

**Error Tracking:**
- No dedicated third-party error tracking service is detected.

**Logs:**
- PM emits CLI/stdout JSON responses from `skills/pm/scripts/pm.py` and its command modules.
- Bridge observability is exposed through status summaries and run metadata inside `plugins/acp-progress-bridge/index.ts`.
- Operator-facing troubleshooting guidance lives in `INSTALL.md` and `.planning/codebase/CONCERNS.md`.

Bridge detection model:

- discovery is polling-based rather than webhook-based
- child sessions are filtered by prefix and correlated via `spawnedBy`
- progress/completion delivery is debounced and settled before being replayed to the parent session

## CI/CD & Deployment

**Hosting:**
- Not applicable as a standalone deployable service. The repo is installed into an existing OpenClaw operator environment.

**CI Pipeline:**
- Not detected. No GitHub Actions, GitLab CI, or other pipeline manifests are present in the repo root.

## Environment Configuration

**Required env vars:**
- `OPENCLAW_BIN` - override OpenClaw CLI discovery in `skills/pm/scripts/pm_runtime.py`.
- `CODEX_BIN` - override Codex CLI discovery in `skills/pm/scripts/pm_runtime.py`.
- `GSD_TOOLS_PATH` - override GSD tool discovery in `skills/pm/scripts/pm_gsd.py` / `skills/pm/scripts/pm_runtime.py`.
- `OPENCLAW_LARK_BRIDGE_SCRIPT` - override the bridge script path in `skills/pm/scripts/pm_bridge.py`.
- `OPENCLAW_CONFIG` and `OPENCLAW_HOME` - locate OpenClaw config and state directories in `skills/pm/scripts/pm_auth.py` and `skills/pm/scripts/pm_runtime.py`.
- `PM_STATE_DIR`, `PM_WORKSPACE_ROOT`, and `PM_WORKSPACE_TEMPLATE_ROOT` - control PM repo/global state placement and workspace bootstrap in `skills/pm/scripts/pm_runtime.py` and `skills/pm/scripts/pm_workspace.py`.
- `OPENCLAW_ACP_PROGRESS_BRIDGE_CHILD` - mark bridge child runs in `plugins/acp-progress-bridge/index.ts`.

**Secrets location:**
- Secrets are intentionally not stored in tracked repo files.
- Feishu/OpenClaw credentials are expected to live in the operator's OpenClaw config or other user-global runtime locations resolved by `skills/pm/scripts/pm_auth.py`.

## Webhooks & Callbacks

**Incoming:**
- None detected. The repo does not expose HTTP endpoints or webhook handlers.

**Outgoing:**
- Feishu document/task HTTP requests originate from `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_docs.py`, and `skills/pm/scripts/pm_tasks.py`.
- OpenClaw CLI callback-style parent-session updates are emitted by `plugins/acp-progress-bridge/index.ts`.
- `scripts/export-drawio-png.mjs` performs package installation through `npm` when exporting diagrams.

---

*Integration audit: 2026-04-07*
