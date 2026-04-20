---
name: pm-metrics-acceptance
description: Define metrics, events, and acceptance coverage for a feature handoff. Use when the user asks to add success metrics, event tracking, acceptance cases, QA coverage, or wants a Build Pack that can be verified after launch instead of ending at implementation.
---

# PM Metrics and Acceptance

Goal: make the feature measurable and testable before launch.

## Require

- Problem framing or target outcome
- Main flow
- State matrix
- Delivery breakdown

## Produce

- Metrics table
- Event list
- Event properties
- Happy path cases
- Edge cases
- Failure cases

## Run This Workflow

1. Start from the desired outcome, not from event names.
2. Define one or more measurable signals that show whether the change worked.
3. Add events at key transitions in the main flow.
4. Add event properties that will actually explain behavior differences later.
5. Derive acceptance cases from the state matrix, not from intuition alone.

## Hold These Gates

- If the metric says only “better experience”, rewrite it.
- If events have no decision value, remove or merge them.
- If test cases only cover the happy path, return to the state matrix.

## Hand Off

Pass the result to `$pm-handoff-qa` and include it in the final Build Pack.
