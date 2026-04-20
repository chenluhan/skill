---
name: pm-state-matrix
description: Derive a complete product state matrix from a flow, prototype, and rules. Use when the user asks to enumerate happy path, edge states, error handling, permission behavior, empty/loading states, or wants to stop engineering and QA from guessing missing product states.
---

# PM State Matrix

Goal: make hidden product states explicit before engineering handoff.

## Require

- Prototype or flow summary
- Business rules
- Any known edge conditions

## Produce

A state matrix with at least these rows:

- normal
- empty
- loading
- failure
- permission denied
- boundary input
- cancel or return

Each row should include:

- trigger condition
- user-visible feedback
- system action
- risk or note

## Run This Workflow

1. Walk step by step through the main flow.
2. Ask what happens if there is no data, delay, refusal, invalid input, or interruption.
3. Separate user-visible behavior from system behavior.
4. Isolate permissions and boundary inputs instead of burying them inside generic failure.
5. Convert unclear cases into explicit open questions.

## Hold These Gates

- Cover all major flow transitions.
- State what the user sees, not only what the system does.
- State what the system does, not only what the UI shows.
- Flag any unresolved state as an open question.

## Hand Off

Pass the matrix to `$pm-delta-spec`, `$pm-delivery-breakdown`, and `$pm-metrics-acceptance`.
