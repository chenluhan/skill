# PM Interview Screen PDF Upgrade Design

## Goal

Upgrade `pm-interview-screen` from a text-first screening skill into a deliverable-ready interview-material generator.

The upgraded skill must:

1. Parse PM resumes more reliably, especially PDF resumes.
2. Generate a visually clear PDF interview pack instead of plain text only.
3. Map each important interview question back to the resume source that triggered it.
4. Preserve graceful degradation when parsing quality is weak.

This change is not a cosmetic add-on. Parsing quality and PDF presentation are coupled. If source extraction is weak, question generation and source mapping both become unreliable.

## Non-Goals

- Replace a full ATS or recruiting workflow.
- Perform final-round assessment.
- Guarantee pixel-accurate page-coordinate highlighting for every PDF source.
- Solve OCR for every scanned document format in every environment.

## User Problem

The current skill can generate PM screening questions, but the output is hard to scan during an actual interview. It also performs poorly on some PDFs, pushing the user into a manual OCR fallback.

The real product problem is:

- The interviewer needs a screening artifact that can be used directly in the interview.
- The system should absorb file-format complexity instead of forcing the interviewer to preprocess resumes.
- Every important question should be explainable from the resume source, not look like generic AI output.

## Recommended Experience

The skill should generate a PDF interview pack with three sections:

1. Cover summary page
2. Core side-by-side comparison pages
3. Closing decision page

The comparison pages are the center of the experience:

- Left column: resume source text
- Right column: interview questions, evaluation notes, and risk annotations
- Mapping style: mixed granularity
  - default to project-level grouping
  - add precise anchors for metrics, ownership claims, result claims, and vague-risk lines

## PDF Structure

### 1. Cover Summary Page

Purpose: give the interviewer a 30-second pre-read.

Include:

- candidate name and inferred level
- target domain or product direction
- overall recommendation status
- top 3 strengths
- top 3 risks
- parsing confidence and strategy

Do not overload this page with full questions.

### 2. Core Comparison Pages

Purpose: connect resume evidence to interview action.

Each major project or work block gets its own comparison section.

Left column:

- project title or work entry
- resume text blocks
- highlighted trigger sentences

Right column:

- question cards
- annotation cards
- quick evaluation signals

Each question card must include:

- question
- why this question exists
- what signal it checks
- expected strong answer pattern
- red-flag answer pattern
- follow-up question
- source anchor reference

Question classes remain:

- `真实性核验题`
- `能力深挖题`
- `淘汰判断题`

### 3. Closing Decision Page

Purpose: convert analysis into interview execution.

Include:

- 30-minute screening script
- must-ask questions
- optional swap questions
- fast reject triggers
- final recommendation
- what the next round must validate

## Visual System

The PDF should look like an interview editor’s working document, not a generic report.

### Layout

- two-column layout on comparison pages
- one project or one major work block per section
- fixed page header showing the active section title and a short judgment

### Color Semantics

Use only three semantic colors:

- blue: `能力深挖`
- orange: `真实性核验`
- red: `淘汰判断`

The same color must be reused on:

- source highlights in the resume column
- tags on the question cards
- summary badges where relevant

### Highlight Types

Only highlight the source text when it falls into one of these categories:

- metric claim
- ownership claim
- result claim
- vague or inflated statement

Avoid over-highlighting. The document must stay readable during live use.

## Mapping Model

The system needs a stable intermediate structure between parsed resume text and rendered PDF.

### Resume Parse Output

`parse_resume.py` should evolve from a text extractor into a normalized source extractor.

Required output fields:

- `raw_text`
- `blocks`
- `spans`
- `anchors`
- `sections_guess`
- `parse_strategy`
- `confidence`
- `parse_warnings`

Definitions:

- `blocks`: paragraph- or bullet-level logical units
- `spans`: smaller text ranges inside a block
- `anchors`: important source references used by question generation and PDF rendering

Each anchor should describe:

- anchor id
- anchor type
- source block id
- source text
- confidence

Anchor types:

- `metric`
- `ownership`
- `result`
- `risk`
- `project-title`

### Interview Pack Output

`build_interview_pack.py` should consume normalized resume JSON and produce a second JSON model for rendering.

Required output sections:

- `summary`
- `comparison_sections`
- `questions`
- `annotations`
- `screening_script`
- `final_recommendation`

