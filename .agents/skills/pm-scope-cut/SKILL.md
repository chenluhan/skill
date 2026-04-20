---
name: pm-scope-cut
description: Cut a feature or workflow into Must, Should, and Not now. Use when the user asks to control scope, define MVP boundaries, reduce requirement bloat, choose what belongs in this iteration, or turn a broad solution into a shippable PM scope.
---

# PM Scope Cut

Goal: convert a broad solution space into one realistic iteration boundary.

## Require

- `Problem Framing`
- Candidate feature list
- Delivery constraints: time, team, launch window, dependencies

## Produce

- `Must`
- `Should`
- `Not now`
- A short reason for each decision

## Run This Workflow

1. List all candidate items before cutting anything.
2. Test each item against the core user job.
3. Put only indispensable items into `Must`.
4. Keep helpful but non-critical items in `Should`.
5. Put future value, polish, exploration, and “maybe later” into `Not now`.
6. Limit `Must` until the iteration remains buildable.

## Hold These Gates

- If everything looks like `Must`, the problem is still too broad.
- If `Not now` is empty, scope has not really been cut.
- If delivery constraints cannot support the `Must` list, cut again.

## Recover From Failure

- If value debates dominate, revisit the core problem and desired outcome.
- If stakeholders keep reintroducing dropped items, document them explicitly in `Not now`.

## Hand Off

Pass the scoped result to `$pm-prototype-flow`. Do not quietly reintroduce `Not now` items later.
