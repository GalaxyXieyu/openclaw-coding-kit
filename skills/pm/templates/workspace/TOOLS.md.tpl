# TOOLS

- PM config: `{{pm_config_path}}`
- Task backend: `{{task_backend_type}}`
- Default worker: `{{default_worker}}`
- Reviewer worker: `{{reviewer_worker}}`

## Expected Entry Points

- `pm context --refresh`
- `pm route-gsd --repo-root {{repo_root}}`
- `pm coder-context`
- `pm run --task-id <T123>`

## How To Dispatch ACP Work

Preferred managed path:

1. refresh PM context
2. resolve or create the task
3. build `pm coder-context`
4. dispatch with `pm run --task-id <T123>`

If implementation is dispatched through ACP `sessions_spawn` instead of `pm run`, use this contract:

- for one-shot ACP execution (`runtime="acp"` + `mode="run"`), default to `streamTo:"parent"`
- this is required for parent-side progress relay and lightweight observer visibility
- without `streamTo:"parent"`, `accepted` or `running` may only mean the session exists, not that useful progress is observable
- only skip it for thread-bound persistent sessions (`mode="session"`) or intentionally silent/background runs
