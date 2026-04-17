# PM Project Board Data Contract

> Status: draft
> Updated: 2026-04-17

## Goal

This contract defines the minimum real-data model for the AgentsGalaxy project board. The board should use Feishu task/comment/doc fields first. Only fields that Feishu does not provide with stable semantics should be parsed from structured comment content.

The frontend should stop depending on the old fake "department/member/score" model. The first production board should feel like a lightweight team development board:

- project overview
- task board grouped by real Feishu tasklists
- task progress timeline
- daily/project review summary

## Source Priority

Use this priority order when building API responses:

1. Feishu task fields are the source of truth for task identity, status, title, dates, members, tasklist section, attachments, and comments.
2. Feishu tasklists are the source of truth for board columns. Do not invent frontend-only groups.
3. Feishu comments are the source of truth for progress updates and human-readable execution notes.
4. Structured `pm_event` blocks inside comment content are optional metadata, parsed only when present.
5. Local `.pm/project-review-state.json` remains the current source for structured review records until review data is also persisted into Feishu.

Do not expose runtime-only fields in the board UI, including `agent_id`, `session_key`, `run_id`, model name, local process id, or dispatch internals.

## TypeScript Interfaces

```ts
export type BoardTaskType = 'planning' | 'development' | 'testing';

export type BoardTaskStatus = 'todo' | 'in_progress' | 'done' | 'blocked';

export type BoardScope = 'configured_tasklist' | 'all_visible_tasklists';

export interface BoardStats {
  totalTasks: number;
  todoTasks: number;
  inProgressTasks: number;
  blockedTasks: number;
  doneTasks: number;
}

export interface BoardProject {
  id: string;
  name: string;
  repoRoot?: string;
  taskBackend: 'feishu' | 'local';
  docBackend: 'feishu' | 'local';
  tasklistGuid?: string;
  tasklistName?: string;
  generatedAt: string;
}

export interface BoardTask {
  taskId: string;
  guid: string;
  url?: string;
  title: string;
  description?: string;
  status: BoardTaskStatus;
  type?: BoardTaskType;
  progress?: number;
  createdAt?: string | null;
  updatedAt?: string | null;
  startedAt?: string | null;
  dueAt?: string | null;
  completedAt?: string | null;
  sectionGuid?: string;
  tasklistGuid?: string;
  tasklistName?: string;
  members: BoardTaskMember[];
  attachments: BoardTaskAttachment[];
  latestEvent?: BoardCommentEvent;
}

export interface BoardColumn {
  id: string;
  kind: 'tasklist';
  title: string;
  tasklistGuid?: string | null;
  tasklistUrl?: string | null;
  updatedAt?: string | null;
  visibleTaskCount: number;
  hasMoreTasks: boolean;
  stats: BoardStats;
  tasks: BoardTask[];
}

export interface BoardTaskMember {
  id: string;
  role?: string;
  name?: string;
}

export interface BoardTaskAttachment {
  id?: string;
  name?: string;
  url?: string;
  mimeType?: string;
}

export interface BoardCommentEvent {
  id: string;
  taskGuid: string;
  taskId?: string;
  kind: 'progress' | 'start' | 'complete' | 'blocked' | 'note';
  type?: BoardTaskType;
  status?: BoardTaskStatus;
  progress?: number;
  startedAt?: string | null;
  endedAt?: string | null;
  content: string;
  rawContent: string;
  createdAt?: string | null;
  updatedAt?: string | null;
  creator?: {
    id?: string;
    type?: string;
    name?: string;
  };
  parsed: boolean;
}

export interface ReviewSummary {
  reviewId: string;
  status: 'draft' | 'ready' | 'sent' | 'skipped' | 'failed';
  projectName: string;
  triggerKind: 'daily' | 'nightly' | 'weekly' | 'manual' | string;
  title: string;
  summary?: string;
  done?: string;
  pending?: string;
  nextStep?: string;
  risks: ReviewRisk[];
  createdAt?: string | null;
  updatedAt?: string | null;
  sentAt?: string | null;
  delivery?: {
    chatId?: string | null;
    messageId?: string | null;
  };
}

export interface ReviewRisk {
  severity?: 'P0' | 'P1' | 'P2' | 'info';
  title: string;
  file?: string;
  line?: number;
  suggestion?: string;
}

export interface ProjectBoardResponse {
  project: BoardProject;
  scope: BoardScope;
  columns: BoardColumn[];
  stats: BoardStats;
  tasks: BoardTask[];
  recentEvents: BoardCommentEvent[];
  latestReview?: ReviewSummary;
}

export interface TaskDetailResponse {
  project: BoardProject;
  task: BoardTask;
  events: BoardCommentEvent[];
  relatedReviews: ReviewSummary[];
}
```

