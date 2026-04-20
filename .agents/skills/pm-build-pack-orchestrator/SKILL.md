---
name: pm-build-pack-orchestrator
description: Coordinate the full AI-native PM delivery workflow from raw requirement to Build Pack v1 for engineering handoff. Use when the user asks how to take a new feature request, organize PM delivery, replace a traditional PRD with a modern handoff package, or orchestrate requirement intake, framing, scope cut, prototype, state matrix, acceptance, metrics, and handoff QA.
---

# PM Build Pack Orchestrator

Goal: turn one raw feature request into one stable `Build Pack v1` without letting the workflow collapse into scattered notes or a long PRD.

## Require

- Raw request, stakeholder ask, user feedback, or candidate feature
- Product context if available
- Any existing evidence, screenshots, logs, or data

## Produce

- `Normalized Brief`
- `Problem Framing`
- `Scope Cut`
- `Prototype Summary`
- `State Matrix`
- `Delta Spec`
- `Delivery Breakdown`
- `Metrics & Acceptance`
- `Open Questions`
- Final `Build Pack v1`

## Run This Workflow

1. Decide whether the request is a `new feature iteration`.
2. If it is actually a migration, pricing change, permission system, or cross-system refactor, stop and mark it as out of scope for this skill.
3. Use `$pm-normalized-brief` to compress noisy input into one stable brief.
4. Use `$pm-problem-framing` to define users, context, success, and non-goals.
5. Use `$pm-scope-cut` to reduce candidate scope into `Must`, `Should`, and `Not now`.
6. Use `$pm-prototype-flow` to make the main flow visible before heavy documentation.
7. Use `$pm-state-matrix` to enumerate happy path, empty, loading, failure, permission, and boundary states.
8. Use `$pm-delta-spec` to describe only this change, not the whole product universe.
9. Use `$pm-delivery-breakdown` to convert the solution into Epic, Stories, AC, dependencies, and handoff structure.
10. Use `$pm-metrics-acceptance` to add metrics, events, and acceptance coverage.
11. Use `$pm-handoff-qa` to find contradictions before handoff.
12. Assemble one `Build Pack v1` as the single source of truth.

## Hold These Gates

- Do not enter prototype work if the problem still reads like a feature wish list.
- Do not hand off to engineering if the main flow cannot be restated from the prototype.
- Do not send the pack if goals, rules, AC, and metrics disagree.

## Recover From Failure

- If one request actually contains multiple problems, split it before continuing.
- If scope keeps growing, return to `$pm-scope-cut` instead of documenting more.
- If the prototype and spec diverge, reconcile them before breakdown.
- If engineering still asks basic “what are we building” questions, revisit `Problem`, `State Matrix`, and `Open Questions`.

## Hand Off

The next consumer should receive one package, not many fragments:

- one prototype or prototype summary
- one Build Pack
- one set of open questions

Do not maintain parallel truths across chat, docs, and ticket systems.
