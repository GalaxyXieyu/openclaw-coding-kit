---
name: pm
description: Use this skill for project task orchestration in this repo. Trigger whenever the user wants to create, plan, refine, run, complete, comment on, search, or manage project work items, or when a coding task should first be registered into task/doc/context before execution. PM is the required entrypoint for repo task automation, task/doc synchronization, bootstrap detection, coder handoff, and future GSD routing.
---

# PM

`pm` is the task orchestration entrypoint for this repo.

Use it before implementation work when the request should become part of the managed task flow rather than an ad-hoc local change.

## Use This Skill When

- The user wants to create or manage a project task
- The user asks to plan, refine, run, complete, or comment on tracked work
- The request should update task/doc/context state, not just code
- You need the current `next_task` / `current_task` / repo bootstrap state
- You want to dispatch work to coder automation
- You need a stable handoff bundle for downstream execution
- The task may later flow into GSD

Do not force `pm` for trivial one-off local edits that clearly should not enter the task system.

## What PM Owns

- project init and bootstrap detection
- task as execution truth
- doc as long-form truth
- repo-local cache in `.pm/*.json`
- planning/refinement bundles
- coder handoff bundles
- run/dispatch side effects back to task comments and STATE doc
- attachment upload and completion flow

PM is the tracked-work front door. If a request should become managed work, it should enter here first rather than starting from GSD or coder directly.

## Role Boundary

Use this contract consistently:

- `PM` owns tracked work intake, task/doc synchronization, repo-local cache, and execution handoff.
- `GSD` owns roadmap / phase planning artifacts under `.planning/*`.
- `coder` owns code execution after PM context is prepared.
- `bridge` only relays progress/completion from child sessions to parent sessions.

PM should not pretend to be the execution worker.
GSD should not pretend to own task/doc truth.
bridge should not be described as a task/doc owner.

## Source Of Truth Policy

Treat the state planes separately:

- task backend is execution truth for tracked work
- PROJECT / ROADMAP / STATE and phase docs are long-form planning truth
- `.pm/*.json` is repo-local cache and handoff state
- OpenClaw session/state is runtime truth for ACP runs and bridge delivery

When these disagree, resolve the mismatch explicitly instead of silently overwriting one with another.

Current implementation lives in:
- `scripts/pm.py`
- `scripts/pm_commands.py`
- `scripts/pm_cli.py`
- `scripts/pm_context.py`
- `scripts/pm_tasks.py`
- `scripts/pm_worker.py`
- `scripts/pm_bootstrap.py`
- `scripts/pm_docs.py`
- `scripts/pm_auth.py`
- `scripts/pm_attachments.py`
- `scripts/pm_dispatch.py`
- `scripts/pm_config.py`
- `scripts/pm_io.py`
- `scripts/pm_runtime.py`
- `scripts/pm_scan.py`

## Default Workflow

For tracked work, follow this order:

1. Ensure PM context exists.
2. Resolve whether the work maps to an existing task or needs a new task.
3. Refresh context and inspect `current_task` / `next_task`.
4. Produce plan/refine/coder bundle when needed.
5. Execute through `pm run` or a downstream workflow.
6. Write progress, evidence, and completion back through `pm`.

For repo-local bootstrap or install verification, use this lighter sequence first:

1. `pm init --project-name "<项目名>" --dry-run`
2. `pm context --refresh`
3. `pm route-gsd --repo-root .`

This verifies local PM/GSD state before you depend on real Feishu bindings.

## Command Workflow

### 1. Initialize or Refresh Context

If the repo is not initialized yet or `.pm/current-context.json` is missing:

```bash
python3 skills/pm/scripts/pm.py init --project-name "<项目名>" --write-config
```

默认会尝试把当前 repo 自动登记到 OpenClaw 根级 `project-review/main_review_sources.json`，供后续 `main` 周报/月报汇总使用。
如果这个项目不想进入全局汇总，可显式关闭：

```bash
python3 skills/pm/scripts/pm.py init --project-name "<项目名>" --no-main-review-source
```

如果要先确认会绑定/创建哪些清单、文档和 workspace，先用：

```bash
python3 skills/pm/scripts/pm.py init --project-name "<项目名>" --dry-run
```

如果项目名包含中文或其他非 ASCII 字符，补 `--english-name`：

```bash
python3 skills/pm/scripts/pm.py init --project-name "测试项目" --english-name demo --dry-run
```

`workspace-init` 只保留为兼容别名；后续统一使用 `init`。
默认只需要传 `project-name`；tasklist 和 doc folder 默认都直接使用这个项目名。若遇到同名歧义，命令会直接失败，此时改用 `--tasklist-guid` / `--doc-folder-token` 明确绑定。
如果没有传 `--group-id`，`dry-run` 里的 `workspace_bootstrap` 为 `null` 是预期行为，不代表失败。

Otherwise start from:

```bash
python3 skills/pm/scripts/pm.py context --refresh
```

For quick routing:

```bash
python3 skills/pm/scripts/pm.py next --refresh
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
```

For board-style read models:

```bash
python3 skills/pm/scripts/pm.py board --include-completed
python3 skills/pm/scripts/pm.py board-task --task-id T123 --include-completed
```

`board` returns a project/task/review aggregate for frontend or adapter debugging.
`board-task` returns one task with parsed progress timeline and related review summaries.
If task comments contain a `[[pm_event]] ... [[/pm_event]]` block, PM will parse it as structured progress metadata while preserving the human-readable comment body.

