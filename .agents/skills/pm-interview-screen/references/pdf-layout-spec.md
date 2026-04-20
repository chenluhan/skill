# PDF Layout Spec

Use this reference when the user wants a deliverable PDF instead of plain-text interview notes.

## Output Shape

The final PDF has three sections:

1. cover summary page
2. side-by-side comparison pages
3. closing decision page

## Comparison Page Rules

- left column = resume source
- right column = interview actions
- default mapping = project-level
- precise highlights = metric, ownership, result, vague-risk

Do not try to render the entire resume when only one section matters. Prefer focused sections that clearly connect source evidence to the question cards.

## Content JSON Shape

Author the input content JSON for `build_interview_pack.py` in this form:

```json
{
  "candidate": {
    "name": "候选人",
    "inferred_level": "3-5 年模块 owner",
    "target_domain": "AI 产品经理"
  },
  "summary": {
    "headline": "亮点强，但 ownership 需核验",
    "overall_assessment": "适合继续一面深挖。",
    "top_strengths": ["..."],
    "top_risks": ["..."]
  },
  "comparison_sections": [
    {
      "source_group_id": "g1",
      "title": "AI 面试 Copilot",
      "judgement": "结果亮眼，但需确认真实 owner 边界。",
      "source_anchor_ids": ["a3", "a5"],
      "questions": [
        {
          "class": "真实性核验题",
          "question": "这个 40% 的准备时间降低是你怎么定义和归因的？",
          "why": "验证指标归因和 owner 边界。",
          "signal": "能说明口径、动作、协作对象和测量方式。",
          "strong_signal": "清楚说明自己定义了什么、推动了什么、怎么测。",
          "red_flag": "只重复结果，不知道口径。",
          "follow_up": "如果把算法能力拿掉，哪些结果仍然归你负责？",
          "source_anchor_ids": ["a5"]
        }
      ],
      "annotations": [
        {
          "class": "淘汰判断题",
          "label": "ownership 风险",
          "note": "该经历的结果强，但角色边界可能被放大。",
          "source_anchor_ids": ["a5"]
        }
      ]
    }
  ],
  "screening_script": {
    "opening": ["..."],
    "must_ask": ["..."],
    "optional_swaps": ["..."],
    "fast_reject_triggers": ["..."]
  },
  "final_recommendation": {
    "decision": "recommend",
    "reason": "项目结果真实感较强，值得继续深挖。",
    "next_round_focus": ["owner 边界", "指标归因"]
  }
}
```

## Visual Semantics

- `能力深挖题` = blue
- `真实性核验题` = orange
- `淘汰判断题` = red

Use the same semantic color on:

- source highlights
- question card tags
- annotation cards

## Source Mapping Rules

- Every question must have `source_anchor_ids`.
- Every annotation must have `source_anchor_ids`.
- If a question has no explainable anchor, rewrite it or remove it.
- When anchor precision is weak, prefer quoting the logical block instead of pretending to know coordinates.

## Parse Confidence Rules

Always surface parse status on the cover page:

- `text / high`
- `text / medium`
- `ocr / low`
- `hybrid / medium`

If OCR was required or confidence is low, keep a visible parse note.