## Field Mapping

| Board field | Preferred source | Fallback source | Notes |
| --- | --- | --- | --- |
| `project.name` | `pm.json.project.name` | `.pm/current-context.json.project.name` | Display only. |
| `project.tasklistGuid` | `pm.json.task.tasklist_guid` | current context project field | Used to list Feishu tasks. |
| `columns[]` | visible Feishu tasklists | configured tasklist | Each tasklist is one board column. |
| `column.tasks[]` | tasks under that Feishu tasklist | none | List cards should not regroup by fake agent/team fields. |
| `task.taskId` | parsed task summary like `[T143]` | task description `任务编号` | Keep current PM prefix rule. |
| `task.guid` | Feishu task `guid` | none | Required for task detail and comments. |
| `task.title` | Feishu task `summary` normalized without id prefix | raw summary | Do not invent titles. |
| `task.status` | Feishu `completed_at` and progress event | Feishu `status` | `completed_at` means `done`; otherwise latest event may refine it. |
| `task.type` | latest parsed `pm_event.task_type` | parsed description label | Optional. Do not use frontend-only fake categories. |
| `task.progress` | latest parsed `pm_event.progress` | `100` when completed, otherwise undefined | Avoid fake progress if no event exists. |
| `task.startedAt` | Feishu `start.timestamp` | latest parsed `pm_event.started_at` | Feishu wins. |
| `task.dueAt` | Feishu `due.timestamp` | none | Feishu wins. |
| `task.completedAt` | Feishu `completed_at` | latest parsed `pm_event.ended_at` only for display | Do not mark done from comment alone unless API chooses to. |
| `task.sectionGuid` | first `tasklists[].section_guid` | none | Can support Feishu grouping. |
| `task.tasklistName` | resolved Feishu tasklist metadata | none | Display context only. |
| `task.members` | Feishu task `members` | empty array | UI can show assignee text, not fake avatars. |
| `task.attachments` | Feishu task `attachments` | empty array | Evidence and deliverables. |
| `event.content` | comment content after removing `pm_event` block | full comment content | Always preserve readable text. |
| `review` | `.pm/project-review-state.json` | Feishu card/message when later persisted | Current structured review is local. |

## Task Description Contract

The board list should stay compact. Full task context belongs in the task detail page. To make this work reliably, Feishu task descriptions should use stable section labels instead of long unstructured prose.

Recommended template:

```md
任务编号：T141
创建时间：2026-04-17 10:00:00 CST
类型：task
Repo：/abs/path/repo
任务类型：development
摘要：一句话说明这个任务到底要做什么。

需求：
- 目标 1
- 目标 2

验收：
- 可验证结果 1
- 可验证结果 2

执行要求：
- 约束 1
- 约束 2

重点风险：
- 风险 1
- 风险 2
```

Frontend parsing rules:

1. List cards should prefer `摘要` as the preview text.
2. If `摘要` is missing, fall back to the first bullet under `需求`.
3. Detail pages should render `需求` / `验收` / `执行要求` / `重点风险` as separate sections.
4. Avoid dumping long execution logs into task descriptions. Progress belongs in comments, ideally with optional `pm_event` blocks.
5. Keep each bullet to one concrete point. If a section becomes longer than 5 bullets, move secondary detail into comments or attachments.

This keeps the board visually compact while still allowing task detail pages to remain informative.

## Comment Event Format

Structured metadata should be small and business-facing. The human-readable body remains the main content.

```md
[[pm_event]]
schema: v1
kind: progress
task_type: development
status: in_progress
progress: 60
started_at: 2026-04-17T10:00:00+08:00
ended_at:
[[/pm_event]]

已完成接口联调，正在补测试和错误提示。
```

Allowed values:

