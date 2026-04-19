---
name: project-review
description: Use this skill for proactive project review, weekly/monthly review generation, key event alerts, Feishu card payload design, and review writeback. Trigger when the user wants active push, review summaries, project retros, plain-language status reviews, or callback/archive rules tied to PM tasks.
---

# Project Review

`project-review` is the review and push layer that sits after `pm`.

Use it when tracked work already exists in PM and the user wants the system to proactively summarize progress, push weekly/monthly updates, or send key event alerts to Feishu.

Treat `project-review` as the umbrella review skill.
Do not split everyday project review, code review, docs review, and UI/UX review into separate top-level truth systems unless a future workflow truly needs that.

When this skill is installed under the OpenClaw runtime root, treat the OpenClaw runtime as the default home for aggregate review config and state.
`main` should mean the user's bound main-agent conversation target, not an arbitrary project group.

## What This Skill Owns

- weekly review generation
- monthly review generation
- key event alert generation
- code health review generation
- docs hygiene review generation
- UI/UX verification routing
- graph-based structure observation routing
- plain-language per-project summaries
- risk card payload structure
- Feishu card payload structure
- callback routing and archive/writeback rules
- review state and idempotency rules

`project-review` does not replace `pm`.
`pm` remains the task/doc source of truth.

## Role Boundary

Use this contract consistently:

- `pm` owns task intake, task/doc truth, and repo-local context.
- `project-review` owns review logic, copy generation, card composition, callback semantics, and archive state.
- `openclaw-lark-bridge` or another delivery adapter owns the actual Feishu tool invocation.

Do not make `project-review` responsible for task creation truth.
Do not make `pm` responsible for review card behavior.

## Internal Review Lanes

Inside `project-review`, organize daily review work as indexed lanes:

- `project-retro`: weekly/monthly/project-event summaries
- `code-review`: recent-commit diff review with P0/P1/P2 findings
- `docs-review`: docs drift, stale files, AGENTS drift, pruning candidates
- `ui-ux-review`: post-fix smoke or targeted UI verification
- `graph-observe`: weekly/monthly structure graph refresh and hotspot inspection

These are internal sub-flows, not separate truth owners.
External skills can be inspiration sources, but the operational contract should live here.

## MVP Scope

Current MVP only covers:

- `weekly_review_card_v1`
- `monthly_review_card_v1`
- `event_alert_card_v1`
- `code_health_risk_card_v1`
- per-project summary copy in plain Chinese
- callback actions: open, acknowledge, snooze, archive
- Feishu live send through the local OpenClaw bot channel

Out of scope for now:

- knowledge cards
- NotebookLM integration
- daily group spam
- graph-driven semantic recall

## Default Workflow

1. Refresh PM context and gather the current project/task snapshot.
2. Detect one trigger: `weekly`, `monthly`, `event`, or `code-health`.
3. Route into the needed internal lane set.
4. For `project-retro`, generate one short summary per project.
5. For `code-health`, inspect the recent commit window and changed scope.
6. Run `code-review` lane, then `docs-review` lane.
7. If UI-related files are touched or a fix changes UI paths, run `ui-ux-review` lane.
8. For weekly/monthly deeper structure inspection, optionally run `graph-observe`.
9. Validate project summaries with `scripts/summary_guard.py`.
10. Choose the matching card pack shape from `references/card-packs.md`.
11. Deliver through Feishu.
12. Write callback and archive state back to the review store and PM comment/doc surface when needed.

## Quick Commands

Prepare one review draft:

```bash
python3 skills/project-review/scripts/review_orchestrator.py prepare \
  --payload @/tmp/project-review/weekly_payload.json \
  --state-path .pm/project-review-state.json
```

Render the stored record into a Feishu card preview:

```bash
python3 skills/project-review/scripts/feishu_card_renderer.py \
  --record @/tmp/project-review/review-record.json
```

Send one prepared review to Feishu:

