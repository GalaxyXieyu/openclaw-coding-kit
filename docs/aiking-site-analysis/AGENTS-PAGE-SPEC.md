# Aiking Agents Page Prototype Spec

## 1. Purpose

This document is the source of truth for the `/agents` page prototype.

Use it for:

- page positioning
- required modules
- tab behavior
- componentization boundaries
- empty / loading / error states
- page-specific design logic
- Next.js implementation structure

Do not use this file for:

- whole-site route planning
- global design token decisions
- backend integration details
- database schema design

Those belong in:

- `PAGE-ARCHITECTURE.md`
- `DESIGN-LOGIC-AND-NEXTJS-ARCHITECTURE.md`

## 2. Page Role

`/agents` is the most product-like page in the prototype.

Its job is not to behave like a chat page.

Its job is to make the visitor feel:

- this is a living multi-agent organization
- work is structured by teams and workflows
- the system is not only running, it is also evolving
- there is real research thinking behind the product story

In one sentence:

> Build this page as a public-facing AI operations showcase, not as an admin dashboard and not as a chatbot UI.

## 3. Live Reference Snapshot

Current visible live copy confirms the following core structure:

- page title: `小龙虾实时交流`
- subtitle: `OpenClaw 多智能体协作动态`
- top tabs:
  - `协作动态`
  - `进化面板`
  - `研究报告`
- research paper card:
  - title: `Organizational Mirroring: LLM Multi-Agent Architectures for Scalable Autonomous Workflows`
  - DOI: `10.5281/zenodo.18957649`
- summary panel title: `当前运行态`
- visible metrics:
  - active agents
  - messages
  - commands
- activity status legend:
  - `工作中`
  - `思考中`
  - `空闲`
  - `休息中`

This means the prototype must preserve:

- the public research framing
- the dashboard-style live summary
- the three-tab information model

## 4. Core User Goals

The page must support these user goals in this order:

1. understand what this multi-agent page is about in under 5 seconds
2. see whether the system is active right now
3. inspect how teams, workflows, and phases are organized
4. understand that the system improves over time
5. see that the system has research backing instead of being a pure marketing claim

## 5. Experience Goals

The prototype should create these feelings:

- alive
- operational
- credible
- structured
- technical but still public-facing

The prototype should avoid these feelings:

- generic AI chat demo
- enterprise admin backend
- academic PDF archive
- noisy cyberpunk poster

## 6. Page Information Architecture

Use this page structure.

```text
AgentsPage
  SiteHeader
  AgentsPageHeader
    PageEyebrow
    PageTitle
    PageSubtitle
    AgentsTabSwitcher
  AgentsBody
    ResearchPaperCard
    ActiveTabContent
      FeedTab
        LiveSummaryCard
        TeamFilterBar
        AgentStatusLegend
        AgentStatusStrip
        WorkflowTimeline
          WorkflowDayGroup
            WorkflowCard
            WorkflowDetailPanel
      EvolutionTab
        EvolutionOverviewNotice
        EvolutionLogPanel
        CapabilityMatrixPanel
        KeywordTrackingPanel
      ResearchTab
        ResearchIntroPanel
        ResearchFilterBar
        TopologyComparisonPanel
        DepartmentDistributionPanel
        QualitativeAnalysisPanel
        ExperimentBrowserPanel
  SiteFooter
```

## 7. Required Sections

Every prototype version of `/agents` must include these sections.

### 7.1 Header Area

Required:

- title
- subtitle
- tab switcher

Design intent:

- immediately tell users this is a live multi-agent collaboration page
- avoid long intro copy
- keep the frame product-like, not essay-like

### 7.2 Research Paper Card

Required:

- preprint / research label
- paper title
- short description
- DOI or external link

Design intent:

- place academic legitimacy above the fold
- make the page feel grounded in system design, not only visuals

### 7.3 Active Tab Content Area

Required:

- one visible tab at a time
- tab body should feel like a large content surface, not separate page navigation

Design intent:

- preserve a single-page dashboard feeling
- allow each tab to act like a self-contained dashboard module

