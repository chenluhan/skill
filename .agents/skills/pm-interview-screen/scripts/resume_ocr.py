#!/usr/bin/env python3
"""OCR wrapper for scanned resume PDFs using macOS Vision."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_ocr(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".pdf":
        raise ValueError("OCR wrapper currently supports PDF files only.")

    swift = shutil.which("swift")
    if swift is None:
        raise RuntimeError("Swift is not available; macOS Vision OCR cannot run.")

    script_path = Path(__file__).with_suffix(".swift")
    if not script_path.exists():
        raise RuntimeError(f"Swift OCR backend not found: {script_path}")

    result = subprocess.run(
        [swift, str(script_path), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or "Vision OCR failed."
        raise RuntimeError(message)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid OCR JSON output: {exc}") from exc

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OCR on a scanned resume PDF using macOS Vision.")
    parser.add_argument("path", help="Path to a PDF resume.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    try:
        payload = run_ocr(Path(args.path).expanduser())
    except Exception as exc:
        payload = {
            "engine": "vision",
            "strategy": "ocr",
            "page_count": 0,
            "confidence": 0.0,
            "warnings": [str(exc)],
            "raw_text": "",
            "pages": [],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
        sys.stdout.write("\n")
        return 1

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
