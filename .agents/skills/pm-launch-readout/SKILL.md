---
name: pm-launch-readout
description: Turn launch data, user feedback, and delivery outcomes into a concrete PM readout and next-step recommendation. Use when the user asks to review a launched feature, compare expected versus actual impact, write a launch recap, or feed release learnings back into the next requirement cycle.
---

# PM Launch Readout

Goal: close the loop between handoff and learning so the workflow does not end at launch.

## Require

- Launch date or release window
- Expected metrics
- Actual metrics
- User feedback
- Engineering or QA feedback

## Produce

- Expected vs actual comparison
- Key signals
- Main deviation
- Conclusion
- Next-step recommendation

## Run This Workflow

1. Compare expected and actual outcomes first.
2. Combine data, user feedback, and delivery feedback in one view.
3. Identify the largest deviation instead of listing every observation.
4. State whether the feature met the intended goal.
5. End with a concrete next action.

## Hold These Gates

- If the readout has no action, it is incomplete.
- If metrics are missing, say so explicitly instead of fabricating confidence.
- If feedback conflicts, explain by segment or scenario.

## Hand Off

Feed the result back into `$pm-normalized-brief` for the next iteration.
