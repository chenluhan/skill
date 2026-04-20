# AI Spec Template

Use this structure for `04-ai-spec.md`.

## Goal

Give another AI a stable, parseable representation of the product spec without requiring it to reread the entire PRD.

## Structure

```markdown
# AI-Ready Spec

## Metadata
```json
{
  "project_name": "",
  "goal": "",
  "users": [],
  "metrics": []
}
```

## Pages
### <page-id>
```json
{
  "id": "",
  "name": "",
  "purpose": "",
  "entry_points": [],
  "exit_points": [],
  "sections": [],
  "user_actions": [],
  "system_feedback": [],
  "states": [],
  "exceptions": [],
  "permissions": [],
  "analytics": []
}
```

## Rules
### <rule-id>
```json
{
  "id": "",
  "trigger": "",
  "condition": "",
  "system_behavior": "",
  "user_feedback": "",
  "fallback": ""
}
```

## Flow Assets
```json
{
  "swimlanes": ["diagrams/flow-main.mmd"],
  "sequences": ["diagrams/sequence-request-submit.mmd"]
}
```

## Open Questions
```json
[
  {
    "id": "",
    "related_to": "",
    "question": "",
    "impact": "",
    "owner": "",
    "default_assumption": ""
  }
]
```
```

## Rules

- Keep keys stable across runs.
- Prefer JSON code blocks over narrative paragraphs.
- Remove information that only sounds polished but does not help execution.
