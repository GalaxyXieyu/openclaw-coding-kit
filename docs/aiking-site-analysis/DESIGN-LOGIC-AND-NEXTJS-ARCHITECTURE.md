# Aiking Design Spec

## 1. Purpose

This document defines the **prototype design system**.

Use it as the source of truth for:

- visual direction
- design tokens
- component appearance
- motion intensity
- page composition style

Do not use this file for route architecture or feature ownership. Those belong in `PAGE-ARCHITECTURE.md`.

## 2. Design Goal

The site should feel like:

- an AI-native personal brand site
- a polished dark product surface
- a portfolio with technical credibility

The site should not feel like:

- a generic SaaS starter
- a pastel creator template
- a heavy cyberpunk poster
- a corporate enterprise dashboard

## 3. Visual Direction

Primary direction:

- `Neon Dark`

Secondary direction:

- `Storytelling Landing`
- `Portfolio Showcase`
- `Dashboard Surface`

Global rule:

- dark layered background
- one neon primary accent
- one supporting accent
- restrained glow
- card-based composition

## 4. Design Tokens

### Core Tokens

```css
:root {
  --bg-base: 10 10 15;
  --bg-card: 18 18 26;
  --bg-surface: 26 26 46;

  --accent-primary: 0 255 136;
  --accent-secondary: 168 85 247;

  --text-primary: 255 255 255;
  --text-secondary: 255 255 255 / 0.72;
  --text-muted: 255 255 255 / 0.52;

  --border-subtle: 255 255 255 / 0.1;
  --border-accent: 0 255 136 / 0.25;

  --glow-primary: 0 0 15px rgba(0, 255, 136, 0.3);
  --glow-soft: 0 0 30px rgba(0, 255, 136, 0.1);
}
```

### Token Rules

1. `accent-primary` is the main interaction color.
2. `accent-secondary` is only for gradient support or secondary highlight.
3. Large surfaces must stay visually quiet.
4. Glow is a support effect, not the default state.

## 5. Typography Rules

Use typography by role.

| Role | Usage |
|---|---|
| `display` | hero headline |
| `heading` | section title |
| `body` | general copy |
| `mono` | metadata, labels, technical fragments |

Rules:

1. Hero headings may use gradient text.
2. Body copy must prioritize readability.
3. Mono is only for technical accents or metadata.
4. Article pages should have calmer typography than marketing pages.

## 6. Layout Rules

### Global Layout

- max width: `1280px` to `1440px`
- use consistent horizontal padding
- use clear section rhythm

### Section Structure

Every major section should follow:

- `SectionHeader`
- `SectionBody`
- `SectionFooter` only when needed

### Grid Rules

- landing pages: 1 to 3 column responsive grids
- portfolio pages: repeatable card grid
- dashboard pages: panel grid
- article pages: prose-focused layout

## 7. Background and Surface Rules

### Background Layers

Use 3 layers:

1. dark base
2. translucent dark overlay
3. cyber-grid overlay

### Surface Rules

Cards and panels should use:

- dark-card or dark-surface
- subtle border
- moderate radius
- optional blur
- hover glow only when interactive

## 8. Prototype Component Appearance Matrix

This section defines how reusable components should look in the prototype.

### 8.1 `SiteHeader`

Style:

- fixed or sticky
- translucent dark background
- subtle bottom border
- active link in primary accent

Behavior:

- desktop horizontal nav
- mobile sheet / drawer nav

### 8.2 `PageHeroBlock`

Style:

- large display heading
- short supporting copy
- one primary CTA
- optional secondary CTA

Do:

- keep strong hierarchy
- allow gradient heading or accent highlight

Do not:

- overload hero with too many links or cards

### 8.3 `StatsBlock` / `MetricsStrip`

Style:

- compact cards or inline metrics
- mono or condensed labels
- accent used only for numbers or active states

### 8.4 `Card`

Style:

- dark layered surface
- thin border
- title + summary + optional meta

Variants:

- `content-card`
- `project-card`
- `dashboard-card`
- `tool-card`

### 8.5 `ProjectCard`

Style:

- visual-first
- cover or thumbnail optional
- tags visible
- hover glow allowed

### 8.6 `PostCard`

Style:

- calmer than project cards
- text-first
- metadata visible
- reduced glow

### 8.7 `PricingCard`

Style:

- strong border hierarchy
- highlight one featured plan only
- CTA always visible

### 8.8 `DashboardPanel`

Style:

- compact panel
- high information density
- small titles
- status emphasis

### 8.9 `FAQAccordion`

Style:

- low visual noise
- dark surface
- simple expand/collapse

### 8.10 `ToolPlaygroundBlock`

Style:

- panel-like container
- obvious action area
- clear result surface

## 9. CTA Rules

### Primary CTA

- accent fill or gradient fill
- strong contrast
- may use glow on hover

### Secondary CTA

- outlined or dark-surface
- subtle accent hover

Rules:

1. Each screen should have one clear primary CTA.
2. Do not create more than 2 CTA hierarchies on the same screen.

## 10. Motion Rules

### Allowed Motion Types

- fade up
- reveal on scroll
- pulse
- shimmer
- spin
- count-up
- hover glow

### Motion Intensity Rules

- home: medium
- works: low to medium
- courses: low to medium
- blog index: low
- article: minimal
- agents: medium to high
- demos: depends on tool

### Motion Principles

1. Motion must communicate hierarchy or state.
2. Motion must not slow reading.
3. Article pages must be calmer than dashboard pages.
4. Hover effects should be subtle, not flashy.

## 11. Page-Type Design Rules

### Home

Should feel:

- most expressive
- most brand-driven
- most atmospheric

### Works

Should feel:

- showcase-first
- structured
- less wordy than home

### Courses

Should feel:

- conversion-oriented
- structured
- trustworthy

### Blog Index

Should feel:

- content-first
- quieter

### Article

Should feel:

- readable
- restrained
- editorial

### Agents

Should feel:

- product-like
- dashboard-like
- alive

Detailed page-specific interaction and motion rules:

- `AGENTS-PAGE-SPEC.md`

### Demos

Should feel:

- practical
- playful in moderation
- interaction-first

## 12. Design Do / Don’t

### Do

- keep a dark layered background
- use accent colors with discipline
- reuse cards and panels
- keep article pages calm
- use motion to indicate hierarchy and state

### Don’t

- do not make every section glow
- do not add many unrelated accent colors
- do not treat blog pages like landing pages
- do not use large decorative gradients everywhere
- do not redesign the same component differently on every page

## 13. Tailwind Token Mapping

Recommended utility names:

```text
bg-dark
bg-dark-card
bg-dark-surface
text-white
text-white/70
text-white/50
border-white/10
border-ai-gold/15
border-ai-gold/30
text-ai-gold
from-ai-gold
to-ai-purple
shadow-gold-glow
cyber-grid-overlay
```

## 14. Minimum Deliverables For Prototype

The prototype design system must at least provide:

- `tokens.css`
- `animations.css`
- `prose.css`
- header style
- footer style
- hero style
- card style
- panel style
- CTA style
- article prose style

## 15. Hard Rules

1. Reuse the same visual language across all routes.
2. Do not create route-specific token systems.
3. Keep the accent system tight.
4. Keep the motion system limited and repeatable.
5. Prefer consistency over novelty in the prototype phase.
