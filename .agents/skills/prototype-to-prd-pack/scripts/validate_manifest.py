#!/usr/bin/env python3
"""Validate full or delta manifest files used by prototype-to-prd-pack."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


VALID_INPUT_TYPES = {"figma", "ai_studio", "html", "screenshots", "mixed"}
VALID_LEVELS = {"L0", "L1", "L2", "L3", "L4"}
VALID_ACTIONS = {"add", "update", "remove", "no_change", "added", "resolved", "unchanged"}


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a JSON object.")
    return data


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def non_empty_list(value) -> bool:
    return any(str(item).strip() for item in ensure_list(value))


def string_list(value) -> list[str]:
    return [str(item).strip() for item in ensure_list(value) if str(item).strip()]


def normalize_input_type(data: dict) -> str:
    raw = str(data.get("input_type", "")).strip().lower()
    aliases = {
        "figma": "figma",
        "ai studio": "ai_studio",
        "aistudio": "ai_studio",
        "ai_studio": "ai_studio",
        "html": "html",
        "frontend": "html",
        "code": "html",
        "screenshot": "screenshots",
        "screenshots": "screenshots",
        "image": "screenshots",
        "images": "screenshots",
        "mixed": "mixed",
    }
    if raw in aliases:
        return aliases[raw]

    sources = ensure_list(data.get("sources") or data.get("change_sources"))
    if sources:
        paths = []
        types = []
        for item in sources:
            if isinstance(item, dict):
                paths.append(str(item.get("path", "")))
                types.append(str(item.get("type", "")).lower())
            else:
                paths.append(str(item))
        joined = " ".join(paths).lower()
        if "figma.com" in joined:
            return "figma"
        if "aistudio" in joined or "ai studio" in joined:
            return "ai_studio"
        if any(path.endswith(".html") for path in paths) or any(t in {"html", "code"} for t in types):
            return "html"
        if types and all(t in {"image", "screenshot"} for t in types if t):
            return "screenshots"
        return "mixed"
    return "mixed"


def has_pages(data: dict) -> bool:
    return non_empty_list(data.get("screens")) or non_empty_list(data.get("pages")) or non_empty_list(data.get("pages_or_artifacts"))


def has_flow_evidence(data: dict) -> bool:
    return (
        non_empty_list(data.get("swimlanes"))
        or non_empty_list(data.get("flows"))
        or non_empty_list(data.get("sequence_diagrams"))
        or non_empty_list(data.get("sequences"))
        or non_empty_list(data.get("flow_evidence"))
    )


def has_state_evidence(data: dict) -> bool:
    if non_empty_list(data.get("state_evidence")):
        return True
    for page in ensure_list(data.get("screens")) + ensure_list(data.get("pages")) + ensure_list(data.get("pages_or_artifacts")):
        if isinstance(page, dict) and (non_empty_list(page.get("states")) or non_empty_list(page.get("exceptions"))):
            return True
    return False


def has_rule_evidence(data: dict) -> bool:
    return non_empty_list(data.get("business_rules")) or non_empty_list(data.get("rules")) or non_empty_list(data.get("business_rule_evidence"))


def readiness_label(present: bool, partial: bool = False) -> str:
    if present:
        return "High"
    if partial:
        return "Medium"
    return "Low"


def source_guidance(input_type: str) -> dict[str, list[tuple[str, bool]]]:
    return {
        "figma": {
            "required": [
                ("Figma file or page link", True),
                ("Key frames or screen names", True),
            ],
            "recommended": [
                ("Prototype connections or page order", False),
                ("Loading, empty, and error frames", False),
            ],
            "optional": [("Notes on business intent", False)],
        },
        "ai_studio": {
            "required": [
                ("AI Studio prototype link or captures", True),
                ("Page or module summary", True),
            ],
            "recommended": [
                ("Page transition mapping", False),
                ("Field or component notes", False),
            ],
            "optional": [("State screenshots", False)],
        },
        "html": {
            "required": [
                ("Runnable page or source files", True),
                ("Route or page inventory", True),
            ],
            "recommended": [
                ("Interaction logic or event handlers", False),
                ("Error-state or validation logic", False),
            ],
            "optional": [("Analytics implementation notes", False)],
        },
        "screenshots": {
            "required": [
                ("Key screen captures", True),
                ("Screen purpose mapping", True),
            ],
            "recommended": [
                ("Screen order or transition mapping", False),
                ("Loading, empty, processing, or error screenshots", False),
            ],
            "optional": [("Supporting user notes", False)],
        },
        "mixed": {
            "required": [
                ("Main source of truth", True),
                ("At least one structured page or artifact list", True),
            ],
            "recommended": [
                ("Source priority or version order", False),
                ("Conflict notes between artifacts", False),
            ],
            "optional": [("Tool-specific annotations", False)],
        },
    }[input_type]


def guidance_missing(data: dict, input_type: str) -> dict[str, list[str]]:
    pages = has_pages(data)
    flows = has_flow_evidence(data)
    states = has_state_evidence(data)
    notes = non_empty_list(data.get("user_notes"))
    sources = non_empty_list(data.get("sources")) or non_empty_list(data.get("change_sources"))
    mapping = {
        "Figma file or page link": sources,
        "Key frames or screen names": pages,
        "Prototype connections or page order": flows,
        "Loading, empty, and error frames": states,
        "Notes on business intent": notes,
        "AI Studio prototype link or captures": sources,
        "Page or module summary": pages,
        "Page transition mapping": flows,
        "Field or component notes": notes,
        "State screenshots": states,
        "Runnable page or source files": sources,
        "Route or page inventory": pages,
        "Interaction logic or event handlers": flows,
        "Error-state or validation logic": states,
        "Analytics implementation notes": non_empty_list(data.get("business_rule_evidence")) or non_empty_list(data.get("metrics")),
        "Key screen captures": sources,
        "Screen purpose mapping": pages,
        "Screen order or transition mapping": flows,
        "Loading, empty, processing, or error screenshots": states,
        "Supporting user notes": notes,
        "Main source of truth": sources,
        "At least one structured page or artifact list": pages,
        "Source priority or version order": non_empty_list(data.get("source_priority")) or notes,
        "Conflict notes between artifacts": notes,
        "Tool-specific annotations": notes,
    }

    missing = {"required": [], "recommended": [], "optional": []}
    for group, items in source_guidance(input_type).items():
        for label, _ in items:
            if not mapping.get(label, False):
                missing[group].append(label)
    return missing


def validate_full_raw(data: dict) -> dict:
    input_type = normalize_input_type(data)
    requested_level = str(data.get("requested_level", "L4")).strip() or "L4"
    blocking = []
    warnings = []

    if not str(data.get("project_name", "")).strip():
        blocking.append("`project_name` is required.")
    if not non_empty_list(data.get("sources")):
        blocking.append("At least one entry in `sources` is required.")
    if not has_pages(data):
        blocking.append("At least one page or artifact must be identified in `pages_or_artifacts`, `screens`, or `pages`.")
    if requested_level not in VALID_LEVELS:
        blocking.append("`requested_level` must be one of L0-L4.")
    if input_type not in VALID_INPUT_TYPES:
        blocking.append("`input_type` must resolve to figma, ai_studio, html, screenshots, or mixed.")

    if not has_flow_evidence(data):
        warnings.append("No structured flow evidence found. Output may stop at L1 unless flow objects are added.")
    if not has_state_evidence(data):
        warnings.append("State and exception evidence is weak. Missing states should move into open questions.")
    if not has_rule_evidence(data):
        warnings.append("Business rule evidence is weak. Rules may remain as inferences or open questions.")

    missing = guidance_missing(data, input_type)
    readiness = {
        "page_reconstruction": readiness_label(has_pages(data)),
        "flow_reconstruction": readiness_label(has_flow_evidence(data), partial=has_pages(data)),
        "state_and_exception_coverage": readiness_label(has_state_evidence(data), partial=has_pages(data)),
    }
    max_level = "L0" if blocking else ("L2" if has_flow_evidence(data) else "L1")
    next_actions = []
    if missing["required"]:
        next_actions.append("补齐 required materials before generation.")
    if missing["recommended"]:
        next_actions.append("补齐 recommended materials to improve flow and state coverage.")

    return {
        "ok": not blocking,
        "mode": "full-raw",
        "input_type": input_type,
        "requested_level": requested_level,
        "blocking_issues": blocking,
        "warnings": warnings,
        "missing_materials": missing,
        "readiness": readiness,
        "max_level_from_evidence": max_level,
        "suggested_next_actions": next_actions,
    }


def validate_full_normalized(data: dict) -> dict:
    blocking = []
    warnings = []
    if not str(data.get("project_name", "")).strip():
        blocking.append("Normalized pack must include `project_name`.")
    pages = ensure_list(data.get("pages"))
    flows = ensure_list(data.get("flows"))
    sequences = ensure_list(data.get("sequences"))
    if not pages:
        blocking.append("Normalized pack must include at least one page.")
    for index, page in enumerate(pages, 1):
        if not isinstance(page, dict):
            blocking.append(f"Page {index} is not a JSON object.")
            continue
        if not str(page.get("id", "")).strip():
            blocking.append(f"Page {index} is missing `id`.")
        if not str(page.get("name", "")).strip():
            blocking.append(f"Page {index} is missing `name`.")
        if not non_empty_list(page.get("states")):
            warnings.append(f"Page `{page.get('id', index)}` has no explicit states.")
        if not non_empty_list(page.get("exceptions")):
            warnings.append(f"Page `{page.get('id', index)}` has no explicit exceptions.")
    for index, flow in enumerate(flows, 1):
        if not isinstance(flow, dict) or not str(flow.get("title", "")).strip():
            blocking.append(f"Flow {index} must be an object with `title`.")
        elif not ensure_list(flow.get("steps")) and not str(flow.get("mermaid", "")).strip():
            warnings.append(f"Flow `{flow.get('id', index)}` has no steps or Mermaid source.")
    for index, sequence in enumerate(sequences, 1):
        if not isinstance(sequence, dict) or not str(sequence.get("title", "")).strip():
            blocking.append(f"Sequence {index} must be an object with `title`.")
        elif not ensure_list(sequence.get("messages")) and not str(sequence.get("mermaid", "")).strip():
            warnings.append(f"Sequence `{sequence.get('id', index)}` has no messages or Mermaid source.")

    return {
        "ok": not blocking,
        "mode": "full-normalized",
        "input_type": str(data.get("input_type", "mixed")),
        "requested_level": str(data.get("requested_level", "L4")),
        "blocking_issues": blocking,
        "warnings": warnings,
        "missing_materials": {"required": [], "recommended": [], "optional": []},
        "readiness": {
            "page_reconstruction": readiness_label(bool(pages)),
            "flow_reconstruction": readiness_label(bool(flows or sequences), partial=bool(pages)),
            "state_and_exception_coverage": readiness_label(any(non_empty_list(page.get("states")) for page in pages), partial=bool(pages)),
        },
        "max_level_from_evidence": "L0" if blocking else ("L2" if flows or sequences else "L1"),
        "suggested_next_actions": [],
    }


def validate_delta_change(data: dict) -> dict:
    input_type = normalize_input_type(data)
    blocking = []
    warnings = []
    if not str(data.get("baseline_ref", "")).strip():
        blocking.append("Delta mode requires `baseline_ref`.")
    if not (non_empty_list(data.get("change_sources")) or non_empty_list(data.get("claimed_changes")) or str(data.get("change_summary", "")).strip()):
        blocking.append("Delta mode requires `change_sources`, `claimed_changes`, or `change_summary`.")
    if not str(data.get("project_name", "")).strip():
        blocking.append("`project_name` is required.")

    if not non_empty_list(data.get("suspected_impacts")):
        warnings.append("No `suspected_impacts` provided. Impact scope may remain broad and imprecise.")

    missing = guidance_missing(
        {
            "sources": data.get("change_sources"),
            "pages_or_artifacts": data.get("claimed_changes"),
            "user_notes": data.get("user_notes"),
            "state_evidence": data.get("suspected_impacts"),
        },
        input_type,
    )
    return {
        "ok": not blocking,
        "mode": "delta-change",
        "input_type": input_type,
        "requested_level": str(data.get("requested_level", "L4")),
        "blocking_issues": blocking,
        "warnings": warnings,
        "missing_materials": missing,
        "readiness": {
            "baseline_coverage": readiness_label(bool(str(data.get("baseline_ref", "")).strip())),
            "change_evidence": readiness_label(
                non_empty_list(data.get("change_sources")) or non_empty_list(data.get("claimed_changes")),
                partial=bool(str(data.get("change_summary", "")).strip()),
            ),
            "impact_scope_clarity": readiness_label(non_empty_list(data.get("suspected_impacts")), partial=non_empty_list(data.get("claimed_changes"))),
        },
        "max_level_from_evidence": "L0" if blocking else "L1",
        "suggested_next_actions": [
            "Write `02-impact-scope.json` before generating delta documents."
        ] if not blocking else [],
    }


def validate_delta_impact(data: dict) -> dict:
    blocking = []
    change_scope = data.get("change_scope")
    if not str(data.get("baseline_ref", "")).strip():
        blocking.append("Impact scope requires `baseline_ref`.")
    if not isinstance(change_scope, dict):
        blocking.append("Impact scope requires a `change_scope` object.")
        change_scope = {}

    total_changes = 0
    warnings = []
    flow_diagram_ready = False
    for key in ("pages", "flows", "rules", "open_questions"):
        entries = ensure_list(change_scope.get(key))
        total_changes += len(entries)
        for index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict):
                blocking.append(f"`change_scope.{key}[{index}]` must be an object.")
                continue
            if not str(entry.get("id", "")).strip():
                blocking.append(f"`change_scope.{key}[{index}]` is missing `id`.")
            if str(entry.get("action", "")).strip() not in VALID_ACTIONS:
                blocking.append(f"`change_scope.{key}[{index}]` has invalid `action`.")
            if not str(entry.get("reason", "")).strip():
                warnings.append(f"`change_scope.{key}[{index}]` is missing `reason`.")
            if key == "flows":
                action = str(entry.get("action", "")).strip()
                has_structure = (
                    bool(str(entry.get("mermaid", "")).strip())
                    or non_empty_list(entry.get("steps"))
                    or non_empty_list(entry.get("messages"))
                )
                if action in {"add", "added", "update"} and not has_structure:
                    warnings.append(
                        f"`change_scope.flows[{index}]` lacks `mermaid`, `steps`, or `messages`; delta output may stop at L1."
                    )
                if has_structure:
                    flow_diagram_ready = True
    if total_changes == 0 and not bool(data.get("merge_recommended")):
        blocking.append("Impact scope must identify at least one changed artifact or set `merge_recommended`.")

    return {
        "ok": not blocking,
        "mode": "delta-impact",
        "input_type": "mixed",
        "requested_level": "L4",
        "blocking_issues": blocking,
        "warnings": warnings,
        "missing_materials": {"required": [], "recommended": [], "optional": []},
        "readiness": {
            "baseline_coverage": readiness_label(bool(str(data.get("baseline_ref", "")).strip())),
            "impact_scope_clarity": readiness_label(total_changes > 0),
            "diagram_source_readiness": readiness_label(flow_diagram_ready, partial=bool(ensure_list(change_scope.get("flows")))),
        },
        "max_level_from_evidence": "L0" if blocking else ("L2" if flow_diagram_ready else "L1"),
        "suggested_next_actions": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["full-raw", "full-normalized", "delta-change", "delta-impact"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    try:
        data = load_json(Path(args.input))
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    validators = {
        "full-raw": validate_full_raw,
        "full-normalized": validate_full_normalized,
        "delta-change": validate_delta_change,
        "delta-impact": validate_delta_impact,
    }
    report = validators[args.mode](data)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
