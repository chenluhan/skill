---
name: pm-delivery-breakdown
description: Break a PM handoff into Epic, Stories, acceptance criteria, dependencies, and handoff structure for engineering. Use when the user asks to split a feature into implementation-ready work, structure a Build Pack for engineering, define task boundaries, or turn product language into execution-ready breakdowns.
---

# PM Delivery Breakdown

Goal: convert product intent into an engineering-readable execution structure without drifting into implementation design.

## Require

- Delta spec
- State matrix
- Prototype or flow summary

## Produce

- One Epic
- A small set of Stories
- Core acceptance criteria
- Dependencies
- Handoff and integration notes

## Run This Workflow

1. State the Epic in terms of user or product outcome.
2. Break the work into Stories that each carry one meaningful value slice.
3. Add 3 to 5 acceptance criteria that can be tested directly.
4. Name dependencies early: upstream data, permissions, API, infra, design, copy.
5. Keep task breakdown aligned with scope, not with every UI fragment.

## Hold These Gates

- If Stories become page fragments with no user value, regroup them.
- If AC requires long verbal explanation, the spec is still too vague.
- If dependencies appear only at the end, rewrite the breakdown.

## Recover From Failure

- If there are too many Stories, the scope is likely too broad.
- If one Story hides several unrelated jobs, split it again.

## Hand Off

Pass the result to `$pm-metrics-acceptance` and `$pm-handoff-qa`.