Each question or annotation must include `source_anchor_ids`.

This requirement is strict. If a question cannot be explained by source anchors, the system should drop or rewrite it.

## Parsing Strategy

PDF handling must move from a single-path approach to a multi-stage strategy.

### Stage 1: Text-Layer Extraction

Try the cheapest and cleanest text extraction first.

Possible strategies:

- system text extraction
- internal PDF text-layer extraction

### Stage 2: Extraction Quality Assessment

Do not treat “some characters were extracted” as success.

Quality checks should include:

- total usable token count
- ratio of readable Chinese or English text
- presence of likely resume sections
- amount of corrupted text or noise
- whether project and metric patterns can be detected

### Stage 3: OCR Fallback

If the PDF is image-based or text extraction quality is too weak, automatically fall back to OCR.

OCR is a formal system path, not a manual user workaround.

### Stage 4: Merge or Select Best Result

If both text extraction and OCR produce usable results:

- prefer the cleaner structure
- optionally merge when one path has stronger headings and the other has stronger body text

### Stage 5: Confidence Exposure

Expose these fields to later stages:

- `parse_strategy: text | ocr | hybrid`
- `confidence: high | medium | low | failed`
- `parse_warnings`

The PDF cover page should surface this status.

## Implementation Structure

Recommended files:

```text
pm-interview-screen/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── parse_resume.py
│   ├── resume_ocr.py
│   ├── build_interview_pack.py
│   └── render_interview_pdf.py
└── references/
    ├── evaluation-rubric.md
    └── pdf-layout-spec.md
```

### `parse_resume.py`

Responsibilities:

- orchestrate extraction strategy
- run quality checks
- decide on OCR fallback
- output normalized source JSON

### `resume_ocr.py`

Responsibilities:

- handle OCR-specific extraction
- return text blocks and page-level structure
- remain isolated from the main parser for maintainability

### `build_interview_pack.py`

Responsibilities:

- build candidate summary
- create anchor-linked questions
- create annotation cards
- produce the final render-ready interview pack JSON

### `render_interview_pdf.py`

Responsibilities:

- apply the layout template
- render left-right comparison pages
- render badges, highlights, and footers
- write the final PDF artifact

### `references/pdf-layout-spec.md`

Responsibilities:

- define layout rules
- define card content rules
- define pagination and highlight rules

## Data Flow

```text
resume file / pasted text
  -> parse_resume.py
  -> normalized resume JSON
  -> build_interview_pack.py
  -> interview pack JSON
  -> render_interview_pdf.py
  -> final PDF
```

## Error Handling and Degradation

### Case 1: text extraction fails and OCR is unavailable

Return a clear failure:

- why parsing failed
- which parser path was attempted
- what the user should do next

Suggested next actions:

- upload DOCX
- paste clean text
- provide a higher-quality PDF

### Case 2: OCR works but quality is weak

Still generate the PDF, but add a visible warning on the cover page:

- source derived from OCR
- mapping may be incomplete

### Case 3: no page coordinates, only logical text blocks

Still generate the PDF using logical anchors:

- block ids
- section ids
- quoted source snippets

Do not block on missing geometric precision.

### Case 4: weak source-question linkage

Prefer fewer, better-grounded questions.

The system should never inflate confidence by generating generic questions with fake provenance.

## Testing Strategy

### Parsing Tests

Test at least:

- clean DOCX resume
- text-layer PDF resume
- scanned PDF that requires OCR
- noisy or low-content resume

Validate:

- parse strategy chosen
- confidence level
- blocks and anchors produced
- warnings emitted

### Pack Generation Tests

Validate:

- every kept question has source anchors
- question classes are present
- summary and script render with incomplete inputs

### PDF Rendering Tests

Validate:

- PDF is produced successfully
- comparison pages preserve source-question pairing
- colors and badges are consistent
- long sections paginate without overlap

## Open Decisions

These are implementation choices, not product-direction blockers:

- exact PDF rendering library
- exact OCR backend available in the environment
- whether to store intermediate JSON artifacts for debugging

The product behavior should remain stable regardless of those choices.

## Recommendation

Implement the upgrade as a three-layer pipeline:

1. source extraction
2. interview-pack generation
3. PDF rendering

Do not mix parsing, reasoning, and rendering in a single script.

That separation is the only way to keep:

- parsing debuggable
- question provenance explainable
- PDF layout maintainable
