# Inference Rules

Use this file on every run.

## Goal

Keep the pack useful without letting the model invent business logic.

## Three Allowed Labels

Every important conclusion must fall into one of these classes:

- `明确事实`: directly visible or explicitly stated by the input
- `稳定推断`: strongly implied by the source and low-risk to assume as structural behavior
- `待确认项`: not safely inferable and important enough to affect implementation

Do not create a fourth class.

## Safe Stable Inference

Use `稳定推断` only when the source strongly implies the behavior and the inference is structural rather than policy-heavy.

Examples:

- A visible form implies validation, loading, success, and failure states must exist.
- A visible CTA implies a next-step transition exists.
- A multi-step flow implies back navigation or return behavior must be defined.
- An async AI action implies timeout, retry, and fallback behavior need explicit handling.
- A login wall near an action implies draft preservation may be needed after authentication.

## Not Safe to Infer

Push these into `待确认项` unless the source explicitly answers them:

- pricing or discount logic
- eligibility or quota rules
- approval thresholds
- operator or support SLA
- compliance and audit rules
- retention or deletion policy
- permission boundaries that change data exposure
- exact analytics definitions and metric targets
- irreversible action safeguards
- service guarantees, compensation, or refund policy

## Escalation Test

If getting the assumption wrong would materially change:

- user-visible behavior
- risk handling
- engineering scope
- legal or policy exposure
- operations burden

then it belongs in `待确认项`.

## Writing Rule

When in doubt:

1. keep the structural requirement
2. avoid the policy detail
3. put the unknown in `05-open-questions.md`

Example:

- Good: `A submission failure state is required.`
- Bad: `The system retries exactly three times over 30 seconds.` unless the source states that.
