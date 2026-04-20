#!/usr/bin/env python3
"""Write delivery status JSON for a generated pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}

FULL_REQUIRED_DOCS = [
    "00-overview.md",
    "01-prd.md",
    "02-pages.md",
    "03-flows.md",
    "04-ai-spec.md",
    "05-open-questions.md",
]

DELTA_REQUIRED_DOCS = [
    "00-change-summary.md",
    "01-changed-pages.md",
    "02-changed-flows.md",
    "03-changed-rules.md",
    "04-open-questions-delta.md",
    "05-ai-delta-spec.md",
]


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def list_relative_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def achieved_level(target_dir: Path, mode: str) -> tuple[str, list[str]]:
    missing = []
    docs = DELTA_REQUIRED_DOCS if mode == "delta" else FULL_REQUIRED_DOCS
    for doc in docs:
        if not (target_dir / doc).exists():
            missing.append(doc)

    asset_files = list((target_dir / "assets").glob("*.json")) if (target_dir / "assets").exists() else []
    mmd_files = list((target_dir / "diagrams").glob("*.mmd")) if (target_dir / "diagrams").exists() else []
    rendered_dir = target_dir / "diagrams" / "rendered"
    rendered_files = []
    if rendered_dir.exists():
        rendered_files.extend(rendered_dir.glob("*.svg"))
        rendered_files.extend(rendered_dir.glob("*.png"))
    pdf_path = target_dir / "export" / "prd-pack.pdf"

    if missing or not asset_files:
        return "L0", missing + (["assets/*.json"] if not asset_files else [])
    if not mmd_files:
        return "L1", []
    if not rendered_files or len(rendered_files) < len(mmd_files):
        return "L2", ([] if rendered_files else ["diagrams/rendered/*.(svg|png)"])
    if not pdf_path.exists():
        return "L3", ["export/prd-pack.pdf"]
    return "L4", []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", required=True, help="Generated pack directory or delta output directory.")
    parser.add_argument("--mode", choices=["full", "delta"], default="full")
    parser.add_argument("--requested-level", default="L4")
    parser.add_argument("--validation-report")
    parser.add_argument("--dependency-report")
    parser.add_argument("--input-type", default="mixed")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    validation = load_json(args.validation_report)
    dependency = load_json(args.dependency_report)
    target_dir = Path(args.target_dir)

    if validation and not validation.get("ok", True):
        achieved = "L0"
        missing_outputs = []
        blocking_issues = list(validation.get("blocking_issues", []))
    else:
        achieved, missing_outputs = achieved_level(target_dir, args.mode)
        blocking_issues = []

    if LEVEL_ORDER[achieved] < LEVEL_ORDER.get(args.requested_level, 4):
        blocking_issues.extend(missing_outputs)
    blocking_issues.extend(dependency.get("missing_dependencies", []))
    requested_level_met = LEVEL_ORDER[achieved] >= LEVEL_ORDER.get(args.requested_level, 4)
    if achieved == "L0":
        status = "blocked"
    elif achieved == "L4":
        status = "complete"
    else:
        status = "partial"

    generated_outputs = list_relative_files(target_dir)
    next_actions = list(validation.get("suggested_next_actions", []))
    next_actions.extend(dependency.get("next_actions", []))
    if "diagrams/rendered/*.(svg|png)" in missing_outputs:
        next_actions.append("Run Mermaid rendering again after installing a stable renderer.")
    if "export/prd-pack.pdf" in missing_outputs:
        next_actions.append("Install pandoc and a supported PDF engine, then rerun PDF export.")

    report = {
        "status": status,
        "achieved_level": achieved,
        "requested_level": args.requested_level,
        "requested_level_met": requested_level_met,
        "mode": args.mode,
        "input_type": validation.get("input_type", args.input_type),
        "blocking_issues": blocking_issues,
        "missing_materials": validation.get("missing_materials", {}),
        "missing_dependencies": dependency.get("missing_dependencies", []),
        "generated_outputs": generated_outputs,
        "next_actions": next_actions,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"[OK] Wrote delivery status to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
