#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install a DESIGN.md from getdesign.md into a project."
    )
    parser.add_argument("slug", help="Catalog slug such as vercel, apple, stripe, or linear.")
    parser.add_argument(
        "--cwd",
        default=".",
        help="Project directory where the DESIGN.md should be created. Defaults to the current directory.",
    )
    parser.add_argument(
        "--out",
        default="DESIGN.md",
        help="Output filename relative to --cwd. Defaults to DESIGN.md.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the destination file if it already exists.",
    )
    return parser.parse_args()


def run_getdesign(slug: str, workdir: Path) -> Path:
    cmd = ["npx", "-y", "getdesign@latest", "add", slug]
    result = subprocess.run(
        cmd,
        cwd=workdir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="")
        raise SystemExit(result.returncode)

    generated = workdir / "DESIGN.md"
    if not generated.exists():
        raise FileNotFoundError(f"Expected file was not created: {generated}")
    return generated


def main() -> int:
    args = parse_args()
    project_dir = Path(args.cwd).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"Project directory not found: {project_dir}", file=sys.stderr)
        return 1

    output_path = (project_dir / args.out).resolve()
    if output_path.exists() and not args.force:
        print(
            f"Destination already exists: {output_path}\nUse --force to overwrite it.",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="design-md-") as tmp:
        tmpdir = Path(tmp)
        generated = run_getdesign(args.slug, tmpdir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(generated, output_path)

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