| Field | Required | Values |
| --- | --- | --- |
| `schema` | yes | `v1` |
| `kind` | yes | `progress`, `start`, `complete`, `blocked`, `note` |
| `task_type` | no | `planning`, `development`, `testing` |
| `status` | no | `todo`, `in_progress`, `done`, `blocked` |
| `progress` | no | integer `0` to `100` |
| `started_at` | no | ISO8601 datetime |
| `ended_at` | no | ISO8601 datetime or empty |

Parsing rules:

1. If no `pm_event` block exists, return a `BoardCommentEvent` with `kind: 'note'`, `parsed: false`, and full comment text as `content`.
2. If a `pm_event` block exists but has invalid values, ignore invalid keys and keep the event as `parsed: false`.
3. Never drop the original comment. Keep `rawContent` for debugging and re-parsing.
4. The latest valid event can enrich `BoardTask.type`, `BoardTask.progress`, and non-authoritative `BoardTask.status`.

## Board List API

Recommended endpoint:

```http
GET /api/pm/board
```

Query options:

| Query | Default | Meaning |
| --- | --- | --- |
| `allVisibleTasklists=1` | off | Return every visible Feishu tasklist as a board column. |
| `limit=100` | `20` | Maximum task cards per column. |
| `commentLimit=2` | `5` | Number of comments read per task for latest event metadata. |
| `includeCompleted=1` | off | Include completed tasks in each column task list. |

Example response:

```json
{
  "project": {
    "id": "pm-toolkit",
    "name": "PM工具链",
    "repoRoot": "/Volumes/DATABASE/code/learn/openclaw-pm-coder-kit",
    "taskBackend": "feishu",
    "docBackend": "feishu",
    "tasklistGuid": "aee23437-3861-408c-aa8a-40a9a7c09dbc",
    "tasklistName": "选育溯源档案",
    "generatedAt": "2026-04-17T10:00:00+08:00"
  },
  "scope": "all_visible_tasklists",
  "columns": [
    {
      "id": "aee23437-3861-408c-aa8a-40a9a7c09dbc",
      "kind": "tasklist",
      "title": "选育溯源档案",
      "tasklistGuid": "aee23437-3861-408c-aa8a-40a9a7c09dbc",
      "tasklistUrl": "https://applink.feishu.cn/client/todo/task_list?guid=...",
      "visibleTaskCount": 4,
      "hasMoreTasks": false,
      "stats": {
        "totalTasks": 125,
        "todoTasks": 4,
        "inProgressTasks": 0,
        "blockedTasks": 0,
        "doneTasks": 121
      },
      "tasks": []
    }
  ],
  "stats": {
    "totalTasks": 4,
    "todoTasks": 3,
    "inProgressTasks": 1,
    "blockedTasks": 0,
    "doneTasks": 0
  },
  "tasks": [
    {
      "taskId": "T141",
      "guid": "9ad6731f-c581-41dc-be07-9fdc2975d23d",
      "title": "检查 nightly review 后台自动发送链路",
      "status": "in_progress",
      "type": "testing",
      "progress": 40,
      "startedAt": "2026-04-17T09:20:00+08:00",
      "dueAt": null,
      "completedAt": null,
      "sectionGuid": "c8039ab1-6c79-1fa1-efe0-2ffb9c542c82",
      "tasklistGuid": "aee23437-3861-408c-aa8a-40a9a7c09dbc",
      "members": [],
      "attachments": [],
      "latestEvent": {
        "id": "7629204947929746635",
        "taskGuid": "9ad6731f-c581-41dc-be07-9fdc2975d23d",
        "taskId": "T141",
        "kind": "progress",
        "type": "testing",
        "status": "in_progress",
        "progress": 40,
        "content": "正在验证 nightly review 发送链路和失败重试行为。",
        "rawContent": "[[pm_event]]\nschema: v1\nkind: progress\ntask_type: testing\nstatus: in_progress\nprogress: 40\n[[/pm_event]]\n\n正在验证 nightly review 发送链路和失败重试行为。",
        "createdAt": "1776312698000",
        "parsed": true
      }
    }
  ],
  "recentEvents": [],
  "latestReview": {
    "reviewId": "RV-5030a49b7a23",
    "status": "sent",
    "projectName": "全部项目",
    "triggerKind": "weekly",
    "title": "本周项目回顾",
    "summary": "PM工具链做了PM同步和文档收口，还差设计主Agent主动节律与知识沉淀。",
    "done": "PM同步和文档收口",
    "pending": "设计主Agent主动节律与知识沉淀",
    "nextStep": "交互看板样例",
    "risks": [],
    "createdAt": "2026-04-14T22:08:45+08:00",
    "updatedAt": "2026-04-15T09:33:45+08:00",
    "sentAt": null,
    "delivery": {
      "chatId": "oc_e4845bf45622f5c6d7471dfc7ed94dd0",
      "messageId": null
    }
  }
}
```

