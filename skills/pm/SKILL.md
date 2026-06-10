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
- coder handoff bundles for local or downstream execution
- progress and completion write-back to task comments / descriptions
- attachment upload and completion flow

PM is the tracked-work front door. If a request should become managed work, it should enter here first rather than starting from GSD or coder directly.

## Feishu Delivery Default

PM Feishu task/doc delivery defaults to the official `lark-cli` adapter. OpenClaw/Gateway/Hermes is no longer a supported default delivery path for PM Feishu operations. Local task/doc backends remain independent and must not invoke `lark-cli`.

Use `pm lark status`, `pm lark doctor`, or `pm lark login --exec` to inspect or initialize official `lark-cli` auth. Do not write app secrets, tenant secrets, access tokens, refresh tokens, or user tokens into `pm.json`.

## Role Boundary

Use this contract consistently:

- `PM` owns tracked work intake, task/doc synchronization, repo-local cache, and execution handoff.
- `GSD` owns roadmap / phase planning artifacts under `.planning/*`.
- `coder` owns code execution after PM context is prepared.
- `bridge` is not part of the default PM task/doc delivery path.

PM should not pretend to be the execution worker.
GSD should not pretend to own task/doc truth.
bridge should not be described as a task/doc owner or required PM dependency.

## Source Of Truth Policy

Treat the state planes separately:

- task backend is execution truth for tracked work
- PROJECT / ROADMAP / STATE and phase docs are long-form planning truth
- `.pm/*.json` is repo-local cache and handoff state
- OpenClaw session/state is runtime truth only when an explicit ACP runtime is in use; PM Feishu delivery defaults to official `lark-cli`, not OpenClaw/Gateway/Hermes

When these disagree, resolve the mismatch explicitly instead of silently overwriting one with another.

Current implementation lives in:
- `scripts/pm.py`
- `scripts/pm_commands.py`
- `scripts/pm_cli.py`
- `scripts/pm_command_support.py`
- `scripts/pm_context.py`
- `scripts/pm_tasks.py`
- `scripts/pm_worker.py`
- `scripts/pm_bootstrap.py`
- `scripts/pm_docs.py`
- `scripts/pm_flow_commands.py`
- `scripts/pm_init_commands.py`
- `scripts/pm_init_command_support.py`
- `scripts/pm_task_commands.py`
- `scripts/pm_task_command_support.py`
- `scripts/pm_auth.py`
- `scripts/pm_attachments.py`
- `scripts/pm_config.py`
- `scripts/pm_io.py`
- `scripts/pm_lark_cli.py`
- `scripts/pm_lark_commands.py`
- `scripts/pm_local_backend.py`
- `scripts/pm_project_review.py`
- `scripts/pm_runtime.py`
- `scripts/pm_scan.py`
- `scripts/pm_task_assignment.py`
- `scripts/pm_task_members.py`
- `scripts/pm_workspace.py`

## Default Workflow

For tracked work, follow this order:

1. Ensure PM context exists.
2. Resolve whether the work maps to an existing task or needs a new task.
3. Refresh context and inspect `current_task` / `next_task`.
4. Produce plan/refine/coder bundle when needed.
5. Execute locally or through the chosen downstream worker using the generated context.
6. Write progress, evidence, and completion back through `pm`.

For repo-local PM read-model verification, use this lighter sequence first:

1. `pm context --refresh`
2. `pm next --refresh`

This verifies local PM task state before you depend on real Feishu bindings without assuming bootstrap.

## Command Workflow

### 1. Initialize or Refresh Context

Default start:

```bash
python3 skills/pm/scripts/pm.py context --refresh
```

Only use `init` when the user explicitly asks for PM bootstrap/binding, or you have already confirmed that this repo truly lacks PM resources and bootstrap is the intended next step.

Explicit bootstrap examples:

```bash
python3 skills/pm/scripts/pm.py init --project-name "<项目名>" --write-config
python3 skills/pm/scripts/pm.py init --project-name "<项目名>" --dry-run
python3 skills/pm/scripts/pm.py init --project-name "测试项目" --english-name demo --dry-run
```

`init` 统一绑定当前真实代码仓库目录，不再保留 `workspace-init` 兼容别名。
默认只需要传 `project-name`；tasklist 和 doc folder 默认都直接使用这个项目名。若遇到同名歧义，命令会直接失败，此时改用 `--tasklist-guid` / `--doc-folder-token` 明确绑定。
`dry-run` 会返回 `repo_contract` 预览；真实执行会写入或更新 repo-local `AGENTS.md` 的 managed contract。

`init` 的默认目标是绑定当前真实代码仓库目录：写入或更新 `pm.json`、`.pm/*` 上下文缓存，以及 repo-local `AGENTS.md` 的 managed contract。Claude Code 和 Codex 都应从这个 repo root 启动或 `cd` 进去工作；OpenClaw workspace / Gateway / Hermes 绑定不再是初始化路径。

Otherwise start from:

```bash
python3 skills/pm/scripts/pm.py context --refresh
```

For quick routing:

```bash
python3 skills/pm/scripts/pm.py next --refresh
python3 skills/pm/scripts/pm.py coder-context --task-id T123
```

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

### 4. Execute With Prepared Context

`pm` currently prepares execution context; it does not expose a `run` command in the CLI command surface. After generating `coder-context`, execute from the real repo root with the chosen worker (usually Codex for engineering work), then return evidence through PM write-back commands.

Read these files before execution:

- `pm.json`
- `.pm/current-context.json`
- `.pm/coder-context.json`

If planning or refinement was generated, also read:

- `.pm/plan-context.json`
- `.pm/refine-context.json`

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
- This setting affects `pm complete` when writing completion state back to the task backend.

## Mandatory Behavioral Rules

- For managed project work, do not skip PM and jump straight to coding.
- Prefer `pm context --refresh` before making task-routing decisions.
- If the user request clearly maps to tracked work, either bind to an existing task or create one first.
- Treat task state as the execution source of truth.
- Treat PROJECT / ROADMAP / STATE as long-form narrative truth.
- Since execution happens outside PM's current CLI command surface, write the result back via `pm comment`, `pm update-description`, or `pm complete`.
- Use `pm search` / `pm get` before creating a duplicate task when the request may already be tracked.

## GSD Integration Policy

PM should be the front door. GSD should be a downstream execution/planning backend, not a competing entrypoint.

Desired routing model:

1. User request enters through PM.
2. PM resolves or creates the task.
3. PM produces context and planning bundle.
4. Downstream execution may use:
   - direct coder work
   - future GSD workflow
5. Outcome is written back through PM.

Current limitation:

- The current PM CLI does not expose `route-gsd`, `plan-phase`, `materialize-gsd-tasks`, or `run` commands.
- If GSD planning is needed today, create or resolve the PM task first, generate `plan` / `refine` / `coder-context`, then execute the GSD workflow separately from the repo root.
- If current work does not depend on Feishu, execute locally and write back `SUMMARY.md` / `STATE.md` evidence where appropriate.
- Do not write “Feishu task sync completed” unless an actual task backend sync command ran and succeeded.

Command boundary:

- `plan` and `refine` produce task planning bundles
- `coder-context` produces the implementation handoff bundle
- external GSD workflows may consume PM context, but must not bypass PM task/doc write-back

If you only need a local planning/execution loop, stop after generating PM context and avoid implying task sync.

## Future GSD Hook Points

When implementing GSD integration later, keep the seam here:

- `pm plan` can route to GSD planning when task type requires it
- a future execution command can select `coder` vs `gsd` backend
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