```bash
python3 skills/project-review/scripts/review_delivery.py \
  --review-id RV-xxxx \
  --state-path .pm/project-review-state.json
```

Build one cross-project main review:

```bash
python3 skills/project-review/scripts/main_review_builder.py build
```

Send all recently updated projects to `main`:

```bash
python3 skills/project-review/scripts/main_review_builder.py send
```

Run one code-health review with Codex end to end:

```bash
python3 skills/project-review/scripts/review_orchestrator.py codex \
  --payload @/tmp/project-review/code-health.json \
  --model codex
```

## Global Runtime Layout

For all-project weekly/monthly reviews, prefer one global runtime config near `openclaw.json`:

- `<openclaw-runtime>/project-review/main_review_sources.json`: global `main` target and source repo list
- `<openclaw-runtime>/project-review/project-review-state.json`: aggregate review state/history

Repo registration rule:

- `pm init` should auto register the current repo into the global `sources`
- use `pm init --no-main-review-source` when a repo should stay out of the aggregate review
- set one source entry to `"enabled": false` if you want to pause that project without deleting it

Resolution order for the aggregate review config:

1. `--config`
2. `PROJECT_REVIEW_MAIN_REVIEW_CONFIG` / `OPENCLAW_PROJECT_REVIEW_MAIN_REVIEW_CONFIG`
3. `<openclaw-runtime>/project-review/main_review_sources.json`
4. bundled skill config fallback

Recommended target shape:

```json
{
  "main_target": {
    "alias": "main",
    "channel": "feishu",
    "chat_id": "oc_xxx",
    "chat_name": "宇宇(main agent)"
  }
}
```

Legacy `main_chat_id` / `main_chat_name` still work, but `main_target` is the preferred schema.

## Required Inputs

For reliable output, the review bundle should contain:

- project name
- target channel or chat binding
- period or event trigger
- active tasks
- recently completed tasks
- stale or blocked tasks
- recent commits or changed file list for code-health review
- optional PM doc/state links

If these fields are missing, fall back to a smaller summary instead of inventing certainty.

## Copy Rules

All user-facing summaries must follow these rules:

- use plain Chinese
- avoid business jargon
- avoid abstract technical slogans
- answer three things: what was done, what is still pending, what happens next
- target `<= 50` Chinese characters per project whenever possible

Read `references/copy-rules.md` before writing or validating card copy.

For deterministic checking or quick generation, use:

```bash
python3 skills/project-review/scripts/summary_guard.py build \
  --project "小程序" \
  --done "登录页" \
  --pending "支付联调" \
  --next "补测试"
```

Validate an existing one-line summary:

```bash
python3 skills/project-review/scripts/summary_guard.py check \
  --text "小程序做了登录页，还差支付联调，下一步先补测试。"
```

Check whether the repo had commits in the review window:

```bash
python3 skills/project-review/scripts/commit_window.py \
  --repo-root . \
  --since "yesterday 00:00" \
  --until "today 00:00" \
  --json
```

Daily review defaults should stay aligned with the PM nightly registration contract:

- run at `06:00` in `Asia/Shanghai`
- summarize the previous calendar day, not a rolling `24 hours ago` window
- focus on the previous day's commits, changed files, doc updates, and delivery risks

## References

Load only what you need:

- `references/product-spec.md`: user stories, trigger rules, writeback contract
- `references/review-lanes.md`: umbrella skill lane index and execution order
- `references/card-packs.md`: card types, sections, actions, archive behavior
- `references/copy-rules.md`: plain-language copy rules and banned wording
- `references/code-health-spec.md`: code review, docs hygiene, AGENTS drift, fix flow, UI/UX verification

## Implementation Notes

- Keep the review runtime small and deterministic.
- Prefer a finite card pattern set over a generic card platform.
- Use idempotency keys for send and callback handling.
- If a click changes state, write the new state first, then do PM writeback.
- Keep code review, docs review, and UI/UX review under one umbrella contract so daily quality retro only has one entrypoint.
