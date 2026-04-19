# WORKFLOW_AUTO

## Default Loop

1. Read `{{pm_config_path}}` and repo-local PM context first.
2. Confirm the active task and source of truth before coding.
3. Route roadmap and phase questions back through PM/GSD.
4. Let `{{default_worker}}` handle implementation work.
5. Let `{{reviewer_worker}}` handle review-only follow-up when needed.

## Dispatch Contract

- Default tracked execution path: `pm run --task-id <T123>`
- If `{{default_worker}}` is dispatched through ACP one-shot execution, the run should be observable:
  - use `runtime="acp"` + `mode="run"` + `streamTo:"parent"`
  - prefer parent-relayed progress over state-only polling
- If progress checks show `running` but no stream/transcript evidence, treat the run as low-confidence / weakly observable rather than assuming healthy execution

## Collaboration Surface

- tasklist: `{{tasklist_name}}`
- doc folder: `{{doc_folder_name}}`
- channel: `{{channel}}`
- group id: `{{group_id}}`
