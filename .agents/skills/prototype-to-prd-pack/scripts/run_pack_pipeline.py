#!/usr/bin/env python3
"""Run the end-to-end prototype-to-prd-pack pipeline in full or delta mode."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def slugify(text: str | None, fallback: str) -> str:
    raw = (text or "").strip().lower()
    slug = "".join(char if char.isalnum() else "-" for char in raw)
    slug = "-".join(filter(None, slug.split("-")))
    return slug or fallback


def run_command(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
    return result


def maybe_bootstrap_dependencies(should_bootstrap: bool) -> None:
    if not should_bootstrap:
        return
    if platform.system().lower() == "windows":
        run_command(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "bootstrap_dependencies.ps1"),
            ]
        )
        return
    run_command(["bash", str(ROOT / "bootstrap_dependencies.sh")])


def prepare_run_dir(output_root: Path, run_name: str | None, input_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_name = f"{timestamp}-{slugify(input_path.stem, 'run')}"
    run_dir = output_root / (run_name or default_name)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def copy_input(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def choose_requested_level(args_level: str | None, data: dict, default_level: str) -> str:
    if args_level:
        return args_level
    return str(data.get("requested_level", default_level)).strip() or default_level


def find_full_pack_dir(output_root: Path) -> Path:
    packs = [path for path in sorted(output_root.iterdir()) if path.is_dir() and (path / "00-overview.md").exists()]
    if len(packs) != 1:
        raise FileNotFoundError(f"Expected one generated pack under {output_root}, found {len(packs)}.")
    return packs[0]


def write_blocked_status(run_dir: Path, target_dir: Path, mode: str, requested_level: str, validation_path: Path, dependency_path: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            PYTHON,
            str(ROOT / "write_delivery_status.py"),
            "--target-dir",
            str(target_dir),
            "--mode",
            mode,
            "--requested-level",
            requested_level,
            "--validation-report",
            str(validation_path),
            "--dependency-report",
            str(dependency_path),
            "--output",
            str(run_dir / "03-delivery-status.json"),
        ]
    )


def maybe_render_and_export(pack_dir: Path, *, skip_render: bool, skip_pdf: bool) -> None:
    if not skip_render:
        run_command(["bash", str(ROOT / "render_mermaid.sh"), str(pack_dir)], check=False)
    if not skip_pdf:
        run_command(["bash", str(ROOT / "export_pdf.sh"), str(pack_dir)], check=False)


def finalize_status(run_dir: Path, target_dir: Path, mode: str, requested_level: str, validation_path: Path, dependency_path: Path) -> dict:
    run_command(
        [
            PYTHON,
            str(ROOT / "write_delivery_status.py"),
            "--target-dir",
            str(target_dir),
            "--mode",
            mode,
            "--requested-level",
            requested_level,
            "--validation-report",
            str(validation_path),
            "--dependency-report",
            str(dependency_path),
            "--output",
            str(run_dir / "03-delivery-status.json"),
        ]
    )
    return load_json(run_dir / "03-delivery-status.json")


def run_full(args: argparse.Namespace, run_dir: Path) -> int:
    source_input = Path(args.input).resolve()
    intake_path = run_dir / "01-raw-intake.json"
    copy_input(source_input, intake_path)
    intake = load_json(intake_path)
    requested_level = choose_requested_level(args.requested_level, intake, "L4")
    dependency_path = run_dir / "dependency-report.json"
    validation_path = run_dir / "validation-report.json"

    run_command(
        [
            PYTHON,
            str(ROOT / "check_dependencies.py"),
            "--requested-level",
            requested_level,
            "--output",
            str(dependency_path),
        ]
    )

    raw_validation = run_command(
        [
            PYTHON,
            str(ROOT / "validate_manifest.py"),
            "--mode",
            "full-raw",
            "--input",
            str(intake_path),
            "--output",
            str(validation_path),
        ],
        check=False,
    )

    run_command(
        [
            PYTHON,
            str(ROOT / "write_intake_diagnosis.py"),
            "--validation-report",
            str(validation_path),
            "--dependency-report",
            str(dependency_path),
            "--output",
            str(run_dir / "00-intake-diagnosis.md"),
        ]
    )

    if raw_validation.returncode != 0:
        write_blocked_status(run_dir, run_dir / "output" / "blocked-full", "full", requested_level, validation_path, dependency_path)
        return 1

    normalized_path = run_dir / "02-normalized-pack.json"
    normalized_validation_path = run_dir / "normalized-validation.json"
    run_command(
        [
            PYTHON,
            str(ROOT / "normalize_inputs.py"),
            "--input",
            str(intake_path),
            "--output",
            str(normalized_path),
        ]
    )
    normalized_validation = run_command(
        [
            PYTHON,
            str(ROOT / "validate_manifest.py"),
            "--mode",
            "full-normalized",
            "--input",
            str(normalized_path),
            "--output",
            str(normalized_validation_path),
        ],
        check=False,
    )
    if normalized_validation.returncode != 0:
        write_blocked_status(run_dir, run_dir / "output" / "blocked-full", "full", requested_level, normalized_validation_path, dependency_path)
        return 1

    output_root = run_dir / "output"
    run_command(
        [
            PYTHON,
            str(ROOT / "build_pack.py"),
            "--input",
            str(normalized_path),
            "--output-dir",
            str(output_root),
        ]
    )

    pack_dir = find_full_pack_dir(output_root)
    maybe_render_and_export(pack_dir, skip_render=args.skip_render, skip_pdf=args.skip_pdf)
    status = finalize_status(run_dir, pack_dir, "full", requested_level, normalized_validation_path, dependency_path)

    print(f"[OK] Run directory: {run_dir}")
    print(f"[OK] Final status: {status['status']} ({status['achieved_level']})")
    return 0


def run_delta(args: argparse.Namespace, run_dir: Path) -> int:
    if not args.impact_scope:
        raise ValueError("Delta mode requires --impact-scope.")

    source_input = Path(args.input).resolve()
    impact_input = Path(args.impact_scope).resolve()
    change_path = run_dir / "01-change-intake.json"
    impact_path = run_dir / "02-impact-scope.json"
    copy_input(source_input, change_path)
    copy_input(impact_input, impact_path)

    intake = load_json(change_path)
    requested_level = choose_requested_level(args.requested_level, intake, "L2")
    dependency_path = run_dir / "dependency-report.json"
    validation_path = run_dir / "validation-report.json"
    impact_validation_path = run_dir / "impact-validation.json"

    run_command(
        [
            PYTHON,
            str(ROOT / "check_dependencies.py"),
            "--requested-level",
            requested_level,
            "--output",
            str(dependency_path),
        ]
    )

    change_validation = run_command(
        [
            PYTHON,
            str(ROOT / "validate_manifest.py"),
            "--mode",
            "delta-change",
            "--input",
            str(change_path),
            "--output",
            str(validation_path),
        ],
        check=False,
    )

    run_command(
        [
            PYTHON,
            str(ROOT / "write_intake_diagnosis.py"),
            "--validation-report",
            str(validation_path),
            "--dependency-report",
            str(dependency_path),
            "--output",
            str(run_dir / "00-intake-diagnosis.md"),
        ]
    )

    if change_validation.returncode != 0:
        write_blocked_status(run_dir, run_dir / "output" / "delta", "delta", requested_level, validation_path, dependency_path)
        return 1

    impact_validation = run_command(
        [
            PYTHON,
            str(ROOT / "validate_manifest.py"),
            "--mode",
            "delta-impact",
            "--input",
            str(impact_path),
            "--output",
            str(impact_validation_path),
        ],
        check=False,
    )
    if impact_validation.returncode != 0:
        write_blocked_status(run_dir, run_dir / "output" / "delta", "delta", requested_level, impact_validation_path, dependency_path)
        return 1

    delta_dir = run_dir / "output" / "delta"
    run_command(
        [
            PYTHON,
            str(ROOT / "build_delta_pack.py"),
            "--input",
            str(impact_path),
            "--output-dir",
            str(delta_dir),
        ]
    )

    maybe_render_and_export(delta_dir, skip_render=args.skip_render, skip_pdf=args.skip_pdf)
    status = finalize_status(run_dir, delta_dir, "delta", requested_level, impact_validation_path, dependency_path)

    print(f"[OK] Run directory: {run_dir}")
    print(f"[OK] Final status: {status['status']} ({status['achieved_level']})")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["full", "delta"])
    parser.add_argument("--input", required=True, help="Raw intake JSON for full mode, or change-intake JSON for delta mode.")
    parser.add_argument("--impact-scope", help="Delta impact-scope JSON. Required in delta mode.")
    parser.add_argument("--output-root", default=".", help="Directory where the run folder will be created.")
    parser.add_argument("--run-name", help="Optional explicit run folder name.")
    parser.add_argument("--requested-level", help="Optional delivery level override.")
    parser.add_argument("--skip-render", action="store_true", help="Skip Mermaid SVG rendering.")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF export.")
    parser.add_argument("--bootstrap-deps", action="store_true", help="Install stable Mermaid and PDF export dependencies before the run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = prepare_run_dir(output_root, args.run_name, Path(args.input))

    try:
        maybe_bootstrap_dependencies(args.bootstrap_deps)
        if args.mode == "full":
            return run_full(args, run_dir)
        return run_delta(args, run_dir)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
