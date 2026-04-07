# Architecture

**Analysis Date:** 2026-04-07

## Pattern Overview

**Overall:** workflow-automation toolkit with repo-local planning state, PM CLI orchestration, and an optional OpenClaw plugin bridge.

**Key Characteristics:**
- Operator behavior is declared in skill docs such as `skills/pm/SKILL.md` and `skills/coder/SKILL.md`, while executable logic lives in `skills/pm/scripts/*.py`.
- The repository keeps two repo-local state planes: planning truth under `.planning/` and PM runtime/cache snapshots under `.pm/`.
- Runtime integration is host-driven: PM invokes external CLIs from `skills/pm/scripts/pm_runtime.py`, and OpenClaw loads `plugins/acp-progress-bridge/index.ts` as a plugin.
- Role boundaries are intentionally split: PM is the tracked-work front door, GSD is the roadmap/phase backend, coder is the canonical execution worker, and bridge is an asynchronous progress relay.

## Source Of Truth Layers

The codebase currently spans four distinct truth planes:

- `.planning/*` is roadmap and phase truth for GSD planning, execution summaries, and codebase mapping.
- `.pm/*.json` is PM repo-local cache and handoff state. It helps execution, but it is not the durable business truth.
- Feishu task/doc objects are collaboration truth when real backend sync is enabled.
- OpenClaw session/state is runtime truth for ACP child runs, parent/child correlation, and bridge delivery.

Most confusion in this repo comes from collapsing these planes into one mental model. The architecture only stays coherent if each plane keeps a narrow responsibility.

## Layers

**Operator Skill Layer:**
- Purpose: define human-facing workflows, command order, and collaboration expectations.
- Location: `skills/pm/`, `skills/coder/`.
- Contains: `SKILL.md` entry docs and a small coder helper script.
- Depends on: the PM script layer and host OpenClaw/Codex runtime.
- Used by: operators running the kit inside OpenClaw or Codex.

**PM CLI Layer:**
- Purpose: expose the repo's tracked-work front door and orchestration command surface.
- Location: `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_cli.py`, `skills/pm/scripts/pm_commands.py`.
- Contains: CLI parsing, command routing, JSON output, and top-level workflow composition.
- Depends on: config, context, runtime, task/doc, and bootstrap helpers.
- Used by: `README.md`, `INSTALL.md`, PM skill flows, and downstream coder handoff.

This is the layer that decides whether a request stays local, routes to GSD, or hands off to coder execution.

**Context And Persistence Layer:**
- Purpose: read/write repo-local config, scans, bootstrap results, and planning metadata.
- Location: `skills/pm/scripts/pm_config.py`, `skills/pm/scripts/pm_context.py`, `skills/pm/scripts/pm_io.py`, `skills/pm/scripts/pm_scan.py`, `skills/pm/scripts/pm_bootstrap.py`.
- Contains: `pm.json` loading, `.pm/*.json` refresh, repo scanning, planning/bootstrap interpretation.
- Depends on: repo files such as `pm.json`, `.pm/current-context.json`, `.planning/STATE.md`.
- Used by: PM commands before task routing, planning, or execution.

**Backend Adapter Layer:**
- Purpose: encapsulate integrations with external systems and host runtimes.
- Location: `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_docs.py`, `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_attachments.py`, `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_dispatch.py`, `skills/pm/scripts/pm_worker.py`, `skills/pm/scripts/pm_gsd.py`, `skills/pm/scripts/pm_bridge.py`, `skills/pm/scripts/pm_workspace.py`.
- Contains: Feishu doc/task operations, runtime command discovery, coder dispatch, GSD routing, bridge helpers, and workspace generation.
- Depends on: host OpenClaw/Codex binaries, Feishu bindings, and repo-local planning/runtime files.
- Used by: the PM CLI layer.

