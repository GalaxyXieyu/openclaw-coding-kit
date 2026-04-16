# Aiking Prototype Architecture Spec

## 1. Purpose

This document is for **prototype implementation first**.

Use it as the source of truth for:

- complete page inventory
- page blueprint per route
- required sections per page
- componentization plan
- reusable template boundaries

Do not use this file for visual style decisions. Visual rules belong in `DESIGN-LOGIC-AND-NEXTJS-ARCHITECTURE.md`.

## 2. Prototype Scope

The prototype should cover these routes only.

### Required Routes

| Route | Page Type | Priority |
|---|---|---|
| `/` | brand landing | required |
| `/works` | portfolio list | required |
| `/courses` | course sales page | required |
| `/blog` | blog index | required |
| `/blog/[slug]` | article detail | required |
| `/agents` | dashboard showcase | required |
| `/referral` | referral / growth page | required |
| `/demos` | demo index | required |
| `/demos/[slug]` | tool demo detail | required |

### Explicitly Excluded From First Prototype

- `/about`
- `/pricing`
- `/works/[slug]`
- `/courses/[slug]`
- auth pages
- account center

## 3. Route Structure

Use `Next.js App Router` with route groups.

```text
src/app/
  (marketing)/
    layout.tsx
    page.tsx
    works/
      page.tsx
    courses/
      page.tsx
    referral/
      page.tsx

  (content)/
    layout.tsx
    blog/
      page.tsx
      [slug]/
        page.tsx

  (product)/
    layout.tsx
    agents/
      page.tsx
    demos/
      page.tsx
      [slug]/
        page.tsx
```

## 4. Page Inventory

Every route must map to one page blueprint.

| Route | User Goal | Core Output | Template |
|---|---|---|---|
| `/` | understand who this is and where to go next | brand story + entry points | `BrandLandingTemplate` |
| `/works` | see execution proof | project grid | `PortfolioListTemplate` |
| `/courses` | decide whether to buy / inquire | structured sales page | `CourseSalesTemplate` |
| `/blog` | browse knowledge content | article list | `ContentIndexTemplate` |
| `/blog/[slug]` | consume one article | readable article page | `ArticleTemplate` |
| `/agents` | feel AI-office / product energy | dashboard-like showcase | `DashboardShowcaseTemplate` |
| `/referral` | understand reward mechanism | clear reward explanation | `ReferralTemplate` |
| `/demos` | browse available tools | tool directory | `DemoIndexTemplate` |
| `/demos/[slug]` | use one tool | playground + output | `UtilityToolTemplate` |

## 5. Page Blueprints

Each page below defines the **required blocks** for the prototype.

### 5.1 `/`

Purpose:

- establish brand
- establish credibility
- route to other domains

Required blocks:

1. `SiteHeader`
2. `HomeHeroBlock`
3. `CredibilityStatsBlock`
4. `CapabilityOverviewBlock`
5. `FeaturedWorksBlock`
6. `FeaturedCoursesBlock`
7. `FeaturedArticlesBlock`
8. `PrimaryCTASection`
9. `SiteFooter`

Optional blocks:

- `TestimonialStrip`
- `TimelineBlock`

### 5.2 `/works`

Purpose:

- present project proof
- support scanning

Required blocks:

1. `SiteHeader`
2. `PageHeroBlock`
3. `FilterBar`
4. `ProjectGridBlock`
5. `BottomCTASection`
6. `SiteFooter`

Optional blocks:

- `FeaturedProjectBlock`
- `CapabilityTagCloud`

### 5.3 `/courses`

Purpose:

- convert trust to purchase or inquiry

Required blocks:

1. `SiteHeader`
2. `CourseHeroBlock`
3. `AudienceBlock`
4. `OutcomeGridBlock`
5. `CurriculumBlock`
6. `PricingBlock`
7. `FAQBlock`
8. `PrimaryCTASection`
9. `SiteFooter`

Optional blocks:

- `InstructorProofBlock`
- `StudentResultBlock`

### 5.4 `/blog`

Purpose:

- expose content inventory
- support search-style browsing

Required blocks:

1. `SiteHeader`
2. `BlogHeroBlock`
3. `FeaturedPostBlock`
4. `CategoryFilterBar`
5. `PostListBlock`
6. `SiteFooter`

Optional blocks:

- `NewsletterCTASection`

### 5.5 `/blog/[slug]`

Purpose:

- present one long-form article clearly

Required blocks:

1. `SiteHeader`
2. `ArticleHeaderBlock`
3. `ArticleMetaRow`
4. `ArticleProseBlock`
5. `RelatedPostsBlock`
6. `BottomCTASection`
7. `SiteFooter`

Optional blocks:

- `TOCAside`
- `AuthorCard`

### 5.6 `/agents`

Purpose:

- create a product / dashboard feeling
- show AI-office state

Detailed page spec:

- `AGENTS-PAGE-SPEC.md`

Required blocks:

1. `SiteHeader`
2. `AgentsHeroBlock`
3. `AgentStatusOverviewBlock`
4. `DashboardPanelGrid`
5. `ActivityFeedBlock`
6. `PrimaryCTASection`
7. `SiteFooter`

Optional blocks:

- `MetricsStrip`
- `LiveOutputPanel`

### 5.7 `/referral`

Purpose:

- explain recommendation system quickly
- drive sharing

Required blocks:

1. `SiteHeader`
2. `ReferralHeroBlock`
3. `RewardRuleBlock`
4. `HowItWorksBlock`
5. `PrimaryCTASection`
6. `SiteFooter`

