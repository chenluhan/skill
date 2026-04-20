---
name: babycare-voice-schema
description: Use when designing or reviewing BabyWhisper voice logging, natural-language parsing, prompt templates, JSON extraction rules, confidence thresholds, or event normalization for baby-care records such as feeding, sleep, diaper, solid food, vaccine, and growth.
---

# Babycare Voice Schema

Use this skill when the task is about turning spoken caregiver language into a safe structured payload.

## Target Event Types

- `feeding`
- `sleep`
- `diaper`
- `solidFood`
- `vaccine`
- `growth`

## Required Payload Shape

```json
{
  "event_type": "feeding",
  "occurred_at": "ISO-8601 datetime",
  "quantity": 150,
  "unit": "ml",
  "method": "formula",
  "body_side": null,
  "duration": null,
  "stool_traits": null,
  "food_name": null,
  "vaccine_name": null,
  "measurement_type": null,
  "value": null,
  "confidence": 0.97,
  "raw_text": "刚刚喂了150ml奶粉",
  "note": "optional"
}
```

## Parsing Rules

- Convert relative time like `刚刚`, `昨晚十点`, `凌晨两点半` into absolute timestamps.
- Do not invent missing quantities or units.
- Return exactly one primary event in v1.
- Preserve the original utterance in `raw_text`.
- Use `confidence` to determine autosave vs confirmation.

## Confidence Thresholds

- `>= 0.93`: auto-save eligible when required fields are present
- `0.75 - 0.92`: send to confirmation sheet
- `< 0.75`: ask for retry or manual entry

## Required Fields by Event Type

- `feeding`: `occurred_at`, and at least one of `quantity` or `duration`
- `sleep`: `occurred_at`, `duration`
- `diaper`: `occurred_at`
- `solidFood`: `occurred_at`, `food_name`
- `vaccine`: `occurred_at`, `vaccine_name`
- `growth`: `occurred_at`, `measurement_type`, `value`

## Normalization Rules

- `奶粉` -> `method=formula`
- `母乳` -> `method=breastmilk`
- `左边` -> `body_side=left`
- `右边` -> `body_side=right`
- `体重` + `公斤` -> `measurement_type=weight`, `unit=kg`
- `身高` -> `measurement_type=height`, `unit=cm`
- `头围` -> `measurement_type=headCircumference`, `unit=cm`

## High-Value Utterances

- `刚刚喂了150ml奶粉`
- `凌晨两点半吃了左边母乳十五分钟`
- `昨晚十点睡到今天早上六点`
- `刚拉了黄色稀便`
- `今天吃了35克胡萝卜泥`
- `今天打了五联第一针`
- `体重6.8公斤`

## Failure Patterns

- One sentence contains multiple events.
- Relative time and explicit time conflict.
- Unit is missing but number is present.
- Family slang maps to more than one event type.
- The user says an observation that should stay in `note`, not a structured field.

## Output Style

- Return the chosen event type first.
- State which fields were inferred vs explicit.
- Call out low-confidence fields directly.
- Prefer safe incompleteness over fabricated structure.
