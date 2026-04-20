---
name: prototype-to-prd-pack
description: Generate or iterate a PRD delivery pack from prototypes, screenshots, Figma, AI Studio, HTML, wireframes, or page-flow notes. Use when Codex needs intake diagnosis, strong-constrained intermediate manifests, PRD reconstruction, Mermaid swimlane or sequence diagrams, delivery-level status, or delta-only PRD updates from an existing baseline instead of rewriting the whole pack.
---

# Prototype to PRD Pack

## Overview

Use this skill when the user wants a PRD delivery pack from design artifacts or wants to iterate on an existing PRD pack.

This skill has two modes:

- `full mode`: generate a full pack from prototypes or screenshots
- `delta mode`: generate only the changed pages, flows, rules, and open questions from an existing baseline

Treat the job as `intake diagnosis -> constrained manifest -> validation -> generation -> delivery status`.

## Non-Negotiable Rules

1. Do not start writing the PRD pack before writing `00-intake-diagnosis.md`.
2. Do not normalize or build from free-form chat text. Always write a constrained intake JSON first.
3. Do not skip validation. If the manifest fails validation, stop and report blockers.
4. Do not say the pack is complete unless delivery status reaches `L4`.
5. In delta mode, do not rewrite unchanged sections. Default to `delta-only`.

## Delivery Levels

Always reason in these levels:

- `L0 Blocked`
- `L1 Structured`
- `L2 Diagram Source`
- `L3 Visual Diagram`
- `L4 Full Delivery`

If SVG or PDF is missing, do not describe the result as fully delivered.

## Step 1: Choose the mode

Use `full mode` when:

- there is no usable baseline pack
- the user is starting from screenshots, Figma, AI Studio, or HTML
- the user wants a new full PRD pack

Use `delta mode` when:

- the user says “基于上一版改”
- a baseline pack or baseline normalized JSON is provided
- the user only wants the changed points

If no baseline exists, do not force delta mode. Say that only full mode is stable.

## Step 2: Diagnose the intake first

Before generation, create a run directory and write:

- `00-intake-diagnosis.md`
- `01-raw-intake.json` in full mode, or `01-change-intake.json` in delta mode

Use these references:

- `references/intake-schema.md`
- `references/intake-templates.md`
- `references/inference-rules.md`

Run dependency preflight before promising SVG or PDF:

```bash
scripts/check_dependencies.py --requested-level L4 --output <run-dir>/dependency-report.json
```

The dependency report must be used to tell the user:

- current platform
- bootstrap command for this platform
- whether direct install is fully supported or only partially supported
- where the cross-platform dependency guide lives

Run validation:

```bash
scripts/validate_manifest.py --mode full-raw --input <run-dir>/01-raw-intake.json --output <run-dir>/validation-report.json
```

or

```bash
scripts/validate_manifest.py --mode delta-change --input <run-dir>/01-change-intake.json --output <run-dir>/validation-report.json
```

Then write the diagnosis markdown:

```bash
scripts/write_intake_diagnosis.py \
  --validation-report <run-dir>/validation-report.json \
  --dependency-report <run-dir>/dependency-report.json \
  --output <run-dir>/00-intake-diagnosis.md
```

If validation fails, stop there and explain blockers.

## Recommended One-Command Path

Prefer the orchestrated runner when you want a stable closed loop instead of hand-stitching commands:

One-time dependency bootstrap on a new machine:

```bash
bash scripts/bootstrap_dependencies.sh
```

This bootstrap should prefer a local Chrome / Edge browser for Mermaid CLI when available, instead of forcing a bundled browser download.

On Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_dependencies.ps1
```

```bash
python3 scripts/run_pack_pipeline.py \
  --mode full \
  --input <raw-intake.json> \
  --output-root <runs-dir>
```

```bash
python3 scripts/run_pack_pipeline.py \
  --mode delta \
  --input <change-intake.json> \
  --impact-scope <impact-scope.json> \
  --output-root <runs-dir>
```

If you want the runner to install missing Mermaid and PDF dependencies before execution:

```bash
python3 scripts/run_pack_pipeline.py \
  --mode full \
  --input <raw-intake.json> \
  --output-root <runs-dir> \
  --bootstrap-deps
