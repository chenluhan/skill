#!/usr/bin/env python3
"""Render a structured interview pack JSON into a PDF comparison brief."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

from weasyprint import HTML


TYPE_TO_CLASS = {
    "metric": "tag-metric",
    "ownership": "tag-ownership",
    "result": "tag-result",
    "risk": "tag-risk",
    "project-title": "tag-project-title",
}

QUESTION_CLASS_META = {
    "真实性核验题": {"class": "theme-auth", "label": "真实性核验"},
    "能力深挖题": {"class": "theme-depth", "label": "能力深挖"},
    "淘汰判断题": {"class": "theme-risk", "label": "淘汰判断"},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def theme_for_question(question_class: str) -> dict[str, str]:
    return QUESTION_CLASS_META.get(question_class, QUESTION_CLASS_META["能力深挖题"])


def find_highlight_ranges(text: str, anchors: list[dict[str, Any]]) -> list[tuple[int, int, str]]:
    candidates: list[tuple[int, int, str]] = []
    for anchor in anchors:
        target = str(anchor.get("highlight_text") or anchor.get("source_text") or "").strip()
        if not target:
            continue
        start = text.find(target)
        if start == -1 and len(target) > 8:
            target = target[: min(16, len(target))]
            start = text.find(target)
        if start == -1:
            continue
        candidates.append((start, start + len(target), TYPE_TO_CLASS.get(anchor["type"], "tag-result")))

    selected: list[tuple[int, int, str]] = []
    for start, end, class_name in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(not (end <= other_start or start >= other_end) for other_start, other_end, _ in selected):
            continue
        selected.append((start, end, class_name))
    return selected


def highlight_text(text: str, anchors: list[dict[str, Any]]) -> str:
    if not anchors:
        return escape(text)

    pieces: list[str] = []
    cursor = 0
    for start, end, class_name in find_highlight_ranges(text, anchors):
        if start > cursor:
            pieces.append(escape(text[cursor:start]))
        pieces.append(f'<span class="highlight {class_name}">{escape(text[start:end])}</span>')
        cursor = end
    if cursor < len(text):
        pieces.append(escape(text[cursor:]))
    return "".join(pieces) if pieces else escape(text)


def render_source_block(block: dict[str, Any], anchors: list[dict[str, Any]]) -> str:
    badges = "".join(
        f'<span class="inline-tag {TYPE_TO_CLASS.get(anchor["type"], "tag-result")}">{escape(anchor["type"])}</span>'
        for anchor in anchors
    )
    return (
        '<div class="source-block">'
        f'<div class="source-meta">L{block.get("line_number", "-")} · {escape(block.get("section_label", ""))}</div>'
        f'<div class="source-text">{highlight_text(str(block.get("text", "")), anchors)}</div>'
        f'<div class="source-tags">{badges}</div>'
        '</div>'
    )


def render_question_card(question: dict[str, Any]) -> str:
    theme = theme_for_question(question.get("class", "能力深挖题"))
    source_quotes = "".join(f"<li>{escape(quote)}</li>" for quote in question.get("source_quotes", []))
    return (
        f'<div class="card question-card {theme["class"]}">'
        f'<div class="card-label">{escape(theme["label"])}</div>'
        f'<h4>{escape(question.get("question", ""))}</h4>'
        f'<p><strong>为什么问</strong>{escape(question.get("why", ""))}</p>'
        f'<p><strong>判断信号</strong>{escape(question.get("signal", ""))}</p>'
        f'<p><strong>强回答</strong>{escape(question.get("strong_signal", ""))}</p>'
        f'<p><strong>红旗</strong>{escape(question.get("red_flag", ""))}</p>'
        f'<p><strong>追问</strong>{escape(question.get("follow_up", ""))}</p>'
        f'<div class="quote-box"><div class="quote-title">来源锚点</div><ul>{source_quotes}</ul></div>'
        '</div>'
    )


def render_annotation_card(annotation: dict[str, Any]) -> str:
    theme = theme_for_question(annotation.get("class", "能力深挖题"))
    source_quotes = "".join(f"<li>{escape(quote)}</li>" for quote in annotation.get("source_quotes", []))
    return (
        f'<div class="card annotation-card {theme["class"]}">'
        f'<div class="card-label">{escape(theme["label"])}</div>'
        f'<h4>{escape(annotation.get("label", annotation.get("note", "批注")))}</h4>'
        f'<p>{escape(annotation.get("note", ""))}</p>'
        f'<div class="quote-box"><div class="quote-title">来源锚点</div><ul>{source_quotes}</ul></div>'
        '</div>'
    )


def render_cover(pack: dict[str, Any]) -> str:
    candidate = pack.get("candidate", {})
    summary = pack.get("summary", {})
    parse_meta = pack.get("parse", {})
    strengths = "".join(f"<li>{escape(item)}</li>" for item in summary.get("top_strengths", []))
    risks = "".join(f"<li>{escape(item)}</li>" for item in summary.get("top_risks", []))
    warnings = "".join(f"<li>{escape(item)}</li>" for item in parse_meta.get("warnings", []))

    return f"""
    <section class="page cover-page">
      <div class="hero">
        <div class="eyebrow">PM Interview Screen</div>
        <h1>{escape(candidate.get("name", "候选人"))}</h1>
        <div class="hero-meta">
          <span class="badge">{escape(candidate.get("inferred_level", "层级待确认"))}</span>
          <span class="badge">{escape(candidate.get("target_domain", "通用产品经理"))}</span>
          <span class="badge">解析 {escape(parse_meta.get("strategy", "text"))} / {escape(parse_meta.get("confidence", "low"))}</span>
        </div>
        <p class="headline">{escape(summary.get("headline", ""))}</p>
        <p class="assessment">{escape(summary.get("overall_assessment", ""))}</p>
      </div>
      <div class="cover-grid">
        <div class="panel">
          <div class="panel-title">Top Strengths</div>
          <ul>{strengths}</ul>
        </div>
        <div class="panel">
          <div class="panel-title">Top Risks</div>
          <ul>{risks}</ul>
        </div>
      </div>
      <div class="warning-panel">
        <div class="panel-title">Parse Notes</div>
        <ul>{warnings}</ul>
      </div>
    </section>
    """


def render_comparison_sections(pack: dict[str, Any]) -> str:
    blocks = {block["id"]: block for block in pack.get("resume_source", {}).get("blocks", [])}
    anchors = {anchor["id"]: anchor for anchor in pack.get("resume_source", {}).get("anchors", [])}
    pages: list[str] = []

    for section in pack.get("comparison_sections", []):
        source_blocks_html = []
        for block_id in section.get("source_block_ids", []):
            block = blocks.get(block_id)
            if not block:
                continue
            block_anchors = [anchors[anchor_id] for anchor_id in section.get("source_anchor_ids", []) if anchor_id in anchors and anchors[anchor_id]["source_block_id"] == block_id]
            source_blocks_html.append(render_source_block(block, block_anchors))

        question_cards = "".join(render_question_card(question) for question in section.get("questions", []))
        annotation_cards = "".join(render_annotation_card(annotation) for annotation in section.get("annotations", []))

        pages.append(
            f"""
            <section class="page comparison-page">
              <div class="section-header">
                <div>
                  <div class="eyebrow">{escape(section.get("section_label", "对照页"))}</div>
                  <h2>{escape(section.get("title", "未命名区块"))}</h2>
                </div>
                <div class="section-judgement">{escape(section.get("judgement", ""))}</div>
              </div>
              <div class="comparison-layout">
                <div class="source-column">
                  <div class="column-title">Resume Source</div>
                  {''.join(source_blocks_html)}
                </div>
                <div class="analysis-column">
                  <div class="column-title">Interview Actions</div>
                  {question_cards}
                  {annotation_cards}
                </div>
              </div>
            </section>
            """
        )
    return "".join(pages)


def render_closing_page(pack: dict[str, Any]) -> str:
    script = pack.get("screening_script", {})
    final_recommendation = pack.get("final_recommendation", {})

    def bullet_list(items: list[str]) -> str:
        return "".join(f"<li>{escape(item)}</li>" for item in items)

    return f"""
    <section class="page closing-page">
      <div class="section-header">
        <div>
          <div class="eyebrow">30-Minute Flow</div>
          <h2>Screening Script</h2>
        </div>
        <div class="section-judgement">{escape(final_recommendation.get("decision", ""))}</div>
      </div>
      <div class="closing-grid">
        <div class="panel">
          <div class="panel-title">Opening</div>
          <ul>{bullet_list(script.get("opening", []))}</ul>
        </div>
        <div class="panel">
          <div class="panel-title">Must Ask</div>
          <ul>{bullet_list(script.get("must_ask", []))}</ul>
        </div>
        <div class="panel">
          <div class="panel-title">Optional Swaps</div>
          <ul>{bullet_list(script.get("optional_swaps", []))}</ul>
        </div>
        <div class="panel">
          <div class="panel-title">Fast Reject Triggers</div>
          <ul>{bullet_list(script.get("fast_reject_triggers", []))}</ul>
        </div>
      </div>
      <div class="final-box">
        <div class="panel-title">Final Recommendation</div>
        <p>{escape(final_recommendation.get("reason", ""))}</p>
        <div class="panel-title">Next Round Focus</div>
        <ul>{bullet_list(final_recommendation.get("next_round_focus", []))}</ul>
      </div>
    </section>
    """


def render_html(pack: dict[str, Any]) -> str:
    return f"""
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8">
        <style>
          @page {{
            size: A4;
            margin: 16mm 14mm 18mm;
          }}

          :root {{
            --paper: #f5efe3;
            --panel: #fffdf8;
            --ink: #172033;
            --muted: #61708c;
            --line: #e6dcca;
            --blue: #2b6cb0;
            --orange: #d97706;
            --red: #b42318;
            --blue-soft: rgba(43, 108, 176, 0.14);
            --orange-soft: rgba(217, 119, 6, 0.14);
            --red-soft: rgba(180, 35, 24, 0.12);
          }}

          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            font-family: "PingFang SC", "SF Pro Text", "Helvetica Neue", sans-serif;
            color: var(--ink);
            background: var(--paper);
            font-size: 11.6px;
            line-height: 1.45;
          }}

          .page {{
            page-break-after: always;
            min-height: 260mm;
          }}

          .page:last-child {{
            page-break-after: auto;
          }}

          .hero {{
            background: linear-gradient(135deg, #f8f3e8 0%, #efe7d9 55%, #e6dbc8 100%);
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 22px 24px 20px;
            margin-bottom: 18px;
          }}

          .eyebrow {{
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 9px;
            color: var(--muted);
            margin-bottom: 8px;
          }}

          h1, h2, h4, p {{
            margin: 0;
          }}

          h1 {{
            font-size: 32px;
            line-height: 1.05;
            margin-bottom: 10px;
          }}

          h2 {{
            font-size: 22px;
            line-height: 1.1;
          }}

          h4 {{
            font-size: 15px;
            line-height: 1.25;
            margin-bottom: 8px;
          }}

          .hero-meta, .source-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
          }}

          .headline {{
            margin-top: 12px;
            font-size: 17px;
            font-weight: 600;
          }}

          .assessment {{
            margin-top: 8px;
            color: var(--muted);
          }}

          .badge, .inline-tag, .card-label {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: 0.02em;
          }}

          .badge {{
            background: rgba(23, 32, 51, 0.08);
          }}

          .cover-grid, .closing-grid {{
            display: flex;
            gap: 12px;
            margin-bottom: 14px;
          }}

          .cover-grid > .panel, .closing-grid > .panel {{
            flex: 1;
          }}

          .panel, .warning-panel, .final-box {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 14px 16px;
          }}

          .panel-title {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            color: var(--muted);
            margin-bottom: 10px;
          }}

          .warning-panel ul, .panel ul, .final-box ul {{
            margin: 0;
            padding-left: 16px;
          }}

          .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 12px;
            margin-bottom: 14px;
          }}

          .section-judgement {{
            max-width: 44%;
            text-align: right;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.3;
          }}

          .comparison-layout {{
            display: flex;
            gap: 14px;
            align-items: flex-start;
          }}

          .source-column {{
            width: 45%;
          }}

          .analysis-column {{
            width: 55%;
          }}

          .column-title {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            color: var(--muted);
            margin-bottom: 8px;
          }}

          .source-block, .card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 12px 14px;
            margin-bottom: 10px;
          }}

          .source-meta {{
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
            margin-bottom: 6px;
          }}

          .source-text {{
            font-size: 12px;
            line-height: 1.5;
            margin-bottom: 8px;
          }}

          .highlight {{
            padding: 1px 2px;
            border-radius: 4px;
          }}

          .theme-depth {{
            border-left: 5px solid var(--blue);
          }}

          .theme-auth {{
            border-left: 5px solid var(--orange);
          }}

          .theme-risk {{
            border-left: 5px solid var(--red);
          }}

          .tag-metric, .tag-result, .theme-depth .card-label {{
            background: var(--blue-soft);
            color: var(--blue);
          }}

          .tag-ownership, .theme-auth .card-label {{
            background: var(--orange-soft);
            color: var(--orange);
          }}

          .tag-risk, .theme-risk .card-label {{
            background: var(--red-soft);
            color: var(--red);
          }}

          .tag-project-title {{
            background: rgba(23, 32, 51, 0.08);
            color: var(--ink);
          }}

          .question-card p, .annotation-card p {{
            margin-top: 8px;
            color: #2d3953;
          }}

          .quote-box {{
            margin-top: 10px;
            background: rgba(23, 32, 51, 0.04);
            border-radius: 12px;
            padding: 10px 12px;
          }}

          .quote-title {{
            font-size: 9px;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: var(--muted);
            margin-bottom: 6px;
          }}

          .quote-box ul {{
            margin: 0;
            padding-left: 14px;
          }}

          .closing-grid {{
            flex-wrap: wrap;
          }}

          .closing-grid > .panel {{
            flex: 1 1 48%;
          }}
        </style>
      </head>
      <body>
        {render_cover(pack)}
        {render_comparison_sections(pack)}
        {render_closing_page(pack)}
      </body>
    </html>
    """


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a structured interview pack JSON into a PDF file.")
    parser.add_argument("--pack", required=True, help="Path to render-ready interview pack JSON.")
    parser.add_argument("--output", required=True, help="Output PDF path.")
    parser.add_argument("--html-output", help="Optional HTML output path for debugging.")
    args = parser.parse_args()

    pack = load_json(Path(args.pack).expanduser())
    html_content = render_html(pack)
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content, base_url=str(output_path.parent)).write_pdf(str(output_path))

    if args.html_output:
        Path(args.html_output).expanduser().write_text(html_content, encoding="utf-8")

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