GSD belongs here as a backend integration seam, not as the primary user entrypoint.
`pm_gsd.py` now owns the pure phase/plan indexing, route reasoning, and GSD task-description contract, while `pm.py` mainly keeps runtime and backend side effects.

**Bridge And Observation Layer:**
- Purpose: observe ACP child sessions and relay progress/completion back to parent sessions.
- Location: `skills/coder/scripts/observe_acp_session.py`, `plugins/acp-progress-bridge/index.ts`, `plugins/acp-progress-bridge/openclaw.plugin.json`.
- Contains: session observation logic, plugin config schema, and relay implementation.
- Depends on: OpenClaw session storage, stream/transcript files, and CLI reinvocation.
- Used by: OpenClaw host runtime and coder-side debugging.

This layer does not own task/doc truth. It only transports runtime signals upward.

`pm_worker.py` also acts as the PM -> coder handoff contract layer: it turns task description fields and coder-context inputs into a structured execution contract before runtime dispatch.

**Documentation And Example Layer:**
- Purpose: explain installation, configuration, and planning status.
- Location: `README.md`, `INSTALL.md`, `examples/pm.json.example`, `examples/openclaw.json5.snippets.md`, `.planning/`, `diagrams/`.
- Contains: operator instructions, snippets, planning docs, and architecture diagrams.
- Depends on: the current repository layout and workflow behavior.
- Used by: humans onboarding the repo and planners generating future phases.

## Data Flow

**PM Context Refresh And Task Routing:**

1. An operator runs `python3 skills/pm/scripts/pm.py ...`.
2. `skills/pm/scripts/pm_cli.py` parses the command and `skills/pm/scripts/pm_commands.py` selects the handler.
3. `skills/pm/scripts/pm_config.py` resolves `pm.json`, and `skills/pm/scripts/pm_context.py` / `skills/pm/scripts/pm_scan.py` inspect repo state.
4. The command reads or refreshes repo-local artifacts in `.pm/*.json` and `.planning/*.md`.
5. If needed, backend adapters call Feishu, OpenClaw, Codex, or GSD-facing helpers.
6. Results are emitted to stdout and usually persisted back to `.pm/` for later runs.

`route-gsd` is the boundary command that decides whether the current phase should plan, execute, or materialize tracked tasks next.

**Planning And Bootstrap Flow:**

1. `skills/pm/scripts/pm_bootstrap.py` interprets brownfield or greenfield bootstrap state.
2. `skills/pm/scripts/pm_gsd.py` inspects `.planning/ROADMAP.md`, `.planning/STATE.md`, and phase files under `.planning/phases/`.
3. PM commands produce bundles such as `.pm/current-context.json` and `.pm/coder-context.json` for downstream workers.
4. Planners and coder workers use those artifacts as the execution index card.

`plan-phase` updates `.planning/phases/*/*-PLAN.md`, while `materialize-gsd-tasks` is the optional bridge from phase plans into task backend objects.
The command handler in `pm_commands.py` now delegates the heavier planning/materialization/progress sequence to a dedicated PM workflow helper instead of inlining the whole orchestration path.

**Bridge Reporting Flow:**

1. OpenClaw loads `plugins/acp-progress-bridge/index.ts` using `plugins/acp-progress-bridge/openclaw.plugin.json`.
2. The plugin polls host session stores for child sessions that match configured prefixes.
3. It correlates child sessions with parent sessions via `spawnedBy` and parent prefix rules.
4. Session stream/transcript data is turned into internal `[[acp_bridge_update]]` messages.
5. OpenClaw CLI reinvocation delivers those updates to the parent session for user-facing summarization.

**State Management:**
- Declarative project configuration lives in `pm.json`.
- Repo-local mutable PM cache lives in `.pm/*.json`.
- Planning truth and codebase mapping live in `.planning/` and `.planning/codebase/`.
- User-global runtime state remains outside the repo and is only referenced by runtime discovery in files such as `skills/pm/scripts/pm_runtime.py`.
- Feishu task/doc state is collaboration truth only when backend sync is enabled; local-only execution can skip that plane.

