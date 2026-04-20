#!/usr/bin/env python3
"""Build a delta-only PRD pack from an impact-scope manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from build_pack import (
    ascii_wireframe,
    bullet_block,
    code_block,
    generate_sequence_mermaid,
    generate_swimlane_mermaid,
    slugify,
    write_text,
)


ACTIVE_ACTIONS = {"add", "added", "update", "remove", "resolved"}
UNCHANGED_ACTIONS = {"no_change", "unchanged"}


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def string_list(value) -> list[str]:
    items = []
    for item in ensure_list(value):
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def first_present(mapping: dict, *keys, default=None):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def is_active(action: str) -> bool:
    return action in ACTIVE_ACTIONS or action not in UNCHANGED_ACTIONS


def action_label(action: str) -> str:
    return action.replace("_", " ").strip() or "update"


def resolve_baseline_pack(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Baseline reference not found: {path}")

    candidates = []
    seen = set()

    def add_candidate(candidate: Path) -> None:
        resolved = candidate.resolve()
        if resolved in seen:
            return
        if candidate.is_dir() and (candidate / "00-overview.md").exists():
            seen.add(resolved)
            candidates.append(candidate)

    if path.is_file():
        if path.name == "00-overview.md":
            add_candidate(path.parent)
        path = path.parent

    search_roots = [path, path / "output", path / "merged", path / "output" / "merged"]
    for root in search_roots:
        if not root.exists() or not root.is_dir():
            continue
        add_candidate(root)
        for child in sorted(root.iterdir()):
            add_candidate(child)

    if not candidates:
        raise FileNotFoundError(f"Could not resolve a baseline pack from: {path}")

    if len(candidates) == 1:
        return candidates[0]

    ranked = sorted(candidates, key=lambda item: (len(item.parts), str(item)))
    if ranked[0].parent == path or ranked[0] == path:
        return ranked[0]

    joined = ", ".join(str(item) for item in ranked)
    raise ValueError(f"Multiple baseline pack candidates found: {joined}")


def load_optional_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback or {}
    return load_json(path)


def read_project_name(pack_dir: Path) -> str:
    overview = pack_dir / "00-overview.md"
    if overview.exists():
        first_line = overview.read_text().splitlines()[0].strip()
        match = re.match(r"#\s+(.*?)\s+Overview$", first_line)
        if match:
            return match.group(1).strip()
    return pack_dir.name


def fallback_flow_index(pack_dir: Path) -> dict:
    flows = []
    diagrams_dir = pack_dir / "diagrams"
    for src in sorted(diagrams_dir.glob("*.mmd")):
        if src.name.startswith("sequence-"):
            item_id = src.stem.removeprefix("sequence-")
            diagram_type = "sequence"
        elif src.name.startswith("flow-"):
            item_id = src.stem.removeprefix("flow-")
            diagram_type = "swimlane"
        else:
            item_id = src.stem
            diagram_type = "swimlane"
        flows.append(
            {
                "id": item_id,
                "title": item_id.replace("-", " ").title(),
                "diagram_type": diagram_type,
                "purpose": "",
                "participants": [],
                "known_gaps": [],
                "source_path": f"diagrams/{src.name}",
                "rendered_path": f"diagrams/rendered/{src.stem}.svg",
            }
        )
    return {"flows": flows}


def load_baseline_context(pack_dir: Path) -> dict:
    assets_dir = pack_dir / "assets"
    page_index = load_optional_json(assets_dir / "page-index.json", {"pages": []})
    screen_map = load_optional_json(assets_dir / "screen-map.json", {"pages": []})
    evidence = load_optional_json(assets_dir / "evidence.json", {"rules": [], "open_questions": []})
    flow_index = load_optional_json(assets_dir / "flow-index.json") or fallback_flow_index(pack_dir)

    pages_by_id = {
        str(page.get("id", "")).strip(): dict(page)
        for page in ensure_list(page_index.get("pages"))
        if isinstance(page, dict) and str(page.get("id", "")).strip()
    }
    for page in ensure_list(screen_map.get("pages")):
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("id", "")).strip()
        if not page_id:
            continue
        pages_by_id.setdefault(page_id, {}).update(page)

    flows_by_id = {
        str(flow.get("id", "")).strip(): dict(flow)
        for flow in ensure_list(flow_index.get("flows"))
        if isinstance(flow, dict) and str(flow.get("id", "")).strip()
    }
    rules_by_id = {
        str(rule.get("id", "")).strip(): dict(rule)
        for rule in ensure_list(evidence.get("rules"))
        if isinstance(rule, dict) and str(rule.get("id", "")).strip()
    }
    questions_by_id = {
        str(item.get("id", "")).strip(): dict(item)
        for item in ensure_list(evidence.get("open_questions"))
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }

    return {
        "project_name": str(
            first_present(
                page_index,
                "project_name",
                default=first_present(screen_map, "project_name", default=first_present(evidence, "project_name", default="")),
            )
        ).strip()
        or read_project_name(pack_dir),
        "pages": pages_by_id,
        "flows": flows_by_id,
        "rules": rules_by_id,
        "open_questions": questions_by_id,
    }


def active_entries(change_scope: dict, key: str) -> list[dict]:
    return [
        entry
        for entry in ensure_list(change_scope.get(key))
        if isinstance(entry, dict) and is_active(str(entry.get("action", "")).strip())
    ]


def unchanged_entries(change_scope: dict, key: str) -> list[dict]:
    return [
        entry
        for entry in ensure_list(change_scope.get(key))
        if isinstance(entry, dict) and str(entry.get("action", "")).strip() in UNCHANGED_ACTIONS
    ]


def baseline_snapshot_lines(title: str, values) -> list[str]:
    lines = [f"### {title}"]
    lines.append(bullet_block(values))
    lines.append("")
    return lines


def summarize_active_counts(change_scope: dict) -> dict:
    return {
        "pages": len(active_entries(change_scope, "pages")),
        "flows": len(active_entries(change_scope, "flows")),
        "rules": len(active_entries(change_scope, "rules")),
        "open_questions": len(active_entries(change_scope, "open_questions")),
    }


def build_change_summary(data: dict, baseline_dir: Path, project_name: str, diagram_notes: list[str]) -> str:
    change_scope = data.get("change_scope", {})
    counts = summarize_active_counts(change_scope)
    unchanged = string_list(data.get("unchanged_artifacts"))

    lines = [
        f"# {project_name} Delta Summary",
        "",
        "## Baseline",
        bullet_block(
            [
                f"Baseline pack: `{baseline_dir}`",
                f"Merge recommended: {'yes' if data.get('merge_recommended') else 'no'}",
            ]
        ),
        "",
        "## Detected Delta",
        bullet_block(
            [
                f"Changed pages: {counts['pages']}",
                f"Changed flows: {counts['flows']}",
                f"Changed rules: {counts['rules']}",
                f"Open-question deltas: {counts['open_questions']}",
            ]
        ),
        "",
        "## Delta Rules",
        bullet_block(
            [
                "This package only includes changed artifacts.",
                "Any artifact not listed here defaults to the baseline version.",
            ]
        ),
        "",
        "## Explicitly Unchanged",
        bullet_block(unchanged, fallback="No unchanged artifacts were explicitly declared."),
    ]

    if diagram_notes:
        lines.extend(["", "## Diagram Notes", bullet_block(diagram_notes)])

    if data.get("merge_recommended"):
        lines.extend(
            [
                "",
                "## Recommendation",
                bullet_block(
                    [
                        "This scope is broad enough that a merged full pack may be easier for engineering to consume.",
                        "Current output remains delta-only; unchanged sections are intentionally not duplicated.",
                    ]
                ),
            ]
        )

    return "\n".join(lines)


def page_title(entry: dict, baseline_page: dict) -> str:
    return (
        str(first_present(entry, "title", "page_name", "name", default="")).strip()
        or str(baseline_page.get("name", "")).strip()
        or str(entry.get("id", "")).strip()
    )


def build_changed_pages(data: dict, baseline: dict) -> str:
    entries = active_entries(data.get("change_scope", {}), "pages")
    lines = ["# Changed Pages", ""]
    if not entries:
        lines.append("- No page deltas were declared.")
        return "\n".join(lines)

    for entry in entries:
        page_id = str(entry.get("id", "")).strip()
        baseline_page = baseline["pages"].get(page_id, {})
        title = page_title(entry, baseline_page)
        lines.extend(
            [
                f"## {title}",
                f"- Page ID: `{page_id}`",
                f"- Action: {action_label(str(entry.get('action', 'update')))}",
                f"- Change reason: {str(entry.get('reason', '')).strip() or 'Unspecified'}",
                "",
            ]
        )

        if baseline_page:
            lines.extend(
                baseline_snapshot_lines("Baseline Purpose", [baseline_page.get("purpose", "")])
            )
            lines.extend(
                baseline_snapshot_lines("Baseline Entry Points", baseline_page.get("entry_points", []))
            )
            lines.extend(
                baseline_snapshot_lines("Baseline Exit Points", baseline_page.get("exit_points", []))
            )
            lines.extend(
                baseline_snapshot_lines("Baseline States", baseline_page.get("states", []))
            )

        delta_sections = [
            ("Changed Elements", first_present(entry, "changed_elements", "changes")),
            ("Updated Entry Points", entry.get("entry_points")),
            ("Updated Exit Points", entry.get("exit_points")),
            ("Updated User Actions", entry.get("user_actions")),
            ("Updated System Feedback", entry.get("system_feedback")),
            ("Updated States", entry.get("states")),
            ("Updated Exceptions", entry.get("exceptions")),
            ("Notes", entry.get("notes")),
            ("Source Refs", first_present(entry, "source_refs", "sources")),
        ]
        for section_title, values in delta_sections:
            values_list = string_list(values)
            if values_list:
                lines.extend([f"### {section_title}", bullet_block(values_list), ""])

        wireframe = string_list(entry.get("wireframe"))
        if wireframe:
            lines.extend(
                [
                    "### Delta Wireframe",
                    code_block(ascii_wireframe({"name": title, "wireframe": wireframe}), "text"),
                    "",
                ]
            )

        if not any(string_list(value) for _, value in delta_sections) and not wireframe:
            lines.extend(
                [
                    "### Delivery Note",
                    "- Only impact-level change evidence was provided. Field-level page deltas still need confirmation.",
                    "",
                ]
            )

    return "\n".join(lines)


def infer_diagram_type(entry: dict, baseline_flow: dict) -> str:
    explicit = str(entry.get("diagram_type", "")).strip().lower()
    if explicit in {"swimlane", "sequence"}:
        return explicit
    if ensure_list(entry.get("messages")):
        return "sequence"
    baseline_type = str(baseline_flow.get("diagram_type", "")).strip().lower()
    if baseline_type in {"swimlane", "sequence"}:
        return baseline_type
    return "swimlane"


def maybe_read_baseline_mermaid(entry: dict, baseline_flow: dict, baseline_dir: Path) -> str:
    if not entry.get("use_baseline_mermaid"):
        return ""
    source_path = str(baseline_flow.get("source_path", "")).strip()
    if not source_path:
        return ""
    source_file = baseline_dir / source_path
    if not source_file.exists():
        return ""
    return source_file.read_text().rstrip() + "\n"


def flow_mermaid(entry: dict, baseline_flow: dict, baseline_dir: Path) -> tuple[str, str]:
    direct = str(entry.get("mermaid", "")).rstrip()
    if direct:
        return direct + "\n", ""

    baseline_copy = maybe_read_baseline_mermaid(entry, baseline_flow, baseline_dir)
    if baseline_copy:
        return baseline_copy, "Baseline Mermaid source was reused because the impact scope explicitly allowed it."

    diagram_type = infer_diagram_type(entry, baseline_flow)
    participants = string_list(entry.get("participants")) or string_list(baseline_flow.get("participants"))

    if diagram_type == "sequence" and ensure_list(entry.get("messages")):
        mermaid = generate_sequence_mermaid(
            {
                "participants": participants,
                "messages": entry.get("messages"),
                "mermaid": "",
            }
        )
        return mermaid, ""

    if diagram_type == "swimlane" and ensure_list(entry.get("steps")):
        mermaid = generate_swimlane_mermaid(
            {
                "participants": participants,
                "steps": entry.get("steps"),
                "edges": ensure_list(entry.get("edges")),
                "mermaid": "",
            }
        )
        return mermaid, ""

    action = str(entry.get("action", "")).strip()
    if action in {"remove", "resolved"}:
        return "", "Removed or resolved flow entries do not require a new diagram source."

    return "", "No Mermaid source was generated because the impact scope did not include `mermaid`, `steps`, or `messages`."


def build_changed_flows(data: dict, baseline: dict, baseline_dir: Path, pack_dir: Path) -> tuple[str, list[dict], list[str]]:
    entries = active_entries(data.get("change_scope", {}), "flows")
    diagrams_dir = pack_dir / "diagrams"
    diagram_entries = []
    diagram_notes = []
    lines = ["# Changed Flows", ""]

    if not entries:
        lines.append("- No flow deltas were declared.")
        return "\n".join(lines), diagram_entries, diagram_notes

    for entry in entries:
        flow_id = str(entry.get("id", "")).strip()
        baseline_flow = baseline["flows"].get(flow_id, {})
        title = (
            str(first_present(entry, "title", "name", default="")).strip()
            or str(baseline_flow.get("title", "")).strip()
            or flow_id
        )
        mermaid, delivery_note = flow_mermaid(entry, baseline_flow, baseline_dir)
        diagram_type = infer_diagram_type(entry, baseline_flow)
        relative_source = ""
        relative_rendered = ""

        if mermaid:
            prefix = "sequence" if diagram_type == "sequence" else "flow"
            filename = f"{prefix}-{slugify(flow_id or title, 'flow')}.mmd"
            write_text(diagrams_dir / filename, mermaid)
            relative_source = f"diagrams/{filename}"
            relative_rendered = f"diagrams/rendered/{filename.replace('.mmd', '.svg')}"
            diagram_entries.append(
                {
                    "id": flow_id,
                    "title": title,
                    "diagram_type": diagram_type,
                    "purpose": str(first_present(entry, "purpose", default=baseline_flow.get("purpose", ""))).strip(),
                    "known_gaps": string_list(first_present(entry, "known_gaps", "gaps", default=[])),
                    "participants": string_list(entry.get("participants")) or string_list(baseline_flow.get("participants")),
                    "source_path": relative_source,
                    "rendered_path": relative_rendered,
                    "mermaid": mermaid,
                }
            )
        elif delivery_note:
            diagram_notes.append(f"{flow_id}: {delivery_note}")

        lines.extend(
            [
                f"## {title}",
                f"- Flow ID: `{flow_id}`",
                f"- Action: {action_label(str(entry.get('action', 'update')))}",
                f"- Change reason: {str(entry.get('reason', '')).strip() or 'Unspecified'}",
                f"- Baseline Mermaid: {str(baseline_flow.get('source_path', '')).strip() or 'Not found'}",
                "",
            ]
        )

        participants = string_list(entry.get("participants")) or string_list(baseline_flow.get("participants"))
        if participants:
            lines.extend(["### Participants", bullet_block(participants), ""])

        notes = string_list(first_present(entry, "notes", "changed_paths"))
        if notes:
            lines.extend(["### Change Notes", bullet_block(notes), ""])

        if mermaid:
            lines.extend(
                [
                    "### Mermaid Source",
                    f"- Source file: `{relative_source}`",
                    "",
                    f"![{title}](./{relative_rendered})",
                    "",
                    code_block(mermaid, "mermaid"),
                    "",
                ]
            )
        elif delivery_note:
            lines.extend(["### Delivery Note", f"- {delivery_note}", ""])

    return "\n".join(lines), diagram_entries, diagram_notes


def build_changed_rules(data: dict, baseline: dict) -> str:
    change_scope = data.get("change_scope", {})
    entries = active_entries(change_scope, "rules")
    unchanged = unchanged_entries(change_scope, "rules")
    lines = ["# Changed Rules", ""]

    if not entries:
        lines.append("- No rule deltas were declared.")
    else:
        for entry in entries:
            rule_id = str(entry.get("id", "")).strip()
            baseline_rule = baseline["rules"].get(rule_id, {})
            title = (
                str(first_present(entry, "title", default="")).strip()
                or str(baseline_rule.get("title", "")).strip()
                or rule_id
            )
            lines.extend(
                [
                    f"## {title}",
                    f"- Rule ID: `{rule_id}`",
                    f"- Action: {action_label(str(entry.get('action', 'update')))}",
                    f"- Change reason: {str(entry.get('reason', '')).strip() or 'Unspecified'}",
                    "",
                ]
            )

            if baseline_rule:
                lines.extend(
                    [
                        "### Baseline Behavior",
                        bullet_block(
                            [
                                f"Trigger: {baseline_rule.get('trigger', '') or 'Unspecified'}",
                                f"Condition: {baseline_rule.get('condition', '') or 'Unspecified'}",
                                f"System behavior: {baseline_rule.get('system_behavior', '') or 'Unspecified'}",
                                f"User feedback: {baseline_rule.get('user_feedback', '') or 'Unspecified'}",
                                f"Fallback: {baseline_rule.get('fallback', '') or 'Unspecified'}",
                            ]
                        ),
                        "",
                    ]
                )

            delta_fields = [
                ("Updated Trigger", entry.get("trigger")),
                ("Updated Condition", entry.get("condition")),
                ("Updated System Behavior", first_present(entry, "system_behavior", "behavior")),
                ("Updated User Feedback", first_present(entry, "user_feedback", "feedback")),
                ("Updated Fallback", entry.get("fallback")),
                ("Notes", entry.get("notes")),
            ]
            for section_title, value in delta_fields:
                values = string_list(value)
                if values:
                    lines.extend([f"### {section_title}", bullet_block(values), ""])

            if not any(string_list(value) for _, value in delta_fields):
                lines.extend(
                    [
                        "### Delivery Note",
                        "- Only impact-level change evidence was provided. The exact rule text still needs confirmation.",
                        "",
                    ]
                )

    if unchanged:
        lines.extend(
            [
                "## Explicitly Unchanged Rules",
                bullet_block(
                    [
                        f"{entry.get('id', '')}: {entry.get('reason', '') or 'No change declared.'}"
                        for entry in unchanged
                    ]
                ),
            ]
        )

    return "\n".join(lines)


def build_open_questions_delta(data: dict, baseline: dict) -> str:
    change_scope = data.get("change_scope", {})
    entries = active_entries(change_scope, "open_questions")
    lines = ["# Open Questions Delta", ""]

    if not entries:
        lines.append("- No open-question delta was declared.")
        return "\n".join(lines)

    for entry in entries:
        question_id = str(entry.get("id", "")).strip()
        baseline_item = baseline["open_questions"].get(question_id, {})
        title = (
            str(first_present(entry, "title", "question", default="")).strip()
            or str(baseline_item.get("title", "")).strip()
            or question_id
        )
        lines.extend(
            [
                f"## {title}",
                f"- Open Question ID: `{question_id}`",
                f"- Action: {action_label(str(entry.get('action', 'update')))}",
                f"- Reason: {str(entry.get('reason', '')).strip() or 'Unspecified'}",
                "",
            ]
        )

        baseline_question = str(baseline_item.get("question", "")).strip()
        if baseline_question:
            lines.extend(["### Baseline Question", f"- {baseline_question}", ""])

        delta_fields = [
            ("Current Question", first_present(entry, "question", "title")),
            ("Impact", entry.get("impact")),
            ("Owner", entry.get("owner")),
            ("Default Assumption", entry.get("default_assumption")),
            ("Resolution", entry.get("resolution")),
            ("Notes", entry.get("notes")),
        ]
        for section_title, value in delta_fields:
            values = string_list(value)
            if values:
                lines.extend([f"### {section_title}", bullet_block(values), ""])

    return "\n".join(lines)


def build_ai_delta_spec(
    data: dict,
    baseline_dir: Path,
    project_name: str,
    baseline: dict,
    diagram_entries: list[dict],
) -> str:
    change_scope = data.get("change_scope", {})
    payload = {
        "project_name": project_name,
        "baseline_ref": str(baseline_dir),
        "merge_recommended": bool(data.get("merge_recommended")),
        "unchanged_artifacts": string_list(data.get("unchanged_artifacts")),
        "changed_pages": [],
        "changed_flows": [],
        "changed_rules": [],
        "open_question_deltas": [],
        "generated_diagrams": [
            {
                "id": item["id"],
                "title": item["title"],
                "diagram_type": item["diagram_type"],
                "source_path": item["source_path"],
            }
            for item in diagram_entries
        ],
    }

    for entry in active_entries(change_scope, "pages"):
        page_id = str(entry.get("id", "")).strip()
        payload["changed_pages"].append(
            {
                "id": page_id,
                "action": entry.get("action", "update"),
                "reason": entry.get("reason", ""),
                "baseline_snapshot": baseline["pages"].get(page_id, {}),
                "delta": {
                    key: value
                    for key, value in entry.items()
                    if key not in {"id", "action", "reason"}
                },
            }
        )

    for entry in active_entries(change_scope, "flows"):
        flow_id = str(entry.get("id", "")).strip()
        payload["changed_flows"].append(
            {
                "id": flow_id,
                "action": entry.get("action", "update"),
                "reason": entry.get("reason", ""),
                "baseline_snapshot": baseline["flows"].get(flow_id, {}),
                "delta": {
                    key: value
                    for key, value in entry.items()
                    if key not in {"id", "action", "reason"}
                },
            }
        )

    for entry in active_entries(change_scope, "rules"):
        rule_id = str(entry.get("id", "")).strip()
        payload["changed_rules"].append(
            {
                "id": rule_id,
                "action": entry.get("action", "update"),
                "reason": entry.get("reason", ""),
                "baseline_snapshot": baseline["rules"].get(rule_id, {}),
                "delta": {
                    key: value
                    for key, value in entry.items()
                    if key not in {"id", "action", "reason"}
                },
            }
        )

    for entry in active_entries(change_scope, "open_questions"):
        question_id = str(entry.get("id", "")).strip()
        payload["open_question_deltas"].append(
            {
                "id": question_id,
                "action": entry.get("action", "update"),
                "reason": entry.get("reason", ""),
                "baseline_snapshot": baseline["open_questions"].get(question_id, {}),
                "delta": {
                    key: value
                    for key, value in entry.items()
                    if key not in {"id", "action", "reason"}
                },
            }
        )

    return "\n".join(
        [
            "# AI Delta Spec",
            "",
            "## Structured Delta Payload",
            code_block(json.dumps(payload, ensure_ascii=False, indent=2), "json"),
        ]
    )


def build_baseline_snapshot(data: dict, baseline: dict) -> dict:
    change_scope = data.get("change_scope", {})
    return {
        "pages": {
            str(entry.get("id", "")).strip(): baseline["pages"].get(str(entry.get("id", "")).strip(), {})
            for entry in active_entries(change_scope, "pages")
        },
        "flows": {
            str(entry.get("id", "")).strip(): baseline["flows"].get(str(entry.get("id", "")).strip(), {})
            for entry in active_entries(change_scope, "flows")
        },
        "rules": {
            str(entry.get("id", "")).strip(): baseline["rules"].get(str(entry.get("id", "")).strip(), {})
            for entry in active_entries(change_scope, "rules")
        },
        "open_questions": {
            str(entry.get("id", "")).strip(): baseline["open_questions"].get(str(entry.get("id", "")).strip(), {})
            for entry in active_entries(change_scope, "open_questions")
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the delta impact-scope JSON file.")
    parser.add_argument("--output-dir", required=True, help="Directory where the delta pack will be created.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    try:
        data = load_json(input_path)
        baseline_dir = resolve_baseline_pack(Path(str(data.get("baseline_ref", "")).strip()))
        baseline = load_baseline_context(baseline_dir)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"[ERROR] Output directory already exists and is not empty: {output_dir}", file=sys.stderr)
        return 1

    project_name = str(data.get("project_name", "")).strip() or baseline["project_name"]
    diagrams_dir = output_dir / "diagrams"
    rendered_dir = diagrams_dir / "rendered"
    assets_dir = output_dir / "assets"
    export_dir = output_dir / "export"
    for path in (diagrams_dir, rendered_dir, assets_dir, export_dir):
        path.mkdir(parents=True, exist_ok=True)

    flows_markdown, diagram_entries, diagram_notes = build_changed_flows(data, baseline, baseline_dir, output_dir)

    write_text(output_dir / "00-change-summary.md", build_change_summary(data, baseline_dir, project_name, diagram_notes))
    write_text(output_dir / "01-changed-pages.md", build_changed_pages(data, baseline))
    write_text(output_dir / "02-changed-flows.md", flows_markdown)
    write_text(output_dir / "03-changed-rules.md", build_changed_rules(data, baseline))
    write_text(output_dir / "04-open-questions-delta.md", build_open_questions_delta(data, baseline))
    write_text(
        output_dir / "05-ai-delta-spec.md",
        build_ai_delta_spec(data, baseline_dir, project_name, baseline, diagram_entries),
    )

    (assets_dir / "change-scope.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (assets_dir / "baseline-snapshot.json").write_text(
        json.dumps(build_baseline_snapshot(data, baseline), ensure_ascii=False, indent=2) + "\n"
    )
    (assets_dir / "delta-summary.json").write_text(
        json.dumps(
            {
                "project_name": project_name,
                "baseline_ref": str(baseline_dir),
                "changed_counts": summarize_active_counts(data.get("change_scope", {})),
                "generated_diagrams": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "diagram_type": item["diagram_type"],
                        "source_path": item["source_path"],
                    }
                    for item in diagram_entries
                ],
                "diagram_notes": diagram_notes,
                "unchanged_artifacts": string_list(data.get("unchanged_artifacts")),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    print(f"[OK] Built delta pack at {output_dir}")
    print(f"[OK] Generated {len(diagram_entries)} Mermaid source file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
