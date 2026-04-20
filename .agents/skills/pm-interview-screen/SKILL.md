---
name: pm-interview-screen
description: Generate targeted product-manager screening interview packs from a candidate resume plus an optional JD. Use when Codex needs to parse a PM resume file or pasted resume text, especially PDF, DOCX, DOC, RTF, TXT, or Markdown resumes, then turn it into a 30-minute 产品经理初筛 question set, follow-up probes, answer-evaluation guidance, or a mapped PDF interview brief with resume-source annotations. Trigger on requests such as “根据简历出产品经理面试题”, “生成 PM 初筛问题”, “根据 JD 和简历做面试脚本”, “把面试题排成 PDF”, or “评估候选人回答”.
---

# PM Interview Screen

## Overview

Turn one PM resume into a focused 30-minute screening pack. Optimize for fast hiring decisions, not comprehensive final-round evaluation.

## Workflow

### 1. Gather the minimum inputs

- Require one of: pasted resume text, a resume file path, or a clearly quoted attachment reference.
- Treat the JD as optional calibration. Do not block on a missing JD.
- Ask for at most three missing runtime variables when they materially change the interview pack:
  - candidate level
  - product domain or business type
  - the main thing this screen should verify
- If the user does not know, default to:
  - level: `mid-level PM`
  - domain: `general product manager`
  - focus: `真实性 + 结构化思考 + 推进力`

### 2. Parse the resume before reasoning

- If the user provides a file path ending in `.pdf`, `.docx`, `.doc`, `.rtf`, `.txt`, `.md`, or `.markdown`, run `scripts/parse_resume.py` first.
- Read `parse_strategy`, `confidence`, `parse_warnings`, `sections_guess`, `blocks`, and `anchors` before trusting the extracted text.
- `scripts/parse_resume.py` already includes OCR fallback for weak PDFs on macOS. Do not ask the user to run OCR manually unless the parser returns `failed`.
- If parsing returns `low`, continue but mark the output confidence explicitly.
- If parsing returns `failed`, request a cleaner file or pasted text.
- Never fabricate projects, metrics, or responsibilities that are not present in the parsed text.

### 3. Build a candidate hypothesis

Extract a concise pre-interview snapshot:

- likely level and scope
- strongest selling points
- biggest risk points
- ownership claims that need verification
- metric claims that need tracing
- collaboration scope and business context

Prefer 3 to 5 concrete hypotheses over a long summary.

### 4. Generate the interview pack

Produce four blocks in this order:

1. `候选人画像摘要`
2. `高针对性题目清单`
3. `30 分钟初筛脚本`
4. `整体建议`

Split questions into exactly three classes:

- `真实性核验题`
- `能力深挖题`
- `淘汰判断题`

For every question, include:

- `问题`
- `为什么问`
- `考察维度`
- `理想回答信号`
- `一般回答信号`
- `危险回答信号`
- `可追加追问`
- `对进入下一轮的影响`

If the user asks for a PDF deliverable:

1. Draft authored content JSON using `references/pdf-layout-spec.md`.
2. Run `scripts/build_interview_pack.py --resume <parsed.json> --content <content.json> --output <pack.json>`.
3. Run `scripts/render_interview_pdf.py --pack <pack.json> --output <interview-pack.pdf>`.
4. Return the PDF path plus a concise explanation of parse confidence and any OCR caveats.

### 5. Evaluate answer patterns, not fictional answers

- Do not invent a fake candidate response transcript.
- Evaluate likely answer patterns instead: `强`, `中`, `弱`, `红旗`.
- Use `references/evaluation-rubric.md` when calibrating difficulty, risk, and pass thresholds.
- If the user later provides actual answers, re-score against the same signal framework instead of changing the rubric ad hoc.

### 6. Keep the screening script decision-oriented

Structure the script as:

- `开场 2 分钟`
- `重点深挖 20 分钟`
- `收尾判断 8 分钟`

Mark:

- must-ask questions
- optional swap questions
- conditions for ending early
- the one or two signals that decide pass or no-pass fastest

## Output Rules

- Keep the candidate summary under 200 Chinese characters unless the user asks for detail.
- Prefer 8 to 12 questions. Reduce to 5 to 7 if the resume is thin or noisy.
- Tie every important question to a specific resume line, project, metric, or ownership claim when possible.
- Use the resume as the primary truth source. Use the JD only to rebalance emphasis.
- State confidence when evidence is weak.

## Failure Modes

- If the resume is image-only or badly parsed, stop pretending certainty and request a cleaner source.
- If the JD is generic, say that it only lightly calibrates the interview focus.
- If the candidate level is unknown, ask once. If still unknown, assume `mid-level PM` and label that assumption.
- If the resume contains obvious inflation signals, increase `真实性核验题` and `淘汰判断题` weight instead of writing more generic questions.

## Resources

- `scripts/parse_resume.py`: Parse resume files into normalized text plus confidence, anchors, and OCR-aware strategy selection.
- `scripts/resume_ocr.py`: Run macOS Vision OCR on scanned PDFs when text extraction is weak.
- `scripts/build_interview_pack.py`: Validate and enrich authored interview content with source anchors.
- `scripts/render_interview_pdf.py`: Render the interview pack JSON into a PDF comparison brief.
- `references/evaluation-rubric.md`: Calibrate question depth, pass thresholds, and red flags for PM screening.
- `references/pdf-layout-spec.md`: Define the JSON shape and visual rules for the PDF brief.
