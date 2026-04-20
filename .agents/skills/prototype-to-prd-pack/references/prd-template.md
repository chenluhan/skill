# PRD Template

Use this structure for `01-prd.md`.

## Required Sections

```markdown
# <Project Name> PRD

## Background
- ...

## Goal
- ...

## Scope
- In scope:
  - ...
- Out of scope:
  - ...

## Target Users
- ...

## Core User Journey
- ...

## Functional Areas
### <Area>
- ...

## Business Rules
### <Rule>
- Trigger:
- Condition:
- System behavior:
- User-facing feedback:
- Fallback:

## States and Exceptions Summary
- ...

## Metrics
- ...

## Risks and Assumptions
- ...
```

## Writing Rules

- Start with user task and scope, not UI description.
- Prefer executable business rules over generic statements.
- Keep relationship to the flow pack explicit. Reference `02-pages.md` and `03-flows.md` when useful.
- Surface uncertainty as assumption or open question. Do not bury it in prose.
