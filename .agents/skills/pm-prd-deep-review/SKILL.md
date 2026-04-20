---
name: pm-prd-deep-review
description: Deep diagnostic review for App product requirements documents, feature specs, prototype notes, and handoff drafts. Use when Codex needs to audit a PRD for funnel breaks, missing interactions, incomplete states, exception or edge-case gaps, business-rule ambiguity, permission issues, metric and tracking blind spots, or optional AI-specific fallback and uncertainty handling before review or engineering handoff.
---

# PM PRD Deep Review

## Goal

Audit an App PRD the way a strong product lead would before review or engineering handoff.
Expose missing funnel logic, interaction gaps, incomplete states, exception paths, business-rule ambiguity, and validation holes.
If the PRD includes AI behavior, add an AI-specific pass instead of forcing AI checks on every document.

## Require

- Read the PRD text, draft, notes, or structured handoff first.
- Use prototype, flow chart, or annotated screenshots if they exist.
- Treat business goal, KPI, role model, and launch constraints as optional calibration inputs.
- State the review limits clearly when the document is too thin to support a confident judgment.

## Produce

Produce one Markdown diagnostic report that helps a product manager revise the PRD directly.
Keep the verdict first, then the evidence, then the fix.
Tie every important finding to an original section heading, quoted excerpt, or clearly named gap in the source.

## Run This Workflow

1. Classify the PRD.
   - Identify the product type: growth, content, transaction, tool, community, membership, or mixed.
   - Identify the primary user task and the business outcome the flow is supposed to drive.
   - If the PRD covers multiple unrelated features, split the review by module instead of blending everything into one checklist.
2. Reconstruct the main funnel before critiquing details.
   - Map `target user -> entry -> key actions -> success state -> return path or retention loop`.
   - If this funnel cannot be reconstructed from the PRD, mark the document structurally incomplete.
3. Walk the funnel step by step.
   - Check preconditions, eligibility, interaction behavior, user feedback, success behavior, failure behavior, and recovery behavior at each step.
   - Separate what the user sees from what the system does.
4. Run the horizontal completeness pass.
   - Read [references/review-checklist.md](references/review-checklist.md).
   - Use it to inspect rules, permissions, data definition, analytics, launch readiness, and app-type-specific blind spots.
5. Run the state and exception pass.
   - Read [references/state-matrix.md](references/state-matrix.md).
   - Enumerate missing empty, loading, failure, weak-network, permission, duplicate-action, cancel, resume, and boundary states for the main flow.
6. Run the AI pass only when the PRD actually contains AI behavior.
   - Read [references/ai-review.md](references/ai-review.md).
   - Check uncertainty, fallback, latency, cost, safety, human correction, and evaluation design.
7. Shape the final report with [references/output-template.md](references/output-template.md).
   - Keep the output decision-oriented.
   - Prefer evidence-backed findings over generic PM advice.

## Hold These Gates

- Make the main user task explicit.
- Make the success funnel explicit.
- Make every major finding traceable to source evidence or an explicit omission.
- Mark what is missing instead of inventing details.
- Explain the user or business impact of each important gap.
- Distinguish `致命缺失`, `高优先级缺失`, `中优先级优化`, and `信息待澄清`.
- Omit the AI section completely when the PRD does not involve AI capability.

## Calibrate The Review

- For growth or onboarding flows, emphasize conversion, attribution, experiment design, and abandon paths.
- For content flows, emphasize discovery, detail consumption, resume behavior, sharing, and moderation/reporting.
- For transaction or subscription flows, emphasize eligibility, price display, payment states, callback failure, refund or cancellation, and legal copy.
- For tool or creation flows, emphasize input validation, draft persistence, undo, background interruption, and recoverability.
- For community flows, emphasize posting rules, moderation, notification re-entry, social visibility, and abuse handling.

Use the app-type lenses in [references/review-checklist.md](references/review-checklist.md) when the PRD's primary mode is clear.

## Failure Modes

- If the source is too thin, produce a constrained review instead of pretending certainty.
- If the PRD is mostly wireframes and almost no rules, focus on flow, interaction, and missing states rather than fabricated business metrics.
- If several modules are bundled together, review each module separately and then summarize cross-module conflicts.
- If metrics exist without definitions, mark them as unverifiable rather than accepting them at face value.
- If the PRD includes AI language but no concrete AI behavior, ask whether AI is actually part of this release instead of auto-expanding the scope.

## Hand Off

- Use this review before `$pm-delta-spec`, `$pm-delivery-breakdown`, `$pm-state-matrix`, or engineering handoff.
- Do not rewrite the entire PRD unless the user explicitly asks for a rewrite.
- Default to a review report, not a replacement document.
