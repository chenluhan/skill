#!/usr/bin/env python3
"""Normalize a raw prototype-to-PRD manifest into the canonical pack schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "1.0"

ALIASES = {
    "target_users": "users",
    "screens": "pages",
    "pages_or_artifacts": "pages",
    "swimlanes": "flows",
    "flow_evidence": "flows",
    "sequence_diagrams": "sequences",
    "business_rules": "rules",
    "business_rule_evidence": "rules",
    "pending_questions": "open_questions",
}

SOURCE_TYPE_MAP = {
    "fact": "explicit_fact",
    "explicit_fact": "explicit_fact",
    "explicit": "explicit_fact",
    "inference": "stable_inference",
    "stable_inference": "stable_inference",
    "assumption": "stable_inference",
    "question": "open_question",
    "open_question": "open_question",
}


def slugify(text: str | None, fallback: str) -> str:
    raw = (text or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or fallback


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def string_list(value) -> list[str]:
    items = []
    for item in ensure_list(value):
        if item is None:
            continue
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def first_present(mapping: dict, *keys, default=None):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def normalize_source_type(value: str | None, default: str = "explicit_fact") -> str:
    if not value:
        return default
    return SOURCE_TYPE_MAP.get(str(value).strip().lower(), default)


def normalize_sources(items) -> list[dict]:
    sources = []
    for index, item in enumerate(ensure_list(items), 1):
        if isinstance(item, str):
            sources.append(
                {
                    "id": f"source-{index}",
                    "type": "note",
                    "path": item,
                    "note": "",
                }
            )
            continue

        if not isinstance(item, dict):
            continue

        path = str(first_present(item, "path", "url", default="")).strip()
        note = str(item.get("note", "")).strip()
        source_id = str(item.get("id", "")).strip() or slugify(path or note, f"source-{index}")
        source_type = str(item.get("type", "file")).strip() or "file"

        sources.append(
            {
                "id": source_id,
                "type": source_type,
                "path": path,
                "note": note,
            }
        )
    return sources


def normalize_page(item: dict, index: int) -> dict:
    name = str(first_present(item, "name", "title", "artifact_name", "screen_name", default=f"Page {index}")).strip()
    page_id = str(item.get("id", "")).strip() or slugify(name, f"page-{index}")
    wireframe = item.get("wireframe", item.get("wireframe_blocks"))
    wireframe_value = wireframe if isinstance(wireframe, list) else string_list(wireframe)

    return {
        "id": page_id,
        "name": name,
        "purpose": str(item.get("purpose", "")).strip(),
        "facts": string_list(item.get("facts")),
        "inferences": string_list(item.get("inferences")),
        "entry_points": string_list(first_present(item, "entry_points", "entries")),
        "exit_points": string_list(first_present(item, "exit_points", "exits")),
        "sections": string_list(first_present(item, "sections", "visible_sections", "modules")),
        "user_actions": string_list(first_present(item, "user_actions", "actions")),
        "system_feedback": string_list(first_present(item, "system_feedback", "feedback")),
        "states": string_list(item.get("states")),
        "exceptions": string_list(item.get("exceptions")),
        "permissions": string_list(item.get("permissions")),
        "analytics": string_list(first_present(item, "analytics", "events")),
        "wireframe": wireframe_value,
        "source_refs": string_list(first_present(item, "source_refs", "sources")),
    }


def normalize_steps(items, participants) -> list[dict]:
    steps = []
    fallback_lane = participants[0] if participants else "System"
    for index, item in enumerate(ensure_list(items), 1):
        if isinstance(item, str):
            label = item.strip()
            lane = fallback_lane
            kind = "normal"
            source_type = "explicit_fact"
            source_ref = ""
        elif isinstance(item, dict):
            label = str(first_present(item, "label", "title", default=f"Step {index}")).strip()
            lane = str(first_present(item, "lane", "participant", "swimlane", default=fallback_lane)).strip() or fallback_lane
            kind = str(item.get("kind", "normal")).strip() or "normal"
            source_type = normalize_source_type(item.get("source_type"))
            source_ref = str(item.get("source_ref", "")).strip()
        else:
            continue

        step_id = str(item.get("id", "")).strip() if isinstance(item, dict) else ""
        step_id = step_id or slugify(label, f"step-{index}")
        steps.append(
            {
                "id": step_id,
                "lane": lane,
                "label": label,
                "kind": kind,
                "source_type": source_type,
                "source_ref": source_ref,
            }
        )
    return steps


def normalize_edges(items, steps) -> list[dict]:
    edges = []
    if not items and len(steps) > 1:
        for current, nxt in zip(steps, steps[1:]):
            edges.append({"from": current["id"], "to": nxt["id"], "label": ""})
        return edges

    for item in ensure_list(items):
        if isinstance(item, dict):
            start = str(first_present(item, "from", "source", default="")).strip()
            end = str(first_present(item, "to", "target", default="")).strip()
            label = str(item.get("label", "")).strip()
            if start and end:
                edges.append({"from": start, "to": end, "label": label})
    return edges


def normalize_flow(item: dict, index: int) -> dict:
    title = str(first_present(item, "title", "name", default=f"Flow {index}")).strip()
    flow_id = str(item.get("id", "")).strip() or slugify(title, f"flow-{index}")
    participants = string_list(first_present(item, "participants", "lanes"))
    steps = normalize_steps(item.get("steps"), participants)
    if not participants:
        deduped = []
        seen = set()
        for step in steps:
            lane = step["lane"]
            if lane not in seen:
                deduped.append(lane)
                seen.add(lane)
        participants = deduped

    return {
        "id": flow_id,
        "title": title,
        "purpose": str(item.get("purpose", "")).strip(),
        "participants": participants,
        "steps": steps,
        "edges": normalize_edges(item.get("edges"), steps),
        "notes": string_list(item.get("notes")),
        "known_gaps": string_list(first_present(item, "known_gaps", "gaps")),
        "mermaid": str(item.get("mermaid", "")).rstrip(),
    }


def normalize_messages(items, participants) -> list[dict]:
    messages = []
    pair = participants[:2] if len(participants) >= 2 else ["System", "User"]
    for index, item in enumerate(ensure_list(items), 1):
        if isinstance(item, str):
            messages.append(
                {
                    "from": pair[0],
                    "to": pair[1],
                    "label": item.strip(),
                    "type": "request",
                }
            )
            continue

        if not isinstance(item, dict):
            continue

        label = str(first_present(item, "label", "message", default=f"Message {index}")).strip()
        source = str(first_present(item, "from", "source", default=pair[0])).strip() or pair[0]
        target = str(first_present(item, "to", "target", default=pair[1])).strip() or pair[1]
        msg_type = str(item.get("type", "request")).strip() or "request"
        messages.append({"from": source, "to": target, "label": label, "type": msg_type})
    return messages


def normalize_sequence(item: dict, index: int) -> dict:
    title = str(first_present(item, "title", "name", default=f"Sequence {index}")).strip()
    sequence_id = str(item.get("id", "")).strip() or slugify(title, f"sequence-{index}")
    participants = string_list(item.get("participants"))
    messages = normalize_messages(item.get("messages"), participants)

    if not participants:
        deduped = []
        seen = set()
        for message in messages:
            for actor in (message["from"], message["to"]):
                if actor not in seen:
                    deduped.append(actor)
                    seen.add(actor)
        participants = deduped

    return {
        "id": sequence_id,
        "title": title,
        "purpose": str(item.get("purpose", "")).strip(),
        "participants": participants,
        "messages": messages,
        "known_gaps": string_list(first_present(item, "known_gaps", "gaps")),
        "mermaid": str(item.get("mermaid", "")).rstrip(),
    }


def normalize_rule(item: dict, index: int) -> dict:
    if isinstance(item, str):
        title = item.strip()
        raw = {}
    else:
        raw = item if isinstance(item, dict) else {}
        title = str(first_present(raw, "title", "name", default=f"Rule {index}")).strip()

    rule_id = str(raw.get("id", "")).strip() if raw else ""
    rule_id = rule_id or slugify(title, f"rule-{index}")

    return {
        "id": rule_id,
        "title": title,
        "trigger": str(raw.get("trigger", "")).strip(),
        "condition": str(raw.get("condition", "")).strip(),
        "system_behavior": str(first_present(raw, "system_behavior", "behavior", default="")).strip(),
        "user_feedback": str(first_present(raw, "user_feedback", "feedback", default="")).strip(),
        "fallback": str(raw.get("fallback", "")).strip(),
        "source_type": normalize_source_type(raw.get("source_type")),
        "source_refs": string_list(first_present(raw, "source_refs", "sources")),
    }


def normalize_open_question(item, index: int) -> dict:
    if isinstance(item, str):
        question = item.strip()
        raw = {}
        title = question
    else:
        raw = item if isinstance(item, dict) else {}
        question = str(raw.get("question", "")).strip() or str(first_present(raw, "title", "name", default="")).strip()
        title = str(first_present(raw, "title", "name", default=question or f"Open Question {index}")).strip()

    question_id = str(raw.get("id", "")).strip() if raw else ""
    question_id = question_id or slugify(title, f"question-{index}")

    return {
        "id": question_id,
        "title": title,
        "related_to": str(raw.get("related_to", "")).strip(),
        "question": question,
        "impact": str(raw.get("impact", "")).strip(),
        "owner": str(raw.get("owner", "PM")).strip() or "PM",
        "default_assumption": str(raw.get("default_assumption", "")).strip(),
    }


def normalize_glossary(items) -> list[dict]:
    glossary = []
    for item in ensure_list(items):
        if isinstance(item, dict):
            term = str(item.get("term", "")).strip()
            definition = str(item.get("definition", "")).strip()
            if term:
                glossary.append({"term": term, "definition": definition})
    return glossary


def remap_aliases(data: dict) -> dict:
    remapped = dict(data)
    for alias, canonical in ALIASES.items():
        if alias in remapped and canonical not in remapped:
            remapped[canonical] = remapped[alias]
    return remapped


def normalize_manifest(data: dict) -> dict:
    data = remap_aliases(data)

    project_name = str(first_present(data, "project_name", "name", default="Untitled Project")).strip()
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "mode": str(data.get("mode", "full")).strip() or "full",
        "input_type": str(data.get("input_type", "")).strip(),
        "requested_level": str(data.get("requested_level", "L4")).strip() or "L4",
        "baseline_ref": str(data.get("baseline_ref", "")).strip(),
        "project_name": project_name,
        "product_summary": str(data.get("product_summary", "")).strip(),
        "goal": str(data.get("goal", "")).strip(),
        "users": string_list(data.get("users")),
        "assumptions": string_list(data.get("assumptions")),
        "non_goals": string_list(data.get("non_goals")),
        "metrics": string_list(data.get("metrics")),
        "sources": normalize_sources(data.get("sources")),
        "pages": [normalize_page(item, index) for index, item in enumerate(ensure_list(data.get("pages")), 1)],
        "flows": [normalize_flow(item, index) for index, item in enumerate(ensure_list(data.get("flows")), 1)],
        "sequences": [normalize_sequence(item, index) for index, item in enumerate(ensure_list(data.get("sequences")), 1)],
        "rules": [normalize_rule(item, index) for index, item in enumerate(ensure_list(data.get("rules")), 1)],
        "open_questions": [
            normalize_open_question(item, index)
            for index, item in enumerate(ensure_list(data.get("open_questions")), 1)
        ],
        "glossary": normalize_glossary(data.get("glossary")),
    }

    normalized["summary"] = {
        "page_count": len(normalized["pages"]),
        "flow_count": len(normalized["flows"]),
        "sequence_count": len(normalized["sequences"]),
        "rule_count": len(normalized["rules"]),
        "open_question_count": len(normalized["open_questions"]),
    }
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the raw manifest JSON file.")
    parser.add_argument("--output", required=True, help="Path to write the normalized JSON file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        raw_data = json.loads(input_path.read_text())
    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON in {input_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw_data, dict):
        print("[ERROR] Input manifest must be a JSON object.", file=sys.stderr)
        return 1

    normalized = normalize_manifest(raw_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")

    summary = normalized["summary"]
    print(
        "[OK] Normalized manifest "
        f"for '{normalized['project_name']}' "
        f"({summary['page_count']} pages, {summary['flow_count']} flows, "
        f"{summary['sequence_count']} sequences, {summary['rule_count']} rules, "
        f"{summary['open_question_count']} open questions)."
    )
    print(f"[OK] Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
