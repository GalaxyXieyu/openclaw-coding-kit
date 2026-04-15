# Eggturtle Sample

Use Eggturtle miniapp as the first sample project because it already has:

- clear `app.config.ts`
- route constants
- wrapper page files
- canonical miniapp runbook
- enough navigation signals to build a first route graph

## Expected First Findings

- registered pages should be derived from `apps/miniapp/src/app.config.ts`
- route constants should come from `apps/miniapp/src/runtime/page-paths.ts`
- wrapper screen mapping should come from `apps/miniapp/src/pages/**/index.tsx` and `src/subpackages/**/index.tsx`
- documentation drift should be checked against `docs/miniapp-runbook.md`

## Current Known Drift

When this sample is regenerated against the current codebase, it should highlight:

- `guiquan-marketplace`
- `guiquan-marketplace-detail`

These routes exist in page constants and wrapper files, but are not registered in `app.config.ts`.