```

This runner will:

- create the run directory
- copy the constrained intake files into it
- run diagnosis and validation
- build the full or delta pack
- attempt Mermaid and PDF export
- always write `03-delivery-status.json`

If dependency bootstrap cannot finish everything automatically, the agent must point the user to `references/dependency-setup.md` instead of giving a vague “please install dependencies” answer.

## Step 3: Build the constrained manifest

### Full mode

Turn the intake into a pack-ready manifest using the normalized schema in `references/pack-schema.md`.

Normalize with:

```bash
scripts/normalize_inputs.py --input <run-dir>/01-raw-intake.json --output <run-dir>/02-normalized-pack.json
scripts/validate_manifest.py --mode full-normalized --input <run-dir>/02-normalized-pack.json --output <run-dir>/normalized-validation.json
```

Only continue if normalized validation passes.

### Delta mode

Write:

- `01-change-intake.json`
- `02-impact-scope.json`

Validate the impact scope:

```bash
scripts/validate_manifest.py --mode delta-impact --input <run-dir>/02-impact-scope.json --output <run-dir>/impact-validation.json
```

If `impact-scope.json` is unclear, do not generate delta documents.

## Step 4: Generate the outputs

### Full mode

Build the pack:

```bash
scripts/build_pack.py --input <run-dir>/02-normalized-pack.json --output-dir <run-dir>/output
```

This creates:

- `00-overview.md`
- `01-prd.md`
- `02-pages.md`
- `03-flows.md`
- `04-ai-spec.md`
- `05-open-questions.md`
- `assets/*.json`
- `diagrams/*.mmd`

### Delta mode

Default to `delta-only` output:

- `00-change-summary.md`
- `01-changed-pages.md`
- `02-changed-flows.md`
- `03-changed-rules.md`
- `04-open-questions-delta.md`
- `05-ai-delta-spec.md`

Build the delta pack with:

```bash
python3 scripts/build_delta_pack.py --input <run-dir>/02-impact-scope.json --output-dir <run-dir>/output/delta
```

Generate a merged full pack only when:

- the user explicitly requests it
- the changed scope is broad enough to justify merge
- `merge_recommended = true`

Current bundled scripts automate `delta-only` output. If a merged full pack is required, use the delta result to confirm impact scope first, then rerun full mode from an updated normalized manifest instead of pretending merge is already automated.

## Step 5: Render Mermaid and export PDF

Only attempt these after diagnosis and validation.

Render Mermaid:

```bash
scripts/render_mermaid.sh <pack-dir>
```

Export PDF:

```bash
scripts/export_pdf.sh <pack-dir>
```

If dependencies are blocked or limited, say so explicitly. Do not hide behind “generation succeeded”.

## Step 6: Write delivery status

Always write a machine-readable status file at the end.

For a full pack:

```bash
scripts/write_delivery_status.py \
  --target-dir <pack-dir> \
  --mode full \
  --requested-level L4 \
  --validation-report <run-dir>/normalized-validation.json \
  --dependency-report <run-dir>/dependency-report.json \
  --output <run-dir>/03-delivery-status.json
```

For delta output:

```bash
scripts/write_delivery_status.py \
  --target-dir <run-dir>/output/delta \
  --mode delta \
  --requested-level L2 \
  --validation-report <run-dir>/impact-validation.json \
  --dependency-report <run-dir>/dependency-report.json \
  --output <run-dir>/03-delivery-status.json
```

Use the status file to report:

- current achieved level
- whether the requested level was met
- blockers
- missing materials
- missing dependencies
- generated outputs
- next actions

When dependencies are blocked or limited, next actions must include platform-specific commands or references.

## Intake Guidance

Use `references/intake-templates.md` to adapt reminders by source type.

The user should never have to guess what to provide next.

Say things like:

- `当前识别为截图输入。你现在可以生成 L1 结构化 PRD 包。若要提高流程图质量，请补页面跳转关系或原型链接。`
- `当前识别为 HTML 输入。页面结构证据足够，但若缺少状态逻辑，异常与状态矩阵会偏弱。`
- `当前识别到 baseline 版本。本轮会先生成 delta-only 输出，未变化部分默认沿用上一版。`

Avoid empty reminders like “Please provide more information.”

## Core References

- `references/intake-schema.md`
- `references/intake-templates.md`
- `references/pack-schema.md`
- `references/page-spec-template.md`
- `references/prd-template.md`
- `references/ai-spec-template.md`
- `references/dependency-setup.md`
- `references/flow-rules.md`
- `references/inference-rules.md`
- `references/open-questions-template.md`

## Script Summary

### `scripts/check_dependencies.py`

Preflight local SVG and PDF export capability and compute the highest provable delivery level from dependencies.

### `scripts/bootstrap_dependencies.sh`

Install the stable macOS local dependencies for `node`, `mmdc`, `pandoc`, and `weasyprint`, then verify the commands exist.

### `scripts/bootstrap_dependencies.ps1`

Install the stable Windows dependency baseline for Node.js, Mermaid CLI, and Pandoc, prefer a local Chrome / Edge browser when available, then tell the user whether a PDF engine still needs one more official setup step.

### `scripts/validate_manifest.py`

Validate full raw intake, normalized packs, delta change intake, and delta impact scope.

### `scripts/write_intake_diagnosis.py`

Turn validation and dependency reports into a stable `00-intake-diagnosis.md`.

### `scripts/normalize_inputs.py`

Normalize raw full-mode intake into the canonical pack schema.

### `scripts/build_pack.py`

Generate a full PRD pack from normalized JSON.

### `scripts/build_delta_pack.py`

Generate a delta-only PRD pack from `02-impact-scope.json` and a baseline pack.

### `scripts/run_pack_pipeline.py`

Run the full or delta workflow end to end, including diagnosis, generation, render attempts, delivery status, and optional dependency bootstrap.

### `scripts/render_mermaid.sh`

Render `.mmd` to `.svg`.

### `scripts/export_pdf.sh`

Export the review PDF when Pandoc and a supported PDF engine exist.

### `scripts/write_delivery_status.py`

Write `03-delivery-status.json` and classify the run as `blocked`, `partial`, or `complete`.
