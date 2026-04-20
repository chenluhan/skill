# Intake Schema

Use this file for the strong-constrained intermediate layer.

## Modes

The skill supports two modes:

- `full`
- `delta`

## Full Mode Raw Intake

This is the file that should exist before normalization.

```json
{
  "mode": "full",
  "input_type": "figma|ai_studio|html|screenshots|mixed",
  "project_name": "string",
  "requested_level": "L1|L2|L3|L4",
  "sources": [],
  "evidence_summary": {
    "pages": "string",
    "flows": "string",
    "states": "string",
    "rules": "string"
  },
  "pages_or_artifacts": [],
  "flow_evidence": [],
  "state_evidence": [],
  "business_rule_evidence": [],
  "missing_materials": [],
  "user_notes": []
}
```

### Rules

- `pages_or_artifacts` should prefer page-shaped objects that can later be normalized into `pages`.
- `flow_evidence` should prefer flow-shaped objects when possible. Use prose only if the flow is too incomplete to structure yet.
- `business_rule_evidence` should prefer rule-shaped objects when possible.
- `state_evidence` can stay as prose if the source only partially exposes states.

## Delta Mode Change Intake

```json
{
  "mode": "delta",
  "input_type": "figma|ai_studio|html|screenshots|mixed",
  "project_name": "string",
  "requested_level": "L1|L2|L3|L4",
  "baseline_ref": "string",
  "change_sources": [],
  "change_summary": "string",
  "claimed_changes": [],
  "suspected_impacts": [],
  "missing_materials": [],
  "user_notes": []
}
```

### Rules

- `baseline_ref` is mandatory for delta mode.
- If baseline is missing, stop and fall back to full mode.
- `claimed_changes` should list what the user believes changed.
- `suspected_impacts` should list page, flow, or rule areas that may need diffing.

## Delta Mode Impact Scope

```json
{
  "baseline_ref": "string",
  "change_scope": {
    "pages": [
      { "id": "home", "action": "update|add|remove|no_change", "reason": "string" }
    ],
    "flows": [
      { "id": "submit-request", "action": "update|add|remove|no_change", "reason": "string" }
    ],
    "rules": [
      { "id": "login-before-submit", "action": "update|add|remove|no_change", "reason": "string" }
    ],
    "open_questions": [
      { "id": "sla", "action": "added|resolved|unchanged", "reason": "string" }
    ]
  },
  "unchanged_artifacts": [],
  "merge_recommended": false
}
```

### Rules

- Do not generate delta output until this file is clear.
- Default to `delta-only` output.
- Set `merge_recommended` only when the affected scope is broad enough to justify a merged full pack.