## 8. Tab 1: Collaboration Feed

This is the primary tab. Build this first.

### 8.1 Purpose

Show the current operating state of the agent organization.

### 8.2 Required Modules

- `LiveSummaryCard`
- `TeamFilterBar`
- `AgentStatusLegend`
- `AgentStatusStrip`
- `WorkflowTimeline`

### 8.3 LiveSummaryCard

Required content:

- active agent count
- message count
- command count
- optional organization count if present in data

Rules:

- the main number must be visually dominant
- labels should use smaller mono or compact text
- the card should be readable even when all values are `0`

### 8.4 Agent Status Legend

Required states:

- `working`
- `thinking`
- `idle`
- `resting`

Reference mapping:

- `working`: activity within 2 hours
- `thinking`: activity within 6 hours
- `idle`: activity within 24 hours
- `resting`: no activity for more than 24 hours

Rules:

- each state must have a color and a short explanation
- do not rely on color only; always show label text

### 8.5 Team Filter

Required behavior:

- `all` filter
- one filter per team / department
- active filter is visually obvious

Purpose:

- let users inspect work by organization slice
- make the org structure visible without opening detail panels

### 8.6 Agent Status Strip

Recommended content per agent:

- agent name
- team name
- current status
- short current task or role label

Rules:

- this strip is for fast scanning
- do not turn it into a dense table
- desktop can show more meta
- mobile should collapse to concise cards or chips

### 8.7 Workflow Timeline

Required behavior:

- group by day
- support filtered results by selected team
- show workflow cards in descending recency
- allow detail expansion

Each workflow card should expose:

- workflow title
- time
- team / department
- status
- short summary
- phase count
- optional review score

Recognized workflow statuses:

- `completed`
- `running`
- `failed`
- `partial`

Recognized phase types:

- `direction`
- `planning`
- `execution`
- `review`
- `revision`
- `feedback`
- `summary`
- `meta_review`
- `verify`
- `evolve`

### 8.8 Workflow Detail Panel

This is the most important deep-inspection surface on the page.

Required content:

- workflow headline
- high-level summary
- phase group list
- detail markdown content
- review score panel if available

Rules:

- desktop: show as adjacent detail panel or inline expandable body
- mobile: show as stacked expansion card, drawer, or full-width detail surface
- preserve a clear master-detail relationship

### 8.9 Review Score Panel

If review data exists, show:

- total score out of `20`
- dimensions:
  - `accuracy`
  - `completeness`
  - `actionability`
  - `format`

Design intent:

- make quality visible
- reinforce that workflows are evaluated, not just executed

### 8.10 Empty State for Feed

Current live empty state is a strong reference:

- `0 个 Agent 正在活跃`
- `0 消息`
- `0 指令`
- `暂无协作动态`

Prototype rule:

- empty state must still feel intentional and well-designed
- do not leave blank panels
- use empty copy plus a structured surface

## 9. Tab 2: Evolution Panel

This tab proves the system is learning and adapting, not only producing activity logs.

### 9.1 Purpose

Show how the organization changes after real workflow execution.

### 9.2 Required Modules

- `EvolutionOverviewNotice`
- `EvolutionLogPanel`
- `CapabilityMatrixPanel`
- `KeywordTrackingPanel`

### 9.3 EvolutionOverviewNotice

Required message:

- explain that evolution data is produced from workflow execution history
- clarify that the panel becomes richer as more runs accumulate

### 9.4 Evolution Log

Recommended fields:

- time
- changed capability or rule
- source workflow
- impact summary

### 9.5 Capability Matrix

Purpose:

- show which capabilities or departments are strengthening
- make progression visible across multiple dimensions

Prototype format options:

- matrix grid
- compact heatmap
- card-based score rows

### 9.6 Keyword Tracking

Purpose:

- show recurring concepts across workflow history
- reveal what the organization is currently optimizing around

Prototype format options:

- ranked list
- small trend bars
- grouped token chips

### 9.7 Empty State for Evolution

Required message pattern:

