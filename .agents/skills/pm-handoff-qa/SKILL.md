---
name: pm-handoff-qa
description: Review a Build Pack for internal consistency before engineering handoff. Use when the user asks to audit a PM handoff, check whether the prototype, rules, AC, metrics, and open questions align, or wants a final QA pass on a modern product-delivery package.
---

# PM Handoff QA

Goal: catch contradictions and missing handoff pieces before engineering receives the package.

## Require

- Build Pack draft
- Prototype or flow summary
- State matrix
- Delivery breakdown
- Metrics and acceptance section

## Produce

- Critical issues
- Non-critical issues
- Missing pieces
- Recommended fixes

## Run This Workflow

1. Compare `Problem` with metrics and intended success.
2. Compare prototype with delta spec and flow rules.
3. Compare state matrix with acceptance criteria.
4. Compare metrics with tracked events.
5. Check whether unresolved items are honestly listed in `Open Questions`.
6. Prioritize only meaningful handoff issues, not cosmetic rewrites.

## Hold These Gates

- If one contradiction could mislead engineering, treat it as critical.
- If a section exists only by implication, mark it missing.
- If unresolved decisions appear as settled text, flag them.

## Recover From Failure

- If the same upstream flaw appears repeatedly, route back to the responsible skill instead of patching symptoms.
- If only phrasing is weak but logic is sound, rewrite directly and move on.

## Hand Off

After this skill passes, the package is ready for engineering handoff.
