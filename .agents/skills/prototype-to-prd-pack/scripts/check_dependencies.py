#!/usr/bin/env python3
"""Check local dependencies for Mermaid and PDF export."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
from pathlib import Path


LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def tool(name: str) -> str | None:
    return shutil.which(name)


def platform_key() -> str:
    raw = platform.system().lower()
    if raw == "darwin":
        return "macos"
    if raw == "windows":
        return "windows"
    if raw == "linux":
        return "linux"
    return raw or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requested-level", default="L4")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    mmdc = tool("mmdc")
    npx = tool("npx")
    pandoc = tool("pandoc")
    pdf_engine = next((candidate for candidate in ("wkhtmltopdf", "weasyprint", "prince", "xelatex", "pdflatex") if tool(candidate)), None)
    scripts_dir = Path(__file__).resolve().parent
    reference_guide = scripts_dir.parent / "references" / "dependency-setup.md"
    current_platform = platform_key()
    bootstrap_script = scripts_dir / ("bootstrap_dependencies.ps1" if current_platform == "windows" else "bootstrap_dependencies.sh")
    bootstrap_command = (
        f"powershell -ExecutionPolicy Bypass -File {bootstrap_script}"
        if current_platform == "windows"
        else f"bash {bootstrap_script}"
    )

    if mmdc:
        mermaid_status = "ready"
        mermaid_tool = "mmdc"
        mermaid_note = "Installed Mermaid CLI detected."
    elif npx:
        mermaid_status = "limited"
        mermaid_tool = "npx @mermaid-js/mermaid-cli"
        mermaid_note = "npx fallback available. First run may install CLI and browser dependencies."
    else:
        mermaid_status = "blocked"
        mermaid_tool = ""
        mermaid_note = "No Mermaid renderer detected."

    if pandoc and pdf_engine:
        pdf_status = "ready"
        pdf_tool = f"pandoc + {pdf_engine}"
        pdf_note = "Pandoc and a PDF engine are available."
    elif pandoc:
        pdf_status = "blocked"
        pdf_tool = "pandoc"
        pdf_note = "Pandoc is installed but no supported PDF engine was found."
    else:
        pdf_status = "blocked"
        pdf_tool = ""
        pdf_note = "Pandoc is not installed."

    if mermaid_status == "ready" and pdf_status == "ready":
        max_level = "L4"
    elif mermaid_status == "ready":
        max_level = "L3"
    else:
        max_level = "L2"

    missing_dependencies = []
    limited_dependencies = []
    next_actions = []
    direct_install_supported = True

    if bootstrap_script.exists() and (mermaid_status != "ready" or pdf_status != "ready"):
        next_actions.append(f"Current platform: {current_platform}.")
        next_actions.append(f"Run `{bootstrap_command}` to bootstrap dependencies for this platform.")

    if mermaid_status == "blocked":
        missing_dependencies.append("Mermaid renderer (`mmdc` or `npx`) missing")
        next_actions.append("Install Mermaid CLI (`mmdc`) to enable stable SVG rendering.")
    elif mermaid_status == "limited":
        limited_dependencies.append("SVG rendering depends on first-run npx installation")
        next_actions.append("Install Mermaid CLI (`mmdc`) locally to avoid slow first-run npx fallback.")

    if not pandoc:
        missing_dependencies.append("pandoc missing")
        next_actions.append("Install `pandoc` to enable PDF export.")
    elif not pdf_engine:
        missing_dependencies.append("supported PDF engine missing")
        if current_platform == "windows":
            direct_install_supported = False
            next_actions.append("On Windows, choose a PDF engine path from the guide: MiKTeX (`pdflatex`) or official WeasyPrint / WSL.")
        else:
            next_actions.append("Install a supported PDF engine such as `wkhtmltopdf`, `weasyprint`, `prince`, `xelatex`, or `pdflatex`.")

    if reference_guide.exists():
        next_actions.append(f"Reference guide: `{reference_guide}`")

    report = {
        "platform": current_platform,
        "requested_level": args.requested_level,
        "mermaid_renderer": {
            "status": mermaid_status,
            "tool": mermaid_tool,
            "note": mermaid_note,
        },
        "pdf_export": {
            "status": pdf_status,
            "tool": pdf_tool,
            "note": pdf_note,
        },
        "missing_dependencies": missing_dependencies,
        "limited_dependencies": limited_dependencies,
        "max_level_from_dependencies": max_level,
        "bootstrap_script": str(bootstrap_script),
        "bootstrap_command": bootstrap_command,
        "reference_guide": str(reference_guide),
        "direct_install_supported": direct_install_supported,
        "next_actions": next_actions,
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
