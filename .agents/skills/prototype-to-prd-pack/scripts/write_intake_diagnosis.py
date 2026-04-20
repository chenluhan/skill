#!/usr/bin/env python3
"""Write a consistent intake diagnosis markdown file from validation and dependency reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    return data


def min_level(a: str, b: str) -> str:
    return a if LEVEL_ORDER[a] <= LEVEL_ORDER[b] else b


def heading(label: str) -> str:
    return label.replace("_", " ").replace("and", "&").title()


def bullet(items, fallback="None.") -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-report", required=True)
    parser.add_argument("--dependency-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    validation = load_json(Path(args.validation_report))
    dependency = load_json(Path(args.dependency_report))

    requested = validation.get("requested_level", "L4")
    evidence_level = validation.get("max_level_from_evidence", "L0")
    dependency_level = dependency.get("max_level_from_dependencies", "L2")
    current_level = "L0" if not validation.get("ok") else min_level(evidence_level, dependency_level)

    lines = [
        "# Intake Diagnosis",
        "",
        "## Platform",
        f"- {dependency.get('platform', 'unknown')}",
        "",
        "## Input Type",
        f"- {validation.get('input_type', 'mixed')}",
        "",
        "## Mode",
        f"- {validation.get('mode', 'full-raw')}",
        "",
        "## Readiness",
    ]

    for key, value in validation.get("readiness", {}).items():
        lines.append(f"- {heading(key)}: {value}")

    mermaid_source = "Ready" if LEVEL_ORDER.get(evidence_level, 0) >= LEVEL_ORDER["L2"] else ("Limited" if validation.get("ok") else "Blocked")
    lines.extend(
        [
            f"- Mermaid Source Generation: {mermaid_source}",
            f"- SVG Rendering: {dependency.get('mermaid_renderer', {}).get('status', 'blocked').title()}",
            f"- PDF Export: {dependency.get('pdf_export', {}).get('status', 'blocked').title()}",
            "",
            "## Missing Materials",
            "### Required",
            bullet(validation.get("missing_materials", {}).get("required", [])),
            "",
            "### Recommended",
            bullet(validation.get("missing_materials", {}).get("recommended", [])),
            "",
            "### Optional",
            bullet(validation.get("missing_materials", {}).get("optional", [])),
            "",
            "## Missing Dependencies",
            bullet(dependency.get("missing_dependencies", []) + dependency.get("limited_dependencies", []), fallback="No dependency blockers detected."),
            "",
            "## Dependency Help",
            f"- Bootstrap command: {dependency.get('bootstrap_command', 'Not available')}",
            f"- Reference guide: {dependency.get('reference_guide', 'Not available')}",
            f"- Direct install supported: {'yes' if dependency.get('direct_install_supported', False) else 'partial / guide-first'}",
            "",
            "## Delivery Level This Round",
            f"- Current achievable level: {current_level}",
            f"- Requested level: {requested}",
            "",
            "## To Reach Next Level",
            bullet(validation.get("suggested_next_actions", []) + dependency.get("next_actions", []), fallback="No additional actions suggested."),
        ]
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n")
    print(f"[OK] Wrote intake diagnosis to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
