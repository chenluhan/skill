#!/usr/bin/env python3
"""Validate and enrich interview-pack content with resume anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SECTION_LABELS = {
    "profile": "个人简介",
    "experience": "工作经历",
    "projects": "项目经历",
    "education": "教育经历",
    "skills": "技能",
    "awards": "奖项",
    "languages": "语言能力",
    "other": "其他",
}

CLASS_LABELS = {"真实性核验题", "能力深挖题", "淘汰判断题"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: dict[str, Any], path: Path | None, pretty: bool) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    if path is None:
        print(payload)
        return
    path.write_text(payload + "\n", encoding="utf-8")


def infer_candidate_name(parsed_resume: dict[str, Any]) -> str:
    blocks = parsed_resume.get("blocks", [])
    for block in blocks:
        if block.get("kind") == "section_heading":
            break
        text = str(block.get("text", "")).strip()
        if text and len(text) <= 16:
            return text
    raw_lines = [line.strip() for line in str(parsed_resume.get("raw_text", "")).splitlines() if line.strip()]
    return raw_lines[0] if raw_lines else "候选人"


def build_source_groups(parsed_resume: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = parsed_resume.get("blocks", [])
    anchors = parsed_resume.get("anchors", [])
    anchor_map_by_block: dict[str, list[str]] = {}
    for anchor in anchors:
        anchor_map_by_block.setdefault(anchor["source_block_id"], []).append(anchor["id"])

    groups: list[dict[str, Any]] = []
    current_group: dict[str, Any] | None = None

    def flush_current() -> None:
        nonlocal current_group
        if current_group and current_group["block_ids"]:
            groups.append(current_group)
        current_group = None

    for block in blocks:
        if block["kind"] == "section_heading":
            flush_current()
            continue

        if block["kind"] == "project_title":
            flush_current()
            current_group = {
                "id": f"g{len(groups) + 1}",
                "title": block["text"],
                "section_name": block["section_name"],
                "section_label": block["section_label"],
                "block_ids": [block["id"]],
                "anchor_ids": list(anchor_map_by_block.get(block["id"], [])),
            }
            continue

        if current_group is None:
            current_group = {
                "id": f"g{len(groups) + 1}",
                "title": block.get("group_title") or SECTION_LABELS.get(block["section_name"], SECTION_LABELS["other"]),
                "section_name": block["section_name"],
                "section_label": block["section_label"],
                "block_ids": [],
                "anchor_ids": [],
            }

        current_group["block_ids"].append(block["id"])
        current_group["anchor_ids"].extend(anchor_map_by_block.get(block["id"], []))

    flush_current()

    block_index = {block["id"]: block for block in blocks}
    for group in groups:
        seen: set[str] = set()
        deduped_anchor_ids = []
        for anchor_id in group["anchor_ids"]:
            if anchor_id not in seen:
                seen.add(anchor_id)
                deduped_anchor_ids.append(anchor_id)
        group["anchor_ids"] = deduped_anchor_ids
        excerpts = [block_index[block_id]["text"] for block_id in group["block_ids"][:3] if block_id in block_index]
        group["excerpt"] = " / ".join(excerpts)

    preferred = [group for group in groups if group["section_name"] in {"projects", "experience"}]
    return preferred or groups


def infer_card_class(item: dict[str, Any], anchor_index: dict[str, dict[str, Any]]) -> str:
    label = item.get("class")
    if label in CLASS_LABELS:
        return str(label)

    anchor_ids = item.get("source_anchor_ids", [])
    types = {anchor_index[anchor_id]["type"] for anchor_id in anchor_ids if anchor_id in anchor_index}
    if "risk" in types:
        return "淘汰判断题"
    if "ownership" in types:
        return "真实性核验题"
    return "能力深挖题"


def normalize_anchor_ids(
    raw_anchor_ids: list[str],
    fallback_anchor_ids: list[str],
    anchor_index: dict[str, dict[str, Any]],
    field_name: str,
) -> list[str]:
    candidate_ids = raw_anchor_ids or fallback_anchor_ids
    valid = [anchor_id for anchor_id in candidate_ids if anchor_id in anchor_index]
    if not valid:
        raise ValueError(f"{field_name} must include at least one valid source anchor id.")
    return valid


def enrich_card(
    card: dict[str, Any],
    fallback_anchor_ids: list[str],
    anchor_index: dict[str, dict[str, Any]],
    field_name: str,
) -> dict[str, Any]:
    source_anchor_ids = normalize_anchor_ids(card.get("source_anchor_ids", []), fallback_anchor_ids, anchor_index, field_name)
    source_quotes = [anchor_index[anchor_id]["source_text"] for anchor_id in source_anchor_ids]
    source_block_ids = list(dict.fromkeys(anchor_index[anchor_id]["source_block_id"] for anchor_id in source_anchor_ids))

    enriched = dict(card)
    enriched["class"] = infer_card_class(card, anchor_index)
    enriched["source_anchor_ids"] = source_anchor_ids
    enriched["source_quotes"] = source_quotes
    enriched["source_block_ids"] = source_block_ids
    return enriched


def seed_interview_pack(parsed_resume: dict[str, Any]) -> dict[str, Any]:
    source_groups = build_source_groups(parsed_resume)
    candidate_name = infer_candidate_name(parsed_resume)
    parse_note = {
        "strategy": parsed_resume.get("parse_strategy", "text"),
        "confidence": parsed_resume.get("confidence", "low"),
        "warnings": parsed_resume.get("parse_warnings", []),
    }

    comparison_sections = []
    for group in source_groups:
        comparison_sections.append(
            {
                "id": group["id"],
                "source_group_id": group["id"],
                "title": group["title"],
                "judgement": "",
                "source_anchor_ids": group["anchor_ids"][:4],
                "questions": [],
                "annotations": [],
            }
        )

    return {
        "candidate": {
            "name": candidate_name,
            "inferred_level": "",
            "target_domain": "",
        },
        "summary": {
            "headline": "",
            "overall_assessment": "",
            "top_strengths": [],
            "top_risks": [],
        },
        "parse": parse_note,
        "source_groups": source_groups,
        "comparison_sections": comparison_sections,
        "screening_script": {
            "opening": [],
            "must_ask": [],
            "optional_swaps": [],
            "fast_reject_triggers": [],
        },
        "final_recommendation": {
            "decision": "",
            "reason": "",
            "next_round_focus": [],
        },
        "resume_source": {
            "blocks": parsed_resume.get("blocks", []),
            "anchors": parsed_resume.get("anchors", []),
            "sections_guess": parsed_resume.get("sections_guess", []),
        },
    }


def build_interview_pack(parsed_resume: dict[str, Any], authored_content: dict[str, Any] | None) -> dict[str, Any]:
    seed = seed_interview_pack(parsed_resume)
    if authored_content is None:
        return seed

    source_groups = {group["id"]: group for group in seed["source_groups"]}
    anchor_index = {anchor["id"]: anchor for anchor in parsed_resume.get("anchors", [])}

    comparison_sections = []
    for index, section in enumerate(authored_content.get("comparison_sections", []), start=1):
        source_group_id = section.get("source_group_id")
        source_group = source_groups.get(source_group_id) if source_group_id else None

        fallback_anchor_ids = []
        fallback_block_ids = []
        title = section.get("title") or ""

        if source_group is not None:
            fallback_anchor_ids = list(source_group.get("anchor_ids", []))
            fallback_block_ids = list(source_group.get("block_ids", []))
            if not title:
                title = source_group["title"]

        section_anchor_ids = normalize_anchor_ids(section.get("source_anchor_ids", []), fallback_anchor_ids, anchor_index, f"comparison_sections[{index}]")
        section_block_ids = list(dict.fromkeys(section.get("source_block_ids", []) or fallback_block_ids or [anchor_index[anchor_id]["source_block_id"] for anchor_id in section_anchor_ids]))

        questions = [
            enrich_card(question, section_anchor_ids, anchor_index, f"comparison_sections[{index}].questions[{question_index}]")
            for question_index, question in enumerate(section.get("questions", []), start=1)
        ]
        annotations = [
            enrich_card(annotation, section_anchor_ids, anchor_index, f"comparison_sections[{index}].annotations[{annotation_index}]")
            for annotation_index, annotation in enumerate(section.get("annotations", []), start=1)
        ]

        comparison_sections.append(
            {
                "id": section.get("id") or f"section-{index}",
                "source_group_id": source_group_id,
                "title": title or f"对照区块 {index}",
                "judgement": section.get("judgement", ""),
                "section_name": source_group["section_name"] if source_group else "",
                "section_label": source_group["section_label"] if source_group else "",
                "source_anchor_ids": section_anchor_ids,
                "source_block_ids": section_block_ids,
                "source_quotes": [anchor_index[anchor_id]["source_text"] for anchor_id in section_anchor_ids],
                "questions": questions,
                "annotations": annotations,
            }
        )

    if not comparison_sections:
        comparison_sections = seed["comparison_sections"]

    candidate = dict(seed["candidate"])
    candidate.update(authored_content.get("candidate", {}))

    summary = dict(seed["summary"])
    summary.update(authored_content.get("summary", {}))

    screening_script = dict(seed["screening_script"])
    screening_script.update(authored_content.get("screening_script", {}))

    final_recommendation = dict(seed["final_recommendation"])
    final_recommendation.update(authored_content.get("final_recommendation", {}))

    return {
        "candidate": candidate,
        "summary": summary,
        "parse": seed["parse"],
        "source_groups": seed["source_groups"],
        "comparison_sections": comparison_sections,
        "screening_script": screening_script,
        "final_recommendation": final_recommendation,
        "resume_source": seed["resume_source"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a render-ready interview pack JSON from parsed resume output.")
    parser.add_argument("--resume", required=True, help="Path to parsed resume JSON.")
    parser.add_argument("--content", help="Path to authored interview content JSON.")
    parser.add_argument("--output", help="Output path for the render-ready interview pack JSON.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    parsed_resume = load_json(Path(args.resume).expanduser())
    authored_content = load_json(Path(args.content).expanduser()) if args.content else None
    pack = build_interview_pack(parsed_resume, authored_content)
    dump_json(pack, Path(args.output).expanduser() if args.output else None, args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
