# Pack Schema

Use this schema for `scripts/normalize_inputs.py` and `scripts/build_pack.py`.

The canonical normalized file is JSON.

## Top-Level Keys

```json
{
  "schema_version": "1.0",
  "project_name": "string",
  "product_summary": "string",
  "goal": "string",
  "users": ["string"],
  "assumptions": ["string"],
  "non_goals": ["string"],
  "metrics": ["string"],
  "sources": [
    {
      "id": "source-id",
      "type": "link|image|note|file",
      "path": "string",
      "note": "string"
    }
  ],
  "pages": [],
  "flows": [],
  "sequences": [],
  "rules": [],
  "open_questions": [],
  "glossary": []
}
```

## Aliases Accepted by `normalize_inputs.py`

The normalizer accepts a few raw aliases:

- `target_users` -> `users`
- `screens` -> `pages`
- `swimlanes` -> `flows`
- `sequence_diagrams` -> `sequences`
- `business_rules` -> `rules`
- `pending_questions` -> `open_questions`

Use aliases only in raw input. The normalized output must use canonical keys.

## Page Object

```json
{
  "id": "request-composer",
  "name": "Request Composer",
  "purpose": "Collect the user's concierge request.",
  "facts": ["Visible fact from the source"],
  "inferences": ["Stable inference"],
  "entry_points": ["Home CTA"],
  "exit_points": ["Submission success screen"],
  "sections": ["Header", "Destination selector", "Primary CTA"],
  "user_actions": ["Select destination", "Tap submit"],
  "system_feedback": ["Inline validation", "Submitting spinner"],
  "states": ["Initial", "Validation error", "Submitting", "Success", "Failure"],
  "exceptions": ["Required fields missing", "Network timeout"],
  "permissions": ["Login required before submission"],
  "analytics": ["request_submit_clicked"],
  "wireframe": ["Header", "Destination selector", "Primary CTA"],
  "source_refs": ["figma-main"]
}
```

## Flow Object

Use `flows` for swimlane-style logic.

```json
{
  "id": "submit-request",
  "title": "Submit Request",
  "purpose": "Show the normal request submission path and the operator handoff.",
  "participants": ["User", "App", "Server", "Operator", "AI"],
  "steps": [
    {
      "id": "open-composer",
      "lane": "User",
      "label": "Open request composer",
      "kind": "normal",
      "source_type": "explicit_fact",
      "source_ref": "screen-request-composer"
    }
  ],
  "edges": [
    {
      "from": "open-composer",
      "to": "show-form",
      "label": ""
    }
  ],
  "notes": ["Explain the main happy path here."],
  "known_gaps": ["Operator SLA is not visible in the prototype."],
  "mermaid": ""
}
```

## Sequence Object

```json
{
  "id": "submit-request-api",
  "title": "Request Submission Sequence",
  "purpose": "Show request, validation, timeout, and fallback timing.",
  "participants": ["User", "App", "Server", "AI"],
  "messages": [
    {
      "from": "User",
      "to": "App",
      "label": "Tap Submit",
      "type": "request"
    }
  ],
  "known_gaps": ["Retry budget is not visible in the prototype."],
  "mermaid": ""
}
```

Allowed message `type` values:

- `request`
- `response`
- `async`
- `error`
- `return`

## Rule Object

```json
{
  "id": "login-before-submit",
  "title": "Login required before request submission",
  "trigger": "User taps Submit without an active session.",
  "condition": "Session token missing or expired.",
  "system_behavior": "Block submission and redirect to login.",
  "user_feedback": "Explain that login is required before continuing.",
  "fallback": "Preserve the draft after login.",
  "source_type": "stable_inference",
  "source_refs": ["screen-request-composer"]
}
```

## Open Question Object

```json
{
  "id": "operator-sla",
  "title": "Operator SLA",
  "related_to": "submit-request",
  "question": "How quickly should an operator pick up a submitted request?",
  "impact": "Affects user expectation copy, progress state design, and exception handling.",
  "owner": "PM",
  "default_assumption": "Use async pickup with no committed SLA in v1."
}
```

## Glossary Object

```json
{
  "term": "Request",
  "definition": "A concierge service request created from the composer."
}
```