### 2. Create or Resolve a Task

When the user gives a new tracked request:

```bash
python3 skills/pm/scripts/pm.py create --summary "<summary>" --request "<request>"
```

默认会在当前 tasklist 内按规范化标题做去重；只有明确需要重复建同题任务时，才用：

```bash
python3 skills/pm/scripts/pm.py create --summary "<summary>" --request "<request>" --force-new
```

When the task may already exist:

```bash
python3 skills/pm/scripts/pm.py search --query "<keywords>"
python3 skills/pm/scripts/pm.py get --task-id T123
```

### 3. Build Task Context for Planning or Execution

For planning:

```bash
python3 skills/pm/scripts/pm.py plan --task-id T123
python3 skills/pm/scripts/pm.py refine --task-id T123
```

For execution:

```bash
python3 skills/pm/scripts/pm.py coder-context --task-id T123
```

### 4. Dispatch Execution

Preferred managed execution path:

```bash
python3 skills/pm/scripts/pm.py run --task-id T123
```

This should be the default when the task should stay inside PM-managed automation.

### 5. Write Back Collaboration State

Progress update:

```bash
python3 skills/pm/scripts/pm.py comment --task-id T123 --content "<progress>"
```

Refine or replace task description:

```bash
python3 skills/pm/scripts/pm.py update-description --task-id T123 --mode append --content "<refined plan>"
```

Completion:

```bash
python3 skills/pm/scripts/pm.py complete --task-id T123 --content "<result summary>"
```

Completion due sync config:

- `pm.json.task.completion_due_mode` controls whether PM also copies `completed_at` into `due` when a task is completed.
- `never` is the default and only writes `completed_at`.
- `if_missing` writes `due.timestamp = completed_at` only when the task does not already have a due value.
- `always` always overwrites `due` with the completion timestamp.
- Legacy `pm.json.task.sync_completed_at_to_due` is still accepted for compatibility: `true -> if_missing`, `false -> never`.
- This setting affects both `pm complete` and `pm materialize-gsd-tasks` when a GSD plan already has `SUMMARY.md`.

## Mandatory Behavioral Rules

- For managed project work, do not skip PM and jump straight to coding.
- Treat every user requirement that changes project behavior, docs, workflow, or code as managed work unless the user explicitly says it is a throwaway local edit.
- Prefer `pm context --refresh` before making task-routing decisions.
- If the user request clearly maps to tracked work, either bind to an existing task or create one first.
- Treat task state as the execution source of truth.
- Treat PROJECT / ROADMAP / STATE as long-form narrative truth.
- If a requirement changes the PM/coder/review/front-agent workflow, update the relevant `skills/*/SKILL.md` and both copies of `AGENTS.md` as part of the same task.
- When execution happens outside `pm run`, still write the result back via `pm comment`, `pm update-description`, or `pm complete`.
- Use `pm search` / `pm get` before creating a duplicate task when the request may already be tracked.

## GSD Integration Policy

PM should be the front door. GSD should be a downstream execution/planning backend, not a competing entrypoint.

Desired routing model:

1. User request enters through PM.
2. PM resolves or creates the task.
3. PM produces context and planning bundle.
4. Downstream execution may use:
   - `pm run`
   - direct coder work
   - future GSD workflow
5. Outcome is written back through PM.

Current limitation:

- `pm.py` 已能提供 `route-gsd` 与 `plan-phase`，可用于 phase 级规划入口。
- `materialize-gsd-tasks` 仍主要面向 Feishu task backend，会把 `PLAN.md` 同步成任务。
- 如果当前不依赖 Feishu，可以先本地执行 phase 计划，再补 `SUMMARY.md` / `STATE.md`。
- 不要把“本地 phase 执行”误写成“已经完成了 Feishu 任务同步”。

Command boundary:

- `route-gsd` answers "what should this phase do next"
- `plan-phase` produces or refreshes phase planning artifacts
- `materialize-gsd-tasks` converts those phase plans into tracked tasks when task syncing is desired

If you only need a local planning/execution loop, stop before `materialize-gsd-tasks`.

Temporary manual pattern for GSD-enabled work:

1. `pm context --refresh`
2. `pm route-gsd --repo-root .`
3. `pm plan-phase --repo-root . --phase <N>` when the phase needs planning
4. execute the phase locally or via PM-managed flow
5. `pm materialize-gsd-tasks --repo-root . --phase <N>` only when you want task syncing

## Future GSD Hook Points

When implementing GSD integration later, keep the seam here:

- `pm plan` can route to GSD planning when task type requires it
- `pm run` can select `coder` vs `gsd` backend
- PM must still own:
  - task creation
  - context cache
  - task/doc write-back
  - final completion state

Do not let GSD bypass PM task/doc synchronization.

## Output Expectations For Agents Using This Skill

When acting through PM, report:

- chosen task id or newly created task id
- whether context was refreshed
- whether a plan/refine/coder bundle was generated
- whether execution was dispatched or done locally
- what was written back to task/doc

If PM could not fully execute the workflow, state the exact missing piece:

- missing init
- missing auth
- missing task id
- missing doc binding
- Feishu task/doc sync intentionally skipped

## Practical Guidance

- Prefer small, explicit PM commands over hidden state assumptions.
- Keep `.pm/current-context.json` fresh after meaningful task transitions.
- Use `pm normalize-titles` only as a deliberate repair step, not as a default read path.
- If attachments or completion evidence matter, use PM’s attachment and completion commands instead of ad-hoc local notes.