## Key Abstractions

**PM Command Surface:**
- Purpose: provide one stable entrypoint for init, context, planning, task sync, and execution dispatch.
- Examples: `skills/pm/scripts/pm.py`, `skills/pm/scripts/pm_cli.py`, `skills/pm/scripts/pm_commands.py`.
- Pattern: thin CLI entrypoint calling specialized helper modules.

**Repo-Local Context Bundle:**
- Purpose: persist refreshed task/doc/bootstrap state between sessions.
- Examples: `.pm/current-context.json`, `.pm/coder-context.json`, `.pm/bootstrap.json`, `.pm/doc-index.json`.
- Pattern: JSON snapshots generated from commands rather than hand-edited source files.

For GSD-backed work, `.pm/coder-context.json` now carries a structured handoff contract with required reads and source-of-truth hints, instead of leaving coder to infer them only from scattered description lines.

**Planning Workspace:**
- Purpose: hold durable long-form project truth for GSD-style planning.
- Examples: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/phases/05-pm-gsd-productization/05-01-PLAN.md`.
- Pattern: markdown-first planning tree committed with the repo.

**Host Integration Adapter:**
- Purpose: isolate host-specific runtime discovery and backend calls.
- Examples: `skills/pm/scripts/pm_runtime.py`, `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_tasks.py`, `skills/pm/scripts/pm_docs.py`.
- Pattern: service-style helper modules invoked from command handlers.

## Entry Points

**Primary CLI:**
- Location: `skills/pm/scripts/pm.py`
- Triggers: direct `python3` invocation from operators, docs, or automation.
- Responsibilities: load PM modules, parse commands, emit JSON results.

**Command Routing:**
- Location: `skills/pm/scripts/pm_cli.py`, `skills/pm/scripts/pm_commands.py`
- Triggers: every PM subcommand.
- Responsibilities: map subcommands to concrete context/task/doc/runtime operations.

**Coder Observation Helper:**
- Location: `skills/coder/scripts/observe_acp_session.py`
- Triggers: manual debugging of ACP session progress.
- Responsibilities: inspect session state without going through the full PM entrypoint.

**Plugin Runtime:**
- Location: `plugins/acp-progress-bridge/index.ts`
- Triggers: OpenClaw plugin loading.
- Responsibilities: detect child-session updates and relay them to parent sessions.

**Documentation Entry Points:**
- Location: `README.md`, `INSTALL.md`, `examples/openclaw.json5.snippets.md`, `examples/pm.json.example`
- Triggers: onboarding, setup, and operator reference.
- Responsibilities: teach users how to invoke the CLI and wire the kit into a host instance.

## Error Handling

**Strategy:** fail early at command boundaries, surface diagnostics in JSON/stdout, and persist enough repo-local context to make the next debugging step explicit.

**Patterns:**
- Validation and discovery happen before side-effecting operations in the PM CLI flow, especially around `pm.json`, task/doc bindings, and bootstrap mode.
- Dry-run support is used as a safe preflight path in commands documented by `README.md` and `INSTALL.md`.
- Runtime uncertainty is externalized through `.pm/*.json` snapshots rather than hidden in process memory.

## Cross-Cutting Concerns

**Logging:** command results are emitted through CLI JSON/stdout; bridge observability is handled by plugin status/log surfaces documented in planning docs.

**Validation:** configuration, repo scan results, and planning/bootstrap mode are validated across `skills/pm/scripts/pm_config.py`, `skills/pm/scripts/pm_context.py`, and `skills/pm/scripts/pm_bootstrap.py`.

**Authentication:** Feishu/Lark auth and doc/task access are handled by `skills/pm/scripts/pm_auth.py`, `skills/pm/scripts/pm_docs.py`, and `skills/pm/scripts/pm_tasks.py`; local-first validation remains possible without those integrations.

---

*Architecture analysis: 2026-04-07*
