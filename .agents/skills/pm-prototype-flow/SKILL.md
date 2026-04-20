---
name: pm-prototype-flow
description: Create a handoff-ready product flow, screen list, and prototype brief from a problem framing and scoped requirement. Use when the user asks for a prototype prompt, solution flow, interaction sketch, screen sequence, or wants to make a product direction visible before writing detailed spec content.
---

# PM Prototype Flow

Goal: make the solution understandable through flow and interaction before heavy documentation starts.

## Require

- `Problem Framing`
- `Scope Cut`

## Produce

- Prototype brief or prototype prompt
- Entry point
- Main flow
- Screen or state list
- At least two risky states
- One fallback or return path

## Run This Workflow

1. Start from the user entry point and the completion point.
2. Describe the main flow as alternating user actions and system responses.
3. Add the minimum screens or interaction blocks needed to express the flow.
4. Add at least two risky states, not only the happy path.
5. Add a fallback path for retry, cancel, or return.
6. Prepare a short walkthrough so another person can restate the flow without you.

## Hold These Gates

- If the flow only works when verbally narrated, it is not ready.
- If the prototype becomes a visual design exercise, simplify it back to interaction level.
- If risky states are absent, do not continue.

## Hand Off

Pass the flow and prototype summary to `$pm-state-matrix` and `$pm-delta-spec`.