- no evolution records yet
- data will appear after workflow execution accumulates

This tab should still ship in the first prototype even if backed by placeholder data.

## 10. Tab 3: Research Report

This tab turns the page from a pure product demo into a research-backed system narrative.

### 10.1 Purpose

Summarize experimental evidence about multi-agent organization design.

### 10.2 Required Narrative

The page should communicate these points:

- the report is based on real task data
- different organizational topologies were compared
- different topologies perform differently under different collaboration scopes

### 10.3 Required Modules

- `ResearchIntroPanel`
- `ResearchFilterBar`
- `TopologyComparisonPanel`
- `DepartmentDistributionPanel`
- `QualitativeAnalysisPanel`
- `ExperimentBrowserPanel`

### 10.4 Required Copy Anchors

Current reference indicates:

- study basis: `30` real tasks
- topologies:
  - `ORG`
  - `CREW`
  - `FLAT`
- example conclusion:
  - `ORG` performs best on cross-department tasks
  - `CREW` is most efficient on single-department tasks

### 10.5 Research Filters

Recommended filter options:

- `all`
- `single department`
- `cross department`
- `whole organization`

### 10.6 Experiment Browser

Purpose:

- allow users to inspect specific experiment slices
- make the report feel browsable instead of static

Recommended fields:

- task category
- department scope
- run count
- code lines
- topology outcome

## 11. State Model

The prototype should plan around this page state.

```ts
type AgentsPageState = {
  activeTab: "feed" | "evolution" | "research";
  selectedTeamId: "all" | string;
  selectedWorkflowId: string | null;
  expandedPhaseIds: string[];
  feedCursor: string | null;
  isFeedLoading: boolean;
  isEvolutionLoading: boolean;
  isResearchLoading: boolean;
  hasFeedError: boolean;
  hasEvolutionError: boolean;
  hasResearchError: boolean;
};
```

Data domains expected by the page:

- `agents`
- `teams`
- `commands`
- `registry`
- `dailyFeed`
- `evolutionLog`
- `capabilities`
- `keywords`

## 12. Component Inventory

Use the following component boundaries.

| Component | Responsibility |
|---|---|
| `AgentsPageTemplate` | page shell and layout rhythm |
| `AgentsPageHeader` | title, subtitle, intro frame |
| `AgentsTabSwitcher` | tab state and tab trigger UI |
| `ResearchPaperCard` | paper metadata and external CTA |
| `LiveSummaryCard` | high-level operating metrics |
| `TeamFilterBar` | team-level narrowing |
| `AgentStatusLegend` | state meanings |
| `AgentStatusStrip` | quick scan of agent roster |
| `WorkflowTimeline` | grouped workflow list |
| `WorkflowCard` | single workflow summary card |
| `WorkflowDetailPanel` | selected workflow details |
| `WorkflowPhaseGroup` | grouped phases inside detail |
| `ReviewScorePanel` | workflow quality scoring |
| `EvolutionOverviewNotice` | empty-intent explainer |
| `EvolutionLogPanel` | evolution record list |
| `CapabilityMatrixPanel` | capability visibility surface |
| `KeywordTrackingPanel` | keyword clusters or trend list |
| `ResearchIntroPanel` | research context |
| `ResearchFilterBar` | report-level filter state |
| `TopologyComparisonPanel` | topology comparison charts |
| `DepartmentDistributionPanel` | department composition view |
| `QualitativeAnalysisPanel` | conclusions and observations |
| `ExperimentBrowserPanel` | browsable experiment dataset |
| `AgentsEmptyState` | empty-state framing |
| `AgentsSkeleton` | loading placeholders |
| `AgentsErrorState` | recoverable error UI |

## 13. Interaction Rules

### 13.1 Tabs

- tab switching should not navigate to separate routes
- keep the page header and paper card persistent
- tab content should crossfade or animate lightly

### 13.2 Workflow Selection

- clicking a workflow card selects it
- clicking the same workflow again may collapse it
- selected state must be visually obvious

### 13.3 Detail Fetching