## Task Detail API

Recommended endpoint:

```http
GET /api/pm/tasks/:taskId
```

Example response:

```json
{
  "project": {
    "id": "pm-toolkit",
    "name": "PM工具链",
    "taskBackend": "feishu",
    "docBackend": "feishu",
    "generatedAt": "2026-04-17T10:00:00+08:00"
  },
  "task": {
    "taskId": "T143",
    "guid": "afe6ee75-0746-4659-b075-f5e8922a5750",
    "url": "https://applink.feishu.cn/client/todo/detail?guid=afe6ee75-0746-4659-b075-f5e8922a5750&suite_entity_num=t100276",
    "title": "修复代码健康风险 RV-8750999cc68d",
    "description": "本次需要修复 review RV-8750999cc68d 暴露出的代码健康问题。",
    "status": "done",
    "type": "development",
    "progress": 100,
    "updatedAt": "1776312645821",
    "completedAt": "1776312644000",
    "sectionGuid": "c8039ab1-6c79-1fa1-efe0-2ffb9c542c82",
    "tasklistGuid": "aee23437-3861-408c-aa8a-40a9a7c09dbc",
    "members": [],
    "attachments": []
  },
  "events": [
    {
      "id": "7629204947929746635",
      "taskGuid": "afe6ee75-0746-4659-b075-f5e8922a5750",
      "taskId": "T143",
      "kind": "complete",
      "type": "development",
      "status": "done",
      "progress": 100,
      "content": "已按合同把 5 个超长函数拆成更小的装配/helper 逻辑，保持 CLI / API / manifest 输出契约不变。",
      "rawContent": "执行进展 T143：\n**完成情况**\n已按合同把 5 个超长函数拆成更小的装配/helper 逻辑，保持 CLI / API / manifest 输出契约不变。",
      "createdAt": "1776312698000",
      "parsed": false
    }
  ],
  "relatedReviews": [
    {
      "reviewId": "RV-8750999cc68d",
      "status": "sent",
      "projectName": "PM工具链",
      "triggerKind": "nightly",
      "title": "代码健康风险修复",
      "risks": [
        {
          "severity": "P1",
          "title": "函数偏长，建议拆责任",
          "file": "skills/pm/scripts/pm_api.py"
        }
      ]
    }
  ]
}
```

## Frontend Rendering Rules

The first board should render with a small set of neutral states:

| UI area | Data |
| --- | --- |
| Header | `project.name`, `stats`, `latestReview.updatedAt` |
| Task board | `tasks`, grouped by `sectionGuid` first, then `status` |
| Task card | `title`, `status`, `type`, `progress`, `startedAt`, `dueAt`, `latestEvent.content` |
| Task detail | `description`, dates, attachments, `events` |
| Timeline | parsed events and plain comments in chronological order |
| Review panel | `latestReview.summary`, `risks`, `nextStep` |

Avoid these UI concepts for the PM board:

- fake departments
- fake agents or avatars
- score bars or stars
- high-saturation color taxonomy
- runtime identifiers
- frontend-only task categories that do not exist in Feishu or `pm_event`

## Implementation Notes

The first backend adapter can be intentionally thin:

1. Read project config from `pm.json`.
2. Read current task snapshot from `.pm/current-context.json` for a fast first board.
3. Fetch full task details and comments from Feishu through the existing PM APIs.
4. Parse optional `pm_event` blocks in comments.
5. Read latest structured review from `.pm/project-review-state.json`.
6. Return `ProjectBoardResponse` and `TaskDetailResponse`.

Later, if review records are also persisted into Feishu docs or a Feishu Base table, only the review adapter should change. The frontend contract should stay stable.
