#!/usr/bin/env python3
"""Build a PRD pack from a normalized prototype manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ARROW_MAP = {
    "request": "->>",
    "response": "-->>",
    "async": "-)",
    "error": "--x",
    "return": "-->>",
}


def slugify(text: str | None, fallback: str) -> str:
    raw = (text or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or fallback


def escape_markdown_table(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def escape_mermaid(text: str) -> str:
    return text.replace('"', '\\"')


def node_id(raw: str) -> str:
    cleaned = slugify(raw, "node")
    if cleaned[0].isdigit():
        cleaned = f"n-{cleaned}"
    return cleaned.replace("-", "_")


def unique_identifier_map(values: list[str], prefix: str) -> dict[str, str]:
    identifiers = {}
    used = set()
    for index, value in enumerate(values, 1):
        base = node_id(value)
        if base == "node":
            base = f"{prefix}_{index}"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        identifiers[value] = candidate
        used.add(candidate)
    return identifiers


def bullet_block(items, fallback: str = "None specified.") -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in values)


def code_block(content: str, language: str = "") -> str:
    fence = f"```{language}".rstrip()
    return f"{fence}\n{content.rstrip()}\n```"


def ascii_wireframe(page: dict) -> str:
    blocks = page.get("wireframe") or page.get("sections") or [page["name"]]
    items = [str(item).strip() for item in blocks if str(item).strip()]
    width = 34
    top = "+" + "-" * width + "+"
    lines = [top]
    for item in items:
        wrapped = item[:width]
        lines.append(f"| {wrapped.ljust(width - 1)}|")
    lines.append(top)
    return "\n".join(lines)


def evidence_counts(data: dict) -> dict:
    facts = sum(len(page.get("facts", [])) for page in data.get("pages", []))
    inferences = sum(len(page.get("inferences", [])) for page in data.get("pages", []))
    open_questions = len(data.get("open_questions", []))
    for rule in data.get("rules", []):
        source_type = rule.get("source_type", "explicit_fact")
        if source_type == "stable_inference":
            inferences += 1
        elif source_type == "open_question":
            open_questions += 1
        else:
            facts += 1
    return {
        "explicit_fact_count": facts,
        "stable_inference_count": inferences,
        "open_question_count": open_questions,
    }


def generate_swimlane_mermaid(flow: dict) -> str:
    if flow.get("mermaid"):
        return flow["mermaid"].rstrip() + "\n"

    lanes = flow.get("participants", [])
    steps = flow.get("steps", [])
    lane_ids = unique_identifier_map(lanes, "lane")
    lines = ["flowchart TD"]
    for lane in lanes:
        lines.append(f'  subgraph {lane_ids[lane]}["{escape_mermaid(lane)}"]')
        lane_steps = [step for step in steps if step.get("lane") == lane]
        for step in lane_steps:
            lines.append(f'    {node_id(step["id"])}["{escape_mermaid(step["label"])}"]')
        lines.append("  end")

    for edge in flow.get("edges", []):
        start = node_id(edge["from"])
        end = node_id(edge["to"])
        label = edge.get("label", "").strip()
        if label:
            lines.append(f'  {start} -->|{escape_mermaid(label)}| {end}')
        else:
            lines.append(f"  {start} --> {end}")
    return "\n".join(lines) + "\n"


def generate_sequence_mermaid(sequence: dict) -> str:
    if sequence.get("mermaid"):
        return sequence["mermaid"].rstrip() + "\n"

    lines = ["sequenceDiagram", "  autonumber"]
    participant_ids = unique_identifier_map(sequence.get("participants", []), "participant")
    for participant in sequence.get("participants", []):
        lines.append(f"  participant {participant_ids[participant]} as {participant}")
    for message in sequence.get("messages", []):
        arrow = ARROW_MAP.get(message.get("type", "request"), "->>")
        lines.append(
            f"  {participant_ids[message['from']]}{arrow}{participant_ids[message['to']]}: "
            f"{message['label']}"
        )
    return "\n".join(lines) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")


def build_overview(data: dict, pack_name: str, counts: dict) -> str:
    summary = data.get("summary", {})
    parts = [
        f"# {data['project_name']} Overview",
        "",
        "## Outcome",
        bullet_block([data.get("product_summary", ""), data.get("goal", "")]),
        "",
        "## Users",
        bullet_block(data.get("users", [])),
        "",
        "## Pack Summary",
        bullet_block(
            [
                f"Pack folder: `{pack_name}`",
                f"Pages: {summary.get('page_count', 0)}",
                f"Swimlane flows: {summary.get('flow_count', 0)}",
                f"Sequence diagrams: {summary.get('sequence_count', 0)}",
                f"Business rules: {summary.get('rule_count', 0)}",
                f"Open questions: {summary.get('open_question_count', 0)}",
            ]
        ),
        "",
        "## Evidence Summary",
        bullet_block(
            [
                f"明确事实: {counts['explicit_fact_count']}",
                f"稳定推断: {counts['stable_inference_count']}",
                f"待确认项: {counts['open_question_count']}",
            ]
        ),
        "",
        "## Source Inventory",
        bullet_block(
            [
                f"{source['id']} ({source['type']}): {source['path'] or source['note']}"
                for source in data.get("sources", [])
            ]
        ),
        "",
        "## Deliverables",
        bullet_block(
            [
                "01-prd.md for the human-readable product requirement document",
                "02-pages.md for page-by-page specs and low-fidelity wireframes",
                "03-flows.md plus Mermaid source for swimlane and sequence diagrams",
                "04-ai-spec.md for AI-ready structured execution input",
                "05-open-questions.md for unresolved product decisions",
            ]
        ),
    ]
    return "\n".join(parts)


def build_prd(data: dict) -> str:
    primary_flows = [flow["title"] for flow in data.get("flows", [])]
    states = sorted({state for page in data.get("pages", []) for state in page.get("states", [])})
    exceptions = sorted({item for page in data.get("pages", []) for item in page.get("exceptions", [])})

    lines = [
        f"# {data['project_name']} PRD",
        "",
        "## Background",
        bullet_block([data.get("product_summary", "")]),
        "",
        "## Goal",
        bullet_block([data.get("goal", "")]),
        "",
        "## Scope",
        "### In Scope",
        bullet_block(primary_flows or ["Primary request creation and tracking experience."]),
        "",
        "### Out of Scope",
        bullet_block(data.get("non_goals", [])),
        "",
        "## Target Users",
        bullet_block(data.get("users", [])),
        "",
        "## Core User Journey",
        bullet_block(primary_flows),
        "",
        "## Functional Areas",
    ]

    for page in data.get("pages", []):
        lines.extend(
            [
                f"### {page['name']}",
                bullet_block([page.get("purpose", "")]),
            ]
        )

    lines.extend(["", "## Business Rules"])
    if not data.get("rules"):
        lines.append("- No explicit rules supplied yet. See `05-open-questions.md`.")
    for rule in data.get("rules", []):
        lines.extend(
            [
                f"### {rule['title']}",
                f"- Trigger: {rule['trigger'] or 'Unspecified'}",
                f"- Condition: {rule['condition'] or 'Unspecified'}",
                f"- System behavior: {rule['system_behavior'] or 'Unspecified'}",
                f"- User-facing feedback: {rule['user_feedback'] or 'Unspecified'}",
                f"- Fallback: {rule['fallback'] or 'Unspecified'}",
                f"- Evidence class: {rule['source_type']}",
            ]
        )

    lines.extend(
        [
            "",
            "## States and Exceptions Summary",
            "### States",
            bullet_block(states),
            "",
            "### Exceptions",
            bullet_block(exceptions),
            "",
            "## Metrics",
            bullet_block(data.get("metrics", [])),
            "",
            "## Risks and Assumptions",
            bullet_block(data.get("assumptions", [])),
        ]
    )
    return "\n".join(lines)


def build_pages(data: dict) -> str:
    sections = ["# Page Specifications", ""]
    for page in data.get("pages", []):
        sections.extend(
            [
                f"## {page['name']}",
                "",
                "### Page Goal",
                bullet_block([page.get("purpose", "")]),
                "",
                "### Evidence",
                "#### 明确事实",
                bullet_block(page.get("facts", [])),
                "",
                "#### 稳定推断",
                bullet_block(page.get("inferences", [])),
                "",
                "### Entry Points",
                bullet_block(page.get("entry_points", [])),
                "",
                "### Exit Points",
                bullet_block(page.get("exit_points", [])),
                "",
                "### Information Blocks",
                bullet_block(page.get("sections", [])),
                "",
                "### User Actions",
                bullet_block(page.get("user_actions", [])),
                "",
                "### System Feedback",
                bullet_block(page.get("system_feedback", [])),
                "",
                "### States",
                bullet_block(page.get("states", [])),
                "",
                "### Exceptions",
                bullet_block(page.get("exceptions", [])),
                "",
                "### Permissions",
                bullet_block(page.get("permissions", [])),
                "",
                "### Analytics",
                bullet_block(page.get("analytics", [])),
                "",
                "### Low-Fidelity Wireframe",
                code_block(ascii_wireframe(page), "text"),
                "",
                "### Source Refs",
                bullet_block(page.get("source_refs", [])),
                "",
            ]
        )
    return "\n".join(sections)


def build_flows_markdown(diagrams: list[dict]) -> str:
    sections = ["# Flows and Diagrams", ""]
    if not diagrams:
        sections.append("- No flow assets were generated.")
        return "\n".join(sections)

    for diagram in diagrams:
        sections.extend(
            [
                f"## {diagram['title']}",
                f"- Type: {diagram['diagram_type']}",
                f"- Purpose: {diagram['purpose'] or 'Unspecified'}",
                f"- Mermaid source: `{diagram['source_path']}`",
                f"- Rendered asset: `./{diagram['rendered_path']}`",
                "",
                f"![{diagram['title']}](./{diagram['rendered_path']})",
                "",
                "### Known Gaps",
                bullet_block(diagram["known_gaps"]),
                "",
            ]
        )
    return "\n".join(sections)


def build_ai_spec(data: dict, diagrams: list[dict]) -> str:
    parts = [
        "# AI-Ready Spec",
        "",
        "## Metadata",
        code_block(
            json.dumps(
                {
                    "project_name": data["project_name"],
                    "goal": data.get("goal", ""),
                    "users": data.get("users", []),
                    "metrics": data.get("metrics", []),
                },
                ensure_ascii=False,
                indent=2,
            ),
            "json",
        ),
        "",
        "## Pages",
    ]
    for page in data.get("pages", []):
        parts.extend(
            [
                f"### {page['id']}",
                code_block(
                    json.dumps(
                        {
                            "id": page["id"],
                            "name": page["name"],
                            "purpose": page.get("purpose", ""),
                            "entry_points": page.get("entry_points", []),
                            "exit_points": page.get("exit_points", []),
                            "sections": page.get("sections", []),
                            "user_actions": page.get("user_actions", []),
                            "system_feedback": page.get("system_feedback", []),
                            "states": page.get("states", []),
                            "exceptions": page.get("exceptions", []),
                            "permissions": page.get("permissions", []),
                            "analytics": page.get("analytics", []),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "json",
                ),
                "",
            ]
        )

    parts.extend(["## Rules"])
    for rule in data.get("rules", []):
        parts.extend(
            [
                f"### {rule['id']}",
                code_block(json.dumps(rule, ensure_ascii=False, indent=2), "json"),
                "",
            ]
        )

    parts.extend(
        [
            "## Flow Assets",
            code_block(
                json.dumps(
                    {
                        "swimlanes": [
                            diagram["source_path"]
                            for diagram in diagrams
                            if diagram["diagram_type"] == "swimlane"
                        ],
                        "sequences": [
                            diagram["source_path"]
                            for diagram in diagrams
                            if diagram["diagram_type"] == "sequence"
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "json",
            ),
            "",
            "## Open Questions",
            code_block(json.dumps(data.get("open_questions", []), ensure_ascii=False, indent=2), "json"),
        ]
    )
    return "\n".join(parts)


def build_open_questions(data: dict) -> str:
    lines = [
        "# Open Questions",
        "",
        "| ID | Related To | Question | Impact | Owner | Default Assumption |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for item in data.get("open_questions", []):
        lines.append(
            "| {id} | {related_to} | {question} | {impact} | {owner} | {default_assumption} |".format(
                id=escape_markdown_table(item["id"]),
                related_to=escape_markdown_table(item.get("related_to", "")),
                question=escape_markdown_table(item.get("question", "")),
                impact=escape_markdown_table(item.get("impact", "")),
                owner=escape_markdown_table(item.get("owner", "")),
                default_assumption=escape_markdown_table(item.get("default_assumption", "")),
            )
        )

    if not data.get("open_questions"):
        lines.append("| none | - | No open questions supplied. | - | - | - |")
    return "\n".join(lines)


def build_page_index(data: dict) -> dict:
    return {
        "project_name": data["project_name"],
        "pages": [
            {
                "id": page["id"],
                "name": page["name"],
                "purpose": page.get("purpose", ""),
                "source_refs": page.get("source_refs", []),
            }
            for page in data.get("pages", [])
        ],
    }


def build_screen_map(data: dict) -> dict:
    return {
        "project_name": data["project_name"],
        "page_order": [page["id"] for page in data.get("pages", [])],
        "pages": [
            {
                "id": page["id"],
                "entry_points": page.get("entry_points", []),
                "exit_points": page.get("exit_points", []),
                "states": page.get("states", []),
            }
            for page in data.get("pages", [])
        ],
    }


def build_evidence_asset(data: dict, counts: dict) -> dict:
    return {
        "project_name": data["project_name"],
        "summary": counts,
        "pages": [
            {
                "id": page["id"],
                "facts": page.get("facts", []),
                "inferences": page.get("inferences", []),
                "source_refs": page.get("source_refs", []),
            }
            for page in data.get("pages", [])
        ],
        "rules": data.get("rules", []),
        "open_questions": data.get("open_questions", []),
    }


def build_flow_index(diagrams: list[dict]) -> dict:
    return {
        "flows": [
            {
                "id": diagram.get("id", ""),
                "title": diagram["title"],
                "diagram_type": diagram["diagram_type"],
                "purpose": diagram.get("purpose", ""),
                "participants": diagram.get("participants", []),
                "known_gaps": diagram.get("known_gaps", []),
                "source_path": diagram["source_path"],
                "rendered_path": diagram["rendered_path"],
            }
            for diagram in diagrams
        ]
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to normalized JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory where the pack folder will be created.")
    parser.add_argument("--pack-name", help="Optional explicit pack directory name.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_root = Path(args.output_dir)

    try:
        data = json.loads(input_path.read_text())
    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON in {input_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("[ERROR] Normalized input must be a JSON object.", file=sys.stderr)
        return 1

    pack_name = args.pack_name or f"{slugify(data.get('project_name'), 'project')}-prd-pack"
    pack_dir = output_root / pack_name
    if pack_dir.exists():
        print(f"[ERROR] Pack directory already exists: {pack_dir}", file=sys.stderr)
        return 1

    diagrams_dir = pack_dir / "diagrams"
    rendered_dir = diagrams_dir / "rendered"
    assets_dir = pack_dir / "assets"
    export_dir = pack_dir / "export"
    for path in (diagrams_dir, rendered_dir, assets_dir, export_dir):
        path.mkdir(parents=True, exist_ok=True)

    diagram_entries = []
    for index, flow in enumerate(data.get("flows", []), 1):
        filename = f"flow-{flow['id'] or index}.mmd"
        mermaid = generate_swimlane_mermaid(flow)
        write_text(diagrams_dir / filename, mermaid)
        diagram_entries.append(
            {
                "id": flow["id"],
                "title": flow["title"],
                "diagram_type": "swimlane",
                "purpose": flow.get("purpose", ""),
                "participants": flow.get("participants", []),
                "known_gaps": flow.get("known_gaps", []),
                "source_path": f"diagrams/{filename}",
                "rendered_path": f"diagrams/rendered/{filename.replace('.mmd', '.png')}",
                "mermaid": mermaid,
            }
        )

    for index, sequence in enumerate(data.get("sequences", []), 1):
        filename = f"sequence-{sequence['id'] or index}.mmd"
        mermaid = generate_sequence_mermaid(sequence)
        write_text(diagrams_dir / filename, mermaid)
        diagram_entries.append(
            {
                "id": sequence["id"],
                "title": sequence["title"],
                "diagram_type": "sequence",
                "purpose": sequence.get("purpose", ""),
                "participants": sequence.get("participants", []),
                "known_gaps": sequence.get("known_gaps", []),
                "source_path": f"diagrams/{filename}",
                "rendered_path": f"diagrams/rendered/{filename.replace('.mmd', '.png')}",
                "mermaid": mermaid,
            }
        )

    counts = evidence_counts(data)

    write_text(pack_dir / "00-overview.md", build_overview(data, pack_name, counts))
    write_text(pack_dir / "01-prd.md", build_prd(data))
    write_text(pack_dir / "02-pages.md", build_pages(data))
    write_text(pack_dir / "03-flows.md", build_flows_markdown(diagram_entries))
    write_text(pack_dir / "04-ai-spec.md", build_ai_spec(data, diagram_entries))
    write_text(pack_dir / "05-open-questions.md", build_open_questions(data))

    (assets_dir / "page-index.json").write_text(
        json.dumps(build_page_index(data), ensure_ascii=False, indent=2) + "\n"
    )
    (assets_dir / "screen-map.json").write_text(
        json.dumps(build_screen_map(data), ensure_ascii=False, indent=2) + "\n"
    )
    (assets_dir / "evidence.json").write_text(
        json.dumps(build_evidence_asset(data, counts), ensure_ascii=False, indent=2) + "\n"
    )
    (assets_dir / "flow-index.json").write_text(
        json.dumps(build_flow_index(diagram_entries), ensure_ascii=False, indent=2) + "\n"
    )

    print(f"[OK] Built pack at {pack_dir}")
    print(f"[OK] Generated {len(diagram_entries)} Mermaid source file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