Optional blocks:

- `FAQBlock`

### 5.8 `/demos`

Purpose:

- show all available tools

Required blocks:

1. `SiteHeader`
2. `DemoDirectoryHeroBlock`
3. `CategoryFilterBar`
4. `DemoCardGrid`
5. `SiteFooter`

### 5.9 `/demos/[slug]`

Purpose:

- host one usable tool prototype

Required blocks:

1. `SiteHeader`
2. `ToolHeroBlock`
3. `ToolPlaygroundBlock`
4. `ToolResultBlock`
5. `ToolHelperBlock`
6. `BottomCTASection`
7. `SiteFooter`

## 6. Template Layer

Each page must be composed from a small set of page templates.

### Required Templates

- `BrandLandingTemplate`
- `PortfolioListTemplate`
- `CourseSalesTemplate`
- `ContentIndexTemplate`
- `ArticleTemplate`
- `DashboardShowcaseTemplate`
- `ReferralTemplate`
- `DemoIndexTemplate`
- `UtilityToolTemplate`

These templates should live under:

```text
src/components/templates/
```

## 7. Componentization Plan

This section is the most important part for prototype implementation.

### 7.1 Global Layout Components

These must be shared across the whole site.

- `SiteHeader`
- `MobileNavSheet`
- `SiteFooter`
- `PageShell`
- `SectionShell`
- `Container`

### 7.2 Shared Content Blocks

These should be reusable across 2 or more routes.

- `PageHeroBlock`
- `PrimaryCTASection`
- `BottomCTASection`
- `FAQBlock`
- `FilterBar`
- `CategoryFilterBar`
- `MetricsStrip`
- `TagCloud`
- `CardGrid`

### 7.3 Marketing Components

- `HomeHeroBlock`
- `CredibilityStatsBlock`
- `CapabilityOverviewBlock`
- `FeaturedWorksBlock`
- `FeaturedCoursesBlock`
- `FeaturedArticlesBlock`
- `CourseHeroBlock`
- `AudienceBlock`
- `OutcomeGridBlock`
- `CurriculumBlock`
- `PricingBlock`
- `ReferralHeroBlock`
- `RewardRuleBlock`
- `HowItWorksBlock`

### 7.4 Content Components

- `BlogHeroBlock`
- `FeaturedPostBlock`
- `PostListBlock`
- `PostCard`
- `ArticleHeaderBlock`
- `ArticleMetaRow`
- `ArticleProseBlock`
- `RelatedPostsBlock`
- `AuthorCard`
- `TOCAside`

### 7.5 Product Components

- `AgentsHeroBlock`
- `AgentStatusOverviewBlock`
- `DashboardPanelGrid`
- `DashboardPanel`
- `ActivityFeedBlock`
- `LiveOutputPanel`

### 7.6 Demo Components

- `DemoDirectoryHeroBlock`
- `DemoCardGrid`
- `DemoCard`
- `ToolHeroBlock`
- `ToolPlaygroundBlock`
- `ToolResultBlock`
- `ToolHelperBlock`

## 8. Primitive UI Components

These are low-level primitives and must stay business-agnostic.

- `Button`
- `Badge`
- `Card`
- `Panel`
- `Input`
- `Textarea`
- `Select`
- `Tabs`
- `Accordion`
- `Pill`
- `Divider`
- `SectionTitle`

Place these under:

```text
src/components/ui/
```

## 9. Recommended Directory Structure

```text
src/
  app/
  components/
    ui/
    layout/
    blocks/
    templates/
  features/
    home/
    works/
    courses/
    blog/
    agents/
    referral/
    demos/
  content/
    blog/
    works/
    courses/
    demos/
  lib/
    seo/
    mdx/
    motion/
    utils/
  config/
    site.ts
    navigation.ts
    seo.ts
  styles/
    tokens.css
    animations.css
    prose.css
  types/
```

## 10. Feature Module Rules

Each feature folder should contain:

```text
features/<domain>/
  components/
  data/
  hooks/
  services/
  types.ts
```

Use feature modules for:

- page-specific composition
- local hooks
- page-only utilities
- domain data mapping

Do not put page-specific logic in `components/ui`.

## 11. Minimal Data Models

### `WorkItem`

```ts
type WorkItem = {
  id: string
  slug: string
  title: string
  summary: string
  tags: string[]
  cover?: string
  links?: {
    demo?: string
    repo?: string
    article?: string
  }
}
```

### `BlogPost`

```ts
type BlogPost = {
  slug: string
  title: string
  excerpt: string
  publishedAt: string
  tags: string[]
  cover?: string
}
```

### `CourseOffer`

```ts
type CourseOffer = {
  id: string
  title: string
  subtitle: string
  audience: string[]
  outcomes: string[]
  modules: string[]
  price: number
  originalPrice?: number
}
```

### `DemoMeta`

```ts
type DemoMeta = {
  slug: string
  title: string
  summary: string
  category: string
  status: 'active' | 'draft'
}
```

## 12. Prototype Build Order

Build in this order.

1. global layout components
2. ui primitives
3. shared blocks
4. templates
5. home
6. works
7. courses
8. blog index
9. blog detail
10. agents
11. demos index
12. demos detail
13. referral

## 13. Hard Rules

1. Every page must be assembled from blocks, not one giant page file.
2. If a block appears on 2 or more routes, promote it to shared component.
3. Keep page templates stable; swap data and blocks, not page architecture.
4. Do not add extra routes during prototype phase.
5. Prefer page completeness over deep interactions in the first prototype.