- detail content may load on demand
- use skeleton or inline loading state
- never freeze the whole page when loading one workflow detail

### 13.4 Team Filtering

- team filtering applies to roster and workflow list together
- summary card remains global unless there is a deliberate filtered-summary mode

### 13.5 Mobile Adaptation

- reduce simultaneous panels
- prefer vertical flow
- detail should appear beneath the selected card or in a drawer

## 14. Empty, Loading, and Error States

### 14.1 Empty

All tabs need an intentional empty state.

Guideline:

- empty does not mean blank
- keep titles, explanations, and light structure

### 14.2 Loading

Use:

- skeleton shimmer for cards and panels
- spinner only for local detail fetch or compact async actions

### 14.3 Error

Use:

- one clear message
- retry action
- fallback copy that does not expose internal backend details

## 15. Design Thinking

### 15.1 Visual Positioning

This page should sit between:

- a public landing page
- a product dashboard
- a research system showcase

It should not fully become any one of them.

### 15.2 Surface Language

Recommended visual language:

- dark layered background
- glass-like panels
- neon green as primary active accent
- purple as secondary support accent
- subtle grid or technical texture

### 15.3 Density Strategy

Rules:

- summary panels can be dense
- detail content must stay readable
- metrics should feel compact, not giant KPI tiles
- charts should feel embedded into the page, not isolated report screenshots

### 15.4 Content Tone

Use copy that feels:

- precise
- system-oriented
- public-facing

Avoid copy that feels:

- too playful
- too enterprise
- too academic

## 16. Motion and Animation

The page uses motion to suggest liveliness and state changes.

Recommended motion set for the prototype:

- page content fade-in with slight upward translate
- tab content crossfade
- hover glow on interactive panels
- skeleton shimmer during loading
- compact spinner for on-demand detail loads
- pulsing status dot for active states
- expand / collapse animation for workflow details and phase groups
- light stagger reveal for timeline cards

Motion rules:

- keep durations short
- motion should support hierarchy and system state
- do not add decorative looping animation to large surfaces

## 17. Next.js Slice Structure

Use a page-specific feature slice.

```text
src/
  app/
    (product)/
      agents/
        page.tsx
  features/
    agents/
      components/
        agents-page-template.tsx
        agents-page-header.tsx
        agents-tab-switcher.tsx
        research-paper-card.tsx
        live-summary-card.tsx
        team-filter-bar.tsx
        agent-status-legend.tsx
        agent-status-strip.tsx
        workflow-timeline.tsx
        workflow-card.tsx
        workflow-detail-panel.tsx
        workflow-phase-group.tsx
        review-score-panel.tsx
        evolution-log-panel.tsx
        capability-matrix-panel.tsx
        keyword-tracking-panel.tsx
        research-intro-panel.tsx
        topology-comparison-panel.tsx
        department-distribution-panel.tsx
        qualitative-analysis-panel.tsx
        experiment-browser-panel.tsx
        agents-empty-state.tsx
        agents-skeleton.tsx
        agents-error-state.tsx
      data/
        agents-page.mock.ts
      hooks/
        use-agents-page-state.ts
        use-workflow-detail.ts
      types/
        agents-page.ts
      utils/
        agents-page-formatters.ts
```

## 18. Prototype Build Order

Build in this order.

1. page shell, header, tab switcher, paper card
2. collaboration feed shell with static mock data
3. live summary, team filter, agent strip
4. workflow timeline and detail panel
5. empty, loading, and error states
6. evolution tab placeholder panels
7. research tab panels
8. motion polish

## 19. Non-Goals

Do not add these in the first prototype:

- real chat window
- command input composer
- full admin analytics backend
- authentication-only controls
- complex chart library before the information architecture is stable

## 20. Prototype Success Check

The `/agents` prototype is good enough when:

- a viewer can explain the three tabs without guidance
- the page feels alive even with mock or empty data
- workflow cards and detail panels clearly express collaboration structure
- the research tab strengthens credibility instead of feeling disconnected
- the component split is clean enough for later AI-assisted build-out
