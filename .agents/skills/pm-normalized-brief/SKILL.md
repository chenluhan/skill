---
name: pm-normalized-brief
description: Convert raw product input into a structured Normalized Brief. Use when the user asks to sort out a messy requirement, turn stakeholder requests or user feedback into a PM-ready brief, clarify what problem is actually being discussed, or prepare requirement intake before solutioning.
---

# PM Normalized Brief

Goal: compress noisy input into one clear problem statement and one stable intake artifact.

## Require

- Raw request text
- Source of the request
- Any evidence: screenshots, logs, support tickets, analytics, recordings

## Produce

- One-line problem
- Impacted users
- Trigger evidence
- Business effect
- Priority hypothesis
- Known unknowns

## Run This Workflow

1. Separate facts, opinions, urgency, and proposed solutions.
2. Identify whether the input is a `problem`, `opportunity`, or `idea`.
3. If multiple issues are mixed together, split them and choose the primary issue.
4. Preserve the strongest evidence instead of rewriting everything as abstract summary.
5. Rewrite proposed features into problem language.
6. End with a brief, not a solution.

## Apply This Output Shape

- `One-line problem`
- `Impacted users`
- `Trigger evidence`
- `Business effect`
- `Priority hypothesis`
- `Known unknowns`

## Hold These Gates

- If the problem cannot be stated in one sentence, split or clarify again.
- If there is no evidence, mark the brief as `evidence weak`.
- If the input is only a proposed solution, demote it to a candidate direction.

## Hand Off

Pass the result to `$pm-problem-framing`. The next skill should not need to reread the whole chat history.
