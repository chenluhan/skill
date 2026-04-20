# State Matrix

Use this file to turn a happy-path PRD into a complete state review.
Apply it to each critical step in the main funnel, not only to the feature as a whole.

## Minimum Matrix

For every critical step, check whether the PRD defines:

| State | What to verify |
| --- | --- |
| normal | What the default usable state looks like |
| loading | What the user sees while data or action is pending |
| empty | What happens when there is no data, no permissioned content, or no history |
| failure | What happens on server or business failure |
| invalid input | What happens when the user input is incomplete, wrong, or out of range |
| permission denied | What happens if the user refuses or permanently blocks a permission |
| weak network or timeout | What happens when the request is slow, lost, or retried |
| duplicate action | What prevents repeat taps, repeat submissions, or double payment |
| cancel or back | What happens when the user exits or backs out mid-flow |
| interrupted and resumed | What happens when the app backgrounds, is killed, or the user returns later |

For each missing state, ask four things:

1. What triggers this state?
2. What does the user see?
3. What does the system do?
4. How does the user recover?

## High-Risk State Patterns By Surface

### List / feed / inbox

Check:

- first-load empty
- filter produces no result
- pagination end
- pagination failure
- partial content unavailable
- stale cache after refresh
- hidden or removed items

### Detail page

Check:

- content unavailable or deleted
- entitlement missing
- geo or age restriction
- preload failure
- deep link lands on invalid target
- share target no longer exists

### Form / creation / edit

Check:

- required-field validation
- format or range validation
- upload failure
- draft persistence
- unsaved-change exit
- retry after failure
- duplicate submission

### Purchase / subscription / payment

Check:

- price changed after exposure
- inventory or eligibility changed
- payment pending
- callback lost
- payment succeeded but UI did not update
- payment failed after leaving the page
- cancel, refund, and restore purchase

### Permissions

Check:

- first permission ask
- deny once
- deny permanently
- limited access mode
- permission later enabled from system settings

### Notification / deep link / re-entry

Check:

- target resource already gone
- target requires login
- target requires entitlement
- stale payload
- app cold start vs warm start behavior

### Account / session

Check:

- logged-out entry
- token expired mid-flow
- banned or restricted account
- region or age gate
- account switched on another device

## Recovery Rules

When a state exists, the PRD should usually define:

- whether the system retries automatically or waits for the user
- whether user progress is preserved
- whether local draft or server state wins after resume
- whether there is a safe back path
- whether the next recommended action is visible

## Severity Heuristics

Use these heuristics while reviewing:

- Mark `致命缺失` when the missing state can block completion, payment, entitlement, publication, or irreversible action.
- Mark `高优先级缺失` when the state is common enough to hit real users and would create confusion, duplicate work, or support cost.
- Mark `中优先级优化` when the happy path works but the experience is rough or ambiguous.
- Mark `信息待澄清` when the PRD hints at a rule or state but does not define it enough to build.

## Output Advice

Do not list states mechanically.
Group them by funnel step and point out the user impact:

- what would break
- who gets stuck
- what engineering or QA would be forced to guess

Call out when multiple states are missing from the same step.
That usually signals the PRD was written at the page level instead of the task-flow level.
