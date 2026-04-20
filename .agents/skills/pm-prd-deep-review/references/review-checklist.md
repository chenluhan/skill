# Review Checklist

Use this file for the horizontal completeness pass after reconstructing the main funnel.
Do not dump the whole checklist into the answer.
Select the sections that match the PRD, then convert missing items into concrete findings.

## Table of Contents

- 1. Pre-check
- 2. User and goal definition
- 3. Funnel and task flow
- 4. Page and interaction completeness
- 5. Business rules and logic consistency
- 6. State, exception, and recovery coverage
- 7. Data, metrics, and experiment design
- 8. Delivery readiness
- 9. App-type lenses

## 1. Pre-check

Check whether the document is reviewable at all.

- Is the feature scope clear?
- Is the target user explicit?
- Is the business goal explicit?
- Is this an MVP, experiment, or full rollout?
- Is anything explicitly out of scope?
- Are dependencies, assumptions, or external systems named?

Mark `致命缺失` when the PRD is mostly feature description with no clear user goal or scope boundary.

## 2. User And Goal Definition

Check whether the feature starts from a real user task instead of a solution stub.

- Is the target user segment named?
- Is the trigger context named?
- Is the user job explicit?
- Is the pain point or obstacle explicit?
- Is the success condition explicit from the user's point of view?
- Is the business success condition explicit and distinguishable from the user goal?

High-risk signs:

- The PRD jumps straight into pages or components.
- The document says "improve experience" with no concrete outcome.
- Business goals and user goals are mixed into one vague sentence.

## 3. Funnel And Task Flow

Check whether the main path can actually be completed.

- Can you identify the entry points?
- Are preconditions or eligibility gates defined?
- Is each major user action named?
- Is the system response after each action defined?
- Is the success state visible to the user?
- Is the next best action after success defined?
- Is the abandon path considered?
- Is the return path or retention loop defined when relevant?

Look for these common funnel gaps:

- Entry exists, but qualification or eligibility is missing.
- User can start, but cannot tell whether the action succeeded.
- Success exists, but there is no next step or re-entry path.
- Main path exists, but interruption and recovery are absent.
- One branch is defined in detail while parallel branches are vague.

Mark `致命缺失` when the reviewer cannot reconstruct the main funnel from the PRD text.

## 4. Page And Interaction Completeness

Check whether the described UI can actually support the task.

### Page-level checks

- Are the required pages or surfaces listed?
- Are navigation transitions explicit?
- Is the back path defined?
- Is the exit or cancel behavior defined?
- Is the confirmation behavior defined for destructive actions?
- Is the result page or result feedback defined?

### Interaction checks

- Are primary and secondary CTAs explicit?
- Are disabled, hidden, and loading CTA states distinguished?
- Are default values, prefills, or remembered values defined?
- Are field validations defined?
- Is inline feedback defined?
- Is multi-step progression explicit?
- Is undo, edit, or revise behavior defined where needed?
- Is repeated tapping or duplicate submission handled?

### Content and guidance checks

- Do titles and helper text help the user decide what to do next?
- Do error messages guide recovery instead of only stating failure?
- Does the PRD define copy for high-risk moments such as permission asks, failures, paywalls, and exits?

High-risk signs:

- The PRD lists components but not interaction behavior.
- Dialogs and sheets exist with no dismissal, cancel, or retry rules.
- The review requires guessing what happens after confirmation.

## 5. Business Rules And Logic Consistency

Check whether the system rules are internally coherent.

- Are role differences explicit?
- Are eligibility rules explicit?
- Are timing, quota, cooldown, or frequency limits defined?
- Are sorting, ranking, recommendation, or exposure rules defined when relevant?
- Are duplicate actions or idempotency rules defined?
- Are cross-platform differences defined if the feature spans iOS, Android, web, or mini-program?
- Are rule conflicts resolved when the same user can satisfy multiple conditions?

Look for these common logic failures:

- The page implies a capability that the rule layer blocks.
- The rule is defined in one section and contradicted elsewhere.
- A premium or gated path exists, but entitlement checks are missing.
- A reward or growth loop exists, but anti-abuse rules are absent.

Mark `高优先级缺失` when rules clearly affect user behavior but remain implicit.

## 6. State, Exception, And Recovery Coverage

Use the detailed patterns in [state-matrix.md](state-matrix.md), then check whether the PRD explicitly handles:

- empty states
- loading states
- first-load failure
- partial failure
- weak network and timeout
- invalid input
- permission denial
- duplicate actions
- cancel and back
- app background, resume, or relaunch
- stale or deleted content
- downstream dependency failure

Mark `致命缺失` when the flow depends on a high-risk state transition and the PRD ignores it completely.

## 7. Data, Metrics, And Experiment Design

Check whether the PRD can be validated after launch.

- Is the primary success metric defined?
- Are guardrail metrics defined when the feature could hurt other behavior?
- Are event triggers explicit enough for analytics implementation?
- Are event definitions unambiguous?
- Are experiment assumptions or rollout criteria defined if this is an A/B or gray release?
- Are stop conditions, rollback criteria, or no-go signals defined?
- Are funnel stages measurable end to end?

Common blind spots:

- Metrics exist, but no one can tell when the event fires.
- The PRD asks for "conversion improvement" without specifying numerator or denominator.
- A new flow exists, but no exposure event or drop-off event is defined.
- AI or async features are evaluated only on business outcome, not on intermediate quality or failure signals.

Mark `高优先级缺失` when the PRD cannot support launch validation.

## 8. Delivery Readiness

Check whether the PRD is ready for design, engineering, QA, and launch.

- Are acceptance conditions explicit?
- Are copy, assets, legal text, or policy dependencies named?
- Are backend, third-party, or operations dependencies named?
- Are notification, deep link, or customer-service implications covered?
- Are QA-critical scenarios visible from the doc?
- Are launch constraints, rollout stages, or fallback plans explicit?

High-risk signs:

- The feature is described at a concept level, but implementation-critical assumptions are hidden.
- The PRD assumes cross-team work without naming ownership.

## 9. App-Type Lenses

Use the relevant lens after the base checklist.

### Growth / onboarding

- Is the activation event explicit?
- Is progressive disclosure used, or does the flow front-load too much friction?
- Are incentives, referral, coupon, or reward rules explicit?
- Is attribution defined?
- Are abandon and retry paths defined?

### Membership / subscription

- Is entitlement timing explicit?
- Are trial start, renewal, cancellation, downgrade, and expiration states explicit?
- Is price presentation consistent across entry points?
- Are payment-pending and callback-lost states defined?

### Content / media

- Are feed, detail, consume, resume, and share loops explicit?
- Are no-result, content-offline, geo-block, deleted-content, and paywall states defined?
- Are moderation, report, or sensitive-content rules defined when needed?

### Transaction / commerce

- Are inventory, price-change, coupon, address, payment, timeout, and refund states explicit?
- Are post-payment success, pending, and failure branches separated?
- Is order lookup or recovery possible after interrupted payment?

### Tool / creation

- Are input constraints defined?
- Is draft auto-save or manual save behavior defined?
- Are undo, revise, duplicate, and resume behaviors defined?
- Are export, upload, or long-running task failures recoverable?

### Community / UGC

- Are visibility, moderation, abuse, report, and notification rules defined?
- Are deletion, edit history, mention, and privacy behaviors defined?
- Are re-entry paths from push, comment, or reply notifications valid?
