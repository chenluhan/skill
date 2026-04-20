---
name: pm-delta-spec
description: Compress a scoped solution into an engineering-ready delta spec that only describes the current change. Use when the user asks to replace a long PRD with a concise handoff spec, summarize product changes for engineering, document rules and impact scope, or convert a prototype into a buildable spec package.
---

# PM Delta Spec

Goal: explain exactly what changes in this iteration, no more and no less.

## Require

- Scoped solution
- Prototype or flow summary
- State matrix
- Discussion outcomes or decisions

## Produce

- Entry and trigger rules
- Module or screen changes
- Interaction rules
- Copy changes
- Permission or config rules
- Dependencies and impacted surface

## Run This Workflow

1. Describe only the current delta, not the whole product.
2. Start from entry and trigger conditions.
3. Enumerate modules, screens, or flows that change.
4. Convert discussion outcomes into stable rules.
5. Keep unresolved items out of the main spec body and move them into `Open Questions`.
6. Keep wording concise enough for engineering handoff.

## Hold These Gates

- If the document needs a long historical preface, the framing is still weak.
- If the body restates meeting notes instead of product rules, rewrite it.
- If prototype and spec disagree, stop and reconcile them.

## Hand Off

Pass the result to `$pm-delivery-breakdown` and `$pm-handoff-qa`.
